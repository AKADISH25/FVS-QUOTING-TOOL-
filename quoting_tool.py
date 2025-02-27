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

# Streamlit App Interface
st.title("Frontline Vehicle Solutions - Quoting Tool")

# Customer Information
st.header("Customer Information")
customer_name = st.text_input("Customer Name")
customer_email = st.text_input("Customer Email")

# Default values from Internal Worksheet
default_markup = 15.0  # Markup percentage
default_labor_rate = 100.0  # Labor rate per hour

# Adjustable labor rate and markup
parts_markup = st.number_input("Parts Markup (%)", min_value=0.0, value=default_markup, step=1.0)
labor_rate = st.number_input("Labor Rate ($ per hour)", min_value=0.0, value=default_labor_rate, step=5.0)
labor_hours = st.number_input("Labor Hours", min_value=0.0, value=0.0, step=0.5)

# Quoting System
st.header("Select Components")
parts_list = [
    {"Part Number": "100SDU-A", "Description": "SPIRE, SHORT STD, DIECAST", "MSRP EA": 263, "Cost EA": 128.87},
    {"Part Number": "200NS-TALL", "Description": "BRANCH GUARD, NIGHTSPIRE", "MSRP EA": 85, "Cost EA": 41.65},
    {"Part Number": "210238-S-MP6", "Description": "MASTERPACK, 6PC", "MSRP EA": 276, "Cost EA": 135.24},
]
master_data_df = pd.DataFrame(parts_list)

selected_parts = st.multiselect("Select Parts", master_data_df["Part Number"].tolist())
part_quantities = {}

for part in selected_parts:
    qty = st.number_input(f"Quantity for {part}", min_value=1, value=1)
    part_quantities[part] = qty

if st.button("Generate Quote"):
    quote_data = []
    for part, qty in part_quantities.items():
        part_info = master_data_df[master_data_df["Part Number"] == part].iloc[0]
        msrp_total = float(part_info["MSRP EA"]) * qty
        cost_total = float(part_info["Cost EA"]) * qty
        customer_price = cost_total * (1 + parts_markup / 100)
        total_cost_per_build = cost_total
        labor_cost = labor_hours * labor_rate
        quote_data.append([part, part_info["Description"], part_info["MSRP EA"], "-", customer_price, qty, "-", part_info["Cost EA"], total_cost_per_build, labor_hours])
    
    # Create DataFrame
    quote_df = pd.DataFrame(quote_data, columns=["Part Number", "Description", "MSRP EA", "MSRP Multiple", "Price EA", "Quantity", "Total", "Cost EA", "Total Cost Per Build", "Labor Hrs Per Part"])
    
    st.success("Quote generated successfully!")
    
    # Display Quote
    st.write("### Quote Summary")
    st.dataframe(quote_df)
