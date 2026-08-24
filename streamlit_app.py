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
import requests

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

@st.cache_data(ttl=60)  # Caches data in memory for 5 minutes
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
# ======================================================
# Transport Record Section
# ======================================================

WORKSHEET_NAME2 = "Delivery_Record"
WORKSHEET_NAME3 = "Inv_Value"

COLUMNS2 = [
    "Date",
    "Vehicle No.",
    "Invoice No.",
    "Driver",
    "Owner",
    "Company & Location",
    "Invoice Received",
    "Remark",
    "Loading Charge",
    "Unloading Charge",
]

COLUMNS3 = [
    "Date",
    "Company",
    "Invoice No.",
    "Taxable Value",
    "SGST",
    "CGST",
    "Total GST",
    "Round Off",
    "Total Value",
]

COMPANY_OPTIONS = [
    "Select",
    "Kamal’s cake (SOUTH SANKRAIL)",
    "Kamal’s Ice Cream (HOWRAH FOOD PARK, ”Adila”)",
    "Kamals ORL O (Dhulagori)",
    "Kamals Ice Cream (Shaoraphuli, ”Adila”)",
    "Agarwal Food Product (Sankrail)",
    "Pamir Ice Cream (Raiganj)",
    "Top notch (Gaighata)",
    "Cold Roll (Gaighata)",
]

VEHICLE_MASTER = {
    "Select": {"driver": "", "owner": ""},
    "WB23C6784": {"driver": "Mangal", "owner": "D Biswas"},
    "WB25L6773": {"driver": "Raja", "owner": "D Biswas"},
    "WB25G3488": {"driver": "Babu", "owner": "D Biswas"},
    "WB25W1226": {"driver": "Sanjay", "owner": "D Biswas"},
    "WB25P9492": {"driver": "Badal", "owner": "D Biswas"},
    "WB25H7255": {"driver": "", "owner": "Chotu"},
    "WB25H5255": {"driver": "", "owner": "Chotu"},
    "Others": {"driver": "", "owner": ""},
}


# ======================================================
# Cached Database Connectors
# ======================================================
@st.cache_resource(ttl=3600)
def connect_delivery_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME2)


@st.cache_resource(ttl=3600)
def connect_invoice_value_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME3)


delivery_sheet = connect_delivery_sheet()
inv_value_sheet = connect_invoice_value_sheet()


@st.cache_data(ttl=10)
def load_delivery_data():
    raw_data = delivery_sheet.get_all_values()
    if not raw_data or len(raw_data) < 2:
        return pd.DataFrame(columns=COLUMNS2)

    headers = [str(h).strip() for h in raw_data[0]]
    df = pd.DataFrame(raw_data[1:], columns=headers)

    for col in COLUMNS2:
        if col not in df.columns:
            df[col] = ""

    df = df[COLUMNS2].copy()
    df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y", errors="coerce")
    text_cols = [
        "Vehicle No.",
        "Invoice No.",
        "Driver",
        "Owner",
        "Company & Location",
        "Invoice Received",
        "Remark",
    ]
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()

    return df


@st.cache_data(ttl=10)
def load_invoice_value_data():
    raw_data = inv_value_sheet.get_all_values()
    if not raw_data or len(raw_data) < 2:
        return pd.DataFrame(columns=COLUMNS3)

    headers = [str(h).strip() for h in raw_data[0]]
    df = pd.DataFrame(raw_data[1:], columns=headers)

    for col in COLUMNS3:
        if col not in df.columns:
            df[col] = 0.0 if "Value" in col or "GST" in col else ""

    df = df[COLUMNS3].copy()
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
    match = re.search(r"(\d+)$", last_invoice)
    if match:
        num_part = match.group(1)
        next_num = int(num_part) + 1
        next_num_str = str(next_num).zfill(len(num_part))
        return last_invoice[: match.start()] + next_num_str
    return "1"


suggested_next_invoice = get_next_invoice_number(delivery_df)

# ======================================================
# Runtime Session States
# ======================================================
if "submit_success" not in st.session_state:
    st.session_state.submit_success = False
if "form_key" not in st.session_state:
    st.session_state.form_key = 0
if "current_driver" not in st.session_state:
    st.session_state.current_driver = ""
if "current_owner" not in st.session_state:
    st.session_state.current_owner = ""
if "current_invoice" not in st.session_state:
    st.session_state.current_invoice = suggested_next_invoice

if st.session_state.submit_success:
    st.success("✅ Log Entry Appended Successfully")
    st.session_state.submit_success = False


def update_vehicle_details():
    sel = st.session_state[f"v_sel_{st.session_state.form_key}"]
    st.session_state.current_driver = VEHICLE_MASTER[sel]["driver"]
    st.session_state.current_owner = VEHICLE_MASTER[sel]["owner"]
    key_suffix = st.session_state.form_key
    st.session_state[f"driver_field_{key_suffix}"] = VEHICLE_MASTER[sel][
        "driver"
    ]
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
        vehicle_selection = st.selectbox(
            "Vehicle No. *",
            options=list(VEHICLE_MASTER.keys()),
            key=f"v_sel_{key_suffix}",
            on_change=update_vehicle_details,
        )
        final_vehicle_no = (
            st.text_input(
                "Manual Vehicle No. *", key=f"v_manual_{key_suffix}"
            )
            if vehicle_selection == "Others"
            else vehicle_selection
        )
    with col2:
        invoice_no = st.text_input(
            "Invoice Number *",
            value=st.session_state.current_invoice,
            key=f"delivery_entry_invoice_field_{key_suffix}",
        )

    col3, col4 = st.columns(2)
    with col3:
        driver_name = st.text_input(
            "Driver",
            value=st.session_state.current_driver,
            key=f"driver_field_{key_suffix}",
        )
    with col4:
        owner_name = st.text_input(
            "Owner",
            value=st.session_state.current_owner,
            key=f"owner_field_{key_suffix}",
        )

    company = st.selectbox(
        "Company & Location *",
        options=COMPANY_OPTIONS,
        key=f"delivery_company_{key_suffix}",
    )
    remark = st.text_area("Remark", key=f"delivery_remark_{key_suffix}")
    delivery_date = st.date_input(
        "Delivery Date", value=date.today(), key=f"delivery_date_{key_suffix}"
    )

    if st.button("Submit Delivery Log", type="primary"):
        if vehicle_selection == "Select":
            st.warning("Please select a Vehicle Number.")
        elif final_vehicle_no.strip() == "":
            st.warning("Please enter the Manual Vehicle Number.")
        elif invoice_no.strip() == "":
            st.warning("Please enter Invoice Number.")
        elif company == "Select":
            st.warning("Please choose a valid Company.")
        else:
            # Full 10-column alignment matching COLUMNS2
            delivery_sheet.append_row([
                delivery_date.strftime("%d/%m/%Y"),
                final_vehicle_no.strip().upper(),
                invoice_no.strip(),
                driver_name.strip(),
                owner_name.strip(),
                company.strip(),
                "No",
                remark.strip(),
                0.0,
                0.0,
            ])
            st.cache_data.clear()
            fresh_df = load_delivery_data()
            st.session_state.current_driver = ""
            st.session_state.current_owner = ""
            st.session_state.current_invoice = get_next_invoice_number(
                fresh_df
            )
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
            key=f"fin_invoice_field_{key_suffix_fin}",
        )
    with col_f2:
        fin_company = st.selectbox(
            "Company *",
            options=COMPANY_OPTIONS,
            key=f"fin_company_{key_suffix_fin}",
        )

    fin_date = st.date_input(
        "Invoice Date",
        value=date.today(),
        key=f"fin_date_{key_suffix_fin}",
    )

    col_tax, col_round = st.columns(2)
    with col_tax:
        taxable_value = st.number_input(
            "Enter Taxable Value *",
            min_value=0.0,
            value=0.0,
            step=100.0,
            format="%.2f",
            key=f"fin_taxable_{key_suffix_fin}",
        )
    with col_round:
        round_off = st.number_input(
            "Round Up/Off (+/-)",
            value=0.0,
            step=0.01,
            format="%.2f",
            key=f"fin_round_{key_suffix_fin}",
        )

    sgst_raw = taxable_value * 0.025
    cgst_raw = taxable_value * 0.025
    sgst_val = round(sgst_raw, 2)
    cgst_val = round(cgst_raw, 2)
    total_gst = sgst_val + cgst_val
    total_value = round(taxable_value + total_gst + round_off, 2)

    st.markdown("### 📊 Live Tax Calculation Breakdown")
    c_m1, c_m2, c_m3 = st.columns(3)
    c_m1.metric("SGST (2.5%)", f"₹ {sgst_val:,.2f}")
    c_m2.metric("CGST (2.5%)", f"₹ {cgst_val:,.2f}")
    c_m3.metric("Total GST (5%)", f"₹ {total_gst:,.2f}")

    st.metric(
        "📦 Final Total Value (Taxable + GST + Round Off)",
        f"₹ {total_value:,.2f}",
    )

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
                round(total_value, 2),
            ])
            st.cache_data.clear()
            fresh_df = load_delivery_data()
            st.session_state.current_invoice = get_next_invoice_number(
                fresh_df
            )
            st.session_state.submit_success = True
            st.session_state.form_key += 1
            st.rerun()

