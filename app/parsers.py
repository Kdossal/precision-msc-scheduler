import pandas as pd
import numpy as np


# ------------------------------------------------------
# Clean & validate Phase 1 preferences
# ------------------------------------------------------
def clean_and_validate_requests(preferences):
    cleaned = {}

    for supplier, meetings in preferences.items():

        # Remove invalid or blank meetings
        valid_meetings = [
            m for m in meetings
            if isinstance(m["attendees"], list)
            and len(m["attendees"]) > 0
            and m["attendees"][0] not in ("-", "", None)
        ]

        # Sort by original meeting number
        valid_meetings = sorted(valid_meetings, key=lambda x: x["meeting_number"])

        # Reassign meeting numbers sequentially
        for i, m in enumerate(valid_meetings, start=1):
            m["meeting_number"] = i

        cleaned[supplier] = valid_meetings

    return cleaned


# ------------------------------------------------------
# Updated parser that mimics old logic but supports new data structure
# ------------------------------------------------------
def parse_meeting_organizer(file_path):

    # Load sheets
    req_df = pd.read_excel(file_path, sheet_name="Meeting Requests")
    reps_df = pd.read_excel(file_path, sheet_name="Sales Reps")

    # ------------------------------------------------------
    # 1. Build suppliers_df (unique suppliers)
    # ------------------------------------------------------
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

    # ------------------------------------------------------
    # 2. Normalize Reps sheet
    # ------------------------------------------------------
    reps_df = reps_df.rename(columns={
        "Name": "Rep Name",
        "Leader Name": "Leader",
        "Leader?": "Is Leader",
        "Segment": "Segment",
        "Region": "Region",
        "District": "District",
        "Weight": "Weight",
        "Email": "Email",
    })

    # Ensure clean string types
    reps_df["Segment"] = reps_df["Segment"].fillna("").astype(str)
    reps_df["Region"] = reps_df["Region"].fillna("").astype(str)

    # ------------------------------------------------------
    # 3. Build preferences dict (supplier → list of meetings)
    # ------------------------------------------------------
    requests_by_supplier = {}

    for _, row in req_df.iterrows():
        supplier = str(row["Supplier Name"]).strip()
        meeting_num = int(row["Meeting #"])

        # Clean attendees list
        attendees_raw = str(row["Request Clean"]).strip()
        attendees = [
            a.strip()
            for a in attendees_raw.split(",")
            if a.strip() not in ("", None)
        ]

        meeting_entry = {
            "meeting_number": meeting_num,
            "supplier_name": supplier,
            "supplier_type": row["Supplier Type"],
            "booth": row["Booth #"],
            "request_name": row["Request Name"],
            "attendees": attendees,
        }

        requests_by_supplier.setdefault(supplier, []).append(meeting_entry)

    # Sort incoming meetings
    for supplier in requests_by_supplier:
        requests_by_supplier[supplier] = sorted(
            requests_by_supplier[supplier],
            key=lambda x: x["meeting_number"]
        )

    # ------------------------------------------------------
    # 4. Clean and reassign numbers
    # ------------------------------------------------------
    cleaned_preferences = clean_and_validate_requests(requests_by_supplier)

    return suppliers_df, reps_df, cleaned_preferences
