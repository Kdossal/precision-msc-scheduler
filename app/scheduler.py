import re
import pandas as pd
import numpy as np
from collections import defaultdict
import random
from copy import deepcopy
from app.utils import time_slots, blocks

def is_district_request(att_list):
    """
    District requests always appear as a single token like:
    K5-6, S4-3, E1-7, etc.
    """
    if len(att_list) != 1:
        return False

    x = att_list[0].strip().upper()[:4]
    return bool(re.match(r"^[KSE]\d-\d$", x))


def build_phase1_requested_attendees(preferences, reps_df, sellers_opp_df):
    """
    Adds requested_attendees list to each meeting based on:

    - Name-based requests:
        return names as-is

    - District-based requests:
        Strategy:
            - District Leader (if available, one per supplier)
            - 1 seller spot
        Planning:
            - 2 seller spots
        Power Pairing:
            - 1 seller spot

    Seller spots are resolved later using district + product_line.
    """

    new_pref = {}

    # Build district leader lookup
    district_leader_map = (
        reps_df.assign(District=reps_df["District"].str.upper())
        [["Rep Name", "District"]]
        .dropna(subset=["District"])
        .groupby("District")["Rep Name"]
        .apply(list)
        .to_dict()
    )

    for supplier, meetings in preferences.items():

        used_leaders_within_supplier = set()
        updated_meetings = []

        for m in meetings:
            raw = m["attendees_raw"]
            session_type = m["session_type"].strip().lower()
            pl1 = (m.get("pl1") or "").upper().strip()

            # -------------------------------
            # CASE 1: NAME-BASED REQUEST
            # -------------------------------
            if not is_district_request(raw):
                clean_names = list(dict.fromkeys(raw))

                m2 = dict(m)
                m2["requested_attendees"] = clean_names
                updated_meetings.append(m2)
                continue

            # -------------------------------
            # CASE 2: DISTRICT-BASED REQUEST
            # -------------------------------
            requested_district = raw[0].strip().upper()
            requested_attendees = []

            # -------------------------------
            # STRATEGY
            # -------------------------------
            if session_type == "strategy":

                leaders = district_leader_map.get(requested_district, [])
                leader_choice = None

                for L in leaders:
                    if L not in used_leaders_within_supplier:
                        leader_choice = L
                        break

                if leader_choice:
                    requested_attendees.append(leader_choice)
                    used_leaders_within_supplier.add(leader_choice)

                requested_attendees.append({
                    "type": "seller_spot",
                    "district": requested_district,
                    "product_line": pl1 if pl1 and pl1 != "NAN" else None,
                    "count": 1
                })

            # -------------------------------
            # PLANNING
            # -------------------------------
            elif session_type == "planning":

                requested_attendees.append({
                    "type": "seller_spot",
                    "district": requested_district,
                    "product_line": pl1 if pl1 and pl1 != "NAN" else None,
                    "count": 2
                })

            # -------------------------------
            # POWER PAIRING
            # -------------------------------
            elif session_type == "power pairing":

                requested_attendees.append({
                    "type": "seller_spot",
                    "district": requested_district,
                    "product_line": pl1 if pl1 and pl1 != "NAN" else None,
                    "count": 1
                })

            else:
                raise ValueError(
                    f"Unknown session_type '{m['session_type']}' "
                    f"for supplier '{supplier}', meeting #{m['meeting_number']}"
                )

            # Fail-safe
            if not requested_attendees:
                raise ValueError(
                    f"Supplier '{supplier}' meeting #{m['meeting_number']} "
                    f"could not assign attendees "
                    f"(session={m['session_type']}, district={requested_district}, pl1={pl1})"
                )

            m2 = dict(m)
            m2["requested_attendees"] = requested_attendees
            updated_meetings.append(m2)

        new_pref[supplier] = updated_meetings

    return new_pref

