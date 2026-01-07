import pandas as pd
import numpy as np
import random
from app.utils import time_slots
from collections import defaultdict
import copy
import numpy as np

######################################################################
####       STEP 1: CLEANING REGIONAL REQUESTS TO REP NAMES        ####
######################################################################

# -----------------------------------------
# Helpers
# -----------------------------------------
def is_region_request(att_list):
    if len(att_list) != 1:
        return False
    x = att_list[0].strip().upper()
    return x.startswith("KAE") or x.startswith("SAE")

def extract_segment(region_name):
    return region_name[:3].upper()

# -----------------------------------------
# Build region attendee sets
# -----------------------------------------
def expand_region_request(att_list, supplier_type, reps_df):
    """
    Returns a list of candidate DataFrames (one per slot in meeting)
    each containing the eligible reps.
    """
    region = att_list[0].strip()
    segment = extract_segment(region)

    region_df = reps_df[reps_df["Region"].str.upper() == region.upper()]
    seg_df = reps_df[reps_df["Segment"].str.upper() == segment]

    # ideal roles
    if supplier_type == "Peak":
        roles = [3, 2]
    else:
        roles = [2, 1]

    out = []
    for w in roles:
        if w == 3:
            out.append((3, seg_df[seg_df["Weight"] == 3]))
        elif w == 2:
            out.append((2, region_df[region_df["Weight"] == 2]))
        else:
            out.append((1, region_df[region_df["Weight"] == 1]))
    return out


def fallback_region(weight, region, segment, reps_df, used):
    region = region.upper()
    segment = segment.upper()

    reg_df = reps_df[reps_df["Region"].str.upper() == region]
    seg_df = reps_df[reps_df["Segment"].str.upper() == segment]

    # remove used
    reg_df = reg_df[~reg_df["Rep Name"].isin(used)]
    seg_df = seg_df[~seg_df["Rep Name"].isin(used)]

    if weight == 3:
        w1 = reg_df[reg_df["Weight"] == 1]
        if len(w1) >= 2:
            return w1.sample(2)["Rep Name"].tolist()
        return []

    if weight == 2:
        w1 = reg_df[reg_df["Weight"] == 1]
        if len(w1) >= 1:
            return [w1.sample(1)["Rep Name"].iloc[0]]
        return []

    if weight == 1:
        r1 = reg_df[reg_df["Weight"] == 1]
        if len(r1) >= 1:
            return [r1.sample(1)["Rep Name"].iloc[0]]
        s1 = seg_df[seg_df["Weight"] == 1]
        if len(s1) >= 1:
            return [s1.sample(1)["Rep Name"].iloc[0]]
        return []

    return []


def fallback_name(orig_name, reps_df, used):
    """
    Simpler: if name is missing or used, we cannot make assumptions.
    Name fallbacks come later in Phase 2 (during scheduling).
    For now, just return [] meaning 'no fallback here'.
    """
    return []


def build_phase1_requested_attendees(preferences, reps_df):
    """
    Returns a new preferences dict with 'requested_attendees' added.
    No scheduling, no timeslots. Only replacing duplicates
    and producing final clean attendee lists.
    """

    # ensure no missing strings
    reps_df["Region"] = reps_df["Region"].fillna("").astype(str)
    reps_df["Segment"] = reps_df["Segment"].fillna("").astype(str)

    new_pref = {}

    for supp, meetings in preferences.items():
        used = set()
        out_meetings = []

        for m in sorted(meetings, key=lambda x: x["meeting_number"]):

            supplier_type = m["supplier_type"]
            atts = m["attendees"]

            if is_region_request(atts):
                region = atts[0]
                segment = extract_segment(region)

                role_list = expand_region_request(atts, supplier_type, reps_df)

                resolved = []

                for w, df_cands in role_list:
                    # remove already-used
                    df_cands = df_cands[~df_cands["Rep Name"].isin(used)]

                    if len(df_cands) > 0:
                        pick = df_cands.sample(1)["Rep Name"].iloc[0]
                        resolved.append(pick)
                        used.add(pick)
                    else:
                        # fallback
                        repl = fallback_region(w, region, segment, reps_df, used)
                        for r in repl:
                            resolved.append(r)
                            used.add(r)

                # done
                m2 = dict(m)
                m2["requested_attendees"] = resolved
                out_meetings.append(m2)

            else:
                # NAME request
                resolved = []
                for name in atts:
                    # if the rep exists AND unused:
                    df_match = reps_df[reps_df["Rep Name"].str.upper() == name.upper()]
                    if len(df_match) > 0:
                        rep_name = df_match.iloc[0]["Rep Name"]
                        if rep_name not in used:
                            resolved.append(rep_name)
                            used.add(rep_name)
                        else:
                            # fallback for duplicate
                            fb = fallback_name(name, reps_df, used)
                            resolved.extend(fb)
                            for f in fb:
                                used.add(f)
                    else:
                        # rep does not exist -- no fallback now
                        pass

                m2 = dict(m)
                m2["requested_attendees"] = resolved
                out_meetings.append(m2)

        new_pref[supp] = out_meetings

    return new_pref


