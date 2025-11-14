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
    st.set_page_config(page_title="Supplier Growth Forum Scheduler Demo", layout="wide")
    render_header("files/logos.png")

    st.sidebar.header("Scheduler Settings")
    max_meetings_rep = st.sidebar.number_input("Max meetings per rep", 1, 50, 5)
    max_peak = st.sidebar.number_input("Meetings per Peak supplier", 1, 50, 5)
    max_acc = st.sidebar.number_input("Meetings per Accelerating supplier", 1, 50, 3)

    uploaded = st.file_uploader(
        "Upload Excel (Sheets: 'Suppliers' & 'Sales Reps.')",
        type=["xlsx"]
    )

    if not uploaded:
        return

    suppliers_df, reps_df, prefs_df = parse_matrix_file(uploaded)


    # ---------------------------
    # Run Scheduler
    # ---------------------------
    if st.button("Run Scheduler"):
        supplier_sched, rep_sched = run_scheduler(
            suppliers_df,
            reps_df,
            prefs_df,
            max_meetings_rep,
            max_peak,
            max_acc
        )

        st.session_state["supplier_sched"] = supplier_sched
        st.session_state["rep_sched"] = rep_sched

        st.success("Schedule generated successfully.")


    if "supplier_sched" not in st.session_state:
        return

    supplier_sched = st.session_state["supplier_sched"]
    rep_sched = st.session_state["rep_sched"]


    # ==========================================================
    # Supplier Schedules
    # ==========================================================
    st.header("Supplier Schedules")

    selected_supplier = st.selectbox(
        "Select Supplier",
        suppliers_df["Supplier"],
        key="supplier_select"
    )

    booth = suppliers_df.loc[
        suppliers_df["Supplier"] == selected_supplier,
        "Booth #"
    ].iloc[0]

    df_s = supplier_sched[supplier_sched["supplier"] == selected_supplier]

    html_s = render_supplier_html(selected_supplier, booth, df_s)
    st.components.v1.html(html_s, height=1000, scrolling=True)


    # ----------------------------
    # PRINT ALL SUPPLIERS
    # ----------------------------
    if st.button("Save ALL Supplier Schedules (PDF)"):

        pages = []
        for supp in suppliers_df["Supplier"]:
            booth_s = suppliers_df.loc[
                suppliers_df["Supplier"] == supp,
                "Booth #"
            ].iloc[0]
            df_s2 = supplier_sched[supplier_sched["supplier"] == supp]
            pages.append(render_supplier_html(supp, booth_s, df_s2))

        big_html = build_combined_html(pages)

        st.components.v1.html(
            f"""
            <iframe id="print_frame" style="display:none;"></iframe>
            <script>
                const iframe = document.getElementById("print_frame");
                const doc = iframe.contentWindow.document;
                doc.open();
                doc.write(`{big_html.replace("`", "\\`")}`);
                doc.close();
                setTimeout(() => iframe.contentWindow.print(), 200);
            </script>
            """,
            height=0
        )

    st.markdown("---")


    # ==========================================================
    # Representative Schedules
    # ==========================================================
    st.header("Sales Representative Schedules")

    selected_rep = st.selectbox(
        "Select Sales Rep",
        reps_df["Sales Rep."],
        key="rep_select"
    )

    df_r = rep_sched[rep_sched["rep"] == selected_rep]
    html_r = render_rep_html(selected_rep, df_r, suppliers_df)

    st.components.v1.html(html_r, height=1000, scrolling=True)


    # ----------------------------
    # PRINT ALL REPRESENTATIVES
    # ----------------------------
    if st.button("Save ALL Rep Schedules (PDF)"):

        pages = []
        for rep in reps_df["Sales Rep."]:
            df_r2 = rep_sched[rep_sched["rep"] == rep]
            pages.append(render_rep_html(rep, df_r2, suppliers_df))

        big_html = build_combined_html(pages)

        st.components.v1.html(
            f"""
            <iframe id="print_frame2" style="display:none;"></iframe>
            <script>
                const iframe = document.getElementById("print_frame2");
                const doc = iframe.contentWindow.document;
                doc.open();
                doc.write(`{big_html.replace("`", "\\`")}`);
                doc.close();
                setTimeout(() => iframe.contentWindow.print(), 200);
            </script>
            """,
            height=0
        )


if __name__ == "__main__":
    main()
