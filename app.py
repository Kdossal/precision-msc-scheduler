import streamlit as st
import pandas as pd
import io

from app.layout import render_header
from app.parsers import (parse_meeting_organizer, parse_uploaded_schedules)
from app.scheduler import run_scheduler
from app.html_renderer import (
    render_supplier_html,
    render_rep_html,
    build_combined_html,
    render_request_summary_table
)

def attach_substitutions(supplier_sched, supplier_summary):
    """
    Add a 'substitutions' column to supplier_sched by mapping:
    (supplier, request_name) -> list of unavailable reps
    """
    subs_map = {}
    for supp, summary in supplier_summary.items():
        subs = summary.get("substitutions", {})
        for req_name, subs_list in subs.items():
            subs_map[(supp, req_name)] = ", ".join(subs_list)

    supplier_sched = supplier_sched.copy()
    supplier_sched["substitutions"] = supplier_sched.apply(
        lambda r: subs_map.get((r["supplier"], r["category"]), ""),
        axis=1
    )
    return supplier_sched

def reshape_supplier_export(supplier_sched, supplier_summary):
    """
    Takes the scheduler output supplier_sched and produces the cleaned
    export DataFrame in the required column order.
    """

    supplier_sched = attach_substitutions(supplier_sched, supplier_summary)

    df = supplier_sched.copy()

    df["Supplier Name"] = df["supplier"]
    df["Day"] = df["day"]
    df["Timeslot"] = df["timeslot"]
    df["Request"] = df["category"]
    df["Session Type"] = df["session_type"]
    df["Booth"] = df["booth"]
    df["Reps"] = df["reps"].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
    df["Opportunity"] = df["total_opportunity"]
    df["Unavailable Requested Reps"] = df["substitutions"]

    desired_cols = [
        "Supplier Name",
        "Day",
        "Timeslot",
        "Request",
        "Session Type",
        "Booth",
        "Reps",
        "Opportunity",
        "Unavailable Requested Reps"
    ]

    return df[desired_cols]

def reshape_rep_export(rep_sched):
    df = rep_sched.copy()

    df["Name"] = df["rep"]
    df["Leader"] = ""            # empty for now
    df["Day"] = df["day"]
    df["Timeslot"] = df["timeslot"]
    df["Supplier"] = df["supplier"]
    df["Session Type"] = df["session_type"]
    df["Booth"] = df["booth"]
    df["Request Name"] = df["category"]
    df["Opportunity"] = df["total_opportunity"]

    desired_cols = [
        "Name",
        "Leader",
        "Day",
        "Timeslot",
        "Supplier",
        "Booth",
        "Session Type",
        "Request Name",
        "Opportunity"
    ]

    return df[desired_cols]


def create_download_workbook(supplier_sched, rep_sched, supplier_summary):

    output = io.BytesIO()

    # Reshape for clean export
    sup_export = reshape_supplier_export(supplier_sched, supplier_summary)
    rep_export = reshape_rep_export(rep_sched)

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:

        sup_export.to_excel(writer, sheet_name="Suppliers", index=False)
        rep_export.to_excel(writer, sheet_name="Representatives", index=False)

        wb = writer.book
        ws_sup = writer.sheets["Suppliers"]
        ws_rep = writer.sheets["Representatives"]

        # Formats
        header_fmt = wb.add_format({
            "bold": True,
            "font_name": "Barlow",
            "font_size": 12,
            "align": "left",
            "valign": "vcenter",
            "font_color": "white",
            "bg_color": "#5533FF",
            "border": 1
        })

        cell_fmt = wb.add_format({
            "font_name": "Barlow",
            "font_size": 12,
            "align": "left",
            "valign": "vcenter",
            "border": 1
        })

        money_fmt = wb.add_format({
            "font_name": "Barlow",
            "font_size": 12,
            "align": "right",
            "valign": "vcenter",
            "border": 1,
            "num_format": "$#,##0"
        })

        # ----------------------------------------------------
        # Write Suppliers Sheet
        # ----------------------------------------------------
        for col_idx, col_name in enumerate(sup_export.columns):

            ws_sup.write(0, col_idx, col_name, header_fmt)

            is_money = (col_name == "Opportunity")

            for row_idx, val in enumerate(sup_export[col_name], start=1):

                if isinstance(val, list):
                    val = ", ".join(map(str, val))
                if pd.isna(val):
                    val = ""

                if is_money:
                    try:
                        ws_sup.write_number(row_idx, col_idx, float(val), money_fmt)
                    except:
                        ws_sup.write(row_idx, col_idx, "", money_fmt)
                else:
                    ws_sup.write(row_idx, col_idx, val, cell_fmt)

            width = min(max(len(col_name), sup_export[col_name].astype(str).map(len).max()) + 2, 40)
            ws_sup.set_column(col_idx, col_idx, width)

        # ----------------------------------------------------
        # Write Representatives Sheet
        # ----------------------------------------------------
        for col_idx, col_name in enumerate(rep_export.columns):

            ws_rep.write(0, col_idx, col_name, header_fmt)

            is_money = (col_name == "Opportunity")

            for row_idx, val in enumerate(rep_export[col_name], start=1):

                if isinstance(val, list):
                    val = ", ".join(map(str, val))
                if pd.isna(val):
                    val = ""

                if is_money:
                    try:
                        ws_rep.write_number(row_idx, col_idx, float(val), money_fmt)
                    except:
                        ws_rep.write(row_idx, col_idx, "", money_fmt)
                else:
                    ws_rep.write(row_idx, col_idx, val, cell_fmt)

            width = min(max(len(col_name), rep_export[col_name].astype(str).map(len).max()) + 2, 40)
            ws_rep.set_column(col_idx, col_idx, width)

    return output.getvalue()



