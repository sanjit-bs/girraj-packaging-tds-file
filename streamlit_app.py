import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
from datetime import date
import datetime
import math
import re
import numpy as np

st.set_page_config(page_title="GIRRAJ PACKAGING", layout="wide")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SPREADSHEET_ID = "1PCJ3BWAj6Wz1N-55XpuWltvfvYd7KD1q194D3N7MzIg"
WORKSHEET_NAME = "Tds_file"

COLUMNS = [
    "Financial Year",
    "Month",
    "Payment Date",
    "Cheque No",
    "Bill Amount",
    "TDS",
    "Net Amount",
    "Payee",
    "Category",
    "Remark"
]


@st.cache_resource
def connect_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)


sheet = connect_sheet()


def get_financial_year(payment_date):
    year = payment_date.year
    if payment_date.month >= 4:
        return f"{year}-{year + 1}"
    return f"{year - 1}-{year}"


def load_data():
    records = sheet.get_all_records()

    if not records:
        return pd.DataFrame(columns=COLUMNS)

    df = pd.DataFrame(records)
    df.columns = df.columns.str.strip()

    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[COLUMNS]

    df["Payment Date"] = pd.to_datetime(
        df["Payment Date"],
        format="%d/%m/%Y",
        errors="coerce"
    )

    df["Bill Amount"] = pd.to_numeric(df["Bill Amount"], errors="coerce").fillna(0)
    df["TDS"] = pd.to_numeric(df["TDS"], errors="coerce").fillna(0)
    df["Net Amount"] = pd.to_numeric(df["Net Amount"], errors="coerce").fillna(0)

    text_cols = ["Financial Year", "Month", "Payee", "Category", "Remark", "Cheque No"]
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()

    return df


df = load_data()

if "submit_success" not in st.session_state:
    st.session_state.submit_success = False

if "form_key" not in st.session_state:
    st.session_state.form_key = 0


st.title("GIRRAJ PACKAGING")
st.subheader("Database and Dashboard")

if st.session_state.submit_success:
    st.success("✅ Record submitted successfully")
    st.session_state.submit_success = False


payee_list = [
    "PILU MRIDHA",
    "TOTON SARKAR",
    "DEBABRATA BISWAS"
]

category_list = [
    "LABOURE",
    "CARRIAGE"
]

# -----------------------------
# New Payment Entry
# -----------------------------
st.subheader("New Payment Entry (TDS)")

key_suffix = st.session_state.form_key

# -----------------------------
# Date
# -----------------------------
col_date, col_month, col_fy = st.columns(3)

with col_date:
    payment_date = st.date_input(
        "Payment Date *",
        value=date.today(),
        key=f"payment_date_{key_suffix}"
    )

month = payment_date.strftime("%B")
financial_year = get_financial_year(payment_date)

with col_month:
    st.text_input(
        "Month",
        value=month,
        disabled=True
    )

with col_fy:
    st.text_input(
        "Financial Year",
        value=financial_year,
        disabled=True
    )

# -----------------------------
# Bill / TDS / Net
# -----------------------------
col_bill, col_tds, col_net = st.columns(3)

with col_bill:
    bill_amount = st.number_input(
        "Bill Amount *",
        min_value=0.0,
        value=0.0,
        step=100.0,
        format="%.2f",
        key=f"bill_{key_suffix}"
    )

tds_amount = round(bill_amount * 0.01, 2)
net_amount = round(bill_amount - tds_amount, 2)

with col_tds:
    st.number_input(
        "TDS Amount (1%)",
        value=tds_amount,
        disabled=True,
        format="%.2f"
    )

with col_net:
    st.number_input(
        "Net Amount",
        value=net_amount,
        disabled=True,
        format="%.2f"
    )

# -----------------------------
# Other Details
# -----------------------------
col1, col2, col3 = st.columns(3)

with col1:
    payee = st.selectbox(
        "Select Payee *",
        [""] + payee_list,
        key=f"payee_{key_suffix}"
    )

with col2:
    cheque_no = st.text_input(
        "Cheque No. *",
        key=f"cheque_{key_suffix}"
    )

with col3:
    category = st.selectbox(
        "Category *",
        [""] + category_list,
        key=f"category_{key_suffix}"
    )

remark = st.text_area(
    "Remark",
    key=f"remark_{key_suffix}"
)

# -----------------------------
# Submit Button
# -----------------------------
if st.button("Submit Payment", type="primary"):

    if payee == "":
        st.warning("Please select a payee.")

    elif cheque_no.strip() == "":
        st.warning("Please enter cheque number.")

    elif bill_amount <= 0:
        st.warning("Please enter bill amount greater than 0.")

    elif category == "":
        st.warning("Please select category.")

    else:

        sheet.append_row([
            financial_year,
            month,
            payment_date.strftime("%d/%m/%Y"),
            cheque_no.strip(),
            float(bill_amount),
            float(tds_amount),
            float(net_amount),
            payee,
            category,
            remark.strip()
        ])

        st.session_state.submit_success = True
        st.session_state.form_key += 1
        st.rerun()

st.divider()


# -----------------------------
# Filter Section
# -----------------------------
st.subheader("Filter Payments")

available_years = ["All"] + sorted(
    df["Financial Year"].dropna().astype(str).str.strip().unique().tolist()
)

available_months = ["All"] + sorted(
    df["Month"].dropna().astype(str).str.strip().unique().tolist()
)

available_payees = ["All"] + sorted(
    df["Payee"].dropna().astype(str).str.strip().unique().tolist()
)

available_categories = ["All"] + sorted(
    df["Category"].dropna().astype(str).str.strip().unique().tolist()
)

col9, col10, col11, col12 = st.columns(4)

with col9:
    selected_year = st.selectbox("Financial Year", available_years)

with col10:
    selected_month = st.selectbox("Month", available_months)

with col11:
    selected_payee = st.selectbox("Payee", available_payees)

with col12:
    selected_category = st.selectbox("Category", available_categories)


filtered_df = df.copy()

