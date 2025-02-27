import os
import streamlit as st
import pandas as pd
import bcrypt
from sqlalchemy import create_engine, text

# Load DATABASE_URL from Streamlit Secrets
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    st.error("postgresql://fvs_quoting_db_user:5st51KNF3Urk7HDnEFq72YAuBfTqMY4t@dpg-cuv8nc0gph6c73eojj0g-a.oregon-postgres.render.com/fvs_quoting_db")
    st.stop()

# Connect to PostgreSQL Database
engine = create_engine(DATABASE_URL)
conn = engine.connect()

# Ensure Quotes Table Exists
conn.execute(text("""
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'quotes') THEN 
        CREATE TABLE quotes (
            id SERIAL PRIMARY KEY,
            customer_name TEXT,
            customer_email TEXT,
            part_number TEXT,
            description TEXT,
            quantity INTEGER,
            msrp_total REAL,
            fvs_price_total REAL,
            cost_total REAL,
            labor_cost REAL,
            labor_rate REAL,
            parts_markup REAL
        );
    END IF;
END $$;
"""))
conn.commit()

# Streamlit App Interface
st.title("Frontline Vehicle Solutions - Quoting Tool")

# Customer Information
st.header("Customer Information")
customer_name = st.text_input("Customer Name")
customer_email = st.text_input("Customer Email")

# Quoting System
st.header("Create a Quote")
parts_list = [
    {"Part Number": "100SDU-A", "Description": "SPIRE, SHORT STD, DIECAST", "MSRP": 263, "Cost": 128.87},
    {"Part Number": "200NS-TALL", "Description": "BRANCH GUARD, NIGHTSPIRE", "MSRP": 85, "Cost": 41.65},
    {"Part Number": "210238-S-MP6", "Description": "MASTERPACK, 6PC", "MSRP": 276, "Cost": 135.24},
]
master_data_df = pd.DataFrame(parts_list)

# Select parts
selected_parts = st.multiselect("Select Parts", master_data_df["Part Number"].tolist())
part_quantities = {}

for part in selected_parts:
    qty = st.number_input(f"Quantity for {part}", min_value=1, value=1)
    part_quantities[part] = qty

# Adjustable labor rate and markup
labor_hours = st.number_input("Labor Hours", min_value=0.0, value=0.0, step=0.5)
labor_rate = st.number_input("Labor Rate ($ per hour)", min_value=0.0, value=100.0, step=5.0)
parts_markup = st.number_input("Parts Markup (%)", min_value=0.0, value=15.0, step=1.0)

if st.button("Generate Quote"):
    quote_data = []
    for part, qty in part_quantities.items():
        part_info = master_data_df[master_data_df["Part Number"] == part].iloc[0]
        cost = float(part_info["Cost"]) * qty
        msrp = float(part_info["MSRP"]) * qty
        fvs_price = cost * (1 + parts_markup / 100)
        quote_data.append([part, part_info["Description"], qty, msrp, fvs_price, cost])
    
    labor_cost = labor_hours * labor_rate
    
    # Create DataFrame
    quote_df = pd.DataFrame(quote_data, columns=["Part Number", "Description", "Quantity", "MSRP Total", "FVS Price Total", "Cost Total"])
    quote_df.loc[len(quote_df)] = ["LABOR", "Labor Charges", "-", "-", labor_cost, "-"]
    
    # Save Quote to Database
    for row in quote_data:
        conn.execute(text("""
            INSERT INTO quotes (customer_name, customer_email, part_number, description, quantity, msrp_total, fvs_price_total, cost_total, labor_cost, labor_rate, parts_markup)
            VALUES (:customer_name, :customer_email, :part, :desc, :qty, :msrp, :fvs_price, :cost, :labor_cost, :labor_rate, :parts_markup)
        """), {
            "customer_name": customer_name,
            "customer_email": customer_email,
            "part": row[0],
            "desc": row[1],
            "qty": row[2],
            "msrp": row[3],
            "fvs_price": row[4],
            "cost": row[5],
            "labor_cost": labor_cost,
            "labor_rate": labor_rate,
            "parts_markup": parts_markup
        })
    conn.commit()
    st.success("Quote saved successfully!")
    
    # Display Quote
    st.write("### Quote Summary")
    st.dataframe(quote_df)
