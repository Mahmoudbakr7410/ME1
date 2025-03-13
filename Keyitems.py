import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import json
import time
import uuid
import numpy as np

# Constants
PLANNING_MATERIALITY = "Planning Materiality"
TOLERABLE_ERROR = "Tolerable Error (50% or 75% of Planning Materiality)"
AUDIT_DIFFERENCES = "Sum of Audit Differences (5% of Planning Materiality)"
CONTROL_APPROACH = "Control Approach (Reliance or No Reliance)"
ACCOUNT_TYPE = "Account Type (Asset/Income or Liability/Expense)"
INHERENT_RISK = "Inherent Risk Level (Low or High)"
COMBINED_RISK = "Combined Risk Level"
ASSURANCE_LEVEL = "Assurance Level from Other Procedures (Little, Some, Medium, Persuasive)"
SAMPLING_APPROACH = "Sampling Approach (MUS or Attribute Sampling)"
AUDIT_TYPE = "Audit Type (Full Year or Interim)"
MONTHS_TESTED = "Number of Months Being Tested"

# Google Drive API Setup
SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_ID = "1UK_F280M9tNVW9_amB27VHOUMEPCf6ze"  # Your Google Drive folder ID

def authenticate_google_drive():
    """Authenticate and return the Google Drive service."""
    try:
        # Load the JSON from Streamlit Secrets
        service_account_info = json.loads(st.secrets["google_credentials"]["service_account_json"])
        creds = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES
        )
        service = build("drive", "v3", credentials=creds)
        return service
    except Exception as e:
        st.error(f"Failed to authenticate Google Drive: {e}")
        return None

def upload_to_google_drive(file_path, folder_id=FOLDER_ID):
    """Upload a file to Google Drive."""
    service = authenticate_google_drive()
    if not service:
        return None

    try:
        file_metadata = {"name": os.path.basename(file_path), "parents": [folder_id]}
        media = MediaFileUpload(file_path, resumable=True)
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        return file.get("id")
    except Exception as e:
        st.error(f"Failed to upload file to Google Drive: {e}")
        return None

# Phase 1: Key Items Selection
def calculate_tolerable_error(planning_materiality, tolerable_error_percentage):
    return planning_materiality * (tolerable_error_percentage / 100)

def get_testing_threshold_percentage(control_approach, account_type, inherent_risk):
    if control_approach == "Reliance":
        if inherent_risk == "Low":
            return (75, 100) if account_type == "Asset/Income" else (25, 50)
        else:
            return (50, 75) if account_type == "Asset/Income" else (15, 25)
    else:
        if inherent_risk == "Low":
            return (25, 50) if account_type == "Asset/Income" else (10, 15)
        else:
            return (10, 25) if account_type == "Asset/Income" else (5, 10)

def calculate_key_items_threshold(tolerable_error, percentage_range):
    st.write(f"**Recommended TE Range:** {percentage_range[0]}% to {percentage_range[1]}%")
    selected_percentage = st.number_input(
        "Enter a specific testing threshold percentage within the range:",
        min_value=float(percentage_range[0]),
        max_value=float(percentage_range[1]),
        value=float(percentage_range[0]),  # Default to lower bound
        step=0.1
    )
    
    # Check if the selected point is skewed toward the higher end of the range
    range_midpoint = (percentage_range[0] + percentage_range[1]) / 2
    if selected_percentage > range_midpoint:
        st.warning("You have selected a testing threshold percentage skewed toward the higher end of the range.")
        rationale = st.text_area(
            "Provide a rationale for choosing a higher testing threshold percentage:",
            placeholder="Explain why you chose a higher percentage..."
        )
        if not rationale:
            st.error("Please provide a rationale for audit documentation.")
            return None, None
        return tolerable_error * (selected_percentage / 100), rationale
    return tolerable_error * (selected_percentage / 100), None

def calculate_coverage_ratio(key_items_sum, total_population_value):
    return (key_items_sum / total_population_value) * 100

# Phase 2: Sample Size Determination
def determine_cra(control_approach, inherent_risk):
    if control_approach == "Reliance":
        if inherent_risk == "Low":
            return "Minimal CRA"
        else:
            return "Low CRA"
    else:
        if inherent_risk == "Low":
            return "Moderate CRA"
        else:
            return "High CRA"