# ======================================================
# UI Section: Pending Deliveries Management
# ======================================================
st.markdown("---")
st.subheader("📋 Pending Deliveries (Not Received)")
pending_df = delivery_df[
    delivery_df["Invoice Received"].str.strip().str.lower() == "no"
]

if pending_df.empty:
    st.info("🎉 All deliveries have been successfully received!")
else:
    col_h1, col_h2, col_h3, col_h4, col_h5, col_h6 = st.columns(
        [1.2, 1.5, 1.5, 1.5, 2.5, 1]
    )
    with col_h1:
        st.markdown("**Date**")
    with col_h2:
        st.markdown("**Invoice No.**")
    with col_h3:
        st.markdown("**Vehicle No.**")
    with col_h4:
        st.markdown("**Driver**")
    with col_h5:
        st.markdown("**Company & Location**")
    with col_h6:
        st.markdown("**Action**")
    st.markdown("---")

    for idx, row in pending_df.iterrows():
        gs_row = idx + 2
        col_date, col_inv, col_veh, col_driver, col_comp, col_act = (
            st.columns([1.2, 1.5, 1.5, 1.5, 2.5, 1])
        )

        with col_date:
            if isinstance(row["Date"], pd.Timestamp) or hasattr(
                row["Date"], "strftime"
            ):
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
                st.session_state.current_invoice = get_next_invoice_number(
                    fresh_df
                )
                st.session_state.submit_success = True
                st.rerun()

# ======================================================
# UI Section: Post-Submission Loading / Unloading Charges
# ======================================================
st.markdown("---")
st.subheader("💰 Add Loading & Unloading Charges")

if delivery_df.empty:
    st.info("No submitted invoices found to apply charges to.")
else:
    submitted_invoices = (
        delivery_df["Invoice No."].dropna().astype(str).str.strip()
    )
    valid_invoice_options = ["Select Invoice"] + [
        inv for inv in submitted_invoices.unique() if inv != ""
    ]

    col_c1, col_c2, col_c3 = st.columns(3)

    with col_c1:
        selected_charge_invoice = st.selectbox(
            "Select Submitted Invoice *",
            options=valid_invoice_options,
            key="charge_invoice_selector",
        )

    target_gs_row = None
    existing_loading = 0.0
    existing_unloading = 0.0

    if selected_charge_invoice != "Select Invoice":
        match_idx = delivery_df[
            delivery_df["Invoice No."] == selected_charge_invoice
        ].index
        if not match_idx.empty:
            target_gs_row = int(match_idx[0]) + 2
            row_data = delivery_df.loc[match_idx[0]]
            if "Loading Charge" in row_data and str(
                row_data["Loading Charge"]
            ).strip():
                existing_loading = float(
                    pd.to_numeric(
                        row_data["Loading Charge"], errors="coerce"
                    )
                    or 0.0
                )
            if "Unloading Charge" in row_data and str(
                row_data["Unloading Charge"]
            ).strip():
                existing_unloading = float(
                    pd.to_numeric(
                        row_data["Unloading Charge"], errors="coerce"
                    )
                    or 0.0
                )

    with col_c2:
        loading_input = st.number_input(
            "Loading Charge (₹)",
            min_value=0.0,
            value=existing_loading,
            step=10.0,
            format="%.2f",
            key="loading_charge_input",
        )

    with col_c3:
        unloading_input = st.number_input(
            "Unloading Charge (₹)",
            min_value=0.0,
            value=existing_unloading,
            step=10.0,
            format="%.2f",
            key="unloading_charge_input",
        )

    if st.button("Save Charges to Invoice", type="secondary"):
        if selected_charge_invoice == "Select Invoice":
            st.warning(
                "Please choose a valid submitted invoice from the dropdown menu first."
            )
        elif target_gs_row is None:
            st.error(
                "Could not trace the structural coordinates of this invoice in Google Sheets."
            )
        else:
            delivery_sheet.update_cell(
                target_gs_row, 9, round(loading_input, 2)
            )
            delivery_sheet.update_cell(
                target_gs_row, 10, round(unloading_input, 2)
            )

            st.toast(
                f"💵 Charges saved successfully for Invoice {selected_charge_invoice}!"
            )
            st.cache_data.clear()
            st.rerun()

# ======================================================
# UI Section: Company Wise Bill Summary & Export
# ======================================================
st.markdown("---")
st.subheader("🔍 Company Wise Bill Value Summary")

if inv_value_df.empty:
    st.info("No corporate financial billing information available yet.")
