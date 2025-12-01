from app.utils import time_slots


# -------------------------------------------------------------
#    Build Day Tables (with alternating row colors)
# -------------------------------------------------------------
def _build_single_day_rows(day_name, timeslot_map, include_booth=False, include_category=False):
    html = ""
    row_index = 0

    for t, blocked_reason in time_slots[day_name].items():

        # Row color selection — darker grey
        bg = "#FFFFFF" if row_index % 2 == 0 else "#F2F2F2"

        # --------------------------
        # LUNCH / BREAK Rows
        # --------------------------
        if blocked_reason == "LUNCH":
            html += f"""
            <tr style="background:{bg};">
                <td>{t}</td>
                <td colspan="3" style="color:#C63434; font-weight:600;">LUNCH</td>
            </tr>
            """
            row_index += 1
            continue

        if blocked_reason == "BREAK":
            html += f"""
            <tr style="background:{bg};">
                <td>{t}</td>
                <td colspan="3" style="color:#C63434; font-weight:600;">BREAK</td>
            </tr>
            """
            row_index += 1
            continue

        # --------------------------
        # Normal appointment row
        # --------------------------
        val = timeslot_map.get((day_name, t), "--AVAILABLE--")

        if include_booth:  # Representative schedule
            if val == "--AVAILABLE--":
                supplier = "--AVAILABLE--"
                booth = ""
            else:
                supplier = val["supplier"]
                booth = val["booth"]

            html += f"""
            <tr style="background:{bg};">
                <td>{t}</td>
                <td>{booth}</td>
                <td>{supplier}</td>
            </tr>
            """

        else:  # Supplier schedule
            if val == "--AVAILABLE--":
                rep = "--AVAILABLE--"
                category = ""
            else:
                rep = val["rep"]
                category = val.get("category", "")

            html += f"""
            <tr style="background:{bg};">
                <td>{t}</td>
                <td>{rep}</td>
                {"<td>"+category+"</td>" if include_category else ""}
            </tr>
            """

        row_index += 1

    return html


# -------------------------------------------------------------
#     COMMON CSS
# -------------------------------------------------------------
COMMON_CSS = """
@page { margin: 0; }

@media print {
    .no-print { display: none; }
    body {
        margin: 0;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }
}

body {
    font-family: 'Barlow', sans-serif;
    margin: 0;
    background: #ffffff;
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
    font-size: 16px;
    margin-top: 4px;
    color: #444;
}

.grid-container {
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
    gap: 0px;
    width: 95%;
    margin: 20px auto 0 auto;
}

.grid-cell {
    padding: 5px 10px;
}

.section-title {
    text-align: center;
    font-size: 18px;
    font-weight: 600;
    margin: 6px 0 6px 0;
    color: #5533FF;
}

table {
    width: 100%;
    border-collapse: collapse;
    background: white;
}

/* ✔ FIX: Left-align header + cells */
th {
    background: #5533FF;
    color: white;
    padding: 6px;
    font-size: 14px;
    text-align: left;
}

td {
    padding: 6px;
    font-size: 13px;
    text-align: left;
}

.summary-box {
    width: 95%;
    margin: 0 auto;
    padding: 12px;
    border-radius: 6px;
    font-size: 14px;
    background: #F7F4FF;
    border: 1px solid #DDD;
}

.top-info {
    text-align: center;
    font-size: 17px;
    margin-top: 15px;
}

.endnote {
    width: 90%;
    margin: 15px auto;
    font-size: 13px;
    color: #C63434;
    text-align: left;
}

.print-button {
    background: #5533FF;
    color: white;
    padding: 10px 18px;
    border-radius: 6px;
    text-decoration: none;
    font-size: 15px;
}

.print-container {
    text-align: center;
    margin: 20px 0;
}

.page-break {
    page-break-before: always;
}
"""


