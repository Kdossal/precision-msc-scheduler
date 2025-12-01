import streamlit as st
import pandas as pd

from app.layout import render_header
from app.parsers import parse_matrix_file
from app.scheduler import run_scheduler
from app.html_renderer import (
    render_supplier_html,
    render_rep_html,
    build_combined_html,
    html_to_pdf
)


def main():
    st.set_page_config(page_title="Supplier Growth Forum Scheduler", layout="wide")
    render_header("files/logos.png")
     # ---------------------------------------------------------
    # GUIDE / INSTRUCTIONS
    # ---------------------------------------------------------
    st.markdown(
        """
        ### How to Use This Tool

        This tool generates meeting schedules for Suppliers and Sales Representatives
        based on the preferences defined in the uploaded Excel file.

        #### **Workflow**
        - Upload a .xlsx containing the “Suppliers” and “Sales Reps.” sheets  
        - Configure meeting limits in the setup section below  
        - Click **Run Scheduler** to create all schedules  
        - Use the tabs to view Supplier or Sales Rep schedules  
        - Export individual schedules or all schedules as PDFs  

        #### **Notes**
        - Do not change the structure of the uploaded workbook (sheet names & columns).  
        - All processing occurs **locally** in your session. Data is not stored or transmitted.  
        - For assistance contact **Precision Business Solutions**.
        """,
        unsafe_allow_html=True
    )

    # ---------------------------------------------------------
    # SETTINGS (Inline — no sidebar)
    # ---------------------------------------------------------
    st.subheader("Scheduler Settings")

    colA, colB, colC = st.columns(3)

    with colA:
        max_meetings_rep = st.number_input(
            "Max meetings per rep", 1, 50, 5
        )

    with colB:
        max_peak = st.number_input(
            "Meetings per Peak supplier", 1, 50, 5
        )

    with colC:
        max_acc = st.number_input(
            "Meetings per Accelerating supplier", 1, 50, 3
        )

    # ---------------------------------------------------------
    # Upload
    # ---------------------------------------------------------
    uploaded = st.file_uploader(
        "Upload Excel (Sheets: 'Suppliers' & 'Sales Reps.')",
        type=["xlsx"]
    )

    if not uploaded:
        return

    suppliers_df, reps_df, prefs_df = parse_matrix_file(uploaded)

    # ---------------------------------------------------------
    # Run Scheduler
    # ---------------------------------------------------------
    if st.button("Run Scheduler"):
        supplier_sched, rep_sched, supplier_summary = run_scheduler(
            suppliers_df,
            reps_df,
            prefs_df,
            max_meetings_rep,
            max_peak,
            max_acc
        )

        st.session_state["supplier_sched"] = supplier_sched
        st.session_state["rep_sched"] = rep_sched
        st.session_state["supplier_summary"] = supplier_summary

        st.success("Schedule generated successfully.")

    # ---------------------------------------------------------
    # Stop if no schedule yet
    # ---------------------------------------------------------
    if "supplier_sched" not in st.session_state:
        return

    supplier_sched = st.session_state["supplier_sched"]
    rep_sched = st.session_state["rep_sched"]
    supplier_summary = st.session_state["supplier_summary"]

    # ---------------------------------------------------------
    # TABS
    # ---------------------------------------------------------
    tab_suppliers, tab_reps = st.tabs(["Supplier View", "Sales Rep View"])

    # =========================================================
    # SUPPLIER TAB
    # =========================================================
    with tab_suppliers:

        col_select, blank, col_btn = st.columns([2, 2, 1])

        with col_select:
            selected_supplier = st.selectbox(
                "Select Supplier",
                suppliers_df["Supplier"],
                key="supplier_select"
            )

        with col_btn:
            if st.button("Save ALL Supplier Schedules (PDF)"):

                pages = []
                for supp in suppliers_df["Supplier"]:
                    booth_s = suppliers_df.loc[
                        suppliers_df["Supplier"] == supp,
                        "Booth #"
                    ].iloc[0]
                    df_s2 = supplier_sched[supplier_sched["supplier"] == supp]

                    pages.append(
                        render_supplier_html(
                            supp,
                            booth_s,
                            df_s2,
                            supplier_summary[supp]
                        )
                    )

                big_html = build_combined_html(pages)

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

        # Render chosen supplier
        booth = suppliers_df.loc[
            suppliers_df["Supplier"] == selected_supplier,
            "Booth #"
        ].iloc[0]

        df_s = supplier_sched[supplier_sched["supplier"] == selected_supplier]

        html_s = render_supplier_html(
            selected_supplier,
            booth,
            df_s,
            supplier_summary[selected_supplier]
        )

        st.components.v1.html(html_s, height=1100, scrolling=True)

    # =========================================================
    # SALES REP TAB
    # =========================================================
    with tab_reps:
        
        col_select, blank, col_btn = st.columns([2, 2, 1])

        with col_select:
            selected_rep = st.selectbox(
                "Select Sales Rep",
                reps_df["Sales Rep."],
                key="rep_select"
            )

        with col_btn:
            if st.button("Save ALL Rep Schedules (PDF)"):

                pages = []
                for rep in reps_df["Sales Rep."]:
                    df_r2 = rep_sched[rep_sched["rep"] == rep]
                    pages.append(render_rep_html(rep, df_r2, suppliers_df))

                big_html = build_combined_html(pages)

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

        # Render chosen rep
        df_r = rep_sched[rep_sched["rep"] == selected_rep]
        html_r = render_rep_html(selected_rep, df_r, suppliers_df)

        st.components.v1.html(html_r, height=1100, scrolling=True)


if __name__ == "__main__":
    main()