else:
    filter_options = ["All Companies"] + [
        c for c in COMPANY_OPTIONS if c != "Select"
    ]
    selected_filter_company = st.selectbox(
        "Select Company to View Breakdown",
        options=filter_options,
        key="bill_summary_filter_comp",
    )

    if selected_filter_company == "All Companies":
        filtered_financial_df = inv_value_df.copy()
    else:
        filtered_financial_df = inv_value_df[
            inv_value_df["Company"].str.strip() == selected_filter_company
        ].copy()

    if filtered_financial_df.empty:
        st.warning(
            f"No logged transactions found matching {selected_filter_company}."
        )
    else:
        numeric_cols = [
            "Taxable Value",
            "SGST",
            "CGST",
            "Total GST",
            "Total Value",
        ]
        for col in numeric_cols:
            filtered_financial_df[col] = pd.to_numeric(
                filtered_financial_df[col], errors="coerce"
            ).fillna(0.0)

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
                "Total Value": st.column_config.NumberColumn(format="₹ %.2f"),
            },
            use_container_width=True,
            hide_index=True,
        )

        csv_data = filtered_financial_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="📥 Download Filtered Bill Report (CSV)",
            data=csv_data,
            file_name=f"bill_report_{selected_filter_company.replace(' ', '_').lower()}_{date.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            type="secondary",
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
# Google Apps Script API Configuration
# ------------------------------------------------------
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzDCxGzu7vP31Ui6ottPoDibQlgGnEu3PPmLPEFq7muq3Kp8eozCkNEke1anGAqI9TZ/exec"

COLUMNS_MASTER = ["Size", "GSM", "BF", "Quantity", "Weight", "Breakup_Weight", "Remark"]
COLUMNS_HISTORY = ["Date", "Type", "Size", "GSM", "BF", "Quantity", "Weight", "Breakup_Weight", "Remark"]

# ------------------------------------------------------
# Helpers: Breakup Weight Processing & Callbacks
# ------------------------------------------------------
def parse_breakup_weights(breakup_str):
    """
    Parses a string like '12.5, 15.0, 10.2' into a total weight sum and count.
    Returns (total_sum, count, cleaned_str)
    """
    if not breakup_str or not str(breakup_str).strip():
        return 0.0, 0, ""
    
    parts = [p.strip() for p in str(breakup_str).split(",") if p.strip()]
    valid_weights = []
    
    for p in parts:
        try:
            val = float(p)
            if val > 0:
                valid_weights.append(val)
        except ValueError:
            continue
            
    total_sum = sum(valid_weights)
    cleaned_str = ", ".join([f"{w:.2f}" for w in valid_weights])
    return round(total_sum, 2), len(valid_weights), cleaned_str


def sync_mod_breakup():
    """Callback to auto-sum and auto-count for Existing Stock updates"""
    key_suf = st.session_state.form_key
    raw = st.session_state.get(f"bk_mod_{key_suf}", "")
    
    # Only override the numbers if there is actually breakup text entered
    if raw.strip():
        calc_w, calc_q, _ = parse_breakup_weights(raw)
        st.session_state[f"q_mod_{key_suf}"] = int(calc_q)
        st.session_state[f"w_mod_{key_suf}"] = float(calc_w)


def sync_new_breakup():
    """Callback to auto-sum and auto-count for New Stock additions"""
    key_suf = st.session_state.form_key
    raw = st.session_state.get(f"bk_new_{key_suf}", "")
    
    # Only override the numbers if there is actually breakup text entered
    if raw.strip():
        calc_w, calc_q, _ = parse_breakup_weights(raw)
        st.session_state[f"q_new_{key_suf}"] = int(calc_q)
        st.session_state[f"w_new_{key_suf}"] = float(calc_w)


def update_master_breakup(curr_breakup_str, txn_breakup_str, action_type):
    _, _, cleaned_curr = parse_breakup_weights(curr_breakup_str)
    curr_list = [float(x.strip()) for x in cleaned_curr.split(",") if x.strip()] if cleaned_curr else []
    
    _, _, cleaned_txn = parse_breakup_weights(txn_breakup_str)
    txn_list = [float(x.strip()) for x in cleaned_txn.split(",") if x.strip()] if cleaned_txn else []
    
    missing_weights = []
    
    if action_type == "Purchased (+)":
        updated_list = curr_list + txn_list
    else:  # "Used (-)"
        updated_list = list(curr_list)
        for item in txn_list:
            match_idx = None
            for idx, val in enumerate(updated_list):
                if abs(val - item) < 0.01:
                    match_idx = idx
                    break
            if match_idx is not None:
                updated_list.pop(match_idx)
            else:
                missing_weights.append(item)
                
    updated_str = ", ".join([f"{w:.2f}" for w in updated_list])
    return updated_str, missing_weights


# ------------------------------------------------------
# Load Data via Apps Script
# ------------------------------------------------------
@st.cache_data(ttl=5)
def fetch_all_data():
    try:
        response = requests.get(f"{APPS_SCRIPT_URL}?action=read_all", allow_redirects=True, timeout=30)
        
        if "text/html" in response.headers.get("Content-Type", ""):
            st.error("⚠️ Google returned HTML instead of JSON. Ensure Web App access is set to 'Anyone'.")
            return pd.DataFrame(columns=COLUMNS_MASTER), pd.DataFrame(columns=COLUMNS_HISTORY)

        data = response.json()
        master_df = pd.DataFrame(data.get("master", []))
        history_df = pd.DataFrame(data.get("history", []))
        
        for col in COLUMNS_MASTER:
            if col not in master_df.columns:
                master_df[col] = 0 if col in ["Quantity", "Weight"] else ""
                
        for col in COLUMNS_HISTORY:
            if col not in history_df.columns:
                history_df[col] = 0 if col in ["Quantity", "Weight"] else ""

        return master_df[COLUMNS_MASTER], history_df[COLUMNS_HISTORY]

    except Exception as e:
        st.error(f"Error connecting to Apps Script API: {e}")
        return pd.DataFrame(columns=COLUMNS_MASTER), pd.DataFrame(columns=COLUMNS_HISTORY)


# ------------------------------------------------------
# Submit Record via Apps Script
# ------------------------------------------------------
def send_update_to_sheet(payload):
    try:
        res = requests.post(APPS_SCRIPT_URL, json=payload, allow_redirects=True, timeout=15)
        
        if "text/html" in res.headers.get("Content-Type", ""):
            st.error("⚠️ Failed to update: Received HTML response. Check Web App URL permissions.")
            return

        res_data = res.json()
        
        if res_data.get("status") == "success":
            st.toast("✅ Updated successfully!")
            st.cache_data.clear()
            st.session_state.form_key += 1
            st.rerun()
        else:
            st.error(f"❌ Apps Script Error: {res_data.get('message', 'Unknown Error')}")

    except Exception as e:
        st.error(f"Failed to send update: {e}")


# ------------------------------------------------------
# Main Application Flow
# ------------------------------------------------------
rill_df, history_df = fetch_all_data()

st.markdown("---")
st.subheader("📜 Paper Rill Stock Ledger & Audit Log")

with st.expander("📐 Quick CM to Inches Converter"):
    cm_input = st.number_input(
        "Enter Size in CM", min_value=0.0, step=0.1, format="%.2f", key="standalone_cm_converter"
    )
    if cm_input > 0:
        inch_result = round(cm_input / 2.54, 2)
        st.success(f"**{cm_input:.2f} cm** = **{inch_result:.2f} Inches**")

if "form_key" not in st.session_state:
    st.session_state.form_key = 0
key_suffix_rill = st.session_state.form_key

