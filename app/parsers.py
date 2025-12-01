import pandas as pd

def parse_matrix_file(file):
    suppliers_df = pd.read_excel(file, sheet_name="Suppliers")
    reps_df = pd.read_excel(file, sheet_name="Sales Reps.")

    # grab all Request columns
    pref_cols = [c for c in suppliers_df.columns if c.startswith("Request")]

    # create preference dict per supplier (ordered list)
    preferences = {}

    for _, row in suppliers_df.iterrows():
        supplier = row["Supplier"]

        requests = []
        for c in pref_cols:
            val = row[c]
            if pd.isna(val): 
                continue
            requests.append(str(val).strip())

        preferences[supplier] = requests

    return suppliers_df, reps_df, preferences