if selected_year != "All":
    filtered_df = filtered_df[filtered_df["Financial Year"] == selected_year]

if selected_month != "All":
    filtered_df = filtered_df[filtered_df["Month"] == selected_month]

if selected_payee != "All":
    filtered_df = filtered_df[filtered_df["Payee"] == selected_payee]

if selected_category != "All":
    filtered_df = filtered_df[filtered_df["Category"] == selected_category]


# -----------------------------
# Summary
# -----------------------------
st.subheader("Summary")

total_bill_amount = filtered_df["Bill Amount"].sum()
total_tds = filtered_df["TDS"].sum()
total_net_amount = filtered_df["Net Amount"].sum()
total_transactions = len(filtered_df)

col13, col14, col15, col16 = st.columns(4)

with col13:
    st.metric("Total Bill Amount", f"₹{total_bill_amount:,.2f}")

with col14:
    st.metric("Total TDS", f"₹{total_tds:,.2f}")

with col15:
    st.metric("Total Net Amount", f"₹{total_net_amount:,.2f}")

with col16:
    st.metric("Total Transactions", total_transactions)


st.subheader("Payee-wise Total")

if not filtered_df.empty:
    payee_summary = (
        filtered_df.groupby("Payee", as_index=False)[
            ["Bill Amount", "TDS", "Net Amount"]
        ]
        .sum()
        .sort_values("Net Amount", ascending=False)
    )

    st.dataframe(payee_summary, width="stretch")
else:
    st.info("No data found for selected filter.")


st.subheader("Category-wise Total")

if not filtered_df.empty:
    category_summary = (
        filtered_df.groupby("Category", as_index=False)[
            ["Bill Amount", "TDS", "Net Amount"]
        ]
        .sum()
        .sort_values("Net Amount", ascending=False)
    )

    st.dataframe(category_summary, width="stretch")


st.subheader("Transaction Records")

display_df = filtered_df.copy()

if not display_df.empty:
    display_df["Payment Date"] = display_df["Payment Date"].dt.strftime("%d/%m/%Y")

st.dataframe(display_df, width="stretch")


def convert_to_excel(dataframe):
    output = BytesIO()
    excel_df = dataframe.copy()

    if not excel_df.empty:
        excel_df["Payment Date"] = excel_df["Payment Date"].dt.strftime("%d/%m/%Y")

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        excel_df.to_excel(writer, index=False, sheet_name="Payments")

    return output.getvalue()


excel_file = convert_to_excel(filtered_df)

st.download_button(
    label="Download Filtered Excel",
    data=excel_file,
    file_name="Payment_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
######-----------------------------------------------------Transport Record Section------------------------------------------------------------#######

WORKSHEET_NAME2 = "Delivery_Record"
WORKSHEET_NAME3 = "Inv_Value" 

COLUMNS2 = [
    "Date", "Vehicle No.", "Invoice No.", "Driver", 
    "Owner", "Company & Location", "Invoice Received", "Remark", "Loading Charge", "Unloading Charge"
]

COLUMNS3 = [
    "Date", "Company", "Invoice No.", "Taxable Value", 
    "SGST", "CGST", "Total GST", "Round Off", "Total Value"
]

COMPANY_OPTIONS = [
    "Select",
    "Kamal’s cake (Dhulagori)",
    "Kamal’s Ice Cream (Dhulagori)",
    "Kamals ORL O (Dhulagori)",
    "Kamals Ice Cream (Shaoraphuli, ”Adila”)",
    "Agarwal Food Product (Sankrail)",
    "Pamir Ice Cream (Raiganj)",
    "Top notch (Gaighata)",
    "Cold Roll (Gaighata)"
]

VEHICLE_MASTER = {
    "Select": {"driver": "", "owner": ""},
    "WB23C6784": {"driver": "Mangal", "owner": "D Biswas"},
    "WB35L6773": {"driver": "Raja", "owner": "D Biswas"},
    "WB25G3488": {"driver": "Babu", "owner": "D Biswas"},
    "WB25W1226": {"driver": "Sanjay", "owner": "D Biswas"},
    "WB25P9492": {"driver": "Badal", "owner": "D Biswas"},
    "WB25H7255": {"driver": "", "owner": "Chotu"},
    "WB25H5255": {"driver": "", "owner": "Chotu"},
    "Others": {"driver": "", "owner": ""}
}

# ======================================================
# Cached Database Connectors
# ======================================================
@st.cache_resource(ttl=3600)  
def connect_delivery_sheet():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME2)

@st.cache_resource(ttl=3600)  
def connect_invoice_value_sheet():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME3)

delivery_sheet = connect_delivery_sheet()
inv_value_sheet = connect_invoice_value_sheet()

@st.cache_data(ttl=10)
def load_delivery_data():
    records = delivery_sheet.get_all_records()
    if not records:
        return pd.DataFrame(columns=COLUMNS2)
    df = pd.DataFrame(records)
    df.columns = df.columns.str.strip()
    for col in COLUMNS2:
        if col not in df.columns: df[col] = ""
    df = df[COLUMNS2]
    df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y", errors="coerce")
    text_cols = ["Vehicle No.", "Invoice No.", "Driver", "Owner", "Company & Location", "Invoice Received", "Remark"]
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()
    return df

@st.cache_data(ttl=10)
def load_invoice_value_data():
    records = inv_value_sheet.get_all_records()
    if not records:
        return pd.DataFrame(columns=COLUMNS3)
    df = pd.DataFrame(records)
    df.columns = df.columns.str.strip()
    for col in COLUMNS3:
        if col not in df.columns: df[col] = 0.0 if "Value" in col or "GST" in col else ""
    df = df[COLUMNS3]
    return df

delivery_df = load_delivery_data()
inv_value_df = load_invoice_value_data()