######################################################################
####  STEP 2: IMPLEMENTING GLOBAL UPPER BOUND FOR MAX MEETINGS    ####
######################################################################


def get_weight(rep_name, reps_df):
    row = reps_df[reps_df["Rep Name"] == rep_name]
    if len(row) == 0:
        return None
    return int(row.iloc[0]["Weight"])


def get_region_segment(rep_name, reps_df):
    row = reps_df[reps_df["Rep Name"] == rep_name]
    if len(row) == 0:
        return None, None
    region = row.iloc[0]["Region"]
    segment = row.iloc[0]["Segment"]
    return region, segment


def find_replacement(rep_name, rep_weight, reps_df, used_reps, target_region, target_segment):

    df = reps_df[~reps_df["Rep Name"].isin(used_reps)]

    # W3 → W1 same segment
    if rep_weight == 3:
        seg_df = df[df["Segment"].str.upper() == target_segment.upper()]
        w1 = seg_df[seg_df["Weight"] == 1]
        if len(w1) > 0:
            return w1.sample(1)["Rep Name"].iloc[0]
        return None

    # W2 → W1 same region
    if rep_weight == 2:
        reg_df = df[df["Region"].str.upper() == target_region.upper()]
        w1 = reg_df[reg_df["Weight"] == 1]
        if len(w1) > 0:
            return w1.sample(1)["Rep Name"].iloc[0]
        return None

    # W1 → W1 same region
    if rep_weight == 1:
        reg_df = df[df["Region"].str.upper() == target_region.upper()]
        w1 = reg_df[reg_df["Weight"] == 1]
        if len(w1) > 0:
            return w1.sample(1)["Rep Name"].iloc[0]
        return None

    return None


def build_phase2_cleaned_requests(preferences, reps_df, max_meetings_rep=12):
    """
    Input:
        preferences = raw preferences
        reps_df = sales rep table
        max_meetings_rep = global upper bound
    Output:
        cleaned preferences
        rep load summary dict
    """

    preferences_phase1 = build_phase1_requested_attendees(preferences, reps_df)

    rep_counts = defaultdict(int)
    for supp, meetings in preferences_phase1.items():
        for m in meetings:
            for rep in m["requested_attendees"]:
                rep_counts[rep] += 1

    starting_counts = dict(rep_counts)

    suppliers_sorted = []

    for supp, meetings in preferences_phase1.items():
        supplier_type = meetings[0]["supplier_type"]
        is_acc = 0 if supplier_type == "Accelerating" else 1
        highest_meeting = max(m["meeting_number"] for m in meetings)
        suppliers_sorted.append((is_acc, highest_meeting, supp))

    suppliers_sorted = sorted(suppliers_sorted, key=lambda x: (x[0], -x[1]))

    cleaned = {supp: [dict(m) for m in meetings] for supp, meetings in preferences_phase1.items()}

    # Core load reduction loop
    for _, _, supp in suppliers_sorted:

        meetings = cleaned[supp]

        for m in sorted(meetings, key=lambda x: -x["meeting_number"]):

            new_list = []
            used = set()

            for rep in m["requested_attendees"]:

                if rep_counts[rep] <= max_meetings_rep:
                    new_list.append(rep)
                    used.add(rep)
                    continue

                rep_w = get_weight(rep, reps_df)
                reg, seg = get_region_segment(rep, reps_df)

                replacement = None

                if rep_w is not None:
                    replacement = find_replacement(rep, rep_w, reps_df, used, reg, seg)

                rep_counts[rep] -= 1
                if rep_counts[rep] < 0:
                    rep_counts[rep] = 0

                if replacement is not None:
                    new_list.append(replacement)
                    used.add(replacement)
                    rep_counts[replacement] += 1

            m["requested_attendees"] = new_list

    # manual override
    cleaned['Simple Green'][0]['requested_attendees'] = ['Matthew Borich', 'William Hollenbach III', 'Dawn Cormier']
    cleaned['Brady'][0]['requested_attendees'] = ['Tom Birchard', 'Ali Mccraw', 'Clayton Davis']

    # Mark unavailable reps in NAME requests
    for supp, meetings in cleaned.items():
        for m in meetings:

            # skip region requests
            if len(m["attendees"]) == 1 and (
                m["attendees"][0].strip().upper().startswith("KAE")
                or m["attendees"][0].strip().upper().startswith("SAE")
            ):
                continue

            original = set(a.strip() for a in m["attendees"])
            final = set(a.strip() for a in m["requested_attendees"])

            missing = sorted(list(original - final))
            m["unavailable"] = missing

    # Summary
    rep_load_summary = {
        "start_counts": starting_counts,
        "final_counts": dict(rep_counts)
    }

    return cleaned, rep_load_summary

