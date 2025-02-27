import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from fpdf import FPDF

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
company_name = st.text_input("Company Name")
address = st.text_area("Company Address")
quote_number = st.text_input("Quote Number", value="Q-1001")
due_date = st.date_input("Valid Until")

# Default values
default_markup = 15.0
default_labor_rate = 100.0

# Adjustable labor rate and markup
parts_markup = st.number_input("Parts Markup (%)", min_value=0.0, value=default_markup, step=1.0)
labor_rate = st.number_input("Labor Rate ($ per hour)", min_value=0.0, value=default_labor_rate, step=5.0)
labor_hours = st.number_input("Labor Hours", min_value=0.0, value=0.0, step=0.5)

# Fetch parts from the database
query = text("SELECT part_number, description, msrp, cost FROM parts")
parts_list = pd.read_sql(query, conn)

# Create table for multiple component selection
st.write("### Add Components to Quote")
quote_items = []

# Editable DataFrame for multiple selections
edited_df = st.data_editor(parts_list, num_rows="dynamic", key="quote_table")

if st.button("Generate Quote"):
    for _, row in edited_df.iterrows():
        if pd.notna(row["part_number"]):
            qty = st.number_input(f"Quantity for {row['part_number']}", min_value=1, value=1, key=row['part_number'])
            msrp_total = row["msrp"] * qty
            cost_total = row["cost"] * qty
            customer_price = cost_total * (1 + parts_markup / 100)
            total_cost_per_build = cost_total
            quote_items.append([row["part_number"], row["description"], row["msrp"], "-", customer_price, qty, msrp_total, row["cost"], total_cost_per_build, labor_hours])
    
    quote_df = pd.DataFrame(quote_items, columns=["Part Number", "Description", "MSRP EA", "MSRP Multiple", "Price EA", "Quantity", "Total", "Cost EA", "Total Cost Per Build", "Labor Hrs Per Part"])
    
    st.success("Quote generated successfully!")
    st.write("### Quote Summary")
    st.dataframe(quote_df)
    
    # PDF Generation
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Quote: {quote_number}", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Company: {company_name}", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Customer: {customer_name}", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Due Date: {due_date}", ln=True, align='C')
    pdf.ln(10)
    
    for index, row in quote_df.iterrows():
        pdf.cell(200, 10, txt=f"{row['Part Number']} - {row['Description']} - Qty: {row['Quantity']} - Price: ${row['Price EA']}", ln=True)
    
    pdf_output_path = "quote.pdf"
    pdf.output(pdf_output_path)
    
    with open(pdf_output_path, "rb") as pdf_file:
        st.download_button("Download Quote PDF", pdf_file, file_name="quote.pdf", mime="application/pdf")

    