# ======================================================
# Auto-Increment Sequence Logic
# ======================================================
def get_next_invoice_number(df):
    if df.empty or "Invoice No." not in df.columns:
        return "1"
    valid_invoices = df["Invoice No."].dropna().astype(str).str.strip()
    valid_invoices = [v for v in valid_invoices if v != ""]
    if not valid_invoices:
        return "1"
    last_invoice = valid_invoices[-1]
    match = re.search(r'(\d+)$', last_invoice)
    if match:
        num_part = match.group(1)
        next_num = int(num_part) + 1
        next_num_str = str(next_num).zfill(len(num_part))
        return last_invoice[:match.start()] + next_num_str
    return "1"

suggested_next_invoice = get_next_invoice_number(delivery_df)

# ======================================================
# Runtime Session States
# ======================================================
if "submit_success" not in st.session_state: st.session_state.submit_success = False
if "form_key" not in st.session_state: st.session_state.form_key = 0
if "current_driver" not in st.session_state: st.session_state.current_driver = ""
if "current_owner" not in st.session_state: st.session_state.current_owner = ""
if "current_invoice" not in st.session_state: st.session_state.current_invoice = suggested_next_invoice

if st.session_state.submit_success:
    st.success("✅ Log Entry Appended Successfully")
    st.session_state.submit_success = False

def update_vehicle_details():
    # 1. Fetch the selected vehicle from the selectbox
    sel = st.session_state[f"v_sel_{st.session_state.form_key}"]
    
    # 2. Push the master values directly into the session states
    st.session_state.current_driver = VEHICLE_MASTER[sel]["driver"]
    st.session_state.current_owner = VEHICLE_MASTER[sel]["owner"]
    
    # 3. FIX: Instantly force-assign those values to the active text_input widget keys
    key_suffix = st.session_state.form_key
    st.session_state[f"driver_field_{key_suffix}"] = VEHICLE_MASTER[sel]["driver"]
    st.session_state[f"owner_field_{key_suffix}"] = VEHICLE_MASTER[sel]["owner"]

# ======================================================
# Tab Layout Organization
# ======================================================
tab1, tab2 = st.tabs(["🚚 Delivery Record", "💰 Invoice Value Record"])

with tab1:
    st.subheader("New Delivery Entry")
    key_suffix = st.session_state.form_key

    col1, col2 = st.columns(2)
    with col1:
        vehicle_selection = st.selectbox("Vehicle No. *", options=list(VEHICLE_MASTER.keys()), key=f"v_sel_{key_suffix}", on_change=update_vehicle_details)
        final_vehicle_no = st.text_input("Manual Vehicle No. *", key=f"v_manual_{key_suffix}") if vehicle_selection == "Others" else vehicle_selection
    with col2:
        # FIX: Separation of key logic and fallback value logic
        invoice_no = st.text_input(
            "Invoice Number *", 
            value=st.session_state.current_invoice,
            key=f"delivery_entry_invoice_field_{key_suffix}"
        )

    col3, col4 = st.columns(2)
    with col3:
        # FIX: Aligned inside block
        driver_name = st.text_input(
            "Driver", 
            value=st.session_state.current_driver,
            key=f"driver_field_{key_suffix}"
        )
    with col4:
        # FIX: Aligned inside block
        owner_name = st.text_input(
            "Owner", 
            value=st.session_state.current_owner,
            key=f"owner_field_{key_suffix}"
        )
        
    company = st.selectbox("Company & Location *", options=COMPANY_OPTIONS, key=f"delivery_company_{key_suffix}")
    remark = st.text_area("Remark", key=f"delivery_remark_{key_suffix}")
    delivery_date = st.date_input("Delivery Date", value=date.today(), key=f"delivery_date_{key_suffix}")

    if st.button("Submit Delivery Log", type="primary"):
        if vehicle_selection == "Select": st.warning("Please select a Vehicle Number.")
        elif final_vehicle_no.strip() == "": st.warning("Please enter the Manual Vehicle Number.")
        elif invoice_no.strip() == "": st.warning("Please enter Invoice Number.")
        elif company == "Select": st.warning("Please choose a valid Company.")
        else:
            delivery_sheet.append_row([
                delivery_date.strftime("%d/%m/%Y"), final_vehicle_no.strip().upper(), 
                invoice_no.strip(), driver_name.strip(), owner_name.strip(), company.strip(), "No", remark.strip()
            ])
            st.cache_data.clear()
            fresh_df = load_delivery_data()
            st.session_state.current_driver = ""
            st.session_state.current_owner = ""
            st.session_state.current_invoice = get_next_invoice_number(fresh_df)
            st.session_state.submit_success = True
            st.session_state.form_key += 1
            st.rerun()

with tab2:
    st.subheader("Invoice Value Calculations (Inv_Value)")
    key_suffix_fin = st.session_state.form_key
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        fin_invoice_no = st.text_input(
            "Invoice Number *", 
            value=st.session_state.current_invoice, 
            key=f"fin_invoice_field_{key_suffix_fin}"
        )
    with col_f2:
        fin_company = st.selectbox("Company *", options=COMPANY_OPTIONS, key=f"fin_company_{key_suffix_fin}")
        
    fin_date = st.date_input("Invoice Date", value=date.today(), key=f"fin_date_{key_suffix_fin}")
    
    col_tax, col_round = st.columns(2)
    with col_tax:
        taxable_value = st.number_input("Enter Taxable Value *", min_value=0.0, value=0.0, step=100.0, format="%.2f", key=f"fin_taxable_{key_suffix_fin}")
    with col_round:
        round_off = st.number_input("Round Up/Off (+/-)", value=0.0, step=0.01, format="%.2f", key=f"fin_round_{key_suffix_fin}")
    
    # 1. Calculate the raw values
    sgst_raw = taxable_value * 0.025
    cgst_raw = taxable_value * 0.025

    # 2. Force round each component immediately to 2 decimal places
    sgst_val = round(sgst_raw, 2)
    cgst_val = round(cgst_raw, 2)

    # 3. Sum the rounded components so there are no hidden decimals
    total_gst = sgst_val + cgst_val

    # 4. Calculate final total value smoothly
    total_value = round(taxable_value + total_gst + round_off, 2)

    st.markdown("### 📊 Live Tax Calculation Breakdown")
    c_m1, c_m2, c_m3 = st.columns(3)
    c_m1.metric("SGST (2.5%)", f"₹ {sgst_val:,.2f}")
    c_m2.metric("CGST (2.5%)", f"₹ {cgst_val:,.2f}")
    c_m3.metric("Total GST (5%)", f"₹ {total_gst:,.2f}")
    
    st.metric("📦 Final Total Value (Taxable + GST + Round Off)", f"₹ {total_value:,.2f}")

    if st.button("Submit Financial Value Log", type="primary"):
        if fin_company == "Select":
            st.warning("Please choose a valid Company.")
        elif taxable_value <= 0.0:
            st.warning("Taxable Value must be greater than zero.")
        elif fin_invoice_no.strip() == "":
            st.warning("Please ensure Invoice Number is not empty.")
        else:
            inv_value_sheet.append_row([
                fin_date.strftime("%d/%m/%Y"), 
                fin_company.strip(), 
                fin_invoice_no.strip(),
                round(taxable_value, 2), 
                round(sgst_val, 2), 
                round(cgst_val, 2), 
                round(total_gst, 2),
                round(round_off, 2),   
                round(total_value, 2)
            ])
            st.cache_data.clear()
            fresh_df = load_delivery_data()
            st.session_state.current_invoice = get_next_invoice_number(fresh_df)
            st.session_state.submit_success = True
            st.session_state.form_key += 1
            st.rerun() # FIX: Removed trailing comma
