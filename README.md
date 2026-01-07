# **Supplier Growth Forum Scheduler**

A Streamlit-based application for generating, viewing, and exporting structured meeting schedules for Suppliers and Sales Representatives for the **Supplier Growth Summit**. This tool is an automated Python scheduler that outputs PDF ready HTML.

## **Features**

### **Scheduling Logic**

* Category-driven matching
* Priority ordering (Peak before Accelerating)
* Max meeting caps
* Break/Lunch blocking
* Automatic timeslot scanning and assignment
* Avoids double-booking suppliers and reps

### **Interface**

* Streamlit UI
* File upload input for the Excel matrix
* Export options for individual or all schedules

### **Output**

* Fully formatted HTML for each Supplier and Rep
* Combined multi-page HTML for “Save All” printing


## **Project Structure**

```
app/
    scheduler.py               # Core scheduling engine
    html_renderer.py           # HTML generation + print-all logic
    layout.py                  # Header and UI layout helpers
    parsers.py                 # Excel matrix importer
    utils.py                   # Time slots, breaks, helpers
files/
    logos.png                  # Page header branding
    demo_data.xlsx             # Data used for Demo purposes
app.py                         # Streamlit front-end UI
README.md
requirements.txt
```

## **Installation**

Make sure you have Python 3.9+ installed.

```bash
pip install -r requirements.txt
```

---

## **Running the App**

```bash
streamlit run app.py
```

## **Limitations (Demo Only)**

This is a prototype intended to demonstrate workflow and UX.
Known limitations:

* No persistent database
* No authentication
* Limited conflict resolution
* No drag-and-drop rearranging
* Scheduling is greedy; advanced optimization not implemented

These can be expanded for a production version.


