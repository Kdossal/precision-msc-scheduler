import pandas as pd
from app.utils import time_slots


def run_scheduler(suppliers_df, reps_df, prefs_df, max_meetings_rep, max_peak, max_acc):
    # Build rep availability: rep → {day → {slot → True/False}}
    rep_avail = {
        rep: {
            day: {slot: True for slot in slots}
            for day, slots in time_slots.items()
        }
        for rep in reps_df["Sales Rep."]
    }

    # Count of meetings per rep
    rep_meeting_count = {rep: 0 for rep in reps_df["Sales Rep."]}

    # Count of meetings per supplier
    supplier_meeting_count = {}

    supplier_rows = []
    rep_rows = []

    # Sort suppliers: Peak first
    ordered_suppliers = suppliers_df.sort_values(
        by="Type",
        key=lambda col: col.map({"Peak": 0, "Accelerating": 1})
    )

    for _, supp in ordered_suppliers.iterrows():
        supplier = supp["Supplier"]
        booth = supp["Booth #"]
        s_type = supp["Type"]

        cap = max_peak if s_type == "Peak" else max_acc
        supplier_meeting_count[supplier] = 0

        # category preferences
        supplier_prefs = prefs_df.loc[supplier]
        preferred_categories = supplier_prefs[supplier_prefs == "Y"].index.tolist()

        for category in preferred_categories:
            if supplier_meeting_count[supplier] >= cap:
                break

            reps_in_cat = reps_df[reps_df["Category"] == category]\
                .sort_values("Ranking")

            assigned_rep = None
            chosen_day = None
            chosen_slot = None

            for _, rep_row in reps_in_cat.iterrows():
                rep = rep_row["Sales Rep."]

                if rep_meeting_count[rep] >= max_meetings_rep:
                    continue

                # find first open day/slot match
                day, slot = _find_available_timeslot(
                    supplier, rep,
                    supplier_rows,
                    rep_avail
                )

                if day and slot:
                    assigned_rep = rep
                    chosen_day = day
                    chosen_slot = slot
                    break

            if assigned_rep:
                # add supplier entry
                supplier_rows.append({
                    "supplier": supplier,
                    "booth": booth,
                    "day": chosen_day,
                    "timeslot": chosen_slot,
                    "rep": assigned_rep,
                    "category": category
                })

                # add rep entry
                rep_rows.append({
                    "rep": assigned_rep,
                    "day": chosen_day,
                    "timeslot": chosen_slot,
                    "supplier": supplier,
                    "booth": booth,
                    "category": category
                })

                # block rep
                rep_avail[assigned_rep][chosen_day][chosen_slot] = False

                rep_meeting_count[assigned_rep] += 1
                supplier_meeting_count[supplier] += 1

    return (
        pd.DataFrame(supplier_rows).sort_values(["supplier", "day", "timeslot"]),
        pd.DataFrame(rep_rows).sort_values(["rep", "day", "timeslot"]),
    )


def _find_available_timeslot(supplier, rep, supplier_rows, rep_avail):
    supplier_used = {
        (row["day"], row["timeslot"])
        for row in supplier_rows
        if row["supplier"] == supplier
    }

    for day, slot_dict in time_slots.items():
        for slot, blocked_reason in slot_dict.items():

            # skip if slot is lunch or break
            if blocked_reason in ("LUNCH", "BREAK"):
                continue

            if (day, slot) in supplier_used:
                continue

            if rep_avail[rep][day][slot] is True:
                return day, slot

    return None, None