# ======================================================
# UI Section: Pending Deliveries Management
# ======================================================
st.markdown("---")
st.subheader("📋 Pending Deliveries (Not Received)")
pending_df = delivery_df[delivery_df["Invoice Received"].str.strip().str.lower() == "no"]

if pending_df.empty:
    st.info("🎉 All deliveries have been successfully received!")
else:
    col_h1, col_h2, col_h3, col_h4, col_h5, col_h6 = st.columns([1.2, 1.5, 1.5, 1.5, 2.5, 1])
    with col_h1: st.markdown("**Date**")
    with col_h2: st.markdown("**Invoice No.**")
    with col_h3: st.markdown("**Vehicle No.**")
    with col_h4: st.markdown("**Driver**")
    with col_h5: st.markdown("**Company & Location**")
    with col_h6: st.markdown("**Action**")
    st.markdown("---")

    for idx, row in pending_df.iterrows():
        gs_row = idx + 2
        col_date, col_inv, col_veh, col_driver, col_comp, col_act = st.columns([1.2, 1.5, 1.5, 1.5, 2.5, 1])
        
        with col_date: 
            # Safely format the date back to DD/MM/YYYY string if it's a datetime object
            if isinstance(row["Date"], pd.Timestamp) or hasattr(row["Date"], "strftime"):
                st.write(row["Date"].strftime("%d/%m/%Y"))
            else:
                st.write(str(row["Date"]))
                
        with col_inv: 
            st.write(row["Invoice No."])
        with col_veh: 
            st.write(row["Vehicle No."])
        with col_driver: 
            st.write(row["Driver"])
        with col_comp: 
            st.write(row["Company & Location"])
        with col_act:
            if st.checkbox("Receive", key=f"recv_approval_act_{gs_row}"):
                delivery_sheet.update_cell(gs_row, 7, "Yes")
                st.cache_data.clear()
                fresh_df = load_delivery_data()
                st.session_state.current_invoice = get_next_invoice_number(fresh_df)
                st.session_state.submit_success = True
                st.rerun()

# ======================================================
# UI Section: Post-Submission Loading / Unloading Charges
# ======================================================
st.markdown("---")
st.subheader("💰 Add Loading & Unloading Charges")

# Filter out empty or unsubmitted rows to only show valid submitted invoices
if delivery_df.empty:
    st.info("No submitted invoices found to apply charges to.")
else:
    # Safely extract unique, non-empty invoice numbers for the dropdown selection
    submitted_invoices = delivery_df["Invoice No."].dropna().astype(str).str.strip()
    valid_invoice_options = ["Select Invoice"] + [inv for inv in submitted_invoices.unique() if inv != ""]
    
    col_c1, col_c2, col_c3 = st.columns(3)
    
    with col_c1:
        selected_charge_invoice = st.selectbox(
            "Select Submitted Invoice *", 
            options=valid_invoice_options,
            key="charge_invoice_selector"
        )
        
    # Locate the row index if an invoice is selected
    target_gs_row = None
    existing_loading = 0.0
    existing_unloading = 0.0
    
    if selected_charge_invoice != "Select Invoice":
        # Match the selected invoice row in the dataframe
        match_idx = delivery_df[delivery_df["Invoice No."] == selected_charge_invoice].index
        if not match_idx.empty:
            # Save index (gspread uses 1-based indexing, add 2 for header offset)
            target_gs_row = int(match_idx[0]) + 2
            
            # Fetch existing values if they already exist in the sheet to pre-fill them safely
            row_data = delivery_df.loc[match_idx[0]]
            if "Loading Charge" in row_data and str(row_data["Loading Charge"]).strip():
                existing_loading = float(pd.to_numeric(row_data["Loading Charge"], errors="coerce") or 0.0)
            if "Unloading Charge" in row_data and str(row_data["Unloading Charge"]).strip():
                existing_unloading = float(pd.to_numeric(row_data["Unloading Charge"], errors="coerce") or 0.0)

    with col_c2:
        loading_input = st.number_input(
            "Loading Charge (₹)", 
            min_value=0.0, 
            value=existing_loading, 
            step=10.0, 
            format="%.2f",
            key="loading_charge_input"
        )
        
    with col_c3:
        unloading_input = st.number_input(
            "Unloading Charge (₹)", 
            min_value=0.0, 
            value=existing_unloading, 
            step=10.0, 
            format="%.2f",
            key="unloading_charge_input"
        )

    # Submission Action Button
    if st.button("Save Charges to Invoice", type="secondary"):
        if selected_charge_invoice == "Select Invoice":
            st.warning("Please choose a valid submitted invoice from the dropdown menu first.")
        elif target_gs_row is None:
            st.error("Could not trace the structural coordinates of this invoice in Google Sheets.")
        else:
            # Column 9 is Loading Charge, Column 10 is Unloading Charge (directly after column 8: Remark)
            delivery_sheet.update_cell(target_gs_row, 9, round(loading_input, 2))
            delivery_sheet.update_cell(target_gs_row, 10, round(unloading_input, 2))
            
            st.toast(f"💵 Charges saved successfully for Invoice {selected_charge_invoice}!")
            st.cache_data.clear()  # Drop cached copy to load updated values immediately
            st.rerun()