######################################################################
####              STEP 3: SCHEDULER AND VALIDATION                ####
######################################################################

def build_validation_report(cleaned_prefs, supplier_schedule, reps_schedule, sup_summary):
    """
    Build analytical report of failures, grouped by total, by type, and by supplier.
    """

    report = {
        "total_failed": 0,
        "failed_by_type": {"Peak": 0, "Accelerating": 0},
        "failed_by_supplier": {},
        "failed_meetings_detail": []
    }

    # Loop each supplier’s summary
    for supp, summary in sup_summary.items():

        requested = summary["requested"]
        fulfilled = summary["fulfilled"]
        failed = [r for r in requested if r not in fulfilled]

        supplier_type = cleaned_prefs[supp][0]["supplier_type"]

        # Init supplier block
        report["failed_by_supplier"][supp] = {
            "supplier_type": supplier_type,
            "requested": len(requested),
            "fulfilled": len(fulfilled),
            "failed": len(failed)
        }

        # Update totals
        report["total_failed"] += len(failed)
        report["failed_by_type"][supplier_type] += len(failed)

        # Build detail for each failed meeting
        for req_name in failed:
            # find the Phase 2 request block
            req_block = next((r for r in cleaned_prefs[supp] if r["request_name"] == req_name), None)

            if req_block is None:
                continue

            requested_attendees = req_block["requested_attendees"]
            substitutions = sup_summary[supp]["substitutions"].get(req_name, [])

            # pull rep schedules for these reps
            rep_scheds = {}
            for rep in requested_attendees:
                rep_scheds[rep] = reps_schedule[reps_schedule["rep"] == rep].copy()

            report["failed_meetings_detail"].append({
                "supplier": supp,
                "supplier_type": supplier_type,
                "request_name": req_name,
                "requested_attendees": requested_attendees,
                "substitutions": substitutions,
                "rep_schedules": rep_scheds
            })

    return report


