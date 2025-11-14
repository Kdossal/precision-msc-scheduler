# app/html_renderer.py

from app.utils import time_slots


# -------------------------------------------------------------
#    Build Day Tables
# -------------------------------------------------------------
def _build_single_day_rows(day_name, timeslot_map, include_booth=False):
    html = ""

    for t, blocked_reason in time_slots[day_name].items():

        # if this is a LUNCH or BREAK slot
        if blocked_reason == "LUNCH":
            html += f"""
            <tr>
                <td>{t}</td>
                <td colspan="2" style="color:#C63434; font-weight:600;">LUNCH</td>
            </tr>
            """ if include_booth else f"""
            <tr>
                <td>{t}</td>
                <td style="color:#C63434; font-weight:600;">LUNCH</td>
            </tr>
            """
            continue

        if blocked_reason == "BREAK":
            html += f"""
            <tr>
                <td>{t}</td>
                <td colspan="2" style="color:#C63434; font-weight:600;">BREAK</td>
            </tr>
            """ if include_booth else f"""
            <tr>
                <td>{t}</td>
                <td style="color:#C63434; font-weight:600;">BREAK</td>
            </tr>
            """
            continue

        # Normal slot
        val = timeslot_map.get((day_name, t), "--AVAILABLE--")

        if include_booth:
            if val == "--AVAILABLE--":
                supplier = "--AVAILABLE--"
                booth = ""
            else:
                supplier = val["supplier"]
                booth = val["booth"]

            html += f"""
            <tr>
                <td>{t}</td>
                <td>{booth}</td>
                <td>{supplier}</td>
            </tr>
            """
        else:
            html += f"""
            <tr>
                <td>{t}</td>
                <td>{val}</td>
            </tr>
            """

    return html


# -------------------------------------------------------------
#     COMMON CSS (used by all pages)
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

.section-title {
    text-align: center;
    font-size: 20px;
    font-weight: 600;
    margin-top: 30px;
    margin-bottom: 10px;
    color: #5533FF;
}

.disclaimer {
    width: 80%;
    margin: 0 auto 40px auto;
    font-size: 13px;
    color: #C63434;
    text-align: left;
}

table {
    width: 80%;
    margin: 0 auto 30px auto;
    border-collapse: collapse;
    background: white;
    border-radius: 6px;
    border: 1px solid #ddd;
}

th {
    background: #5533FF;
    color: white;
    padding: 10px;
    text-align: left;
}

td {
    padding: 8px;
    border-bottom: 1px solid #ddd;
}

tr:last-child td {
    border-bottom: none;
}

.top-info {
    text-align: center;
    font-size: 17px;
    margin-top: 15px;
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
def render_supplier_html(supplier_name, booth, schedule_df):

    data_map = {}
    for _, r in schedule_df.iterrows():
        data_map[(r["day"], r["timeslot"])] = r.get("rep", "--AVAILABLE--")

    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">

        <style>{COMMON_CSS}</style>

        <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;500;600&display=swap"
              rel="stylesheet">
    </head>

    <body>

        <div class="title">2026 Supplier Growth Summit</div>
        <div class="subtitle">XXXXXXX January XXth through XXXXXXX January XXth</div>

        <div class="top-info">{supplier_name} — Booth {booth}</div>

        <div class="print-container no-print">
            <a class="print-button" onclick="window.print()" href="javascript:void(0)">Save PDF</a>
        </div>

        <div class="section-title">Day 1</div>

        <table>
            <tr><th>Time:</th><th>Appointment with:</th></tr>
            {_build_single_day_rows("Day 1", data_map)}
        </table>

        <div class="section-title">Day 2</div>

        <table>
            <tr><th>Time:</th><th>Appointment with:</th></tr>
            {_build_single_day_rows("Day 2", data_map)}
        </table>

        <div class="disclaimer">
            Some Members may have free slots. If you're looking to connect with a
            Sales Representative, consult with our Information Desk Staff for Member availability.
        </div>

    </body>
    </html>
    """

    return html


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

    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">

        <style>{COMMON_CSS}</style>

        <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;500;600&display=swap"
              rel="stylesheet">
    </head>

    <body>

        <div class="title">2026 Supplier Growth Summit</div>
        <div class="subtitle">XXXXXXX January XXth through XXXXXXX January XXth</div>

        <div class="top-info">{rep_name}</div>

        <div class="print-container no-print">
            <a class="print-button" onclick="window.print()" href="javascript:void(0)">Save PDF</a>
        </div>

        <div class="section-title">Day 1</div>
        <table>
            <tr><th>Time:</th><th>Booth:</th><th>Appointment with:</th></tr>
            {_build_single_day_rows("Day 1", data_map, include_booth=True)}
        </table>

        <div class="section-title">Day 2</div>
        <table>
            <tr><th>Time:</th><th>Booth:</th><th>Appointment with:</th></tr>
            {_build_single_day_rows("Day 2", data_map, include_booth=True)}
        </table>

        <div class="disclaimer">
            If you have a Sponsor Suite meeting, you don't have to keep the Floor appointment.<br>
            During free slots, please visit with our Associate and Program Suppliers
            that don't have rotation appointments.
        </div>

    </body>
    </html>
    """

    return html


# ===================================================================
#      Build Combined HTML for Print-All
# ===================================================================
def build_combined_html(html_pages):
    """Combine many full HTML pages into ONE printable HTML with page breaks."""

    # Extract <head> contents from first page
    first = html_pages[0]
    head = first.split("<head>")[1].split("</head>")[0]

    combined = []

    for idx, page in enumerate(html_pages):
        body = page.split("<body>")[1].split("</body>")[0]

        # Only add page break if not last page
        if idx < len(html_pages) - 1:
            combined.append(f"""
                <div class="schedule-page">
                    {body}
                </div>
                <div class="page-break"></div>
            """)
        else:
            combined.append(f"""
                <div class="schedule-page">
                    {body}
                </div>
            """)

    return f"""
    <html>
    <head>{head}</head>
    <body>
        {''.join(combined)}
    </body>
    </html>
    """



# ===================================================================
#     html_to_pdf — Browser-based, no wkhtmltopdf, no subprocess
# ===================================================================
def html_to_pdf(html):
    """
    This function does NOT create PDFs itself.
    It returns HTML that the browser can print as PDF.
    The backend does NOT generate PDFs.
    """
    return html