def build_phase2_strategy_sessions(
    phase1,
    reps_df,
    sellers_opp_df,
    supplier_busy,
    rep_busy,
    supplier_rows,
    rep_rows,
    sup_summary,
    rng
):
    """
    Schedule ONLY Strategy sessions using:
      supplier + leader (if any) + seller
    Sellers are tried by opportunity.
    Time windows are tried in RANDOMIZED order per meeting.
    """

    def all_strategy_windows():
        windows = []
        for day, slots in time_slots.items():
            slot_list = list(slots.keys())
            for i in range(len(slot_list) - 1):
                s1, s2 = slot_list[i], slot_list[i + 1]
                if slots[s1] == "LUNCH" or slots[s2] == "LUNCH":
                    continue
                windows.append((day, s1, s2))
        return windows

    base_windows = all_strategy_windows()

    for supplier, meetings in phase1.items():

        for m in meetings:
            if m["session_type"] != "Strategy":
                continue

            req_name = m["request_name"]
            booth = m["booth"]
            tot_opp = m["total_opportunity"]

            requested = m["requested_attendees"]

            leaders = [a for a in requested if isinstance(a, str)]
            seller_spots = [a for a in requested if isinstance(a, dict)]

            # Randomize time windows per meeting
            windows = base_windows.copy()
            rng.shuffle(windows)

            # --------------------------------------------------
            # CASE 1: Name-based Strategy (no seller spots)
            # --------------------------------------------------
            if not seller_spots:
                required_reps = leaders
                booked = False

                for day, s1, s2 in windows:
                    if supplier_busy[supplier][day][s1] or supplier_busy[supplier][day][s2]:
                        continue
                    if any(rep_busy[r][day][s1] or rep_busy[r][day][s2] for r in required_reps):
                        continue

                    _book_strategy(
                        supplier, required_reps, day, s1, s2,
                        booth, req_name, tot_opp,
                        supplier_busy, rep_busy, supplier_rows, rep_rows
                    )

                    sup_summary[supplier]["fulfilled"].append(req_name)
                    booked = True
                    break

                if not booked:
                    sup_summary[supplier]["unfulfilled"].append(req_name)

                continue

            # --------------------------------------------------
            # CASE 2: District-based Strategy (leader + seller)
            # --------------------------------------------------
            spot = seller_spots[0]
            district = spot["district"].upper().strip()
            product_line = spot.get("product_line")

            candidates = sellers_opp_df[
                sellers_opp_df["district"].str.upper() == district
            ]

            if product_line:
                candidates = candidates[
                    candidates["product_line"] == product_line.upper().strip()
                ]

            candidates = candidates.sort_values("opportunity", ascending=False)

            booked = False

            for _, row in candidates.iterrows():
                seller = row["name"]
                required_reps = leaders + [seller]

                for day, s1, s2 in windows:
                    if supplier_busy[supplier][day][s1] or supplier_busy[supplier][day][s2]:
                        continue
                    if any(rep_busy[r][day][s1] or rep_busy[r][day][s2] for r in required_reps):
                        continue

                    _book_strategy(
                        supplier, required_reps, day, s1, s2,
                        booth, req_name, tot_opp,
                        supplier_busy, rep_busy, supplier_rows, rep_rows
                    )

                    sup_summary[supplier]["fulfilled"].append(req_name)
                    booked = True
                    break

                if booked:
                    break

            if not booked:
                sup_summary[supplier]["unfulfilled"].append(req_name)

def _book_strategy(
    supplier, reps, day, s1, s2,
    booth, req_name, tot_opp,
    supplier_busy, rep_busy, supplier_rows, rep_rows
):
    supplier_busy[supplier][day][s1] = True
    supplier_busy[supplier][day][s2] = True

    for r in reps:
        rep_busy[r][day][s1] = True
        rep_busy[r][day][s2] = True

    for slot in (s1, s2):
        supplier_rows.append({
            "supplier": supplier,
            "booth": booth,
            "day": day,
            "timeslot": slot,
            "session_type": "Strategy",
            "reps": reps,
            "category": req_name,
            "total_opportunity": tot_opp
        })

        for r in reps:
            rep_rows.append({
                "rep": r,
                "day": day,
                "timeslot": slot,
                "supplier": supplier,
                "booth": booth,
                "session_type": "Strategy",
                "category": req_name,
                "total_opportunity": tot_opp
            })

