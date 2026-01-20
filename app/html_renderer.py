from app.utils import time_slots, blocks, act_session_times
import pandas as pd

# =====================================================================
#   Helper: Build Rows for One Day  (Supplier or Rep)
# =====================================================================
def _format_millions(x):
    if x is None or x == "" or pd.isna(x):
        return ""
    if x == 0:
        return "n/a"
    if abs(x) < 1_000_000:
        return f"${int(round(x / 1_000)):,.0f}k"
    return f"${x / 1_000_000:,.1f}M"


def _build_single_day_rows(day_name, data_map, supplier_name=None, *, mode):
    """
    mode:
      supplier_full   → Time | Session | Request | Appointment With | Opp. $
      supplier_light  → Time | Session | Request | Appointment With
      rep             → Time | Location | Session | Supplier | Opp. $
    """

    html = ""
    row_idx = 0
    day_blocks = blocks.get(day_name, {})
    slot_list = list(time_slots[day_name].keys())
    n = len(slot_list)
    i = 0

    while i < n:
        t = slot_list[i]
        default_marker = time_slots[day_name][t]
        bg = "#FFFFFF" if row_idx % 2 == 0 else "#F7F7F7"

        # ----------------------------------
        # Lunch / Break
        # ----------------------------------
        if default_marker in ("LUNCH", "BREAK"):
            cells = f"<td>{t}</td><td></td><td style='font-weight:600; color:#C63434;'>{default_marker}</td><td></td>"
            if mode == "supplier_full" or mode == "rep":
                cells += "<td></td>"

            html += f"<tr style='background:{bg};'>{cells}</tr>"
            i += 1
            row_idx += 1
            continue

        # ----------------------------------
        # Supplier Innovation block
        # ----------------------------------
        if mode.startswith("supplier") and supplier_name:
            blocked = day_blocks.get(t, [])
            if supplier_name in blocked:
                time_cell = act_session_times.get(supplier_name, t)

                j = i + 1
                while j < n and supplier_name in day_blocks.get(slot_list[j], []):
                    j += 1
                i = j

                cells = f"""
                    <td>{time_cell}</td>
                    <td></td>
                    <td>Innovation Theater Presentation</td>
                    <td></td>
                """
                if mode == "supplier_full":
                    cells += "<td></td>"

                html += f"<tr style='background:{bg};'>{cells}</tr>"
                row_idx += 1
                continue

        # ----------------------------------
        # Lookup scheduled meeting
        # ----------------------------------
        val = data_map.get((day_name, t))

        if not val:
            cells = f"<td>{t}</td><td></td><td>--AVAILABLE--</td><td></td>"
            if mode in ("supplier_full", "rep"):
                cells += "<td></td>"

            html += f"<tr style='background:{bg};'>{cells}</tr>"
            i += 1
            row_idx += 1
            continue

        session = val["session_type"]

        # ----------------------------------
        # Innovation Theater (rep view)
        # ----------------------------------
        if mode == "rep" and session == "Innovation Theater":
            supplier = val.get("supplier", "")
            time_cell = act_session_times.get(supplier, t)

            j = i + 1
            while j < n:
                nxt = data_map.get((day_name, slot_list[j]))
                if nxt and nxt.get("session_type") == "Innovation Theater" and nxt.get("supplier") == supplier:
                    j += 1
                else:
                    break
            i = j

            html += f"""
            <tr style="background:{bg};">
                <td>{time_cell}</td>
                <td>TBD</td>
                <td>Innovation Theater</td>
                <td>{supplier}</td>
                <td></td>
            </tr>
            """
            row_idx += 1
            continue

        # ----------------------------------
        # Strategy merge (2-slot)
        # ----------------------------------
        time_cell = t
        if session == "Strategy" and i + 1 < n:
            nxt = data_map.get((day_name, slot_list[i + 1]))
            if nxt and nxt.get("session_type") == "Strategy" and nxt.get("category") == val.get("category"):
                time_cell = f"<div style='height:3mm'></div>{t}<div style='height:3mm'></div>"
                i += 2
            else:
                i += 1
        else:
            i += 1

        # ----------------------------------
        # Render rows
        # ----------------------------------
        if mode.startswith("supplier"):
            opp_cell = ""
            if mode == "supplier_full" and session not in ("Power Pairing",):
                opp_cell = _format_millions(val.get("opportunity", ""))

            cells = f"""
                <td>{time_cell}</td>
                <td>{session}</td>
                <td>{val.get("category","")}</td>
                <td>{val.get("rep","")}</td>
            """
            if mode == "supplier_full":
                cells += f"<td>{opp_cell}</td>"

        else:  # rep view
            opp_cell = "" if session in ("Power Pairing", "Innovation Theater") else _format_millions(val.get("opportunity", ""))

            cells = f"""
                <td>{time_cell}</td>
                <td>TBD</td>
                <td>{session}</td>
                <td>{val.get("supplier","")}</td>
                <td>{opp_cell}</td>
            """

        html += f"<tr style='background:{bg};'>{cells}</tr>"
        row_idx += 1

    return html



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

    has_major_sessions = (
        schedule_df["session_type"]
        .fillna("")
        .str.lower()
        .isin(["strategy", "planning"])
        .any()
    )

    mode = "supplier_full" if has_major_sessions else "supplier_light"

    col_widths = (
        {"time":"15%","session":"12%","request":"28%","reps":"35%","opp":"10%"}
        if mode == "supplier_full"
        else {"time":"15%","session":"20%","request":"28%","reps":"27%"}
    )

    data_map = {
        (r["day"], r["timeslot"]): {
            "rep": ", ".join(r["reps"]) if isinstance(r["reps"], list) else r["reps"],
            "category": r["category"],
            "opportunity": r.get("total_opportunity", ""),
            "session_type": r.get("session_type", ""),
            "supplier": supplier_name
        }
        for _, r in schedule_df.iterrows()
    }

    day_blocks = []
    for day in time_slots:
        rows = _build_single_day_rows(day, data_map, supplier_name, mode=mode)

        headers = f"""
            <th style="width:{col_widths['time']};">Time</th>
            <th style="width:{col_widths['session']};">Session</th>
            <th style="width:{col_widths['request']};">Request</th>
            <th style="width:{col_widths['reps']};">Appointment With</th>
        """
        if mode == "supplier_full":
            headers += f"<th style='width:{col_widths['opp']};'>Opp. $</th>"

        day_blocks.append(f"""
        <div>
            <div class="section-title">{day}</div>
            <table>
                <tr>{headers}</tr>
                {rows}
            </table>
        </div>
        """)

    # --------------------------------------------------
    # Representative Roles Section
    # --------------------------------------------------
    all_reps = []
    for _, r in schedule_df.iterrows():
        if isinstance(r["reps"], list):
            all_reps.extend(r["reps"])

    all_reps = list(dict.fromkeys(all_reps))

    role_rows = []
    for rep in all_reps:
        match = reps_df[reps_df["Rep Name"] == rep]
        role = match["Role"].iloc[0] if len(match) > 0 else ""
        role_rows.append((rep, role))

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
                <td style="padding:5px; width:30%;">{name}</td>
                <td style="padding:5px; width:70%;">{role}</td>
            </tr>
            """
            idx += 1
        return html

    roles_html = f"""
    <div class="section-title" style="margin-top:18px;">Representative Roles</div>

    <div class="flex-row" style="margin-top:4px;">
        <div style="width:48%;">
            <table>
                <tr>
                    <th style="width:30%;">Name</th>
                    <th style="width:70%;">Role</th>
                </tr>
                {build_role_table(left_rows)}
            </table>
        </div>
        <div style="width:48%;">
            <table>
                <tr>
                    <th style="width:30%;">Name</th>
                    <th style="width:70%;">Role</th>
                </tr>
                {build_role_table(right_rows)}
            </table>
        </div>
    </div>
    """

    note_html = """
    <div class="endnote" style="width:85%; margin:30px auto 10px auto;">
        Representatives may have free slots. For additional availability,
        please check with the Information Desk staff.
    </div>
    """

    body_days = "".join(day_blocks)

    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>{COMMON_CSS}</style>
        <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;500;600&display=swap" rel="stylesheet">
    </head>

    <body>

        <div class="title">2026 Supplier Growth Forum</div>
        <div class="subtitle">February 23rd – 25th</div>
        <div class="top-info">{supplier_name}</div>

        <div class="print-container no-print">
            <a class="print-button" onclick="window.print()">Save PDF</a>
        </div>

        <div class="flex-col" style="gap:10px; margin-top:10px;">
            {body_days}
        </div>

        <div class='page-break'></div>
        <br><br>

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
                "session_type": r.get("session_type", ""),
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
                    <th style="width:18%;">Time</th>
                    <th style="width:18%;">Location</th>
                    <th style="width:18%;">Session</th>
                    <th style="width:36%;">Supplier</th>
                    <th style="width:10%;">Opp. $</th>
                </tr>
                {rows}
            </table>
        </div>
        """)

    body_days = "".join(day_blocks)

    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>{COMMON_CSS}</style>
        <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;500;600&display=swap" rel="stylesheet">
    </head>

    <body>

        <div class="title">2026 Supplier Growth Forum</div>
        <div class="subtitle">February 23rd – 25th</div>

        <div class="top-info">{rep_name}</div>
        <div class="top-info-small">{rep_email}</div>

        <div class="print-container no-print">
            <a class="print-button" onclick="window.print()">Save PDF</a>
        </div>

        <div class="flex-col">
            {body_days}
        </div>

    </body>
    </html>
    """



#   Combined HTML for multi-page PDF printing
import base64

def load_logo_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def render_intro_page(logo_b64: str):
    return f"""
    <div style="height:8px;"></div>

    <div style="width:80%; margin:0 auto; display:flex; justify-content:flex-end; padding:6px 0;">
        <img src="data:image/png;base64,{logo_b64}" style="height:42px;"/>
    </div>

    <div style="
        width:80%;
        margin:0 auto;
        background-color:#5533FF;
        padding:16px;
        border-radius:6px;
        text-align:center;
        margin-bottom:18px;
    ">
        <h1 style="color:white; margin:0; font-family:Barlow, sans-serif;">
            Supplier Growth Forum Schedules
        </h1>
    </div>

    <div style="width:80%; margin:0 auto; font-family:Barlow, sans-serif; line-height:1.4;">

        <!-- ================================================= -->
        <h2 style="color:#5533FF; font-size:20px; margin-bottom:6px;">
            Logic & Assumptions
        </h2>

        <ul style="font-size:14px; margin:4px 0 10px 18px;">
            <li><b>Peak Suppliers</b> – 6 Strategy Sessions &amp; maximum of 12 Planning Sessions</li>
            <li><b>Accelerating Suppliers</b> – 3 Strategy Sessions &amp; maximum of 18 Planning Sessions</li>
            <li><b>Rising Suppliers</b> – maximum of 22 Power Pairings</li>
            <li>No representative meets with the same supplier more than once.</li>
        </ul>

        <!-- ================================================= -->
        <h3 style="color:#5533FF; font-size:16px; margin:8px 0 4px 0;">
            Strategy Sessions
        </h3>

        <ul style="font-size:14px; margin:2px 0 8px 18px;">
            <li>Includes District Leaders &amp; Sellers (Regional Directors optional to join at their discretion)</li>
            <li>Participants assigned based on supplier meeting requests (where provided)</li>
            <li>60 minutes long</li>
        </ul>

        <!-- ================================================= -->
        <h3 style="color:#5533FF; font-size:16px; margin:8px 0 4px 0;">
            Planning Sessions
        </h3>

        <ul style="font-size:14px; margin:2px 0 8px 18px;">
            <li>Includes only Sellers</li>
            <li>Participants assigned based on districts with highest opportunity per supplier</li>
            <li>30 minutes long</li>
        </ul>

        <!-- ================================================= -->
        <h3 style="color:#5533FF; font-size:16px; margin:8px 0 4px 0;">
            Power Pairings
        </h3>

        <ul style="font-size:14px; margin:2px 0 8px 18px;">
            <li>Includes a single Seller</li>
            <li>Participants assigned based on districts with highest opportunity per supplier</li>
            <li>30 minutes long</li>
        </ul>

        <!-- ================================================= -->
        <h3 style="color:#5533FF; font-size:16px; margin:8px 0 4px 0;">
            Opportunity
        </h3>

        <p style="font-size:14px; margin:2px 0 4px 0;">
            Assumes the following Close Rates (varies by Product Line):
        </p>

        <ul style="font-size:14px; margin:2px 0 10px 18px;">
            <li>Penetration: 5%</li>
            <li>Acquisition: 1%</li>
        </ul>

        <p style="font-size:14px; margin:6px 0 12px 0;">
            List of sales reps attending sourced from Leah Bacon &amp; Casey Ray<br>
            Sales Team Hierarchy &amp; Roles sourced as is from Steve Huffman &amp; Katie Risolo
        </p>

        <!-- ================================================= -->
        <h2 style="color:#5533FF; font-size:20px; margin:12px 0 6px 0;">
            Support
        </h2>

        <p style="font-size:14px; margin:0;">
            For questions, contact <b>Precision</b><br>
            Jesse Katz &lt;jkatz@precisionmarketdata.com&gt;<br>
            Henrik Elster &lt;helster@precisionmarketdata.com&gt;
        </p>

    </div>
    """


def render_supplier_toc_page(logo_b64, supplier_names, start_page):
    """
    Builds paginated Table of Contents pages for Supplier schedules.
    Breaks after 27 rows while preserving layout.
    """

    # Build full TOC entries first
    entries = []
    for i, name in enumerate(supplier_names):
        entries.append((name, start_page + i*2))

    # Logic & Assumptions entry
    entries.append((
        "Logic & Assumptions",
        start_page + len(supplier_names)*2
    ))

    ROWS_PER_PAGE = 27
    chunks = [
        entries[i:i + ROWS_PER_PAGE]
        for i in range(0, len(entries), ROWS_PER_PAGE)
    ]

    pages = []

    for page_idx, chunk in enumerate(chunks):

        rows_html = ""
        for name, page_num in chunk:
            rows_html += f"""
                <tr>
                    <td>{name}</td>
                    <td style="text-align:right;">{page_num}</td>
                </tr>
            """

        page_html = f"""
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
            margin-bottom:12px;
        ">
            <h1 style="color:white; margin:0; font-family:Barlow, sans-serif;">
                Supplier Growth Forum Schedules
            </h1>
        </div>

        <div class="section-title">
            Table of Contents
        </div>

        <div style="width:80%; margin:0 auto;">
            <table>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        """

        pages.append(page_html)

    # Join pages with hard page breaks
    return "<div class='page-break'></div>".join(pages)




def build_combined_html(
    html_pages,
    logo_path="files/logos.png",
    mode="Supplier",
    supplier_names=None
):
    """
    Builds a printable HTML document with:
    - TOC page
    - Schedule pages
    - Logic & Assumptions page (last)
    """

    first = html_pages[0]
    head = first.split("<head>")[1].split("</head>")[0]

    logo_b64 = load_logo_base64(logo_path)

    pages = []

    # -----------------------------
    # SUPPLIER MODE
    # -----------------------------
    if mode == "Supplier":

        if supplier_names is None:
            raise ValueError("supplier_names must be provided for Supplier mode")

        # Page numbers:
        # 1 = TOC
        # 2..N = suppliers
        # last = Logic & Assumptions
        toc_body = render_supplier_toc_page(
            logo_b64=logo_b64,
            supplier_names=supplier_names,
            start_page=7
        )

        pages.append(f"<div>{toc_body}</div><div class='page-break'></div>")

        # Supplier pages
        for html in html_pages:
            body = html.split("<body>")[1].split("</body>")[0]
            pages.append(f"<div>{body}</div><div class='page-break'></div>")

        # Logic & Assumptions (last page, no page break)
        logic_body = render_intro_page(logo_b64)
        pages.append(f"<div>{logic_body}</div>")

    # -----------------------------
    # REP MODE (placeholder)
    # -----------------------------
    else:
        # Rep schedule pages
        for html in html_pages:
            body = html.split("<body>")[1].split("</body>")[0]
            pages.append(f"<div>{body}</div><div class='page-break'></div>")

        # Logic & Assumptions (last page, no page break)
        logic_body = render_intro_page(logo_b64)
        pages.append(f"<div>{logic_body}</div>")

    return f"""
    <html>
        <head>{head}</head>
        <body>
            {''.join(pages)}
        </body>
    </html>
    """