def get_coverage_matrix_multiplier(cra_level, assurance_level, coverage_ratio):
    coverage_matrix = {
        "Minimal CRA": {
            "Little": {0: 0.5, 10: 0.4, 30: 0.1},
            "Some": {0: 0.2, 10: 0.1},
            "Medium": {0: "*", 10: "*", 30: "*", 50: "*", 70: "*", 90: "*", 100: "*"},
            "Persuasive": {0: "*", 10: "*", 30: "*", 50: "*", 70: "*", 90: "*", 100: "*"}
        },
        "Low CRA": {
            "Little": {0: 1.0, 10: 0.9, 30: 0.7, 50: 0.3},
            "Some": {0: 0.7, 10: 0.6, 30: 0.4},
            "Medium": {0: 0.3, 10: 0.2},
            "Persuasive": {0: "*", 10: "*", 30: "*", 50: "*", 70: "*", 90: "*", 100: "*"}
        },
        "Moderate CRA": {
            "Little": {0: 2.1, 10: 2.0, 30: 1.7, 50: 1.4, 70: 0.9},
            "Some": {0: 1.8, 10: 1.7, 30: 1.4, 50: 1.1, 70: 0.7},
            "Medium": {0: 1.4, 10: 1.3, 30: 1.0, 50: 0.7, 70: 0.2},
            "Persuasive": {0: "*", 10: "*", 30: "*", 50: "*", 70: "*", 90: "*", 100: "*"}
        },
        "High CRA": {
            "Little": {0: 2.6, 10: 2.5, 30: 2.3, 50: 1.9, 70: 1.4, 90: 0.3},
            "Some": {0: 2.4, 10: 2.2, 30: 2.0, 50: 1.7, 70: 1.1},
            "Medium": {0: 1.9, 10: 1.8, 30: 1.6, 50: 1.3, 70: 0.8},
            "Persuasive": {0: "*", 10: "*", 30: "*", 50: "*", 70: "*", 90: "*", 100: "*"}
        }
    }
    closest_ratio = min(coverage_matrix[cra_level][assurance_level].keys(), key=lambda x: abs(x - coverage_ratio))
    return coverage_matrix[cra_level][assurance_level][closest_ratio]

def calculate_sample_size(number_of_key_items, multiplier, population_size, tolerable_error):
    if multiplier == "*" or multiplier == 0:
        return number_of_key_items  # Keep key items as is
    basic_sample_size = (population_size - number_of_key_items) / tolerable_error
    return number_of_key_items + int(basic_sample_size * multiplier)

def calculate_additional_sample_size(population_data, account_nature, sample_size):
    """Calculate additional 10% sample size for the other side (non-natural side)."""
    if account_nature == "Debit":
        other_side_data = population_data[population_data["Negative Testing"] == "Credit"]
    else:
        other_side_data = population_data[population_data["Negative Testing"] == "Debit"]
    
    additional_sample_size = max(1, int(sample_size * 0.1))  # Minimum of 1
    if len(other_side_data) < additional_sample_size:
        additional_sample_size = len(other_side_data)  # Adjust if population is smaller
    return other_side_data.sample(n=additional_sample_size, random_state=42)

