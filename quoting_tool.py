import os
import streamlit as st
import pandas as pd
from fpdf import FPDF

# File uploader to allow users to upload the MASTER PARTS TABLE
st.sidebar.header("Upload MASTER PARTS TABLE")
uploaded_file = st.sidebar.file_uploader("Upload MASTER PARTS TABLE (.xlsx)", type=["xlsx"])

# Define file path
excel_file_path = "/mnt/data/MASTER PARTS TABLE .xlsx"

if uploaded_file is not None:
    with open(excel_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success("File uploaded successfully! Reload the app to apply changes.")

# Load MASTER PARTS TABLE from Excel file
if os.path.exists(excel_file_path):
    try:
        parts_list = pd.read_excel(excel_file_path)
        st.success("Parts data loaded successfully from MASTER PARTS TABLE.")
    except Exception as e:
        st.error(f"Error loading parts table: {e}")
        parts_list = pd.DataFrame(columns=["Part Number", "Description", "MSRP", "Cost"])
else:
    st.error(f"File not found: {excel_file_path}. Please upload the file.")
    parts_list = pd.DataFrame(columns=["Part Number", "Description", "MSRP", "Cost"])

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

# Ensure correct column names
expected_columns = ["Part Number", "Description", "MSRP", "Cost"]
missing_columns = [col for col in expected_columns if col not in parts_list.columns]

if not missing_columns:
    parts_list = parts_list[expected_columns]
else:
    st.error(f"The MASTER PARTS TABLE is missing columns: {missing_columns}. Please check the file format.")
    parts_list = pd.DataFrame(columns=expected_columns)

# Create table for multiple component selection
st.write("### Add Components to Quote")
quote_items = []

# Editable DataFrame for multiple selections
edited_df = st.data_editor(parts_list, num_rows="dynamic", key="quote_table")

if st.button("Generate Quote"):
    for _, row in edited_df.iterrows():
        if pd.notna(row["Part Number"]):
            qty = st.number_input(f"Quantity for {row['Part Number']}", min_value=1, value=1, key=str(row['Part Number']))
            msrp_total = row["MSRP"] * qty if pd.notna(row["MSRP"]) else 0
            cost_total = row["Cost"] * qty if pd.notna(row["Cost"]) else 0
            customer_price = cost_total * (1 + parts_markup / 100) if cost_total > 0 else 0
            total_cost_per_build = cost_total
            quote_items.append([
                row["Part Number"], row["Description"], row["MSRP"], "-", customer_price,
                qty, msrp_total, row["Cost"], total_cost_per_build, labor_hours
            ])
    
    quote_df = pd.DataFrame(quote_items, columns=[
        "Part Number", "Description", "MSRP EA", "MSRP Multiple", "Price EA", 
        "Quantity", "Total", "Cost EA", "Total Cost Per Build", "Labor Hrs Per Part"
    ])
    
    st.success("Quote generated successfully!")
    st.write("### Quote Summary")
    st.dataframe(quote_df)
    
    # PDF Generation
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Quote: {quote_number}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.cell(200, 10, txt=f"Company: {company_name}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.cell(200, 10, txt=f"Due Date: {due_date.strftime('%Y-%m-%d')}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(10)
    
    for index, row in quote_df.iterrows():
        pdf.cell(200, 10, txt=f"{row['Part Number']} - {row['Description']} - Qty: {row['Quantity']} - Price: ${row['Price EA']:.2f}", new_x="LMARGIN", new_y="NEXT")
    
    pdf_output_path = os.path.join("/mnt/data", "quote.pdf")
    pdf.output(pdf_output_path)
    
    with open(pdf_output_path, "rb") as pdf_file:
        st.download_button("Download Quote PDF", pdf_file, file_name="quote.pdf", mime="application/pdf")