def build_phase2_planning_sessions(
    phase1,
    sellers_opp_df,
    supplier_busy,
    rep_busy,
    supplier_rows,
    rep_rows,
    sup_summary,
    rng
):
    """
    Schedule ONLY Planning sessions using:
      supplier + 2 sellers
    Sellers are chosen by opportunity.
    Time slots are tried in RANDOMIZED order per meeting.
    """

    def all_planning_slots():
        slots_out = []
        for day, slots in time_slots.items():
            for s in slots.keys():
                if slots[s] == "LUNCH":
                    continue
                slots_out.append((day, s))
        return slots_out

    base_slots = all_planning_slots()

    for supplier, meetings in phase1.items():

        for m in meetings:
            if m["session_type"] != "Planning":
                continue

            req_name = m["request_name"]
            booth = m["booth"]
            tot_opp = m["total_opportunity"]

            requested = m["requested_attendees"]
            spot = requested[0]  # Planning always has one seller_spot

            district = spot["district"].upper().strip()
            product_line = spot.get("product_line")
            count_needed = spot.get("count", 2)

            # Candidate sellers ordered by opportunity
            candidates = sellers_opp_df[
                sellers_opp_df["district"].str.upper() == district
            ]

            if product_line:
                candidates = candidates[
                    candidates["product_line"] == product_line.upper().strip()
                ]

            candidates = candidates.sort_values("opportunity", ascending=False)
            seller_list = candidates["name"].tolist()

            booked = False

            # Randomize slots per meeting
            slots = base_slots.copy()
            rng.shuffle(slots)

            # Try all seller pairs in priority order
            for i in range(len(seller_list)):
                for j in range(i + 1, len(seller_list)):
                    sellers = [seller_list[i], seller_list[j]]

                    if len(sellers) < count_needed:
                        continue

                    for day, s in slots:
                        if supplier_busy[supplier][day][s]:
                            continue
                        if any(rep_busy[r][day][s] for r in sellers):
                            continue

                        _book_planning(
                            supplier, sellers, day, s,
                            booth, req_name, tot_opp,
                            supplier_busy, rep_busy,
                            supplier_rows, rep_rows
                        )

                        sup_summary[supplier]["fulfilled"].append(req_name)
                        booked = True
                        break

                    if booked:
                        break
                if booked:
                    break

            if not booked:
                sup_summary[supplier]["unfulfilled"].append(req_name)

def _book_planning(
    supplier, reps, day, s,
    booth, req_name, tot_opp,
    supplier_busy, rep_busy,
    supplier_rows, rep_rows
):
    supplier_busy[supplier][day][s] = True

    for r in reps:
        rep_busy[r][day][s] = True

    supplier_rows.append({
        "supplier": supplier,
        "booth": booth,
        "day": day,
        "timeslot": s,
        "session_type": "Planning",
        "reps": reps,
        "category": req_name,
        "total_opportunity": tot_opp
    })

    for r in reps:
        rep_rows.append({
            "rep": r,
            "day": day,
            "timeslot": s,
            "supplier": supplier,
            "booth": booth,
            "session_type": "Planning",
            "category": req_name,
            "total_opportunity": tot_opp
        })


def get_innovation_workers(reps_df):
    """
    EDIT HERE if worker definition changes.
    """
    return reps_df[reps_df["Seller"]=="Y"]["Rep Name"].tolist()

def build_innovation_sessions_from_blocks():
    """
    Build innovation sessions ONCE.
    Each session has a hard capacity of 100 total reps.
    """

    sessions = []

    for day, slot_map in blocks.items():
        slots = list(slot_map.keys())
        i = 0

        while i < len(slots):
            slot = slots[i]
            suppliers = slot_map[slot]

            if not suppliers:
                i += 1
                continue

            supplier = suppliers[0]
            session_slots = [slot]

            # Merge consecutive slots for same supplier
            if i + 1 < len(slots) and slot_map[slots[i + 1]] == suppliers:
                session_slots.append(slots[i + 1])
                i += 1

            sessions.append({
                "supplier": supplier,
                "day": day,
                "slots": session_slots,
                "assigned": set(),     # IMPORTANT: set, not list
                "capacity": 85
            })

            i += 1

    return sessions