# ======================================================
# UI Section: Company Wise Bill Summary & Export
# ======================================================
st.markdown("---")
st.subheader("🔍 Company Wise Bill Value Summary")

if inv_value_df.empty:
    st.info("No corporate financial billing information available yet.")
else:
    filter_options = ["All Companies"] + [c for c in COMPANY_OPTIONS if c != "Select"]
    selected_filter_company = st.selectbox("Select Company to View Breakdown", options=filter_options, key="bill_summary_filter_comp")
    
    if selected_filter_company == "All Companies":
        filtered_financial_df = inv_value_df
    else:
        filtered_financial_df = inv_value_df[inv_value_df["Company"].str.strip() == selected_filter_company]
        
    if filtered_financial_df.empty:
        st.warning(f"No logged transactions found matching {selected_filter_company}.")
    else:
        numeric_cols = ["Taxable Value", "SGST", "CGST", "Total GST", "Total Value"]
        for col in numeric_cols:
            filtered_financial_df[col] = pd.to_numeric(filtered_financial_df[col], errors="coerce").fillna(0.0)
            
        sum_taxable = filtered_financial_df["Taxable Value"].sum()
        sum_total_gst = filtered_financial_df["Total GST"].sum()
        sum_total_val = filtered_financial_df["Total Value"].sum()
        
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Total Taxable Amt", f"₹ {sum_taxable:,.2f}")
        m_col2.metric("Accumulated GST Collected", f"₹ {sum_total_gst:,.2f}")
        m_col3.metric("Gross Aggregate Valuation", f"₹ {sum_total_val:,.2f}")
        
        st.dataframe(
            filtered_financial_df,
            column_config={
                "Taxable Value": st.column_config.NumberColumn(format="₹ %.2f"),
                "SGST": st.column_config.NumberColumn(format="₹ %.2f"),
                "CGST": st.column_config.NumberColumn(format="₹ %.2f"),
                "Total GST": st.column_config.NumberColumn(format="₹ %.2f"),
                "Total Value": st.column_config.NumberColumn(format="₹ %.2f")
            },
            use_container_width=True,
            hide_index=True
        )
        
        csv_data = filtered_financial_df.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="📥 Download Filtered Bill Report (CSV)",
            data=csv_data,
            file_name=f"bill_report_{selected_filter_company.replace(' ', '_').lower()}_{date.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            type="secondary"
        )

############################--------------------------------------------------Stock Record----------------------------------###################################
WORKSHEET_NAME4 = "Stock_Record"

COLUMNS4 = ["Date", "Company", "Product", "Total Production", "Total Delivery", "Total Stock"]

# Product lists matching your provided inventory categories
PRODUCTS_KAMAL = [
    "Select", "RED BOX-NEW", "GREEN BOX", "YELLOW Box", "AMRIT BHANDER Box", 
    "SMALL CONE Box", "BIG CONE BOX", "PINK box", "Small CHOCOBAR BOX", 
    "Big CHOCOBAR BOX", "Kulfi BOX (extra hard)", "BLUE BOX", "SWIRL BOX", 
    "TRIO BOX", "PURPLE BOX", "MULTI Crush BOX", "BIG CONE INNER", 
    "KULFI INNER", "MANGO/CARAMEL INNER", "SMALL CONE INNER", "PURPLE INNER"
]

PRODUCTS_AGARWAL = [
    "Select", "CRIMOSE-AGARWAL Small CONE BOX", "CRIMOSE-AGARWAL Small CONE INNER", 
    "CRIMOSE-AGARWAL Small CHOCOBAR BOX", "CRIMOSE-AGARWAL CARAMEL BOX", 
    "CRIMOSE-AGARWAL CARAMEL INNER BOX", "CRIMOSE-AGARWAL BIG CHOCOBAR BOX", 
    "CRIMOSE-AGARWAL Nutt Roll BOX", "CIMOSE-AGARWAL 80 ML CUP BOX"
]

@st.cache_resource(ttl=3600)  
def connect_stock_sheet():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME4)

stock_sheet = connect_stock_sheet()

@st.cache_data(ttl=10)
def load_stock_data():
    records = stock_sheet.get_all_records()
    if not records:
        return pd.DataFrame(columns=COLUMNS4)
    df = pd.DataFrame(records)
    df.columns = df.columns.str.strip()
    for col in COLUMNS4:
        if col not in df.columns: 
            df[col] = 0 if "Total" in col else ""
    return df[COLUMNS4]

# Load current stock master table dataframe
stock_df = load_stock_data()

st.subheader("📦 Live Product Stock Master (Modification Basis)")
key_suffix_stock = st.session_state.form_key

col_s1, col_s2, col_s3 = st.columns(3)

with col_s1:
    stock_company = st.selectbox(
        "Company *", 
        options=["Select", "Kamal’s Ice Cream (Dhulagori)", "Agarwal Food Product (Sankrail)"],
        key=f"stock_comp_{key_suffix_stock}"
    )

with col_s2:
    if "Kamal" in stock_company:
        product_options = PRODUCTS_KAMAL
    elif "Agarwal" in stock_company:
        product_options = PRODUCTS_AGARWAL
    else:
        product_options = ["Select"]
        
    stock_product = st.selectbox(
        "Product Item *", 
        options=product_options, 
        key=f"stock_prod_{key_suffix_stock}"
    )

with col_s3:
    stock_date = st.date_input("Last Update Date", value=date.today(), key=f"stock_date_{key_suffix_stock}")

