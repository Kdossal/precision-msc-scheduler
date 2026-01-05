from app.utils import time_slots

# =====================================================================
#   Helper: Build Rows for One Day  (Supplier or Rep)
# =====================================================================
def _build_single_day_rows(day_name, data_map, *, mode):
    """
    mode = "supplier" → columns: Time | Request | Appointment With
    mode = "rep"      → columns: Time | Booth | Supplier
    """

    html = ""
    row_idx = 0

    for t, blocked in time_slots[day_name].items():

        bg = "#FFFFFF" if row_idx % 2 == 0 else "#F7F7F7"

        # ----- LUNCH -----
        if blocked == "LUNCH":
            html += f"""
            <tr style="background:{bg};">
                <td>{t}</td>
                <td colspan="2" style="font-weight:600; color:#C63434;">LUNCH</td>
            </tr>
            """
            row_idx += 1
            continue

        # ----- BREAK -----
        if blocked == "BREAK":
            html += f"""
            <tr style="background:{bg};">
                <td>{t}</td>
                <td colspan="2" style="font-weight:600; color:#C63434;">BREAK</td>
            </tr>
            """
            row_idx += 1
            continue

        val = data_map.get((day_name, t), None)

        if mode == "supplier":
            if val is None:
                req = ""
                reps = "--AVAILABLE--"
            else:
                req = val.get("category", "")
                reps = val.get("rep", "--AVAILABLE--")

            html += f"""
            <tr style="background:{bg};">
                <td>{t}</td>
                <td>{req}</td>
                <td>{reps}</td>
            </tr>
            """

        elif mode == "rep":
            if val is None:
                booth = ""
                supplier = "--AVAILABLE--"
            else:
                booth = val.get("booth", "")
                supplier = val.get("supplier", "--AVAILABLE--")

            html += f"""
            <tr style="background:{bg};">
                <td>{t}</td>
                <td>{booth}</td>
                <td>{supplier}</td>
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
    font-size: 18px;
    font-weight: 600;
    margin: 10px 0 6px 0;
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
    font-size: 14px;
}

td {
    padding: 6px;
    text-align: left;
    font-size: 13px;
}

.summary-box {
    width: 100%;
    padding: 12px;
    border-radius: 6px;
    background: #F7F4FF;
    border: 1px solid #CCC;
    font-size: 14px;
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
def render_supplier_html(supplier_name, booth, schedule_df, supplier_summary):

    # Build mapping
    data_map = {
        (r["day"], r["timeslot"]): {
            "rep": ", ".join(r["reps"]) if isinstance(r["reps"], list) else r["reps"],
            "category": r["category"]
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
                    <th style="width:18%;">Time</th>
                    <th style="width:28%;">Request</th>
                    <th style="width:54%;">Appointment With</th>
                </tr>
                {rows}
            </table>
        </div>
        """)

    # summary list
    summary = supplier_summary["requested"]
    fulfilled = set(supplier_summary["fulfilled"])

    summary_lines = [
        f"{req}" if req in fulfilled else f"{req} <span style='color:#C63434;'>[UNAVAILABLE]</span>"
        for req in summary
    ]

    summary_html = f"""
    <div style="width:45%;">
        <div class="section-title">Request Summary</div>
        <div class="summary-box">
            {"<br>".join(summary_lines)}
        </div>
    </div>
    """

    note_html = """
    <div style="width:45%;">
        <div class="section-title">Notes</div>
        <div class="endnote">
            Representatives may have free slots. For additional availability,
            please check with the Information Desk Staff.
        </div>
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
        <div class="title">2026 Supplier Growth Summit</div>
        <div class="subtitle">February 23rd – 25th</div>

        <div class="top-info">{supplier_name} — Booth {booth}</div>

        <div class="print-container no-print">
            <a class="print-button" onclick="window.print()">Save PDF</a>
        </div>

        <div class="flex-col">
            {body_days}
        </div>

        <div class="flex-row">
            {summary_html}
            {note_html}
        </div>

    </body>
    </html>
    """


# =====================================================================
#   REP HTML (now includes EMAIL)
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
                "booth": booth
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
                    <th style="width:20%;">Booth</th>
                    <th style="width:60%;">Supplier</th>
                </tr>
                {rows}
            </table>
        </div>
        """)

    body_days = "".join(day_blocks)

    note_html = """
    <div class="endnote" style="width:80%; margin: 20px auto;">
        Sponsor Suite meetings override floor appointments. During free slots,
        please visit Associate and Program Suppliers.
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
def build_combined_html(html_pages):
    first = html_pages[0]
    head = first.split("<head>")[1].split("</head>")[0]

    page_blocks = []
    for i, html in enumerate(html_pages):
        body = html.split("<body>")[1].split("</body>")[0]
        if i < len(html_pages) - 1:
            page_blocks.append(f"<div>{body}</div><div class='page-break'></div>")
        else:
            page_blocks.append(f"<div>{body}</div>")

    return f"""
    <html>
    <head>{head}</head>
    <body>
        {''.join(page_blocks)}
    </body>
    </html>
    """


def html_to_pdf(html):
    return html