def assign_minimum_innovation_sessions(
    reps_df,
    innovation_sessions,
    rep_busy,
    rep_rows,
    rng
):
    """
    Assign exactly 1 Innovation Theater session per worker first,
    spreading reps evenly across sessions in round-robin order.
    """

    workers = get_innovation_workers(reps_df)

    # Randomize order to avoid bias
    rng.shuffle(workers)
    rng.shuffle(innovation_sessions)

    num_sessions = len(innovation_sessions)
    session_idx = 0

    for rep in workers:
        tried = 0
        assigned = False

        # Try sessions in round-robin order
        while tried < num_sessions:
            session = innovation_sessions[session_idx]
            session_idx = (session_idx + 1) % num_sessions
            tried += 1

            # Capacity check
            if len(session["assigned"]) >= session["capacity"]:
                continue

            day = session["day"]
            slots = session["slots"]

            # Availability check
            if any(rep_busy[rep][day].get(s, False) for s in slots):
                continue

            # Assign rep
            session["assigned"].add(rep)

            for s in slots:
                rep_busy[rep][day][s] = True
                rep_rows.append({
                    "rep": rep,
                    "day": day,
                    "timeslot": s,
                    "supplier": session["supplier"],
                    "booth": "",
                    "session_type": "Innovation Theater",
                    "category": "",
                    "total_opportunity": ""
                })

            assigned = True
            break

        if not assigned:
            print(f"WARNING: {rep} received no Innovation session")


def fill_innovation_sessions_to_capacity(
    reps_df,
    innovation_sessions,
    rep_busy,
    rep_rows,
    rng
):
    workers = get_innovation_workers(reps_df)

    worker_counts = {
        r: sum(
            1 for row in rep_rows
            if row["rep"] == r and row["session_type"] == "Innovation Theater"
        )
        for r in workers
    }

    round_num = 1

    while True:
        progress = False

        for session in innovation_sessions:
            if len(session["assigned"]) >= session["capacity"]:
                continue

            day = session["day"]
            slots = session["slots"]

            for rep in workers:
                if len(session["assigned"]) >= session["capacity"]:
                    break

                if worker_counts[rep] > round_num:
                    continue

                if rep in session["assigned"]:
                    continue

                if any(rep_busy[rep][day].get(s, False) for s in slots):
                    continue

                session["assigned"].add(rep)
                worker_counts[rep] += 1
                progress = True

                for s in slots:
                    rep_busy[rep][day][s] = True
                    rep_rows.append({
                        "rep": rep,
                        "day": day,
                        "timeslot": s,
                        "supplier": session["supplier"],
                        "booth": "",
                        "session_type": "Innovation Theater",
                        "category": "",
                        "total_opportunity": ""
                    })

        if not progress:
            break

        round_num += 1