# ===================================================================
#                 SUPPLIER HTML
# ===================================================================
def render_supplier_html(supplier_name, booth, schedule_df, supplier_summary):
    data_map = {}
    for _, r in schedule_df.iterrows():
        data_map[(r["day"], r["timeslot"])] = {
            "rep": r.get("rep", "--AVAILABLE--"),
            "category": r.get("category", "")
        }

    requested = supplier_summary["requested"]
    fulfilled = set(supplier_summary["fulfilled"])

    summary_lines = []
    for cat in requested:
        if cat in fulfilled:
            summary_lines.append(f"{cat}")
        else:
            summary_lines.append(f"{cat} <span style='color:#C63434;'>[UNAVAILABLE]</span>")

    # 3-day grid layout — top-left, top-right, bottom-left
    day_cells = ""
    for day in time_slots.keys():
        day_cells += f"""
        <div class="grid-cell">
            <div class="section-title">{day}</div>
            <table>
                <tr><th>Time</th><th>Appointment with</th><th>Category</th></tr>
                {_build_single_day_rows(day, data_map, include_booth=False, include_category=True)}
            </table>
        </div>
        """

    summary_cell = f"""
    <div class="grid-cell">
        <div class="section-title">Request Summary</div>
        <div class="summary-box">
            {"<br>".join(summary_lines)}
        </div>
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
        <div class="top-info">{supplier_name} — Booth {booth}</div>

        <div class="print-container no-print">
            <a class="print-button" onclick="window.print()" href="javascript:void(0)">Save PDF</a>
        </div>

        <div class="grid-container">
            {day_cells}
            {summary_cell}
        </div>

        <div class="endnote">
            Some Members may have free slots. If you're looking to connect with a Sales Representative,
            consult with our Information Desk Staff for Member availability.
        </div>

    </body>
    </html>
    """


# ===================================================================
#                 REP HTML
# ===================================================================
def render_rep_html(rep_name, schedule_df, suppliers_df):
    data_map = {}

    for _, r in schedule_df.iterrows():
        supplier = r.get("supplier", "--AVAILABLE--")
        if supplier == "--AVAILABLE--":
            val = "--AVAILABLE--"
        else:
            booth = suppliers_df.loc[
                suppliers_df["Supplier"] == supplier, "Booth #"
            ].iloc[0]
            val = {"supplier": supplier, "booth": booth}
        data_map[(r["day"], r["timeslot"])] = val

    day_cells = ""
    for day in time_slots.keys():
        day_cells += f"""
        <div class="grid-cell">
            <div class="section-title">{day}</div>
            <table>
                <tr><th>Time</th><th>Booth</th><th>Supplier</th></tr>
                {_build_single_day_rows(day, data_map, include_booth=True, include_category=False)}
            </table>
        </div>
        """

    empty_cell = "<div class='grid-cell'></div>"

    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>{COMMON_CSS}></style>
        <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;500;600&display=swap" rel="stylesheet">
    </head>

    <body>

        <div class="title">2026 Supplier Growth Summit</div>
        <div class="subtitle">February 23rd – 25th</div>
        <div class="top-info">{rep_name}</div>

        <div class="print-container no-print">
            <a class="print-button" onclick="window.print()" href="javascript:void(0)">Save PDF</a>
        </div>

        <div class="grid-container">
            {day_cells}
            {empty_cell}
        </div>

        <div class="endnote">
            If you have a Sponsor Suite meeting, you don't have to keep the Floor appointment.<br>
            During free slots, please visit with our Associate and Program Suppliers that don't have rotation appointments.
        </div>

    </body>
    </html>
    """


# ===================================================================
#      Build Combined HTML for Print-All
# ===================================================================
def build_combined_html(html_pages):
    first = html_pages[0]
    head = first.split("<head>")[1].split("</head>")[0]

    combined = []
    for idx, page in enumerate(html_pages):
        body = page.split("<body>")[1].split("</body>")[0]

        if idx < len(html_pages) - 1:
            combined.append(f"""
            <div class="schedule-page">{body}</div>
            <div class="page-break"></div>
            """)
        else:
            combined.append(f"""
            <div class="schedule-page">{body}</div>
            """)

    return f"""
    <html>
    <head>{head}</head>
    <body>
        {''.join(combined)}
    </body>
    </html>
    """


def html_to_pdf(html):
    return html