def shuffle_timeslots(supplier_df, reps_df, seed=42):
    """
    Shuffle ALL timeslots globally while keeping the meeting assignments identical.

    Example:
        Tuesday 8am  -> Wednesday 10am
        Tuesday 9am  -> Tuesday 3pm
        etc.

    This is a bijection mapping (one-to-one).
    """

    # ----------------------------------------------------
    # 1. Collect all valid timeslots
    # ----------------------------------------------------
    all_slots = []
    for day, mapping in time_slots.items():
        for slot, state in mapping.items():
            if state not in ("LUNCH", "BREAK"):
                all_slots.append((day, slot))

    # Safety
    if len(all_slots) == 0:
        return supplier_df, reps_df

    # ----------------------------------------------------
    # 2. Shuffle timeslots
    # ----------------------------------------------------
    rng = np.random.default_rng(seed)
    shuffled = all_slots.copy()
    rng.shuffle(shuffled)

    # Build mapping dict
    remap = {old: new for old, new in zip(all_slots, shuffled)}

    # ----------------------------------------------------
    # 3. Apply mapping to supplier schedule
    # ----------------------------------------------------
    supplier_df = supplier_df.copy()
    supplier_df["day_new"] = supplier_df.apply(
        lambda r: remap[(r["day"], r["timeslot"])][0],
        axis=1
    )
    supplier_df["timeslot_new"] = supplier_df.apply(
        lambda r: remap[(r["day"], r["timeslot"])][1],
        axis=1
    )
    supplier_df.drop(columns=["day", "timeslot"], inplace=True)
    supplier_df.rename(columns={"day_new": "day", "timeslot_new": "timeslot"}, inplace=True)

    # ----------------------------------------------------
    # 4. Apply mapping to rep schedule
    # ----------------------------------------------------
    reps_df = reps_df.copy()
    reps_df["day_new"] = reps_df.apply(
        lambda r: remap[(r["day"], r["timeslot"])][0],
        axis=1
    )
    reps_df["timeslot_new"] = reps_df.apply(
        lambda r: remap[(r["day"], r["timeslot"])][1],
        axis=1
    )
    reps_df.drop(columns=["day", "timeslot"], inplace=True)
    reps_df.rename(columns={"day_new": "day", "timeslot_new": "timeslot"}, inplace=True)

    return supplier_df, reps_df

def build_phase3_create_schedules(preferences,
                                  reps_df,
                                  max_meetings_rep=12,
                                  max_peak=6,
                                  max_acc=3,
                                  seed=42):

    """
    Phase 3: Use Phase 2 cleaned attendee lists and attempt to schedule all meetings,
    then shuffle timeslots globally.
    """

    # ------------------------------------------------------
    # Step 1: Run Phase 2 preprocessing
    # ------------------------------------------------------
    cleaned_prefs, rep_summary = build_phase2_cleaned_requests(
        preferences, reps_df, max_meetings_rep
    )

    # ------------------------------------------------------
    # Step 2: Track rep availability
    # ------------------------------------------------------
    rep_avail = {
        rep: {
            day: {slot: (state is None) for slot, state in time_slots[day].items()}
            for day in time_slots
        }
        for rep in reps_df["Rep Name"]
    }

    rep_meet_count = {rep: 0 for rep in reps_df["Rep Name"]}

    supplier_rows = []
    rep_rows = []
    sup_summary = {}

    # ------------------------------------------------------
    # Step 3: Supplier scheduling order
    # ------------------------------------------------------
    suppliers = list(cleaned_prefs.keys())

    def sort_key(supp):
        t = cleaned_prefs[supp][0]["supplier_type"]
        return 0 if t == "Peak" else 1

    suppliers = sorted(suppliers, key=sort_key)

    # ------------------------------------------------------
    # Step 4: All usable timeslots
    # ------------------------------------------------------
    def all_slots():
        out = []
        for day, mapping in time_slots.items():
            for slot, state in mapping.items():
                if state not in ("LUNCH", "BREAK"):
                    out.append((day, slot))
        return out

    slot_order = all_slots()

    random.seed(seed)
    np.random.seed(seed)

    # ------------------------------------------------------
    # Step 5: Scheduling loop
    # ------------------------------------------------------
    for supp in suppliers:

        meetings = cleaned_prefs[supp]
        supplier_type = meetings[0]["supplier_type"]
        booth = meetings[0]["booth"]

        cap = max_peak if supplier_type == "Peak" else max_acc

        sup_summary[supp] = {
            "requested": [],
            "fulfilled": [],
            "substitutions": {},
            "req_types": {},
        }

        used_count = 0

        for m in sorted(meetings, key=lambda x: x["meeting_number"]):

            req_name = m["request_name"]
            attendees = m["requested_attendees"]
            tot_opp = m.get("total_opportunity", 0.0)
            type = m["request_type"]

            sup_summary[supp]["requested"].append(req_name)

            if used_count >= cap:
                break

            assigned = False

            for day, slot in slot_order:

                supplier_double = any(
                    r["supplier"] == supp and r["day"] == day and r["timeslot"] == slot
                    for r in supplier_rows
                )
                if supplier_double:
                    continue

                available = True
                for rep in attendees:
                    if rep_meet_count[rep] >= max_meetings_rep:
                        available = False
                        break
                    if not rep_avail[rep][day][slot]:
                        available = False
                        break
                if not available:
                    continue

                # Assign meeting
                assigned = True
                used_count += 1
                sup_summary[supp]["fulfilled"].append(req_name)

                # Missing names → substitutions
                subs = m["unavailable"] if "unavailable" in m else []
                sup_summary[supp]["substitutions"][req_name] = subs
                sup_summary[supp]["req_types"][req_name] = type

                # --------------------------
                # Write Supplier schedule row
                # --------------------------
                supplier_rows.append({
                    "supplier": supp,
                    "booth": booth,
                    "day": day,
                    "timeslot": slot,
                    "reps": attendees,
                    "category": req_name,
                    "total_opportunity": tot_opp
                })

                # --------------------------
                # Write Rep schedule rows
                # --------------------------
                for rep in attendees:
                    rep_rows.append({
                        "rep": rep,
                        "day": day,
                        "timeslot": slot,
                        "supplier": supp,
                        "booth": booth,
                        "category": req_name,
                        "total_opportunity": tot_opp
                    })

                    rep_avail[rep][day][slot] = False
                    rep_meet_count[rep] += 1

                break  # stop searching for slots

            if not assigned:
                sup_summary[supp]["substitutions"][req_name] = \
                    m["unavailable"] if "unavailable" in m else []

        if cap > 0:
            new_requested = []
            fulfilled_count = 0

            for req in sup_summary[supp]["requested"]:
                new_requested.append(req)

                if req in sup_summary[supp]["fulfilled"]:
                    fulfilled_count += 1

                # stop as soon as we have shown *cap* fulfilled meetings
                if fulfilled_count >= cap:
                    break

            sup_summary[supp]["requested"] = new_requested

    # Convert to DataFrames (now with opportunity values)
    supplier_df = pd.DataFrame(supplier_rows)
    reps_df_sched = pd.DataFrame(rep_rows)

    # ------------------------------------------------------
    # Shuffle timeslots globally
    # ------------------------------------------------------
    supplier_df, reps_df_sched = shuffle_timeslots(
        supplier_df, reps_df_sched, seed=seed
    )

    # ------------------------------------------------------
    # Final validation
    # ------------------------------------------------------
    validation = build_validation_report(
        cleaned_prefs, supplier_df, reps_df_sched, sup_summary
    )

    return supplier_df, reps_df_sched, sup_summary, validation

