from app.utils import time_slots
import pandas as pd

# =====================================================================
#   Helper: Build Rows for One Day  (Supplier or Rep)
# =====================================================================
def _format_millions(x):
    if x is None or x == "" or pd.isna(x):
        return ""
    if x == 0:
        return "-"
    return f"${x/1_000_000:,.1f}M"

def _build_single_day_rows(day_name, data_map, *, mode):
    """
    mode = "supplier" → columns: Time | Request | Appointment With | Opp. $
    mode = "rep"      → columns: Time | Location | Supplier | Opp. $
    """

    html = ""
    row_idx = 0

    for t, blocked in time_slots[day_name].items():

        bg = "#FFFFFF" if row_idx % 2 == 0 else "#F7F7F7"

        # LUNCH
        if blocked == "LUNCH":
            html += f"""
            <tr style="background:{bg};">
                <td>{t}</td>
                <td colspan="3" style="font-weight:600; color:#C63434;">LUNCH</td>
            </tr>
            """
            row_idx += 1
            continue

        # BREAK
        if blocked == "BREAK":
            html += f"""
            <tr style="background:{bg};">
                <td>{t}</td>
                <td colspan="3" style="font-weight:600; color:#C63434;">BREAK</td>
            </tr>
            """
            row_idx += 1
            continue

        val = data_map.get((day_name, t), None)

        if mode == "supplier":
            if val is None:
                req = ""
                reps = "--AVAILABLE--"
                opp = ""
            else:
                req = val.get("category", "")
                reps = val.get("rep", "--AVAILABLE--")
                opp = _format_millions(val.get("opportunity", ""))

            html += f"""
            <tr style="background:{bg};">
                <td>{t}</td>
                <td>{req}</td>
                <td>{reps}</td>
                <td>{opp}</td>
            </tr>
            """

        elif mode == "rep":
            if val is None:
                booth = ""
                supplier = "--AVAILABLE--"
                opp = ""
            else:
                booth = "TBD" # val.get("booth", "")
                supplier = val.get("supplier", "--AVAILABLE--")
                opp = _format_millions(val.get("opportunity", ""))

            html += f"""
            <tr style="background:{bg};">
                <td>{t}</td>
                <td>{booth}</td>
                <td>{supplier}</td>
                <td>{opp}</td>
            </tr>
            """

        row_idx += 1

    return html


# =====================================================================
#   COMMON CSS (Tight alignment across all pages)
# =====================================================================
COMMON_CSS = """
@page { margin: 0; }

@media print {
    .no-print { display: none; }
    body { margin:0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}

body {
    font-family: 'Barlow', sans-serif;
    margin: 0;
    padding: 0;
}

.title {
    text-align: center;
    font-size: 30px;
    font-weight: 600;
    margin-top: 20px;
    color: #5533FF;
}

.subtitle {
    text-align: center;
    font-size: 17px;
    margin-top: 4px;
    color: #444;
}

.top-info {
    text-align: center;
    font-size: 17px;
    margin-top: 12px;
}

.top-info-small {
    text-align:center;
    font-size:14px;
    margin-top:2px;
    color:#666;
}

.section-title {
    text-align: center;
    font-size: 16px;
    font-weight: 600;
    margin: 6px 0 6px 0;
    color: #5533FF;
}

.flex-col {
    width: 80%;
    margin: 20px auto 0 auto;
    display: flex;
    flex-direction: column;
    gap: 22px;
}

.flex-row {
    width: 80%;
    margin: 20px auto;
    display: flex;
    flex-direction: row;
    justify-content: space-between;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th {
    background: #5533FF;
    color: white;
    padding: 6px;
    text-align: left;
    font-size: 13px;
}

td {
    padding: 6px;
    text-align: left;
    font-size: 12px;
}

.summary-box {
    width: 100%;
    padding: 12px;
    border-radius: 6px;
    background: #F7F4FF;
    border: 1px solid #CCC;
    font-size: 12px;
}

.endnote {
    width: 100%;
    font-size: 13px;
    color: #C63434;
}

.print-button {
    background: #5533FF;
    color: white;
    padding: 8px 16px;
    border-radius: 6px;
    text-decoration: none;
    font-size: 15px;
}

.print-container { text-align:center; margin:20px 0; }

.page-break { page-break-before: always; }
"""