def main():
    st.set_page_config(page_title="Supplier Growth Forum Scheduler", layout="wide")
    render_header("files/logos.png")

    # ------------------------------------------------------------
    # Instructions
    # ------------------------------------------------------------
    st.markdown(
        """
        #### How to Use This Tool
        This application generates schedules for all Suppliers and attending MSC Sales Representatives for the Supplier Growth Forum.

        1. Upload the Meeting Organizer Excel file  
        2. Choose to run the scheduler or upload existing schedules  
        3. View Supplier or Sales Rep calendars  
        4. Export single or combined PDFs  

        All processing happens locally in your browser session. 

        #### Support
        For questions or assistance, contact **Precision**  
        Jesse Katz &lt;jkatz@precisionmarketdata.com&gt;  
        Henrik Elster &lt;helster@precisionmarketdata.com&gt;
        """
    )

    # ------------------------------------------------------------
    # Upload Meeting Organizer (always required)
    # ------------------------------------------------------------
    uploaded = st.file_uploader(
        "Upload Meeting Organizer Excel File",
        type=["xlsx"],
        key="meeting_organizer"
    )

    if not uploaded:
        return

    suppliers_df, reps_df, preferences, sellers = parse_meeting_organizer(uploaded)

    # ------------------------------------------------------------
    # Mode Selection
    # ------------------------------------------------------------
    mode = st.radio(
        "Select Action",
        ["Run Scheduler", "Upload Existing Schedules"],
        horizontal=True
    )

    # ------------------------------------------------------------
    # Scheduler Mode
    # ------------------------------------------------------------
    if mode == "Run Scheduler":
        if st.button("Run Scheduler"):
            with st.spinner("Generating schedules… this may take a moment."):
                supplier_sched, rep_sched, supplier_summary, validation = run_scheduler(
                    preferences,
                    reps_df,
                    sellers
                )

                for i in supplier_summary:
                    for v in supplier_summary[i]['unfulfilled']:
                        print(v,i)

                print(validation)

                st.session_state["supplier_sched"] = supplier_sched
                st.session_state["rep_sched"] = rep_sched
                st.session_state["supplier_summary"] = supplier_summary
                st.session_state["validation"] = validation

                missing = [
                    s for s in suppliers_df["Supplier"]
                    if s not in supplier_summary
                ]

            if missing:
                st.warning(
                    f"Warning: The following suppliers did not appear in schedule results: {missing}"
                )

            st.success("Schedule generated successfully!")

    # ------------------------------------------------------------
    # Upload Existing Schedules Mode
    # ------------------------------------------------------------
    if mode == "Upload Existing Schedules":
        uploaded_sched = st.file_uploader(
            "Upload Scheduler Output Excel",
            type=["xlsx"],
            key="uploaded_schedules"
        )

        if uploaded_sched and st.button("Load Schedules"):
            (
                supplier_sched,
                rep_sched,
                supplier_summary,
                validation
            ) = parse_uploaded_schedules(uploaded_sched)

            st.session_state["supplier_sched"] = supplier_sched
            st.session_state["rep_sched"] = rep_sched
            st.session_state["supplier_summary"] = supplier_summary
            st.session_state["validation"] = validation

            st.success("Schedules loaded successfully.")

    # ------------------------------------------------------------
    # Stop if no schedules loaded yet
    # ------------------------------------------------------------
    if "supplier_sched" not in st.session_state:
        return

    supplier_sched = st.session_state["supplier_sched"]
    rep_sched = st.session_state["rep_sched"]
    supplier_summary = st.session_state["supplier_summary"]

    # ------------------------------------------------------------
    # Tabs
    # ------------------------------------------------------------
    tab_suppliers, tab_reps, tab_download = st.tabs(
        ["Supplier View", "Sales Rep View", "Download"]
    )

    # ============================================================
    # SUPPLIER TAB
    # ============================================================
    with tab_suppliers:
        col_select, _, col_btn = st.columns([2, 2, 1])

        with col_select:
            selected_supplier = st.selectbox(
                "Select Supplier",
                suppliers_df["Supplier"].tolist(),
                key="supplier_select"
            )

        with col_btn:
            if st.button("Save ALL Supplier Schedules (PDF)"):
                pages = []
                for supp in suppliers_df["Supplier"]:
                    booth_s = suppliers_df.loc[
                        suppliers_df["Supplier"] == supp,
                        "Booth"
                    ].iloc[0]

                    df_s = supplier_sched[supplier_sched["supplier"] == supp]
                    summary_s = supplier_summary.get(supp, {})

                    pages.append(
                        render_supplier_html(
                            supp, booth_s, df_s, summary_s, reps_df
                        )
                    )

                supplier_names = suppliers_df["Supplier"].tolist()

                big_html = build_combined_html(
                    pages,
                    mode="Supplier",
                    supplier_names=supplier_names
                )

                st.components.v1.html(
                    f"""
                    <iframe id="print_all_suppliers" style="display:none;"></iframe>
                    <script>
                        const iframe = document.getElementById("print_all_suppliers");
                        const doc = iframe.contentWindow.document;
                        doc.open();
                        doc.write(`{big_html.replace("`", "\\`")}`);
                        doc.close();
                        setTimeout(() => iframe.contentWindow.print(), 300);
                    </script>
                    """,
                    height=0
                )

        booth_val = suppliers_df.loc[
            suppliers_df["Supplier"] == selected_supplier,
            "Booth"
        ].iloc[0]

        df_supplier = supplier_sched[
            supplier_sched["supplier"] == selected_supplier
        ]

        html_supplier = render_supplier_html(
            selected_supplier,
            booth_val,
            df_supplier,
            supplier_summary[selected_supplier],
            reps_df
        )

        st.components.v1.html(html_supplier, height=950, scrolling=True)

        summary_html_block = render_request_summary_table(
            supplier_summary[selected_supplier]
        )
        st.components.v1.html(summary_html_block, height=400, scrolling=True)

    # ============================================================
    # REP TAB
    # ============================================================
    with tab_reps:
        meeting_reps = sorted(rep_sched["rep"].unique().tolist())

        col_select, _, col_btn = st.columns([2, 2, 1])

        with col_select:
            selected_rep = st.selectbox(
                "Select Sales Rep",
                meeting_reps,
                key="rep_select"
            )

        with col_btn:
            if st.button("Save ALL Rep Schedules (PDF)"):
                pages = []
                for rep in meeting_reps:
                    df_rep = rep_sched[rep_sched["rep"] == rep]
                    pages.append(
                        render_rep_html(rep, df_rep, suppliers_df, reps_df)
                    )

                big_html = build_combined_html(pages, mode="Rep")

                st.components.v1.html(
                    f"""
                    <iframe id="print_all_reps" style="display:none;"></iframe>
                    <script>
                        const iframe = document.getElementById("print_all_reps");
                        const doc = iframe.contentWindow.document;
                        doc.open();
                        doc.write(`{big_html.replace("`", "\\`")}`);
                        doc.close();
                        setTimeout(() => iframe.contentWindow.print(), 300);
                    </script>
                    """,
                    height=0
                )

        df_rep_selected = rep_sched[rep_sched["rep"] == selected_rep]

        html_rep = render_rep_html(
            selected_rep,
            df_rep_selected,
            suppliers_df,
            reps_df
        )

        st.components.v1.html(html_rep, height=1100, scrolling=True)

    # ============================================================
    # DOWNLOAD TAB
    # ============================================================
    with tab_download:
        st.subheader("Download Raw Schedule Outputs")

        st.markdown(
            """
            This export includes:
            - **Suppliers**: the full supplier meeting schedule  
            - **Representatives**: the full sales rep meeting schedule  
            """
        )

        if st.button("Prepare Excel Export"):
            with st.spinner("Preparing Excel file…"):
                excel_bytes = create_download_workbook(
                    supplier_sched,
                    rep_sched,
                    supplier_summary
                )

            st.download_button(
                label="Download Scheduler Output (Excel)",
                data=excel_bytes,
                file_name="SGF_Schedule_Output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )



if __name__ == "__main__":
    main()