######################################################################
####                  STEP 4: RUN SCHEDULER                       ####
######################################################################

def run_scheduler(preferences,
                  reps_df,
                  max_meetings_rep=12,
                  max_peak=6,
                  max_acc=3,
                  seeds=100):
    """
    Runs Phase 3 scheduling across many seeds and returns the result
    from the best-performing seed (least total failures).
    """

    results = []
    best_output = None

    for s in range(seeds):

        supplier_schedule, reps_schedule, sup_summary, validation = \
            build_phase3_create_schedules(
                preferences,
                reps_df,
                max_meetings_rep=max_meetings_rep,
                max_peak=max_peak,
                max_acc=max_acc,
                seed=s
            )

        fail_peak = validation["failed_by_type"]["Peak"]
        fail_acc = validation["failed_by_type"]["Accelerating"]
        fail_total = fail_peak + fail_acc

        results.append({
            "seed": s,
            "fail_peak": fail_peak,
            "fail_acc": fail_acc,
            "fail_total": fail_total
        })

        # track best
        if best_output is None or fail_total < best_output["fail_total"]:
            best_output = {
                "seed": s,
                "fail_total": fail_total,
                "fail_peak": fail_peak,
                "fail_acc": fail_acc,
                "supplier_schedule": supplier_schedule,
                "reps_schedule": reps_schedule,
                "sup_summary": sup_summary,
                "validation": validation
            }

    # package as tuple to match Phase 3 return style
    return (
        best_output["supplier_schedule"],
        best_output["reps_schedule"],
        best_output["sup_summary"],
        best_output["validation"]
    )

