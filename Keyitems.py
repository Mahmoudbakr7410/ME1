import streamlit as st
import pandas as pd

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
    return tolerable_error * (percentage_range[0] / 100)

def calculate_coverage_ratio(key_items_sum, total_population_value):
    return (key_items_sum / total_population_value) * 100

# Phase 2: Sample Size Determination
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
        # Add other CRA levels here...
    }

    # Find the closest coverage ratio in the matrix
    closest_ratio = min(coverage_matrix[cra_level][assurance_level].keys(), key=lambda x: abs(x - coverage_ratio))
    return coverage_matrix[cra_level][assurance_level][closest_ratio]

def calculate_sample_size(number_of_key_items, multiplier):
    if multiplier == "*":
        return 0  # No sampling required
    return int(number_of_key_items * multiplier)

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

    # Determine Testing Threshold Percentage
    percentage_range = get_testing_threshold_percentage(control_approach, account_type, inherent_risk)
    st.write(f"Testing Threshold Percentage Range: {percentage_range[0]}% to {percentage_range[1]}%")

    # Calculate Key Items Threshold
    key_items_threshold = calculate_key_items_threshold(tolerable_error, percentage_range)
    st.write(f"Key Items Threshold: {key_items_threshold}")

    # Upload CSV for Key Items
    uploaded_file = st.file_uploader("Upload Population Data (CSV)", type=["csv"])
    if uploaded_file:
        population_data = pd.read_csv(uploaded_file)
        st.write("Population Data:")
        st.write(population_data)

        # Identify Key Items
        key_items = population_data[population_data["Value"] >= key_items_threshold]
        st.write("Key Items:")
        st.write(key_items)

        # Calculate Coverage Ratio
        key_items_sum = key_items["Value"].sum()
        coverage_ratio = calculate_coverage_ratio(key_items_sum, total_population_value)
        st.write(f"Coverage Ratio: {coverage_ratio:.2f}%")

        # Phase 2: Sample Size Determination
        st.header("Phase 2: Sample Size Determination")
        cra_level = st.selectbox("Combined Risk Assessment (CRA) Level", ["Minimal CRA", "Low CRA", "Low + Significant Risk CRA", "Moderate CRA", "High CRA", "High + Significant Risk CRA"])
        assurance_level = st.selectbox(ASSURANCE_LEVEL, ["Little", "Some", "Medium", "Persuasive"])

        # Get Multiplier from Coverage Matrix
        multiplier = get_coverage_matrix_multiplier(cra_level, assurance_level, coverage_ratio)
        st.write(f"Multiplier: {multiplier}")

        # Calculate Sample Size
        number_of_key_items = len(key_items)
        sample_size = calculate_sample_size(number_of_key_items, multiplier)
        st.write(f"Final Sample Size: {sample_size}")

if __name__ == "__main__":
    main()