tab_entry, tab_history = st.tabs(["⚡ Record Entry", "📜 History Log"])

# ------------------------------------------------------
# Tab 1: Record Entry
# ------------------------------------------------------
with tab_entry:
    st.markdown("##### 🔍 Select Product Specifications (Auto-Fills Details or Add New)")

    avail_sizes = sorted(list(set(rill_df["Size"].astype(str).str.strip().unique()))) if not rill_df.empty else []
    avail_gsms = sorted(list(set(rill_df["GSM"].astype(str).str.strip().unique()))) if not rill_df.empty else []
    avail_bfs = sorted(list(set(rill_df["BF"].astype(str).str.strip().unique()))) if not rill_df.empty else []

    col_s1, col_s2, col_s3 = st.columns(3)

    with col_s1:
        sel_sz = st.selectbox("Size *", options=["Select Size...", "➕ Add New..."] + avail_sizes, key=f"sheet_sz_{key_suffix_rill}")
        if sel_sz == "➕ Add New...":
            final_size = st.text_input("Type New Size *", key=f"new_sz_{key_suffix_rill}")
        else:
            final_size = sel_sz if sel_sz != "Select Size..." else ""

    with col_s2:
        sel_gsm = st.selectbox("GSM *", options=["Select GSM...", "➕ Add New..."] + avail_gsms, key=f"sheet_gsm_{key_suffix_rill}")
        if sel_gsm == "➕ Add New...":
            final_gsm = st.text_input("Type New GSM *", key=f"new_gsm_{key_suffix_rill}")
        else:
            final_gsm = sel_gsm if sel_gsm != "Select GSM..." else ""

    with col_s3:
        sel_bf = st.selectbox("BF *", options=["Select BF...", "➕ Add New..."] + avail_bfs, key=f"sheet_bf_{key_suffix_rill}")
        if sel_bf == "➕ Add New...":
            final_bf = st.text_input("Type New BF *", key=f"new_bf_{key_suffix_rill}")
        else:
            final_bf = sel_bf if sel_bf != "Select BF..." else ""

    has_unselected = not (final_size and final_gsm and final_bf)

    if has_unselected:
        st.info("👆 Please select or type all details to proceed.")
    else:
        match_df = rill_df[
            (rill_df["Size"].astype(str).str.strip() == final_size.strip()) &
            (rill_df["GSM"].astype(str).str.strip() == final_gsm.strip()) &
            (rill_df["BF"].astype(str).str.strip() == final_bf.strip())
        ]

        # ==========================================
        # MODE A: UPDATE EXISTING STOCK
        # ==========================================
        if not match_df.empty:
            curr_qty = int(pd.to_numeric(match_df["Quantity"]).sum())
            curr_weight = float(pd.to_numeric(match_df["Weight"]).sum())
            curr_breakup = str(match_df.iloc[0]["Breakup_Weight"])
            display_breakup = curr_breakup if curr_breakup.strip() else 'None'

            st.success(
                f"📌 **Selected Spec:** {final_size} Size | {final_gsm} GSM | {final_bf} BF  \n"
                f"⚡ **Current Stock:** {curr_qty} Rolls | **Weight:** {curr_weight:.2f} kg  \n"
                f"📦 **Available Breakup Weights:** {display_breakup}"
            )

            action_type = st.radio("Transaction Type", ["Purchased (+)", "Used (-)"], horizontal=True)

            col_m1, col_m2 = st.columns([1.5, 4.5])
            with col_m1:
                txn_date = st.date_input("Date", value=date.today(), key=f"dt_mod_{key_suffix_rill}")
            with col_m2:
                raw_breakup = st.text_input(
                    "Breakup Weight Entry (kg)", 
                    placeholder="e.g. 25.5, 30.0, 28.2", 
                    help="Enter weights separated by commas.",
                    key=f"bk_mod_{key_suffix_rill}",
                    on_change=sync_mod_breakup
                )

            _, _, clean_breakup_str = parse_breakup_weights(raw_breakup)
            new_master_breakup, missing_weights = update_master_breakup(curr_breakup, raw_breakup, action_type)

            # Initialize states so the callbacks can safely overwrite them
            if f"q_mod_{key_suffix_rill}" not in st.session_state:
                st.session_state[f"q_mod_{key_suffix_rill}"] = 0
            if f"w_mod_{key_suffix_rill}" not in st.session_state:
                st.session_state[f"w_mod_{key_suffix_rill}"] = 0.0

            col_m4, col_m5, col_m6 = st.columns([1.5, 1.5, 3])
            with col_m4:
                qty_change = st.number_input("Qty (Rills) *", min_value=0, step=1, key=f"q_mod_{key_suffix_rill}")
            with col_m5:
                weight_change = st.number_input("Total Weight (kg) *", min_value=0.0, step=0.1, format="%.2f", key=f"w_mod_{key_suffix_rill}")
            with col_m6:
                new_remark = st.text_input("Remark", value="", key=f"r_mod_{key_suffix_rill}")

            final_qty = curr_qty + qty_change if action_type == "Purchased (+)" else curr_qty - qty_change
            final_weight = curr_weight + weight_change if action_type == "Purchased (+)" else curr_weight - weight_change

            if st.button("Submit Record", type="primary", key="btn_update_rill"):
                if action_type == "Used (-)" and qty_change > curr_qty:
                    st.warning(f"Cannot subtract {qty_change} rills! Available stock is only {curr_qty} rills.")
                elif action_type == "Used (-)" and weight_change > curr_weight:
                    st.warning(f"Cannot subtract {weight_change:.2f} kg! Available weight is only {curr_weight:.2f} kg.")
                elif qty_change == 0 and weight_change == 0:
                    st.warning("Please enter weight breakups or a non-zero quantity/weight.")
                else:
                    if action_type == "Used (-)" and missing_weights:
                        missing_str = ", ".join([f"{w:.2f}" for w in missing_weights])
                        st.info(f"ℹ️ Note: Weight(s) [{missing_str}] were not originally in the stock breakup list.")

                    payload = {
                        "action": "update_stock",
                        "date": txn_date.strftime("%d/%m/%Y"),
                        "type": "Purchased" if action_type == "Purchased (+)" else "Used",
                        "size": final_size.strip(),
                        "gsm": final_gsm.strip(),
                        "bf": final_bf.strip(),
                        "qty_change": int(qty_change),
                        "weight_change": float(weight_change),
                        "new_qty": int(final_qty),
                        "new_weight": float(final_weight),
                        "breakup_weight": clean_breakup_str,
                        "new_breakup_weight": new_master_breakup,
                        "remark": new_remark.strip()
                    }
                    send_update_to_sheet(payload)

        # ==========================================
        # MODE B: ADD NEW ITEM
        # ==========================================
        else:
            st.warning("💡 **New Combination Detected:** Create this new specification below.")
            st.markdown("##### 📝 Initial Stock Entry for New Specification")

            col_n1, col_n2 = st.columns([1.5, 4.5])
            with col_n1:
                txn_date = st.date_input("Date", value=date.today(), key=f"dt_new_{key_suffix_rill}")
            with col_n2:
                raw_breakup_new = st.text_input(
                    "Breakup Weight Entry (kg)", 
                    placeholder="e.g. 25.5, 30.0, 28.2", 
                    help="Optional: Enter initial weights separated by commas.",
                    key=f"bk_new_{key_suffix_rill}",
                    on_change=sync_new_breakup
                )

            _, _, clean_breakup_new = parse_breakup_weights(raw_breakup_new)

            # Initialize states so the callbacks can safely overwrite them
            if f"q_new_{key_suffix_rill}" not in st.session_state:
                st.session_state[f"q_new_{key_suffix_rill}"] = 0
            if f"w_new_{key_suffix_rill}" not in st.session_state:
                st.session_state[f"w_new_{key_suffix_rill}"] = 0.0

            col_n3, col_n4, col_n5 = st.columns([1.5, 1.5, 3])
            with col_n3:
                new_initial_qty = st.number_input("Initial Quantity *", min_value=0, step=1, key=f"q_new_{key_suffix_rill}")
            with col_n4:
                new_weight = st.number_input("Initial Weight (kg) *", min_value=0.0, step=0.1, format="%.2f", key=f"w_new_{key_suffix_rill}")
            with col_n5:
                new_remark_text = st.text_input("Remark", key=f"r_new_{key_suffix_rill}")

            if st.button("Save New Stock Item", type="primary", key="btn_add_new_rill"):
                clean_size, clean_gsm, clean_bf = final_size.strip(), final_gsm.strip(), final_bf.strip()

                if not clean_size or not clean_gsm or not clean_bf:
                    st.warning("Please fill in Size, GSM, and BF.")
                else:
                    payload = {
                        "action": "add_new",
                        "date": txn_date.strftime("%d/%m/%Y"),
                        "type": "Purchased",
                        "size": clean_size,
                        "gsm": clean_gsm,
                        "bf": clean_bf,
                        "qty": int(new_initial_qty),
                        "weight": float(new_weight),
                        "qty_change": int(new_initial_qty),
                        "weight_change": float(new_weight),
                        "new_qty": int(new_initial_qty),
                        "new_weight": float(new_weight),
                        "breakup_weight": clean_breakup_new,
                        "new_breakup_weight": clean_breakup_new,
                        "remark": f"Initial Stock - {new_remark_text.strip()}".strip(" -")
                    }
                    send_update_to_sheet(payload)

    st.markdown("### 📋 Current Stock Summary")
    st.dataframe(rill_df, use_container_width=True, hide_index=True)


