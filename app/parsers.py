import pandas as pd
import numpy as np


# Utility: Clean attendees 
def _parse_attendees(raw):
    if raw is None or str(raw).strip() in ("", "-", "nan", "None"):
        return []
    parts = [p.strip() for p in str(raw).split(",") if p.strip()]
    # If multiple names, return list of names
    if len(parts) > 1:
        return parts
    # Exactly one thing; could be a name or district (ex: K5-6 San Diego)
    return parts


# Clean & validate meeting definitions
def clean_and_validate_requests(preferences):
    cleaned = {}
    for supplier, meetings in preferences.items():
        # Remove blank/invalid meetings
        valid = [
            m for m in meetings
            if m["attendees_raw"] and len(m["attendees_raw"]) > 0
        ]
        # Sort by Meeting #
        valid = sorted(valid, key=lambda x: x["meeting_number"])
        # Reset numbering
        for i, m in enumerate(valid, start=1):
            m["meeting_number"] = i
        cleaned[supplier] = valid
    return cleaned


# Main Parser
def parse_meeting_organizer(file_path):

    # Load sheets
    req_df = pd.read_excel(file_path, sheet_name="Meeting Requests")
    reps_df = pd.read_excel(file_path, sheet_name="Sales Reps")
    sellers_df = pd.read_excel(file_path, sheet_name="Sales Rep District Oppty")

    # Normalize sellers_opp_df
    sellers_opp_df = sellers_df.rename(columns={
        "District": "district",
        "Name": "name",
        "Product Line": "product_line",
        "Opportunity": "opportunity"
    })

    # standardize product lines (uppercase for matching)
    sellers_opp_df["product_line"] = sellers_opp_df["product_line"].astype(str).str.upper()

    # clean $ opportunity → numeric
    sellers_opp_df["opportunity"] = (
        sellers_opp_df["opportunity"]
        .astype(str)
        .str.replace("$", "")
        .str.replace(",", "")
        .astype(float)
        .fillna(0.0)
    )

    # Build suppliers_df
    suppliers_df = (
        req_df[["Supplier Name", "Supplier Type", "Booth #"]]
        .drop_duplicates()
        .rename(columns={
            "Supplier Name": "Supplier",
            "Supplier Type": "Supplier Type",
            "Booth #": "Booth"
        })
        .reset_index(drop=True)
    )

    # Normalize reps_df
    reps_df = reps_df.rename(columns={
        "Name": "Rep Name",
        "Leader Name": "Leader",
        "Leader?": "Is Leader",
        "Segment": "Segment",
        "Region": "Region",
        "District": "District",
        "Email": "Email",
        "Role": "Role",
        "Weight": "Weight"
    })

    reps_df["Segment"] = reps_df["Segment"].fillna("").astype(str)
    reps_df["Region"] = reps_df["Region"].fillna("").astype(str)
    reps_df["District"] = reps_df["District"].fillna("").astype(str)

    # weight numeric fallback
    reps_df["Weight"] = pd.to_numeric(reps_df["Weight"], errors="coerce").fillna(1).astype(int)

    # Build preferences dict
    preferences = {}

    # convert pl1 to uppercase for matching seller product_line
    req_df["pl1"] = req_df["pl1"].astype(str).str.upper().fillna("")

    # clean numeric fields
    req_df["Penetration Clean"] = (
        pd.to_numeric(req_df["Penetration Clean"], errors="coerce").fillna(0)
    )
    req_df["Acquisition Clean"] = (
        pd.to_numeric(req_df["Acquisition Clean"], errors="coerce").fillna(0)
    )

    for _, row in req_df.iterrows():

        supplier = str(row["Supplier Name"]).strip()
        meeting_num = int(row["Meeting #"])

        attendees_raw = _parse_attendees(row["Request Clean"])
        product_line = str(row["pl1"]).strip().upper()

        total_opp = float(row["Penetration Clean"]) + float(row["Acquisition Clean"])

        entry = {
            "meeting_number": meeting_num,
            "supplier_name": supplier,
            "supplier_type": row["Supplier Type"],
            "booth": row["Booth #"],
            "request_name": row["Request Name"],
            "session_type": str(row["Session Type"]).strip(),   # Strategy or Planning
            "pl1": product_line,
            "total_opportunity": total_opp,
            "attendees_raw": attendees_raw
        }

        preferences.setdefault(supplier, []).append(entry)

    # clean, sort, and reindex meetings
    cleaned_preferences = clean_and_validate_requests(preferences)

    # Return all four datasets
    return suppliers_df, reps_df, cleaned_preferences, sellers_opp_df


def parse_uploaded_schedules(uploaded_file):

    xl = pd.ExcelFile(uploaded_file)

    if "Suppliers" not in xl.sheet_names or "Representatives" not in xl.sheet_names:
        raise ValueError("Uploaded file must contain Suppliers and Representatives sheets.")

    sup_df = pd.read_excel(xl, "Suppliers")
    rep_df = pd.read_excel(xl, "Representatives")

    # -----------------------------
    # Rebuild supplier_sched
    # -----------------------------
    supplier_sched = pd.DataFrame({
        "supplier": sup_df["Supplier Name"],
        "booth": sup_df["Booth"],
        "day": sup_df["Day"],
        "timeslot": sup_df["Timeslot"],
        "session_type": sup_df["Session Type"],
        "reps": sup_df["Reps"].apply(
            lambda x: [r.strip() for r in x.split(",")] if isinstance(x, str) else []
        ),
        "category": sup_df["Request"],
        "total_opportunity": sup_df["Opportunity"]
    })

    # -----------------------------
    # Rebuild rep_sched
    # -----------------------------
    rep_sched = pd.DataFrame({
        "rep": rep_df["Name"],
        "day": rep_df["Day"],
        "timeslot": rep_df["Timeslot"],
        "supplier": rep_df["Supplier"],
        "booth": rep_df["Booth"],
        "session_type": rep_df["Session Type"],
        "category": rep_df["Request Name"],
        "total_opportunity": rep_df["Opportunity"]
    })

    # -----------------------------
    # Build default supplier_summary
    # -----------------------------
    supplier_summary = {}

    for supplier, grp in sup_df.groupby("Supplier Name"):
        requests = grp["Request"].unique().tolist()
        supplier_summary[supplier] = {
            "requested": requests,
            "fulfilled": requests.copy(),
            "unfulfilled": [],
            "substitutions": {}
        }

    validation = {
        "total_unfulfilled": 0,
        "unfulfilled_detail": {}
    }

    return supplier_sched, rep_sched, supplier_summary, validation