# =====================================================================
#   SUPPLIER HTML
# =====================================================================
def render_supplier_html(supplier_name, booth, schedule_df, supplier_summary, reps_df):

    # ===============================================================
    # BUILD DAY TABLE MAPPING
    # ===============================================================
    data_map = {
        (r["day"], r["timeslot"]): {
            "rep": ", ".join(r["reps"]) if isinstance(r["reps"], list) else r["reps"],
            "category": r["category"],
            "opportunity": r.get("total_opportunity", "")
        }
        for _, r in schedule_df.iterrows()
    }

    days = list(time_slots.keys())
    day_blocks = []

    for day in days:
        rows = _build_single_day_rows(day, data_map, mode="supplier")
        day_blocks.append(f"""
        <div>
            <div class="section-title">{day}</div>
            <table>
                <tr>
                    <th style="width:10%;">Time</th>
                    <th style="width:35%;">Request</th>
                    <th style="width:45%;">Appointment With</th>
                    <th style="width:10%;">Opp. $</th>
                </tr>
                {rows}
            </table>
        </div>
        """)

    all_reps = []
    for _, r in schedule_df.iterrows():
        reps = r["reps"]
        if isinstance(reps, list):
            all_reps.extend(reps)

    all_reps = list(dict.fromkeys(all_reps))  # unique preserve order

    # Build (name, role) tuples
    role_rows = []
    for rep in all_reps:
        match = reps_df[reps_df["Rep Name"] == rep]
        role = match["Role"].iloc[0] if ("Role" in match and len(match) > 0) else ""
        role_rows.append((rep, role))

    # Split evenly between left and right
    half = (len(role_rows) + 1) // 2
    left_rows = role_rows[:half]
    right_rows = role_rows[half:]

    def build_role_table(rows):
        html = ""
        idx = 0
        for name, role in rows:
            bg = "#FFFFFF" if idx % 2 == 0 else "#F2F2F2"
            html += f"""
            <tr style="background:{bg}; font-size:11px;">
                <td style="padding:5px; font-size:10px; width:30%;">{name}</td>
                <td style="padding:5px; font-size:10px; width:70%;">{role}</td>
            </tr>
            """
            idx += 1
        return html

    left_table = build_role_table(left_rows)
    right_table = build_role_table(right_rows)

    roles_html = f"""
    <div class="section-title" style="margin-top:16px; margin-bottom:4px;">Representative Roles</div>

    <div class="flex-row" style="margin-top:5px;">

        <div style="width:48%;">
            <table style="width:100%; border-collapse:collapse;">
                <tr>
                    <th style="width:30%; font-size:12px;">Name</th>
                    <th style="width:70%; font-size:12px;">Role</th>
                </tr>
                {left_table}
            </table>
        </div>

        <div style="width:48%;">
            <table style="width:100%; border-collapse:collapse;">
                <tr>
                    <th style="width:30%; font-size:12px;">Name</th>
                    <th style="width:70%; font-size:12px;">Role</th>
                </tr>
                {right_table}
            </table>
        </div>

    </div>
    """

    # ===============================================================
    # NOTE AT BOTTOM
    # ===============================================================
    note_html = """
    <div class="endnote" style="width:85%; margin:30px auto 10px auto;">
        Representatives may have free slots. For additional availability,
        please check with the Information Desk staff.
    </div>
    """

    # ===============================================================
    # FINAL HTML ASSEMBLY
    # ===============================================================
    body_days = "".join(day_blocks)

    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>{COMMON_CSS}</style>
        <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;500;600&display=swap" rel="stylesheet">
    </head>

    <body>

        <div class="title">2026 Supplier Growth Summit</div>
        <div class="subtitle">February 23rd – 25th</div>
        <div class="top-info">{supplier_name}</div>

        <div class="print-container no-print">
            <a class="print-button" onclick="window.print()">Save PDF</a>
        </div>

        <div class="flex-col" style="gap:10px; margin-top:10px;">
            {body_days}
        </div>

        {roles_html}

        {note_html}

    </body>
    </html>
    """

def render_request_summary_table(supplier_summary):
    requested = supplier_summary.get("requested", [])
    fulfilled = set(supplier_summary.get("fulfilled", []))
    substitutions = supplier_summary.get("substitutions", {})
    req_types = supplier_summary.get("req_types", {})

    summary_rows = ""
    row_idx = 0

    for req in requested:
        row_bg = "#FFFFFF" if row_idx % 2 == 0 else "#F7F7F7"

        is_fulfilled = req in fulfilled
        subs = substitutions.get(req, [])
        req_type = req_types.get(req, "Name")

        # scoring
        if req_type != "Name":
            score = 5 if is_fulfilled else 0
        else:
            score = max(1, 5 - len(subs))

        # unavailable names in red
        if subs:
            subs_str = ", ".join(
                f"<span style='color:#C63434;'>{s}</span>"
                for s in subs
            )
        else:
            subs_str = ""

        summary_rows += f"""
        <tr style="background:{row_bg}; font-size:12px;">
            <td style="padding:6px; width:55%;">{req}</td>
            <td style="padding:6px; width:30%;">{subs_str}</td>
            <td style="padding:6px; text-align:center; width:15%;">{score}</td>
        </tr>
        """

        row_idx += 1

    # full HTML with CSS included
    return f"""
    <html>
    <head>
        <style>{COMMON_CSS}</style>
        <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;500;600&display=swap" rel="stylesheet">
    </head>

    <body style="background:white;">

        <div class="section-title" style="margin-top:4px; margin-bottom:4px;">
            Request Summary
        </div>

        <table style="width:80%; margin:auto; border-collapse:collapse; font-size:12px;">
            <tr>
                <th style="width:55%;">Request</th>
                <th style="width:30%;">Unavailable(s)</th>
                <th style="width:15%;">Score</th>
            </tr>
            {summary_rows}
        </table>

    </body>
    </html>
    """


# =====================================================================
#   REP HTML
# =====================================================================
def render_rep_html(rep_name, schedule_df, suppliers_df, reps_df):

    rep_email = reps_df.loc[
        reps_df["Rep Name"] == rep_name, "Email"
    ].fillna("").iloc[0]

    data_map = {}
    for _, r in schedule_df.iterrows():
        supplier = r.get("supplier")
        if supplier is None:
            data_map[(r["day"], r["timeslot"])] = None
        else:
            booth = suppliers_df.loc[
                suppliers_df["Supplier"] == supplier, "Booth"
            ].iloc[0]
            data_map[(r["day"], r["timeslot"])] = {
                "supplier": supplier,
                "booth": booth,
                "opportunity": r.get("total_opportunity", "")
            }

    days = list(time_slots.keys())
    day_blocks = []

    for day in days:
        rows = _build_single_day_rows(day, data_map, mode="rep")
        day_blocks.append(f"""
        <div>
            <div class="section-title">{day}</div>
            <table>
                <tr>
                    <th style="width:20%;">Time</th>
                    <th style="width:20%;">Location</th>
                    <th style="width:45%;">Supplier</th>
                    <th style="width:15%;">Opp. $</th>
                </tr>
                {rows}
            </table>
        </div>
        """)

    body_days = "".join(day_blocks)

    note_html = """
    <div class="endnote" style="width:80%; margin:20px auto;">
        During available slots, please visit Associate and Program Suppliers.
    </div>
    """

    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>{COMMON_CSS}</style>
        <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;500;600&display=swap" rel="stylesheet">
    </head>

    <body>

        <div class="title">2026 Supplier Growth Summit</div>
        <div class="subtitle">February 23rd – 25th</div>

        <div class="top-info">{rep_name}</div>
        <div class="top-info-small">{rep_email}</div>

        <div class="print-container no-print">
            <a class="print-button" onclick="window.print()">Save PDF</a>
        </div>

        <div class="flex-col">
            {body_days}
        </div>

        {note_html}

    </body>
    </html>
    """