# ------------------------------------------------------
# Tab 2: Record History Log View
# ------------------------------------------------------
with tab_history:
    st.markdown("### 📜 Detailed Record History Log")

    if history_df.empty:
        st.info("No record history available yet.")
    else:
        filtered_df = history_df.copy()

        # Data Cleaning
        filtered_df["Date"] = filtered_df["Date"].astype(str).str.replace("'", "").str.strip()
        filtered_df["Type"] = filtered_df["Type"].astype(str).str.strip()
        filtered_df["Size"] = filtered_df["Size"].astype(str).str.strip()
        filtered_df["GSM"] = filtered_df["GSM"].astype(str).str.strip()
        filtered_df["BF"] = filtered_df["BF"].astype(str).str.strip()

        filtered_df["Quantity"] = pd.to_numeric(filtered_df["Quantity"], errors="coerce").fillna(0).astype(int)
        filtered_df["Weight"] = pd.to_numeric(filtered_df["Weight"], errors="coerce").fillna(0.0).astype(float)
        filtered_df["Breakup_Weight"] = filtered_df["Breakup_Weight"].astype(str).replace("nan", "").str.strip()
        filtered_df["Remark"] = filtered_df["Remark"].astype(str).replace("nan", "").str.strip()

        parsed_dates = pd.to_datetime(filtered_df["Date"], dayfirst=True, format="mixed", errors="coerce").dt.date
        valid_dates = parsed_dates.dropna()
        min_date = valid_dates.min() if not valid_dates.empty else date.today()
        max_date = valid_dates.max() if not valid_dates.empty else date.today()

        col_h1, col_h2, col_h3, col_h4 = st.columns(4)
        with col_h1:
            date_range = st.date_input("Filter Date Range", value=(min_date, max_date), key=f"rill_hist_filter_date_{key_suffix_rill}")
        with col_h2:
            filter_type = st.multiselect("Filter Action Type", options=["Purchased", "Used"], default=["Purchased", "Used"], key=f"rill_hist_filter_type_{key_suffix_rill}")
        with col_h3:
            filter_size = st.multiselect("Filter Size", options=sorted(filtered_df["Size"].unique()), key=f"rill_hist_filter_size_{key_suffix_rill}")
        with col_h4:
            search_text = st.text_input("Search Remarks/Breakups/Specs", key=f"rill_hist_search_{key_suffix_rill}")

        if date_range:
            if isinstance(date_range, (tuple, list)):
                if len(date_range) == 2:
                    start_d, end_d = date_range
                    filtered_df = filtered_df[(parsed_dates >= start_d) & (parsed_dates <= end_d)]
                elif len(date_range) == 1:
                    start_d = date_range[0]
                    filtered_df = filtered_df[parsed_dates >= start_d]
            elif isinstance(date_range, date):
                filtered_df = filtered_df[parsed_dates == date_range]

        if filter_type:
            filtered_df = filtered_df[filtered_df["Type"].isin(filter_type)]
        if filter_size:
            filtered_df = filtered_df[filtered_df["Size"].isin(filter_size)]
        if search_text:
            filtered_df = filtered_df[
                filtered_df["Remark"].str.contains(search_text, case=False) |
                filtered_df["Breakup_Weight"].str.contains(search_text, case=False) |
                filtered_df["Size"].str.contains(search_text, case=False)
            ]

        st.dataframe(
            filtered_df,
            column_config={
                "Quantity": st.column_config.NumberColumn("Quantity (Rolls)", format="%d"),
                "Weight": st.column_config.NumberColumn("Weight (kg)", format="%.2f"),
                "Breakup_Weight": st.column_config.TextColumn("Breakup Weight Entry")
            },
            use_container_width=True,
            hide_index=True
        )


####################################### Paper Sheet Stock ######################################
# Update with your deployed Web App URL
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwp3QoPvjhC_GJaFdj4z7tGB9MhIecBIf7IbgeLeg-hsD7qf8DGUzdBQaOx3A0xOp4R/exec"

COLUMNS_MASTER = ["Product", "Width", "Length", "GSM", "Grus", "Pcs", "Weight", "Remark"]
COLUMNS_HISTORY = ["Date", "Type", "Product", "Width", "Length", "GSM", "Grus", "Pcs", "Weight", "Remark"]

# ------------------------------------------------------
# Helper Functions & Callbacks
# ------------------------------------------------------
def calculate_weight(w, l, gsm, pcs):
    """Calculates weight based on: (((Width * Length * GSM) / 1550) / 1000) * Pcs"""
    try:
        w_float, l_float, gsm_float, pcs_int = float(w), float(l), float(gsm), int(pcs)
        weight = (((w_float * l_float * gsm_float) / 1550) / 1000) * pcs_int
        return round(weight, 3)
    except (ValueError, TypeError):
        return 0.000