col_qty1, col_qty2 = st.columns(2)
with col_qty1:
    new_prod_input = st.number_input("Add to Production Quantity", min_value=0, value=0, step=1, key=f"add_prod_{key_suffix_stock}")
with col_qty2:
    new_deliv_input = st.number_input("Add to Delivery Quantity", min_value=0, value=0, step=1, key=f"add_deliv_{key_suffix_stock}")

# --- Core Dynamic Row-Locating Logic ---
existing_row_idx = None
current_total_prod = 0
current_total_deliv = 0

if not stock_df.empty and stock_product != "Select":
    # Search for an existing row matching Company and Product
    match_condition = (stock_df["Company"] == stock_company) & (stock_df["Product"] == stock_product)
    matching_rows = stock_df[match_condition]
    
    if not matching_rows.empty:
        # Save the dataframe index to calculate the spreadsheet row number later
        existing_row_idx = matching_rows.index[0]
        current_total_prod = int(pd.to_numeric(matching_rows.iloc[0]["Total Production"], errors="coerce") or 0)
        current_total_deliv = int(pd.to_numeric(matching_rows.iloc[0]["Total Delivery"], errors="coerce") or 0)

# Calculate updated accumulated totals
updated_total_prod = current_total_prod + new_prod_input
updated_total_deliv = current_total_deliv + new_deliv_input
updated_total_stock = updated_total_prod - updated_total_deliv

# Live Metrics Dashboard UI Summary
st.markdown("### 📊 Preview of Live Inventory Updates")
sm_col1, sm_col2, sm_col3 = st.columns(3)
sm_col1.metric("Updated Total Production", f"{updated_total_prod} units", delta=f"+{new_prod_input}" if new_prod_input else None)
sm_col2.metric("Updated Total Delivery", f"{updated_total_deliv} units", delta=f"+{new_deliv_input}" if new_deliv_input else None)
sm_col3.metric("Live Total Stock Balance", f"{updated_total_stock} units")

if st.button("Update Stock", type="primary"):
    if stock_company == "Select":
        st.warning("Please choose a valid Company.")
    elif stock_product == "Select":
        st.warning("Please select a target Product Item.")
    elif new_prod_input == 0 and new_deliv_input == 0:
        st.warning("Please enter an amount to add to either Production or Delivery.")
    else:
        row_payload = [
            stock_date.strftime("%d/%m/%Y"),
            stock_company.strip(),
            stock_product.strip(),
            int(updated_total_prod),
            int(updated_total_deliv),
            int(updated_total_stock)
        ]
        
        if existing_row_idx is not None:
            # Match found! Calculate spreadsheet row (gspread uses 1-based indexing, add 2 for header offset)
            gs_row_num = int(existing_row_idx) + 2
            
            # Select range matching columns 1 through 6 on that row and update it
            cell_range = f"A{gs_row_num}:F{gs_row_num}"
            stock_sheet.update(cell_range, [row_payload])
            st.toast("✏️ Existing product stock row updated successfully!")
        else:
            # Match not found! Append a brand-new row for this item
            stock_sheet.append_row(row_payload)
            st.toast("✨ New product added to stock sheet successfully!")
        
        st.cache_data.clear()
        st.session_state.submit_success = True
        st.session_state.form_key += 1
        st.rerun()

# ======================================================
# Real-Time Master Stock Viewer Window
# ======================================================
st.markdown("---")
st.subheader("📋 Master Inventory Stock Status")

if stock_df.empty:
    st.info("No product stock configurations found in your Google Sheet.")
else:
    st.dataframe(
        stock_df,
        use_container_width=True,
        hide_index=True
    )

WORKSHEET_NAME5 = "Unloading"  # <-- Your new sheet target configurations
COLUMNS5 = ["Date", "Amount", "Remark"]

# Add this connector block with your other sheet connections
@st.cache_resource(ttl=3600)  
def connect_unloading_sheet():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME5)

################------------Unloading--------------#####################

unloading_sheet = connect_unloading_sheet()

@st.cache_data(ttl=10)  # Shorter TTL cache allows manual deletions to sync quickly
def load_unloading_data():
    records = unloading_sheet.get_all_records()
    if not records:
        return pd.DataFrame(columns=COLUMNS5)
    df = pd.DataFrame(records)
    df.columns = df.columns.str.strip()
    for col in COLUMNS5:
        if col not in df.columns: 
            df[col] = 0.0 if col == "Amount" else ""
    return df[COLUMNS5]

# Load active tracker data rows from the new sheet
unloading_df = load_unloading_data()

st.markdown("---")
st.subheader("🚛 Miscellaneous Unloading Expense Ledger")
key_suffix_unload = st.session_state.form_key

col_u1, col_u2, col_u3 = st.columns([1.5, 2, 3])

with col_u1:
    unload_date = st.date_input("Expense Date", value=date.today(), key=f"unload_date_{key_suffix_unload}")

with col_u2:
    unload_amount = st.number_input(
        "Amount (₹) *", 
        min_value=0.0, 
        value=0.0, 
        step=50.0, 
        format="%.2f", 
        key=f"unload_amt_{key_suffix_unload}"
    )

with col_u3:
    unload_remark = st.text_input("Remark / Details", key=f"unload_rem_{key_suffix_unload}")

# Form Submission Action Logic
if st.button("Submit Unloading Entry", type="primary", key="btn_submit_unloading"):
    if unload_amount <= 0.0:
        st.warning("Please enter an amount greater than zero.")
    else:
        # Appends items strictly to the rows of Worksheet 5: Unloading
        unloading_sheet.append_row([
            unload_date.strftime("%d/%m/%Y"),
            round(unload_amount, 2),
            unload_remark.strip()
        ])
        
        st.cache_data.clear()  # Clear memory cache so data refreshes instantly
        st.session_state.submit_success = True
        st.session_state.form_key += 1
        st.rerun()

# ======================================================
# Real-Time Unloading Sheet Data Table Record Viewer
# ======================================================
st.markdown("### 📋 Logged Unloading Entries")

