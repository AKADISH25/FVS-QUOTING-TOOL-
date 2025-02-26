import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import bcrypt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Database Connection (PostgreSQL on Render)
DATABASE_URL = "your_database_url"  # Replace with your actual database URL from Render
engine = create_engine(DATABASE_URL)
conn = engine.connect()

# Email Configuration
SMTP_SERVER = "smtp.example.com"
SMTP_PORT = 587
SENDER_EMAIL = "your-email@example.com"
SENDER_PASSWORD = "your-email-password"

# User Authentication Setup
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# Ensure Tables Exist
conn.execute(text("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
"""))

conn.execute(text("""
CREATE TABLE IF NOT EXISTS quotes (
    id SERIAL PRIMARY KEY,
    part_number TEXT,
    description TEXT,
    quantity INTEGER,
    msrp_total REAL,
    fvs_price_total REAL,
    labor_cost REAL,
    email TEXT
)
"""))

# Add Admin User
admin_username = "admin"
admin_password = "admin123"  # Change this before deployment!
hashed_password = hash_password(admin_password)

conn.execute(text("""
INSERT INTO users (username, password, role)
VALUES (:username, :password, 'admin')
ON CONFLICT (username) DO NOTHING
"""), {"username": admin_username, "password": hashed_password})

# Streamlit App
st.title("Frontline Vehicle Solutions Quoting Tool")

# Login Form
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.sidebar.header("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    
    if st.sidebar.button("Login"):
        result = conn.execute(text("SELECT * FROM users WHERE username = :username"), {"username": username}).fetchone()
        if result and verify_password(password, result[2]):
            st.session_state["logged_in"] = True
            st.session_state["role"] = result[3]
            st.session_state["username"] = username
            st.experimental_rerun()
        else:
            st.sidebar.error("Invalid credentials")

if st.session_state["logged_in"]:
    st.sidebar.header(f"Welcome, {st.session_state['username']}")

    # Load Master Data (Replace with actual part data)
    master_data = [
        {"Part Number": "100SDU-A", "Description": "SPIRE, SHORT STD, DIECAST", "MSRP": 263, "Cost": 128.87},
        {"Part Number": "200NS-TALL", "Description": "BRANCH GUARD, NIGHTSPIRE", "MSRP": 85, "Cost": 41.65},
        {"Part Number": "210238-S-MP6", "Description": "MASTERPACK, 6PC", "MSRP": 276, "Cost": 135.24},
    ]
    master_data_df = pd.DataFrame(master_data)

    # Quoting System
    st.header("Create a Quote")
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

        # Save Quote to Database
        for row in quote_data:
            conn.execute(text("""
                INSERT INTO quotes (part_number, description, quantity, msrp_total, fvs_price_total, labor_cost, email)
                VALUES (:part, :desc, :qty, :msrp, :fvs_price, :labor_cost, :email)
            """), {"part": row[0], "desc": row[1], "qty": row[2], "msrp": row[3], "fvs_price": row[4], "labor_cost": labor_cost, "email": customer_email})

        st.success("Quote saved successfully!")

    # Admin Dashboard
    if st.session_state["role"] == "admin":
        st.sidebar.subheader("Admin Panel")

        if st.sidebar.button("View Quotes"):
            quotes = conn.execute(text("SELECT * FROM quotes")).fetchall()
            st.write(pd.DataFrame(quotes, columns=["ID", "Part", "Description", "Quantity", "MSRP", "FVS Price", "Labor Cost", "Email"]))

        if st.sidebar.button("Manage Users"):
            users = conn.execute(text("SELECT * FROM users")).fetchall()
            st.write(pd.DataFrame(users, columns=["ID", "Username", "Password (hashed)", "Role"]))

    # Send Email Quote
    if st.button("Send Quote via Email"):
        if customer_email:
            msg = MIMEMultipart()
            msg["From"] = SENDER_EMAIL
            msg["To"] = customer_email
            msg["Subject"] = "Your Quote from Frontline Vehicle Solutions"

            body = "Please find attached your requested quote."
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.sendmail(SENDER_EMAIL, customer_email, msg.as_string())

            st.success(f"Quote sent to {customer_email}!")
        else:
            st.error("Please enter a valid email address.")