# Export to PDF and Excel
def export_to_pdf_and_excel(key_items, sample_size, additional_sample, coverage_ratio, cra_level, assurance_level, company_name, audited_year, user_name, computer_id, population_size, population_value, rationale, multiplier, remaining_population_samples):
    # Generate PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt="Audit Sampling Report", ln=True, align="C")
    pdf.ln(10)
    
    pdf.cell(200, 10, txt=f"Company Name: {company_name}", ln=True)
    pdf.cell(200, 10, txt=f"Audited Year: {audited_year}", ln=True)
    pdf.cell(200, 10, txt=f"Combined Risk Assessment (CRA): {cra_level}", ln=True)
    pdf.cell(200, 10, txt=f"Assurance Level: {assurance_level}", ln=True)
    pdf.cell(200, 10, txt=f"Coverage Ratio: {coverage_ratio:.2f}%", ln=True)
    pdf.cell(200, 10, txt=f"Multiplier: {multiplier}", ln=True)
    pdf.cell(200, 10, txt=f"Sample Size: {sample_size}", ln=True)
    pdf.cell(200, 10, txt=f"Additional Sample Size (Negative Testing): {len(additional_sample)}", ln=True)
    pdf.cell(200, 10, txt=f"Remaining Population Sample Size: {len(remaining_population_samples)}", ln=True)
    pdf.cell(200, 10, txt=f"User Name: {user_name}", ln=True)
    pdf.cell(200, 10, txt=f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.cell(200, 10, txt=f"Computer ID: {computer_id}", ln=True)
    pdf.cell(200, 10, txt=f"Population Size: {population_size:,}", ln=True)  # Format with commas
    pdf.cell(200, 10, txt=f"Population Value: {population_value:,}", ln=True)  # Format with commas
    pdf.cell(200, 10, txt=f"Rationale: {rationale}", ln=True)
    pdf.ln(10)
    
    # Key Items
    pdf.cell(200, 10, txt="Key Items (Above TE Threshold):", ln=True)
    for index, row in key_items.iterrows():
        pdf.cell(200, 10, txt=f"{row['Item Number']} - {row['Item Value']}", ln=True)
    
    # Additional Sample (Negative Testing)
    pdf.cell(200, 10, txt="Additional Sample (Negative Testing):", ln=True)
    for index, row in additional_sample.iterrows():
        pdf.cell(200, 10, txt=f"{row['Item Number']} - {row['Item Value']}", ln=True)
    
    # Remaining Population Samples (Added due to Multiplier)
    pdf.cell(200, 10, txt="Remaining Population Samples (Added due to Multiplier):", ln=True)
    for index, row in remaining_population_samples.iterrows():
        pdf.cell(200, 10, txt=f"{row['Item Number']} - {row['Item Value']}", ln=True)
    
    # Save PDF to a temporary file
    pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(pdf_file.name)
    
    # Generate Excel
    excel_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    with pd.ExcelWriter(excel_file.name) as writer:
        # Key Items Sheet
        key_items.to_excel(writer, sheet_name="Key Items", index=False)
        
        # Additional Sample Sheet
        additional_sample.to_excel(writer, sheet_name="Negative Testing", index=False)
        
        # Remaining Population Samples Sheet
        remaining_population_samples.to_excel(writer, sheet_name="Remaining Population Samples", index=False)
        
        # Summary Sheet
        summary_data = {
            "Company Name": [company_name],
            "Audited Year": [audited_year],
            "Coverage Ratio": [coverage_ratio],
            "Multiplier": [multiplier],
            "Sample Size": [sample_size],
            "Additional Sample Size": [len(additional_sample)],
            "Remaining Population Sample Size": [len(remaining_population_samples)],
            "User Name": [user_name],
            "Date": [time.strftime('%Y-%m-%d %H:%M:%S')],
            "Computer ID": [computer_id],
            "Population Size": [population_size],
            "Population Value": [population_value],
            "Rationale": [rationale]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Summary", index=False)
    
    return pdf_file.name, excel_file.name

# Streamlit App
def main():
    st.title("Audit Sampling Software")
    st.sidebar.header("User Inputs")

    # Company Name and Audited Year
    company_name = st.sidebar.text_input("Company Name")
    audited_year = st.sidebar.text_input("Audited Year")

    # Phase 1: Key Items Selection
    st.header("Phase 1: Key Items Selection")
    planning_materiality = st.sidebar.number_input(PLANNING_MATERIALITY, min_value=0.0)
    tolerable_error_percentage = st.sidebar.selectbox(TOLERABLE_ERROR, [50, 75])
    control_approach = st.sidebar.selectbox(CONTROL_APPROACH, ["Reliance", "No Reliance"])
    account_type = st.sidebar.selectbox(ACCOUNT_TYPE, ["Asset/Income", "Liability/Expense"])
    inherent_risk = st.sidebar.selectbox(INHERENT_RISK, ["Low", "High"])

    # Debit/Credit Account Nature
    account_nature = st.sidebar.selectbox("Is this a Debit or Credit account?", ["Debit", "Credit"])

    # Sampling Approach
    sampling_approach = st.sidebar.selectbox(SAMPLING_APPROACH, ["MUS", "Attribute Sampling"])

    if sampling_approach == "MUS":
        audit_type = st.sidebar.selectbox(AUDIT_TYPE, ["Full Year", "Interim"])
        if audit_type == "Interim":
            months_tested = st.sidebar.number_input(MONTHS_TESTED, min_value=1, max_value=12, value=6)
    else:
        sample_size = st.sidebar.number_input("Enter Sample Size for Attribute Sampling", min_value=1, value=30)

    # Upload CSV for Key Items
    uploaded_file = st.file_uploader("Upload Population Data (CSV)", type=["csv"])
    if uploaded_file:
        population_data = pd.read_csv(uploaded_file)
        st.write("Uploaded Data Preview:")
        st.write(population_data.head())

        # Column Mapping
        st.subheader("Map Columns")
        columns = population_data.columns.tolist()
        item_number_col = st.selectbox("Select Column for Item Number", columns, index=0)
        item_value_col = st.selectbox("Select Column for Item Value", columns, index=1)
        description_col = st.selectbox("Select Column for Description (Optional)", [None] + columns, index=0)
        date_col = st.selectbox("Select Column for Date (Optional)", [None] + columns, index=0)
        currency_col = st.selectbox("Select Column for Currency (Optional)", [None] + columns, index=0)
        account_number_col = st.selectbox("Select Column for Account Number (Optional)", [None] + columns, index=0)
        negative_testing_col = st.selectbox("Select Column for Negative Testing (Optional)", [None] + columns, index=0)

        # Validate mandatory columns
        if not item_number_col or not item_value_col:
            st.error("Item Number and Item Value are mandatory fields. Please map them correctly.")
        else:
            # Rename columns for consistency
            rename_dict = {
                item_number_col: "Item Number",
                item_value_col: "Item Value"
            }
            if description_col:
                rename_dict[description_col] = "Description"
            if date_col:
                rename_dict[date_col] = "Date"
            if currency_col:
                rename_dict[currency_col] = "Currency"
            if account_number_col:
                rename_dict[account_number_col] = "Account Number"
            if negative_testing_col:
                rename_dict[negative_testing_col] = "Negative Testing"

            population_data.rename(columns=rename_dict, inplace=True)

            # Keep only mapped columns
            keep_columns = ["Item Number", "Item Value"]
            if description_col:
                keep_columns.append("Description")
            if date_col:
                keep_columns.append("Date")
            if currency_col:
                keep_columns.append("Currency")
            if account_number_col:
                keep_columns.append("Account Number")
            if negative_testing_col:
                keep_columns.append("Negative Testing")

            population_data = population_data[keep_columns]

            # Convert "Item Value" to numeric, handling errors
            population_data["Item Value"] = pd.to_numeric(population_data["Item Value"], errors="coerce")

            # Drop rows with invalid "Item Value" (e.g., non-numeric values)
            if population_data["Item Value"].isnull().any():
                st.warning("Some rows have invalid 'Item Value' and will be dropped.")
                population_data = population_data.dropna(subset=["Item Value"])

            st.write("Mapped Data Preview:")
            st.write(population_data.head())

            # Calculate Total Population Value (sum of Item Value)
            total_population_value = population_data["Item Value"].sum()
            population_size = len(population_data)
            st.sidebar.write(f"**Total Population Value (Auto-calculated):** {total_population_value:,.2f}")  # Format with commas
            st.sidebar.write(f"**Population Size (Auto-calculated):** {population_size:,}")  # Format with commas

            # Calculate Tolerable Error
            tolerable_error = calculate_tolerable_error(planning_materiality, tolerable_error_percentage)
            st.write(f"Tolerable Error: {tolerable_error:,.2f}")  # Format with commas

            # Determine Testing Threshold Percentage Range
            percentage_range = get_testing_threshold_percentage(control_approach, account_type, inherent_risk)
            
            # Calculate Key Items Threshold
            key_items_threshold, rationale = calculate_key_items_threshold(tolerable_error, percentage_range)
            if key_items_threshold is None:
                return  # Stop execution if no rationale is provided for a higher percentage

            # Identify Key Items
            key_items = population_data[population_data["Item Value"] >= key_items_threshold]
            st.write("Key Items:")
            st.write(key_items)

            # Calculate Coverage Ratio
            key_items_sum = key_items["Item Value"].sum()
            coverage_ratio = calculate_coverage_ratio(key_items_sum, total_population_value)
            st.write(f"Coverage Ratio: {coverage_ratio:.2f}%")

            # Phase 2: Sample Size Determination
            st.header("Phase 2: Sample Size Determination")
            assurance_level = st.selectbox(ASSURANCE_LEVEL, ["Little", "Some", "Medium", "Persuasive"])

            # Determine CRA based on control approach and inherent risk
            cra_level = determine_cra(control_approach, inherent_risk)
            st.write(f"Combined Risk Assessment (CRA): {cra_level}")

            # Get Multiplier from Coverage Matrix
            multiplier = get_coverage_matrix_multiplier(cra_level, assurance_level, coverage_ratio)

            # Calculate Sample Size
            if sampling_approach == "MUS":
                if audit_type == "Full Year":
                    number_of_key_items = len(key_items)
                    sample_size = calculate_sample_size(number_of_key_items, multiplier, population_size, tolerable_error)
                else:
                    # Prorate sample size based on months tested
                    number_of_key_items = len(key_items)
                    sample_size = calculate_sample_size(number_of_key_items, multiplier, population_size, tolerable_error)
                    sample_size = int(sample_size * (months_tested / 12))
            else:
                # Attribute Sampling: Use user-provided sample size
                sample_size = sample_size

            st.write(f"Final Sample Size: {sample_size:,}")  # Format with commas

            # Calculate Additional Sample Size for Negative Testing
            if negative_testing_col:
                additional_sample = calculate_additional_sample_size(population_data, account_nature, sample_size)
                st.write("Additional Sample (Negative Testing):")
                st.write(additional_sample)
            else:
                additional_sample = pd.DataFrame()  # Empty DataFrame if no negative testing column

            # Identify remaining population after key items are selected
            remaining_population = population_data[~population_data["Item Number"].isin(key_items["Item Number"])]
            
            # Calculate the number of additional samples based on the multiplier
            additional_sample_size = int(len(key_items) * multiplier)
            
            # Stratify the remaining population and select samples
            remaining_population_samples = remaining_population.sample(n=min(additional_sample_size, len(remaining_population)), random_state=42)
            st.write("Remaining Population Samples (Added due to Multiplier):")
            st.write(remaining_population_samples)

            # Run Sampling Button
            if st.button("Run Sampling"):
                with st.spinner("Please wait maham KI selector..."):
                    # Simulate processing time (optional)
                    time.sleep(2)  # Simulate a 2-second delay

                    # Set a flag to indicate sampling is complete
                    st.session_state.sampling_complete = True

            # Export Options (only show if sampling is complete)
            if st.session_state.get("sampling_complete", False):
                st.header("Export Results")
                if st.button("Export to PDF and Excel"):
                    # Try to get the username, or use a placeholder if it fails
                    try:
                        user_name = os.getlogin()
                    except OSError:
                        user_name = "Unknown User"  # Placeholder if username cannot be retrieved
                    
                    computer_id = str(uuid.getnode())
                    pdf_file, excel_file = export_to_pdf_and_excel(
                        key_items, sample_size, additional_sample, coverage_ratio, cra_level, assurance_level,
                        company_name, audited_year, user_name, computer_id, population_size,
                        total_population_value, rationale, multiplier, remaining_population_samples
                    )
                    
                    # Download PDF
                    with open(pdf_file, "rb") as f:
                        st.download_button("Download PDF", f, file_name=f"{company_name}_audit_sampling_report.pdf")
                    
                    # Download Excel
                    with open(excel_file, "rb") as f:
                        st.download_button("Download Excel", f, file_name=f"{company_name}_audit_sampling_report.xlsx")
                    
                    # Upload to Google Drive
                    pdf_file_id = upload_to_google_drive(pdf_file)
                    excel_file_id = upload_to_google_drive(excel_file)
                    if pdf_file_id and excel_file_id:
                        st.success(f"Files uploaded to Google Drive with IDs: PDF - {pdf_file_id}, Excel - {excel_file_id}")
                    else:
                        st.error("Failed to upload files to Google Drive.")
                    
                    # Clean up temporary files
                    os.remove(pdf_file)
                    os.remove(excel_file)

if __name__ == "__main__":
    main()