if unloading_df.empty:
    st.info("No recorded unloading expense records found.")
else:
    # 1. Real-time metric summary tally calculation box
    total_unloading_spent = pd.to_numeric(unloading_df["Amount"], errors="coerce").sum()
    st.metric("Total Unloading Expenses Applied", f"₹ {total_unloading_spent:,.2f}")
    
    # 2. Interactive Data View window 
    st.dataframe(
        unloading_df,
        column_config={
            "Amount": st.column_config.NumberColumn(format="₹ %.2f")
        },
        use_container_width=True,
        hide_index=True
    )

#######################################Paper Rill Stock######################################
# ------------------------------------------------------
# Helper: Native Python JSON Sanitizer for gspread
# ------------------------------------------------------
def sanitize_value(val):
    """Converts Pandas/NumPy types, NaNs, and dates into standard Python primitives."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return ""
    # Safe explicit check directly against module attributes to prevent NameError
    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.strftime("%d/%m/%Y")
    if isinstance(val, (np.integer, int)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        return float(val)
    return str(val).strip()

# ------------------------------------------------------
# Paper Rill Stock Ledger Configuration & Connection
# ------------------------------------------------------
WORKSHEET_MASTER = "rill_stock"
WORKSHEET_HISTORY = "rill_history"

COLUMNS_MASTER = ["Size", "GSM", "BF", "Quantity", "Weight", "Remark"]
COLUMNS_HISTORY = ["Date", "Type", "Size", "GSM", "BF", "Quantity", "Weight", "Remark"]

@st.cache_resource(ttl=3600)  
def connect_spreadsheet():
    """Connects once and caches the gspread Spreadsheet object."""
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID)

spreadsheet = connect_spreadsheet()

# Get sheet references (not passed to cached functions directly)
rill_master_sheet = spreadsheet.worksheet(WORKSHEET_MASTER)
rill_history_sheet = spreadsheet.worksheet(WORKSHEET_HISTORY)

@st.cache_data(ttl=10)
def load_data(sheet_name, columns):
    """Pass sheet_name (string) instead of the gspread worksheet object so Streamlit can cache it."""
    sheet = spreadsheet.worksheet(sheet_name)
    records = sheet.get_all_records()
    if not records:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(records)
    df.columns = df.columns.str.strip()
    for col in columns:
        if col not in df.columns: 
            df[col] = 0 if col in ["Quantity", "Weight"] else ""
    return df[columns]

# Load current dataframes safely passing string names
rill_df = load_data(WORKSHEET_MASTER, COLUMNS_MASTER)
history_df = load_data(WORKSHEET_HISTORY, COLUMNS_HISTORY)

st.markdown("---")
st.subheader("📜 Paper Rill Stock Ledger & Audit Log")
key_suffix_rill = st.session_state.form_key

# Tabs for Operations vs History
tab_entry, tab_history = st.tabs(["⚡ Transaction Entry", "📜 History Log"])

with tab_entry:
    st.markdown("##### 🔍 Select Specification")

    unique_sizes = sorted(list(set(rill_df["Size"].astype(str).str.strip().unique()))) if not rill_df.empty else []
    unique_gsms = sorted(list(set(rill_df["GSM"].astype(str).str.strip().unique()))) if not rill_df.empty else []
    unique_bfs = sorted(list(set(rill_df["BF"].astype(str).str.strip().unique()))) if not rill_df.empty else []

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        selected_size = st.selectbox("Size *", options=["Select Size..."] + unique_sizes + ["➕ New Size"], key=f"s_{key_suffix_rill}")
    with col_s2:
        selected_gsm = st.selectbox("GSM *", options=["Select GSM..."] + unique_gsms + ["➕ New GSM"], key=f"g_{key_suffix_rill}")
    with col_s3:
        selected_bf = st.selectbox("BF *", options=["Select BF..."] + unique_bfs + ["➕ New BF"], key=f"b_{key_suffix_rill}")

    is_new_entry = (
        "➕ New Size" in selected_size or 
        "➕ New GSM" in selected_gsm or 
        "➕ New BF" in selected_bf or
        selected_size == "Select Size..." or
        selected_gsm == "Select GSM..." or
        selected_bf == "Select BF..."
    )

    matched_rows = pd.DataFrame()
    if not is_new_entry and not rill_df.empty:
        matched_rows = rill_df[
            (rill_df["Size"].astype(str).str.strip().str.lower() == selected_size.lower()) &
            (rill_df["GSM"].astype(str).str.strip().str.lower() == selected_gsm.lower()) &
            (rill_df["BF"].astype(str).str.strip().str.lower() == selected_bf.lower())
        ]

    # Mode A: Existing Item Modification
    if not matched_rows.empty:
        matched_idx = matched_rows.index[0]
        matched_row = matched_rows.iloc[0]
        gs_row_num = matched_idx + 2

        curr_qty = int(pd.to_numeric(matched_row["Quantity"], errors="coerce") or 0)
        curr_weight = float(pd.to_numeric(matched_row["Weight"], errors="coerce") or 0.0)
        curr_remark = str(matched_row["Remark"])

        st.info(f"📌 **Current Balance:** {curr_qty} Rolls | **Weight:** {curr_weight:.2f} kg")

        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns([1.5, 1.5, 1.5, 1.5, 2])
        with col_m1:
            txn_date = st.date_input("Date", value=date.today(), key=f"dt_mod_{key_suffix_rill}")
        with col_m2:
            action_type = st.radio("Action *", options=["Purchased (+)", "Used (-)"], horizontal=True, key=f"act_{key_suffix_rill}")
        with col_m3:
            qty_change = st.number_input("Qty (Rolls) *", min_value=0, value=0, step=1, key=f"q_mod_{key_suffix_rill}")
        with col_m4:
            weight_change = st.number_input("Weight (kg) *", min_value=0.0, value=0.0, step=0.1, format="%.2f", key=f"w_mod_{key_suffix_rill}")
        with col_m5:
            new_remark = st.text_input("Remark", value="", key=f"r_mod_{key_suffix_rill}")

        final_qty = curr_qty + qty_change if action_type == "Purchased (+)" else curr_qty - qty_change
        final_weight = curr_weight + weight_change if action_type == "Purchased (+)" else curr_weight - weight_change

        if st.button("Submit Transaction", type="primary", key="btn_update_rill"):
            if action_type == "Used (-)" and qty_change > curr_qty:
                st.warning(f"Cannot subtract {qty_change} rolls! Available stock is only {curr_qty} rolls.")
            elif action_type == "Used (-)" and weight_change > curr_weight:
                st.warning(f"Cannot subtract {weight_change:.2f} kg! Available weight is only {curr_weight:.2f} kg.")
            elif qty_change == 0 and weight_change == 0:
                st.warning("Please enter a quantity or weight change.")
            else:
                # 1. Update Master Stock Row
                master_payload = [selected_size, selected_gsm, selected_bf, int(final_qty), round(final_weight, 2), new_remark.strip()]
                clean_master = [sanitize_value(x) for x in master_payload]
                rill_master_sheet.update(range_name=f"A{gs_row_num}:F{gs_row_num}", values=[clean_master])

                # 2. Append to Transaction History Log
                history_payload = [
                    txn_date.strftime("%d/%m/%Y"),
                    "Purchased" if action_type == "Purchased (+)" else "Used",
                    selected_size,
                    selected_gsm,
                    selected_bf,
                    int(qty_change),
                    round(weight_change, 2),
                    new_remark.strip()
                ]
                clean_history = [sanitize_value(x) for x in history_payload]
                rill_history_sheet.append_row(clean_history)

                st.toast(f"✅ Transaction logged! New stock balance: {final_qty} rolls | {final_weight:.2f} kg.")
                st.cache_data.clear()
                st.session_state.form_key += 1
                st.rerun()

    # Mode B: Add New Item Specification
    else:
        st.markdown("##### 📝 Create New Item Specification")
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            final_size = st.text_input("Size *", value="" if selected_size == "Select Size..." else (selected_size if selected_size != "➕ New Size" else ""), key=f"in_sz_{key_suffix_rill}")
        with col_f2:
            final_gsm = st.text_input("GSM *", value="" if selected_gsm == "Select GSM..." else (selected_gsm if selected_gsm != "➕ New GSM" else ""), key=f"in_gsm_{key_suffix_rill}")
        with col_f3:
            final_bf = st.text_input("BF *", value="" if selected_bf == "Select BF..." else (selected_bf if selected_bf != "➕ New BF" else ""), key=f"in_bf_{key_suffix_rill}")

        col_n1, col_n2, col_n3, col_n4 = st.columns([1.5, 1.5, 1.5, 2.5])
        with col_n1:
            txn_date = st.date_input("Date", value=date.today(), key=f"dt_new_{key_suffix_rill}")
        with col_n2:
            new_initial_qty = st.number_input("Initial Quantity *", min_value=0, value=0, step=1, key=f"q_new_{key_suffix_rill}")
        with col_n3:
            new_weight = st.number_input("Initial Weight (kg) *", min_value=0.0, value=0.0, step=0.1, format="%.2f", key=f"w_new_{key_suffix_rill}")
        with col_n4:
            new_remark_text = st.text_input("Remark", key=f"r_new_{key_suffix_rill}")

        if st.button("Save New Stock Item", type="primary", key="btn_add_new_rill"):
            clean_size, clean_gsm, clean_bf = final_size.strip(), final_gsm.strip(), final_bf.strip()

            if not clean_size or not clean_gsm or not clean_bf:
                st.warning("Please fill in Size, GSM, and BF.")
            else:
                # 1. Append to Master Sheet
                master_payload = [clean_size, clean_gsm, clean_bf, int(new_initial_qty), round(float(new_weight), 2), new_remark_text.strip()]
                rill_master_sheet.append_row([sanitize_value(x) for x in master_payload])

                # 2. Log initial opening stock in History Sheet
                history_payload = [
                    txn_date.strftime("%d/%m/%Y"),
                    "Purchased",
                    clean_size,
                    clean_gsm,
                    clean_bf,
                    int(new_initial_qty),
                    round(float(new_weight), 2),
                    f"Initial Stock - {new_remark_text.strip()}".strip(" -")
                ]
                rill_history_sheet.append_row([sanitize_value(x) for x in history_payload])

                st.toast("✨ New rill item added and transaction logged!")
                st.cache_data.clear()
                st.session_state.form_key += 1
                st.rerun()

    st.markdown("### 📋 Current Stock Summary")
    st.dataframe(rill_df, use_container_width=True, hide_index=True)

# ------------------------------------------------------
# Tab 2: Transaction History Log View
# ------------------------------------------------------
with tab_history:
    st.markdown("### 📜 Date-Wise Transaction History Log")

    if history_df.empty:
        st.info("No transaction history available yet.")
    else:
        # Filter options
        col_h1, col_h2, col_h3 = st.columns(3)
        with col_h1:
            filter_type = st.multiselect("Filter Action Type", options=["Purchased", "Used"], default=["Purchased", "Used"])
        with col_h2:
            filter_size = st.multiselect("Filter Size", options=sorted(history_df["Size"].astype(str).unique()))
        with col_h3:
            search_text = st.text_input("Search Remarks/Specs")

        filtered_df = history_df.copy()

        if filter_type:
            filtered_df = filtered_df[filtered_df["Type"].isin(filter_type)]
        if filter_size:
            filtered_df = filtered_df[filtered_df["Size"].astype(str).isin(filter_size)]
        if search_text:
            filtered_df = filtered_df[
                filtered_df["Remark"].astype(str).str.contains(search_text, case=False) |
                filtered_df["Size"].astype(str).str.contains(search_text, case=False)
            ]

        st.dataframe(
            filtered_df,
            column_config={
                "Quantity": st.column_config.NumberColumn("Quantity (Rolls)", format="%d"),
                "Weight": st.column_config.NumberColumn("Weight (kg)", format="%.2f")
            },
            use_container_width=True,
            hide_index=True
        )