def build_phase2_power_pairings(
    phase1,
    sellers_opp_df,
    supplier_busy,
    rep_busy,
    supplier_rows,
    rep_rows,
    sup_summary,
    rng
):
    """
    Book Power Pairing sessions:
    - Supplier + 1 seller
    - Seller chosen by district + PL, ordered by opportunity
    - Slot chosen randomly from all valid options

    HARD CONSTRAINT:
    - No Power Pairings on Tuesday, February 24th at 11:00 AM or 11:30 AM
    """

    # -------------------------------------------------
    # Hard-coded blocked window for Power Pairings
    # -------------------------------------------------
    BLOCKED_PP_DAY = "Tuesday, February 24th"
    BLOCKED_PP_SLOTS = {"11:00 AM", "11:30 AM"}

    # Collect all Power Pairing meetings
    meetings = []
    for supplier, ms in phase1.items():
        for m in ms:
            if m["session_type"].strip().lower() == "power pairing":
                meetings.append(m)

    # Highest opportunity first
    meetings.sort(key=lambda m: m["total_opportunity"], reverse=True)

    for m in meetings:
        supplier = m["supplier_name"]
        booth = m["booth"]
        req_name = m["request_name"]
        tot_opp = m["total_opportunity"]

        seller_spot = next(
            a for a in m["requested_attendees"]
            if isinstance(a, dict) and a.get("type") == "seller_spot"
        )

        district = seller_spot["district"].upper().strip()
        product_line = seller_spot.get("product_line")

        # Candidate sellers
        sellers = sellers_opp_df[
            sellers_opp_df["district"].str.upper() == district
        ]

        if product_line:
            sellers = sellers[
                sellers["product_line"].str.upper() == product_line.upper()
            ]

        sellers = sellers.sort_values("opportunity", ascending=False)

        booked = False

        for _, row in sellers.iterrows():
            seller = row["name"]

            valid_slots = []

            for day, slots in time_slots.items():
                for slot, label in slots.items():

                    # Skip lunch
                    if label == "LUNCH":
                        continue

                    # Skip Power Pairing blocked window
                    if (
                        day == BLOCKED_PP_DAY
                        and slot in BLOCKED_PP_SLOTS
                    ):
                        continue

                    if supplier_busy[supplier][day][slot]:
                        continue

                    if rep_busy[seller][day][slot]:
                        continue

                    valid_slots.append((day, slot))

            if not valid_slots:
                continue

            day, slot = rng.choice(valid_slots)

            # Mark busy
            supplier_busy[supplier][day][slot] = True
            rep_busy[seller][day][slot] = True

            supplier_rows.append({
                "supplier": supplier,
                "booth": booth,
                "day": day,
                "timeslot": slot,
                "session_type": "Power Pairing",
                "reps": [seller],
                "category": req_name,
                "total_opportunity": tot_opp
            })

            rep_rows.append({
                "rep": seller,
                "day": day,
                "timeslot": slot,
                "supplier": supplier,
                "booth": booth,
                "session_type": "Power Pairing",
                "category": req_name,
                "total_opportunity": tot_opp
            })

            sup_summary[supplier]["fulfilled"].append(req_name)
            booked = True
            break

        if not booked:
            sup_summary[supplier]["unfulfilled"].append(req_name)


def build_phase3_core_scheduler(preferences, reps_df, sellers_opp_df, seed):
    rng = random.Random(seed)

    phase1 = build_phase1_requested_attendees(preferences, reps_df, sellers_opp_df)

    supplier_rows = []
    rep_rows = []

    supplier_busy = {
        s: {d: {t: False for t in time_slots[d]} for d in time_slots}
        for s in preferences.keys()
    }

    rep_busy = {
        r: {d: {t: False for t in time_slots[d]} for d in time_slots}
        for r in reps_df["Rep Name"].tolist()
    }

    for day, blk in blocks.items():
        for slot, blocked in blk.items():
            for s in blocked:
                if s in supplier_busy:
                    supplier_busy[s][day][slot] = True

    sup_summary = {
        s: {
            "requested": [m["request_name"] for m in meetings],
            "fulfilled": [],
            "unfulfilled": [],
            "unfulfilled_power_pairings": []
        }
        for s, meetings in phase1.items()
    }

    # 🔹 Build innovation sessions ONCE
    innovation_sessions = build_innovation_sessions_from_blocks()

    # 🔹 Pass A: guarantee 1 per worker
    assign_minimum_innovation_sessions(
        reps_df,
        innovation_sessions,
        rep_busy,
        rep_rows,
        rng
    )

    # Strategy
    build_phase2_strategy_sessions(
        phase1, reps_df, sellers_opp_df,
        supplier_busy, rep_busy,
        supplier_rows, rep_rows,
        sup_summary, rng
    )

    # Planning
    build_phase2_planning_sessions(
        phase1, sellers_opp_df,
        supplier_busy, rep_busy,
        supplier_rows, rep_rows,
        sup_summary, rng
    )

    validation = {
        "total_unfulfilled": sum(len(v["unfulfilled"]) for v in sup_summary.values()),
        "unfulfilled_detail": {
            s: v["unfulfilled"]
            for s, v in sup_summary.items()
            if v["unfulfilled"]
        }
    }

    return {
        "seed": seed,
        "phase1": phase1,
        "supplier_rows": supplier_rows,
        "rep_rows": rep_rows,
        "supplier_busy": supplier_busy,
        "rep_busy": rep_busy,
        "innovation_sessions": innovation_sessions,
        "summary": sup_summary,
        "validation": validation
    }



