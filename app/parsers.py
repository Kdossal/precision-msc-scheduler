import pandas as pd

def parse_matrix_file(file):
    # read entire workbook
    suppliers_df = pd.read_excel(file, sheet_name="Suppliers")
    reps_df = pd.read_excel(file, sheet_name="Sales Reps.")

    pref_cols = suppliers_df.columns[3:]  # first 3 columns are Supplier, Booth, Type

    # create preference matrix: rows = suppliers, cols = categories
    preferences_matrix = suppliers_df[["Supplier"] + list(pref_cols)].copy()
    preferences_matrix.set_index("Supplier", inplace=True)

    return suppliers_df, reps_df, preferences_matrix