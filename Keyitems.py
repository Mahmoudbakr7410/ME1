import streamlit as st
import pandas as pd
from fpdf import FPDF  # For PDF export
import tempfile
import os

# Constants
PLANNING_MATERIALITY = "Planning Materiality"
TOLERABLE_ERROR = "Tolerable Error (50% or 75% of Planning Materiality)"
AUDIT_DIFFERENCES = "Sum of Audit Differences (5% of Planning Materiality)"
CONTROL_APPROACH = "Control Approach (Reliance or No Reliance)"
ACCOUNT_TYPE = "Account Type (Asset/Income or Liability/Expense)"
INHERENT_RISK = "Inherent Risk Level (Low or High)"
COMBINED_RISK = "Combined Risk Level"
ASSURANCE_LEVEL = "Assurance Level from Other Procedures (Little, Some, Medium, Persuasive)"

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
    st.write(f"Testing Threshold Percentage Range: {percentage_range[0]}% to {percentage_range[1]}%")
    
    # Let the user input a specific point within the range
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
            return None
    
    return tolerable_error * (selected_percentage / 100)

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
    # Define the coverage matrix
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

    # Find the closest coverage ratio in the matrix
    closest_ratio = min(coverage_matrix[cra_level][assurance_level].keys(), key=lambda x: abs(x - coverage_ratio))
    return coverage_matrix[cra_level][assurance_level][closest_ratio]

def calculate_sample_size(number_of_key_items, multiplier):
    if multiplier == "*":
        return 0  # No sampling required
    return int(number_of_key_items * multiplier)

# Export to PDF
def export_to_pdf(key_items, sample_size, coverage_ratio, cra_level, assurance_level):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt="Audit Sampling Report", ln=True, align="C")
    pdf.ln(10)
    
    pdf.cell(200, 10, txt=f"Combined Risk Assessment (CRA): {cra_level}", ln=True)
    pdf.cell(200, 10, txt=f"Assurance Level: {assurance_level}", ln=True)
    pdf.cell(200, 10, txt=f"Coverage Ratio: {coverage_ratio:.2f}%", ln=True)
    pdf.cell(200, 10, txt=f"Sample Size: {sample_size}", ln=True)
    pdf.ln(10)
    
    pdf.cell(200, 10, txt="Key Items:", ln=True)
    for index, row in key_items.iterrows():
        pdf.cell(200, 10, txt=f"{row['Item Number']} - {row['Item Value']}", ln=True)
    
    # Save to a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    return temp_file.name

# Export to Excel
def export_to_excel(key_items, sample_size, coverage_ratio, cra_level, assurance_level):
    output = pd.DataFrame({
        "CRA Level": [cra_level],
        "Assurance Level": [assurance_level],
        "Coverage Ratio": [coverage_ratio],
        "Sample Size": [sample_size]
    })
    key_items_sheet = key_items.copy()
    
    # Save to a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    with pd.ExcelWriter(temp_file.name) as writer:
        output.to_excel(writer, sheet_name="Summary", index=False)
        key_items_sheet.to_excel(writer, sheet_name="Key Items", index=False)
    return temp_file.name

# Streamlit App
def main():
    st.title("Audit Sampling Software")
    st.sidebar.header("User Inputs")

    # Phase 1: Key Items Selection
    st.header("Phase 1: Key Items Selection")
    planning_materiality = st.sidebar.number_input(PLANNING_MATERIALITY, min_value=0.0)
    tolerable_error_percentage = st.sidebar.selectbox(TOLERABLE_ERROR, [50, 75])
    control_approach = st.sidebar.selectbox(CONTROL_APPROACH, ["Reliance", "No Reliance"])
    account_type = st.sidebar.selectbox(ACCOUNT_TYPE, ["Asset/Income", "Liability/Expense"])
    inherent_risk = st.sidebar.selectbox(INHERENT_RISK, ["Low", "High"])
    total_population_value = st.sidebar.number_input("Total Population Value", min_value=0.0)

    # Calculate Tolerable Error
    tolerable_error = calculate_tolerable_error(planning_materiality, tolerable_error_percentage)
    st.write(f"Tolerable Error: {tolerable_error}")

    # Determine Testing Threshold Percentage Range
    percentage_range = get_testing_threshold_percentage(control_approach, account_type, inherent_risk)
    
    # Calculate Key Items Threshold
    key_items_threshold = calculate_key_items_threshold(tolerable_error, percentage_range)
    if key_items_threshold is None:
        return  # Stop execution if no rationale is provided for a higher percentage

    st.write(f"Key Items Threshold: {key_items_threshold}")

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

            population_data = population_data[keep_columns]

            # Convert "Item Value" to numeric, handling errors
            population_data["Item Value"] = pd.to_numeric(population_data["Item Value"], errors="coerce")

            # Drop rows with invalid "Item Value" (e.g., non-numeric values)
            if population_data["Item Value"].isnull().any():
                st.warning("Some rows have invalid 'Item Value' and will be dropped.")
                population_data = population_data.dropna(subset=["Item Value"])

            st.write("Mapped Data Preview:")
            st.write(population_data.head())

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
            st.write(f"Multiplier: {multiplier}")

            # Calculate Sample Size
            number_of_key_items = len(key_items)
            sample_size = calculate_sample_size(number_of_key_items, multiplier)
            st.write(f"Final Sample Size: {sample_size}")

            # Export Options
            st.header("Export Results")
            if st.button("Export to PDF"):
                pdf_file = export_to_pdf(key_items, sample_size, coverage_ratio, cra_level, assurance_level)
                with open(pdf_file, "rb") as f:
                    st.download_button("Download PDF", f, file_name="audit_sampling_report.pdf")
                os.remove(pdf_file)  # Clean up temporary file

            if st.button("Export to Excel"):
                excel_file = export_to_excel(key_items, sample_size, coverage_ratio, cra_level, assurance_level)
                with open(excel_file, "rb") as f:
                    st.download_button("Download Excel", f, file_name="audit_sampling_report.xlsx")
                os.remove(excel_file)  # Clean up temporary file

if __name__ == "__main__":
    main()