def extend_with_addons(core_result, reps_df, sellers_opp_df, seed):
    rng = random.Random(seed)

    supplier_rows = list(core_result["supplier_rows"])
    rep_rows = list(core_result["rep_rows"])

    supplier_busy = deepcopy(core_result["supplier_busy"])
    rep_busy = deepcopy(core_result["rep_busy"])
    innovation_sessions = core_result["innovation_sessions"]

    sup_summary = deepcopy(core_result["summary"])
    phase1 = core_result["phase1"]

    # Power Pairings
    build_phase2_power_pairings(
        phase1, sellers_opp_df,
        supplier_busy, rep_busy,
        supplier_rows, rep_rows,
        sup_summary, rng
    )

    # 🔹 Pass B: fill innovation to 100
    # fill_innovation_sessions_to_capacity(
    #     reps_df,
    #     innovation_sessions,
    #     rep_busy,
    #     rep_rows,
    #     rng
    # )

    return {
        "seed": seed,
        "supplier_sched": pd.DataFrame(supplier_rows),
        "rep_sched": pd.DataFrame(rep_rows),
        "summary": sup_summary
    }



def count_unfulfilled(summary):
    total = 0
    suppliers = 0

    for s, v in summary.items():
        n = len(v.get("unfulfilled", []))
        if n > 0:
            suppliers += 1
            total += n

    return total, suppliers

def run_scheduler(preferences, reps_df, sellers_opp_df, core_seeds=10, addon_seeds=10):
    core_best = None
    core_diagnostics = []

    # Phase A: Core seed search
    for seed in range(core_seeds):
        print(f"Running core scheduler seed {seed}")

        result = build_phase3_core_scheduler(
            preferences, reps_df, sellers_opp_df, seed
        )

        total_un = result["validation"]["total_unfulfilled"]
        num_suppliers_un = len(result["validation"]["unfulfilled_detail"])

        core_diagnostics.append({
            "seed": seed,
            "total_unfulfilled": total_un,
            "num_suppliers_unfulfilled": num_suppliers_un
        })

        if core_best is None:
            core_best = result
            continue

        prev_un = core_best["validation"]["total_unfulfilled"]
        prev_sup = len(core_best["validation"]["unfulfilled_detail"])

        if (total_un < prev_un) or (
            total_un == prev_un and num_suppliers_un < prev_sup
        ):
            core_best = result

    print(f"Selected best core seed {core_best['seed']}")

    # Phase B: Extension seed search
    extended_best = None

    for seed in range(addon_seeds):
        print(f"Running extension seed {seed}")

        extended = extend_with_addons(
            core_best, reps_df, sellers_opp_df, seed
        )

        total_un, suppliers_un = count_unfulfilled(extended["summary"])

        if extended_best is None:
            extended_best = extended
            best_un = total_un
            best_sup = suppliers_un
            best_var = extended["rep_sched"]["rep"].value_counts().std()
            continue

        # Primary: fewer unfulfilled
        if total_un < best_un:
            extended_best = extended
            best_un = total_un
            best_sup = suppliers_un
            best_var = extended["rep_sched"]["rep"].value_counts().std()
            continue

        # Secondary: fewer suppliers impacted
        if total_un == best_un and suppliers_un < best_sup:
            extended_best = extended
            best_sup = suppliers_un
            best_var = extended["rep_sched"]["rep"].value_counts().std()
            continue

        # Optional tertiary: smoother rep load
        if total_un == best_un and suppliers_un == best_sup:
            rep_var = extended["rep_sched"]["rep"].value_counts().std()
            if rep_var < best_var:
                extended_best = extended
                best_var = rep_var

    print(
        f"Selected best extension seed {extended_best['seed']} "
        f"(unfulfilled={best_un}, suppliers={best_sup})"
    )

    return (
        extended_best["supplier_sched"],
        extended_best["rep_sched"],
        extended_best["summary"],
        core_best["validation"],
        # core_best["phase1"]
    )

