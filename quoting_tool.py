import os
import streamlit as st
import pandas as pd
import bcrypt
from sqlalchemy import create_engine, text

# 🔹 Load DATABASE_URL from Streamlit Secrets
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    st.error("postgresql://fvs_quoting_db_user:5st51KNF3Urk7HDnEFq72YAuBfTqMY4t@dpg-cuv8nc0gph6c73eojj0g-a.oregon-postgres.render.com/fvs_quoting_db")
    st.stop()

# 🔹 Connect to PostgreSQL Database
engine = create_engine(DATABASE_URL)
conn = engine.connect()

# 🔹 Ensure Users Table Exists Without Duplicates
conn.execute(text("""
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'users') THEN 
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        );
    END IF;
END $$;
"""))
conn.commit()

# 🔹 Ensure Quotes Table Exists Without Duplicates
conn.execute(text("""
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'quotes') THEN 
        CREATE TABLE quotes (
            id SERIAL PRIMARY KEY,
            part_number TEXT,
            description TEXT,
            quantity INTEGER,
            msrp_total REAL,
            fvs_price_total REAL,
            labor_cost REAL,
            email TEXT
        );
    END IF;
END $$;
"""))
conn.commit()

# 🔹 Ensure Admin User Exists
admin_username = "admin"
admin_password = "admin123"
hashed_password = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt()).decode()

conn.execute(text("""
INSERT INTO users (username, password, role)
VALUES (:username, :password, 'admin')
ON CONFLICT (username) DO NOTHING
"""), {"username": admin_username, "password": hashed_password})
conn.commit()

# 🔹 Verify Login Credentials
def verify_login(username, password):
    result = conn.execute(text("SELECT password FROM users WHERE username = :username"), {"username": username}).fetchone()
    if result and bcrypt.checkpw(password.encode(), result[0].encode()):
        return True
    return False

# 🔹 Streamlit App Interface
st.title("Frontline Vehicle Solutions - Quoting Tool")

# 🔹 Login Form
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.sidebar.header("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    
    if st.sidebar.button("Login"):
        if verify_login(username, password):
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.sidebar.success("Login Successful!")
            st.rerun()
        else:
            st.sidebar.error("Invalid credentials. Please try again.")

# 🔹 Main App (After Login)
if st.session_state["logged_in"]:
    st.sidebar.header(f"Welcome, {st.session_state['username']}")

    # 🔹 Quoting System
    st.header("Create a Quote")
    parts_list = [
        {"Part Number": "100SDU-A", "Description": "SPIRE, SHORT STD, DIECAST", "MSRP": 263, "Cost": 128.87},
        {"Part Number": "200NS-TALL", "Description": "BRANCH GUARD, NIGHTSPIRE", "MSRP": 85, "Cost": 41.65},
        {"Part Number": "210238-S-MP6", "Description": "MASTERPACK, 6PC", "MSRP": 276, "Cost": 135.24},
    ]
    master_data_df = pd.DataFrame(parts_list)

    selected_parts = st.multiselect("Select Parts", master_data_df["Part Number"].tolist())
    part_quantities = {}

    for part in selected_parts:
        qty = st.number_input(f"Quantity for {part}", min_value=1, value=1)
        part_quantities[part] = qty

    labor_hours = st.number_input("Labor Hours", min_value=0.0, value=0.0, step=0.5)
    customer_email = st.text_input("Customer Email")

    if st.button("Generate Quote"):
        quote_data = []
        for part, qty in part_quantities.items():
            part_info = master_data_df[master_data_df["Part Number"] == part].iloc[0]
            cost = float(part_info["Cost"]) * qty
            msrp = float(part_info["MSRP"]) * qty
            fvs_price = cost * 1.15  # 15% markup
            quote_data.append([part, part_info["Description"], qty, msrp, fvs_price])

        labor_cost = labor_hours * 100  # Assuming $100 per labor hour
        quote_df = pd.DataFrame(quote_data, columns=["Part Number", "Description", "Quantity", "MSRP Total", "FVS Price Total"])
        quote_df.loc[len(quote_df)] = ["LABOR", "Labor Charges", "-", "-", labor_cost]

        # 🔹 Save Quote to Database
        for row in quote_data:
            conn.execute(text("""
                INSERT INTO quotes (part_number, description, quantity, msrp_total, fvs_price_total, labor_cost, email)
                VALUES (:part, :desc, :qty, :msrp, :fvs_price, :labor_cost, :email)
            """), {"part": row[0], "desc": row[1], "qty": row[2], "msrp": row[3], "fvs_price": row[4], "labor_cost": labor_cost, "email": customer_email})
        conn.commit()
        st.success("Quote saved successfully!")