def sync_grus(w, l, gsm):
    key_suf = st.session_state.form_key
    g_val = st.session_state.get(f"g_in_{key_suf}", 0.0)
    pcs = int(round(g_val * 144))
    st.session_state[f"pcs_in_{key_suf}"] = pcs
    st.session_state[f"wt_in_{key_suf}"] = calculate_weight(w, l, gsm, pcs)

def sync_pcs(w, l, gsm):
    key_suf = st.session_state.form_key
    pcs_val = st.session_state.get(f"pcs_in_{key_suf}", 0)
    st.session_state[f"g_in_{key_suf}"] = round(float(pcs_val) / 144.0, 2)
    st.session_state[f"wt_in_{key_suf}"] = calculate_weight(w, l, gsm, pcs_val)

# ------------------------------------------------------
# Data Fetch & Push Functions
# ------------------------------------------------------
@st.cache_data(ttl=5)
def fetch_all_data():
    try:
        response = requests.get(f"{APPS_SCRIPT_URL}?action=read_all", timeout=20)
        data = response.json()
        master_df = pd.DataFrame(data.get("master", []))
        history_df = pd.DataFrame(data.get("history", []))

        for col in COLUMNS_MASTER:
            if col not in master_df.columns:
                master_df[col] = 0.0 if col in ["Grus", "Pcs", "Weight"] else ""
        for col in COLUMNS_HISTORY:
            if col not in history_df.columns:
                history_df[col] = 0.0 if col in ["Grus", "Pcs", "Weight"] else ""

        return master_df[COLUMNS_MASTER], history_df[COLUMNS_HISTORY]
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame(columns=COLUMNS_MASTER), pd.DataFrame(columns=COLUMNS_HISTORY)

def send_update_to_sheet(payload):
    try:
        res = requests.post(APPS_SCRIPT_URL, json=payload, timeout=15)
        res_data = res.json()
        if res_data.get("status") == "success":
            st.toast("✅ Stock updated successfully!")
            st.cache_data.clear()
            st.session_state.form_key += 1
            st.rerun()
        else:
            err_msg = res_data.get("message") or "Unknown server error. Check Google Script logs."
            st.error(f"Backend Error: {err_msg}")
    except Exception as e:
        st.error(f"Transaction failed: {e}")

# ------------------------------------------------------
# Main Application Setup
# ------------------------------------------------------
sheet_df, history_df = fetch_all_data()

st.title("📄 Paper Sheet Stock Manager")

# Converter Expander
with st.expander("📐 Quick CM to Inches Converter"):
    col_cm1, col_cm2 = st.columns(2)
    with col_cm1:
        w_cm = st.number_input("Enter Width in CM", min_value=0.0, step=0.1, format="%.2f", key="standalone_w_cm_converter")
    with col_cm2:
        l_cm = st.number_input("Enter Length in CM", min_value=0.0, step=0.1, format="%.2f", key="standalone_l_cm_converter")
    if w_cm > 0 or l_cm > 0:
        w_inch = round(w_cm / 2.54, 2)
        l_inch = round(l_cm / 2.54, 2)
        st.success(f"**Converted Dimensions:** {w_inch:.2f}″ (W) × {l_inch:.2f}″ (L)\n\n*Original:* {w_cm:.2f} cm × {l_cm:.2f} cm")

if "form_key" not in st.session_state:
    st.session_state.form_key = 0
key_suffix = st.session_state.form_key

tab_entry, tab_history = st.tabs(["⚡ Record Transaction", "📜 Stock & History Log"])

# ------------------------------------------------------
# TAB 1: RECORD TRANSACTION
# ------------------------------------------------------
with tab_entry:
    st.markdown("##### 🔍 Product & Specifications Selection")

    avail_p = sorted(list(set(sheet_df["Product"].astype(str).str.strip().unique()))) if not sheet_df.empty else []

    if f"p_sel_{key_suffix}" in st.session_state and st.session_state[f"p_sel_{key_suffix}"] not in ["Select Product...", "➕ Add New..."]:
        selected_product = st.session_state[f"p_sel_{key_suffix}"]
        matched_specs = sheet_df[sheet_df["Product"].astype(str).str.strip() == selected_product.strip()]
        avail_w = sorted(list(set(matched_specs["Width"].astype(str).str.strip().unique())))
        avail_l = sorted(list(set(matched_specs["Length"].astype(str).str.strip().unique())))
        avail_g = sorted(list(set(matched_specs["GSM"].astype(str).str.strip().unique())))
    else:
        avail_w = sorted(list(set(sheet_df["Width"].astype(str).str.strip().unique()))) if not sheet_df.empty else []
        avail_l = sorted(list(set(sheet_df["Length"].astype(str).str.strip().unique()))) if not sheet_df.empty else []
        avail_g = sorted(list(set(sheet_df["GSM"].astype(str).str.strip().unique()))) if not sheet_df.empty else []

    col_s0, col_s1, col_s2, col_s3 = st.columns(4)

    with col_s0:
        sel_p = st.selectbox("Product", options=["Select Product...", "➕ Add New..."] + avail_p, key=f"p_sel_{key_suffix}")
        final_p = st.text_input("New Product Name", key=f"np_{key_suffix}") if sel_p == "➕ Add New..." else (sel_p if sel_p != "Select Product..." else "")

    with col_s1:
        sel_w = st.selectbox("Width", options=["Select Width...", "➕ Add New..."] + avail_w, key=f"w_{key_suffix}")
        final_w = st.text_input("New Width", key=f"nw_{key_suffix}") if sel_w == "➕ Add New..." else (sel_w if sel_w != "Select Width..." else "")

    with col_s2:
        sel_l = st.selectbox("Length", options=["Select Length...", "➕ Add New..."] + avail_l, key=f"l_{key_suffix}")
        final_l = st.text_input("New Length", key=f"nl_{key_suffix}") if sel_l == "➕ Add New..." else (sel_l if sel_l != "Select Length..." else "")

    with col_s3:
        sel_g = st.selectbox("GSM", options=["Select GSM...", "➕ Add New..."] + avail_g, key=f"g_{key_suffix}")
        final_g = st.text_input("New GSM", key=f"ng_{key_suffix}") if sel_g == "➕ Add New..." else (sel_g if sel_g != "Select GSM..." else "")

    if not (final_p and final_w and final_l and final_g):
        st.info("Fill out all 4 specifications above to make an entry.")
    else:
        match = sheet_df[
            (sheet_df["Product"].astype(str).str.strip() == final_p.strip()) &
            (sheet_df["Width"].astype(str).str.strip() == final_w.strip()) &
            (sheet_df["Length"].astype(str).str.strip() == final_l.strip()) &
            (sheet_df["GSM"].astype(str).str.strip() == final_g.strip())
        ]

        curr_grus = float(pd.to_numeric(match["Grus"]).sum()) if not match.empty else 0.0
        curr_pcs = int(pd.to_numeric(match["Pcs"]).sum()) if not match.empty else 0
        curr_weight = float(pd.to_numeric(match["Weight"]).sum()) if not match.empty else 0.0

        st.info(f"**Current Existing Stock:** {curr_grus:.2f} Grus | {curr_pcs} Pcs | {curr_weight:.3f} Kg")

        st.markdown("##### 📝 Entry Details")

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            action_type = st.radio("Transaction Type", ["Purchased", "Used"], horizontal=True, key=f"type_{key_suffix}")
        with col_t2:
            txn_date = st.date_input("Date", value=date.today(), key=f"dt_{key_suffix}")

        if f"g_in_{key_suffix}" not in st.session_state:
            st.session_state[f"g_in_{key_suffix}"] = 0.0
        if f"pcs_in_{key_suffix}" not in st.session_state:
            st.session_state[f"pcs_in_{key_suffix}"] = 0
        if f"wt_in_{key_suffix}" not in st.session_state:
            st.session_state[f"wt_in_{key_suffix}"] = 0.0

        col_e1, col_e2, col_e3, col_e4 = st.columns(4)
        
        with col_e1:
            grus_val = st.number_input("Grus", min_value=0.0, step=0.1, format="%.2f", key=f"g_in_{key_suffix}", on_change=sync_grus, args=(final_w, final_l, final_g))
        with col_e2:
            pcs_val = st.number_input("Pcs (Grus × 144)", min_value=0, step=1, key=f"pcs_in_{key_suffix}", on_change=sync_pcs, args=(final_w, final_l, final_g))
        
        # Unlocked Weight Input Box
        with col_e3:
            weight_val = st.number_input("Weight (Kg)", min_value=0.0, step=0.001, format="%.3f", key=f"wt_in_{key_suffix}")
        with col_e4:
            remark = st.text_input("Remark", key=f"rm_{key_suffix}")

        if st.button("Submit Entry", type="primary", key=f"btn_sub_{key_suffix}"):
            if grus_val == 0 and pcs_val == 0 and weight_val == 0:
                st.warning("Please specify a quantity (Grus, Pcs, or Weight) higher than 0.")
            elif action_type == "Used" and pcs_val > curr_pcs:
                st.error(f"Cannot subtract {pcs_val} Pcs. Available stock is only {curr_pcs} Pcs.")
            elif action_type == "Used" and weight_val > curr_weight:
                st.error(f"Cannot subtract {weight_val:.3f} Kg. Available stock is only {curr_weight:.3f} Kg.")
            else:
                new_grus = curr_grus + grus_val if action_type == "Purchased" else curr_grus - grus_val
                new_pcs = curr_pcs + pcs_val if action_type == "Purchased" else curr_pcs - pcs_val
                new_weight = curr_weight + weight_val if action_type == "Purchased" else curr_weight - weight_val

                payload = {
                    "action": "update_stock",
                    "date": txn_date.strftime("%d/%m/%Y"),
                    "type": action_type,
                    "product": final_p.strip(),
                    "width": final_w.strip(),
                    "length": final_l.strip(),
                    "gsm": final_g.strip(),
                    "grus_change": float(grus_val),
                    "pcs_change": int(pcs_val),
                    "weight_change": float(weight_val),
                    "new_grus": float(new_grus),
                    "new_pcs": int(new_pcs),
                    "new_weight": float(round(new_weight, 3)),
                    "remark": remark.strip()
                }
                send_update_to_sheet(payload)