# =====================================================================
#   Combined HTML for multi-page PDF printing
# =====================================================================
import base64

def load_logo_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def render_intro_page(logo_b64: str):
    return f"""
    <div style="height:10px;"></div>

    <div style="width:80%; margin:0 auto; display:flex; justify-content:flex-end; padding:8px 0;">
        <img src="data:image/png;base64,{logo_b64}" style="height:45px;"/>
    </div>

    <div style="
        width:80%;
        margin:0 auto;
        background-color:#5533FF;
        padding:18px;
        border-radius:6px;
        text-align:center;
        margin-bottom:22px;
    ">
        <h1 style="color:white; margin:0; font-family:Barlow, sans-serif;">
            Supplier Growth Summit Schedules
        </h1>
    </div>

    <div style="width:80%; margin:0 auto; font-family:Barlow, sans-serif; line-height:1.45;">

        <!-- ================================================= -->
        <h2 style="color:#5533FF; font-size:20px;">Scope & Definitions</h2>

        <p style="font-size:14px;">
            The list of attending Sales Representatives was sourced from the MSC invite list delivered by Leah Bacon on Jan. 6, 2026.
            Supplier meeting requests come from the Growth Forum Insights Meeting Tracker via SharePoint.
        </p>

        <p style="font-size:14px; margin-top:10px;">
            <b>Supplier Requests</b> were standardized to representative names or regions, following these rules:
        </p>

        <ul style="font-size:14px; margin-left:20px;">
            <li>Use explicit region or name requests when provided.</li>
            <li>If a request references a sector or vertical, assign reps most aligned with opportunity.</li>
            <li>When unclear, assign the region with the greatest modeled opportunity.</li>
        </ul>

        <!-- ================================================= -->
        <h2 style="color:#5533FF; font-size:20px; margin-top:20px;">Scheduling Overview</h2>

        <p style="font-size:14px;">
            Each supplier request is interpreted into the representatives who should attend.  
            Region-based requests expand into VP, Region, or District Leaders depending on whether the supplier is Peak or Accelerating.
            Workloads are balanced so no rep exceeds their daily meeting limit. When conflicts occur, substitution logic is applied:
        </p>

        <ul style="font-size:14px; margin-left:20px;">
            <li><b>Senior Leaders:</b> replaced with relevant Region or District Leaders.</li>
            <li><b>Region Leaders:</b> replaced with District Leaders in the same region.</li>
            <li><b>District Leaders:</b> swapped with another District Leader in the same region.</li>
            <li>Non-replaceable reps are marked unavailable.</li>
            <li>See the Supplier Growth Summit Schedules Model Output for a complete record of substitutions.</li>
        </ul>

        <p style="font-size:14px; margin-top:10px;">
            Scheduling prioritizes Peak suppliers first, then Accelerating.  
            Meetings are processed in priority order, and a placement is made only when:
        </p>

        <ul style="font-size:14px; margin-left:20px;">
            <li>All assigned representatives are available.</li>
            <li>The supplier has no existing booking in that timeslot.</li>
            <li>No representative meets with the same supplier more than once.</li>
        </ul>

        <p style="font-size:14px;">
            Multiple configurations are evaluated, and the solution
            with the fewest unscheduled or substituted representatives is selected.
        </p>

        <!-- ================================================= -->
        <h2 style="color:#5533FF; font-size:20px; margin-top:20px;">Support</h2>

        <p style="font-size:14px;">
            For questions, contact <b>Precision Business Solutions</b><br>
            Henrik Elster &lt;helster@precisionmarketdata.com&gt;<br>
            Kameel Dossal &lt;kdossal@precisionmarketdata.com&gt;
        </p>

    </div>
    """



def build_combined_html(html_pages, logo_path="files/logos.png"):
    """
    Inserts an intro page as the first sheet, then all schedule pages.
    """

    # Extract shared <head> from the first page
    first = html_pages[0]
    head = first.split("<head>")[1].split("</head>")[0]

    # Load logo for intro sheet
    logo_b64 = load_logo_base64(logo_path)

    # Build intro sheet
    intro_body = render_intro_page(logo_b64)

    pages = []

    # Add intro page as page 1
    pages.append(f"<div>{intro_body}</div><div class='page-break'></div>")

    # Add all schedule pages
    for i, html in enumerate(html_pages):
        body = html.split("<body>")[1].split("</body>")[0]
        if i < len(html_pages) - 1:
            pages.append(f"<div>{body}</div><div class='page-break'></div>")
        else:
            pages.append(f"<div>{body}</div>")

    return f"""
    <html>
    <head>{head}</head>
    <body>
        {''.join(pages)}
    </body>
    </html>
    """



def html_to_pdf(html):
    return html