# ------------------------------------------------------
# TAB 2: FIELD-WISE FILTERED TRANSACTION HISTORY LOG
# ------------------------------------------------------
with tab_history:
    st.markdown("### 📋 Current Master Stock (`sheet_stock`)")
    
    display_master_df = sheet_df.copy()
    display_master_df["Weight"] = pd.to_numeric(display_master_df["Weight"], errors="coerce").fillna(0.0)
    
    st.dataframe(
        display_master_df, 
        column_config={
            "Grus": st.column_config.NumberColumn("Grus", format="%.2f"),
            "Weight": st.column_config.NumberColumn("Weight (Kg)", format="%.3f"),
        },
        use_container_width=True, 
        hide_index=True
    )

    st.markdown("---")
    st.markdown("### 📜 Field-Wise Filtered History Log (`sheet_history`)")

    if history_df.empty:
        st.info("No transaction history available.")
    else:
        filtered_df = history_df.copy()

        for col in ["Product", "Width", "Length", "GSM", "Type", "Remark"]:
            if col in filtered_df.columns:
                filtered_df[col] = filtered_df[col].astype(str).str.strip()

        with st.expander("🔍 Column Filter Controls", expanded=True):
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            with f_col1:
                f_type = st.multiselect("Filter Type", options=sorted(filtered_df["Type"].unique()), key=f"f_type_{key_suffix}")
            with f_col2:
                f_prod = st.multiselect("Filter Product", options=sorted(filtered_df["Product"].unique()), key=f"f_prod_{key_suffix}")
            with f_col3:
                f_width = st.multiselect("Filter Width", options=sorted(filtered_df["Width"].unique()), key=f"f_w_{key_suffix}")
            with f_col4:
                f_length = st.multiselect("Filter Length", options=sorted(filtered_df["Length"].unique()), key=f"f_l_{key_suffix}")

            f_col5, f_col6, f_col7, f_col8 = st.columns(4)
            with f_col5:
                f_gsm = st.multiselect("Filter GSM", options=sorted(filtered_df["GSM"].unique()), key=f"f_gsm_{key_suffix}")
            with f_col6:
                search_remark = st.text_input("Filter Remark", key=f"f_rm_{key_suffix}")
            with f_col7:
                search_global = st.text_input("Global Search", key=f"f_glob_{key_suffix}")
            with f_col8:
                st.write("")

        if f_type:
            filtered_df = filtered_df[filtered_df["Type"].isin(f_type)]
        if f_prod:
            filtered_df = filtered_df[filtered_df["Product"].isin(f_prod)]
        if f_width:
            filtered_df = filtered_df[filtered_df["Width"].isin(f_width)]
        if f_length:
            filtered_df = filtered_df[filtered_df["Length"].isin(f_length)]
        if f_gsm:
            filtered_df = filtered_df[filtered_df["GSM"].isin(f_gsm)]
        if search_remark:
            filtered_df = filtered_df[filtered_df["Remark"].str.contains(search_remark, case=False, na=False)]
        if search_global:
            filtered_df = filtered_df[
                filtered_df.astype(str).apply(lambda row: row.str.contains(search_global, case=False).any(), axis=1)
            ]

        filtered_df["Weight"] = pd.to_numeric(filtered_df["Weight"], errors="coerce").fillna(0.0)

        st.dataframe(
            filtered_df,
            column_config={
                "Grus": st.column_config.NumberColumn("Grus", format="%.2f"),
                "Pcs": st.column_config.NumberColumn("Pcs", format="%d"),
                "Weight": st.column_config.NumberColumn("Weight (Kg)", format="%.3f"),
            },
            use_container_width=True,
            hide_index=True
        )
# ==========================================
################################## Purchase Order & Verification System #########################################
# ==========================================
PURCHASE_APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyjlawSLUajBvH6CgN4wdMU3Foo5O8daYD1LNdR-Wrc4zEYpxdSHgZDoTi96k4iP7TU/exec"

CREDITORS_LIST = [
    "Select Creditor...", "BALAJI ENTERPRISE", "DHANUKA UDYOG PRIVATE LIMITED", 
    "EVEREST PAPER MILLS (P) LTD.", "KRISHNA TRADERS", "PAPERS (India)", 
    "PS INDUSTRIES", "Reflection Papers Pvt. Ltd.", "RIPCO TRADERS PVT. LTD.", 
    "RM INDUSTRIAL EQUIPMENTS", "Samir Board World", "SHIV SHAKTI TRADERS", 
    "Shree Durga Trading Co.", "Star Trading Corporation", "STARK RIDGE PAPER PVT LTD", 
    "The Synthetic Glue & Chemical Industries", "VIJAY ENTERPRISE"
]

st.markdown("---")
st.subheader("📦 Purchase Order & Verification System")

tab1, tab2 = st.tabs(["📝 New Order Entry", "🔍 Verify Pending Deliveries"])

# Initialize session state tracking
if "item_count" not in st.session_state:
    st.session_state.item_count = 1
if "form_version" not in st.session_state:
    st.session_state.form_version = 0

# ------------------------------------------------------
# TAB 1: NEW MULTI-PRODUCT ORDER ENTRY
# ------------------------------------------------------
with tab1:
    def add_product_row():
        st.session_state.item_count += 1

    v = st.session_state.form_version  # Version suffix for widget keys

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            creditor = st.selectbox("Supplier / Creditor *", CREDITORS_LIST, key=f"creditor_{v}")
        with col2:
            order_date = st.date_input("Order Date", value=date.today(), key=f"date_{v}")

    st.markdown("#### Product Details")
    order_items = []
    grand_total = 0.0

    with st.container(border=True):
        for i in range(st.session_state.item_count):
            st.markdown(f"**Item {i+1}**")
            c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 2])
            
            with c1:
                p_desc = st.text_input("Product Description", key=f"prod_{v}_{i}")
            with c2:
                p_rate = st.number_input("Rate (₹)", min_value=0.0, step=1.0, format="%.2f", key=f"rate_{v}_{i}")
            with c3:
                p_qty = st.number_input("Quantity", min_value=0.0, step=1.0, key=f"qty_{v}_{i}")
            
            p_amt = p_rate * p_qty
            grand_total += p_amt
            
            with c4:
                st.metric(label="Amount", value=f"₹ {p_amt:,.2f}")
                
            if p_desc.strip():
                order_items.append({
                    "Product": p_desc.strip(),
                    "Rate": p_rate,
                    "Quantity": p_qty,
                    "Amount": p_amt
                })
                
        st.button("➕ Add Another Product", on_click=add_product_row)

    st.metric("Grand Total (₹)", f"₹ {grand_total:,.2f}")

    if st.button("Save New Order", type="primary"):
        if creditor == "Select Creditor...":
            st.warning("⚠️ Please select a Creditor.")
        elif not order_items:
            st.warning("⚠️ Please enter at least one product with a description.")
        else:
            payload = {
                "action": "insert",
                "Date": order_date.strftime("%Y-%m-%d"),
                "Creditor": creditor,
                "Status": "⏳ Pending Delivery",
                "CancellationReason": "",
                "Items": order_items
            }
            try:
                with st.spinner("Saving to Google Sheets..."):
                    res = requests.post(PURCHASE_APPS_SCRIPT_URL, json=payload, timeout=15)
                    if res.status_code == 200:
                        st.toast(f"✅ Saved {len(order_items)} item(s) for {creditor}!")
                        
                        # Reset fields safely by incrementing form version
                        st.session_state.form_version += 1
                        st.session_state.item_count = 1
                        st.rerun()
                    else:
                        st.error(f"⚠️ Server returned status code {res.status_code}")
            except Exception as e:
                st.error(f"❌ Connection error: {e}")

# ------------------------------------------------------
# TAB 2: VERIFICATION DASHBOARD (PENDING ORDERS)
# ------------------------------------------------------
with tab2:
    st.subheader("📋 Pending Deliveries & Verification")
    
    if st.button("🔄 Refresh Pending List"):
        st.rerun()

    # Fetch Pending Entries
    pending_list = []
    try:
        payload = {"action": "read_pending"}
        response = requests.post(PURCHASE_APPS_SCRIPT_URL, json=payload, timeout=15)
        
        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                data = response.json()
                if isinstance(data, list):
                    pending_list = data
                elif isinstance(data, dict) and "error" in data:
                    st.error(f"Apps Script Error: {data['error']}")
            else:
                st.error("⚠️ Access Denied: Apps Script returned HTML instead of JSON.")
        else:
            st.error(f"Failed with status code: {response.status_code}")
    except Exception as e:
        st.error(f"Failed to fetch pending list: {e}")

    if not pending_list:
        st.info("🎉 No pending orders found in 'purchase_order_entry'!")
    else:
        st.markdown(f"Found **{len(pending_list)}** item(s) awaiting delivery verification.")
        
        for idx, item in enumerate(pending_list):
            with st.container(border=True):
                st.markdown(f"##### 📅 Date: `{item.get('date')}` | Creditor: **{item.get('creditor')}**")
                
                c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 2])
                c1.write(f"**Product:** {item.get('product')}")
                c2.write(f"**Rate:** ₹{item.get('rate')}")
                c3.write(f"**Qty:** {item.get('quantity')}")
                c4.write(f"**Total:** ₹{item.get('amount')}")

                st.markdown("---")
                
                act_col1, act_col2 = st.columns([2, 4])
                
                with act_col1:
                    action_choice = st.radio(
                        "Verification Action:",
                        ["Keep Pending", "✅ Verify Order", "❌ Cancel Order"],
                        key=f"act_{idx}"
                    )

                with act_col2:
                    reason_text = ""
                    if action_choice == "❌ Cancel Order":
                        reason_text = st.text_input(
                            "Cancellation Reason *", 
                            placeholder="Enter reason (e.g., Damaged goods, Rate mismatch)", 
                            key=f"reason_{idx}"
                        )

                    if action_choice != "Keep Pending":
                        btn_label = "Confirm & Cancel" if action_choice == "❌ Cancel Order" else "Confirm & Verify"
                        
                        if st.button(btn_label, key=f"btn_{idx}", type="primary"):
                            if action_choice == "❌ Cancel Order" and not reason_text.strip():
                                st.warning("⚠️ Please provide a cancellation reason before submitting.")
                            else:
                                new_status = "✅ Verified" if action_choice == "✅ Verify Order" else "❌ Cancelled"
                                
                                update_payload = {
                                    "action": "update_status",
                                    "rowIndex": item.get("rowIndex"),
                                    "status": new_status,
                                    "cancellationReason": reason_text.strip()
                                }

                                try:
                                    with st.spinner("Updating status..."):
                                        res = requests.post(PURCHASE_APPS_SCRIPT_URL, json=update_payload, timeout=15)
                                        if res.status_code == 200:
                                            st.toast(f"Status updated to {new_status}!")
                                            st.rerun()
                                        else:
                                            st.error("Failed to update status in Google Sheet.")
                                except Exception as e:
                                    st.error(f"Error updating record: {e}")
