import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
from datetime import date

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
st.subheader("Payment Entry and Dashboard")

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
st.subheader("New Payment Entry")

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

COLUMNS2 = [
    "Date",
    "Vehicle No.",
    "Invoice No.",
    "Driver",
    "Owner",
    "Company & Location",
    "Invoice Received",  # <-- Updated from "Received"
    "Remark"
]

# 1. Added ttl=3600 to prevent Google Auth Token expiration crashes
@st.cache_resource(ttl=3600)
def connect_delivery_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME2)

delivery_sheet = connect_delivery_sheet()

# 2. Added cache_data to prevent making API calls on every keystroke
@st.cache_data
def load_delivery_data():
    records = delivery_sheet.get_all_records()
    if not records:
        return pd.DataFrame(columns=COLUMNS2)

    df = pd.DataFrame(records)
    df.columns = df.columns.str.strip()

    for col in COLUMNS2:
        if col not in df.columns:
            df[col] = ""

    df = df[COLUMNS2]
    df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y", errors="coerce")

    text_cols = ["Vehicle No.", "Invoice No.", "Driver", "Owner", "Company & Location", "Invoice Received", "Remark"]
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()

    return df

delivery_df = load_delivery_data()

# Initialize Session State
if "submit_success" not in st.session_state:
    st.session_state.submit_success = False

if "form_key" not in st.session_state:
    st.session_state.form_key = 0

# 3. Display success message HERE so it persists after st.rerun()
if st.session_state.submit_success:
    st.success("✅ Delivery Record Submitted Successfully")
    # Reset it so the message doesn't persist on unrelated future interactions
    st.session_state.submit_success = False 

# -----------------------------
# New Delivery Entry
# -----------------------------
# -----------------------------
# New Delivery Entry
# -----------------------------
st.subheader("New Delivery Entry")

key_suffix = st.session_state.form_key

col1, col2 = st.columns(2)
with col1:
    # Changed from vehicle_ to delivery_vehicle_
    vehicle_no = st.text_input("Vehicle No. *", key=f"delivery_vehicle_{key_suffix}")
with col2:
    # Changed from invoice_ to delivery_invoice_
    invoice_no = st.text_input("Invoice Number *", key=f"delivery_invoice_{key_suffix}")

col3, col4 = st.columns(2)
with col3:
    # Changed from driver_ to delivery_driver_
    driver_name = st.text_input("Driver Name", key=f"delivery_driver_{key_suffix}")
with col4:
    # Changed from owner_ to delivery_owner_
    owner_name = st.text_input("Owner Name", key=f"delivery_owner_{key_suffix}")

# Changed from company_ to delivery_company_
company = st.text_input("Company & Location *", key=f"delivery_company_{key_suffix}")

# CRITICAL FIX: Changed from remark_ to delivery_remark_
remark = st.text_area("Remark", key=f"delivery_remark_{key_suffix}")

# Changed from delivery_date_ to delivery_date_input_
delivery_date = st.date_input("Delivery Date", value=date.today(), key=f"delivery_date_input_{key_suffix}")

# -----------------------------
# Submit Button
# -----------------------------
if st.button("Submit Delivery", type="primary"):
    if vehicle_no.strip() == "":
        st.warning("Please enter Vehicle Number.")
    elif invoice_no.strip() == "":
        st.warning("Please enter Invoice Number.")
    elif company.strip() == "":
        st.warning("Please enter Company & Location.")
    else:
        # Append data to Google Sheets
        delivery_sheet.append_row([
            delivery_date.strftime("%d/%m/%Y"),   # Date
            vehicle_no.strip(),                    # Vehicle No.
            invoice_no.strip(),                    # Invoice No.
            driver_name.strip(),                   # Driver
            owner_name.strip(),                    # Owner
            company.strip(),                       # Company & Location
            "No",                                  # Received
            remark.strip()                         # Remark
        ])

        # 4. Clear the data cache so the new row loads on rerun
        st.cache_data.clear()

        # Update states and trigger rerun
        st.session_state.submit_success = True
        st.session_state.form_key += 1
        st.rerun()

# -----------------------------
# Pending Deliveries Section
# -----------------------------
st.markdown("---")
st.subheader("📋 Pending Deliveries (Not Received)")

# Filter data to only show rows where Received is "No"
# Using string cleaning to prevent issues with trailing spaces or casing
pending_df = delivery_df[delivery_df["Invoice Received"].str.strip().str.lower() == "No"]

if pending_df.empty:
    st.info("🎉 All deliveries have been successfully received!")
else:
    st.write("Check the box next to an invoice to mark it as **Received (Yes)**:")
    
    # Create a clean tabular layout header
    col_h1, col_h2, col_h3, col_h4 = st.columns([1.5, 1.5, 3, 1])
    with col_h1: st.markdown("**Invoice No.**")
    with col_h2: st.markdown("**Vehicle No.**")
    with col_h3: st.markdown("**Company & Location**")
    with col_h4: st.markdown("**Action**")
    st.markdown("---")

    # Loop through each pending item
    for idx, row in pending_df.iterrows():
        # Map DataFrame index back to the exact Google Sheet row number 
        # (e.g., DF Index 0 + 2 = Google Sheet Row 2)
        gs_row = idx + 2
        
        col_inv, col_veh, col_comp, col_act = st.columns([1.5, 1.5, 3, 1])
        
        with col_inv:
            st.write(row["Invoice No."])
        with col_veh:
            st.write(row["Vehicle No."])
        with col_comp:
            st.write(row["Company & Location"])
        with col_act:
            # Dynamic unique key prevents widget duplicate errors
            if st.checkbox("Receive", key=f"recv_action_{gs_row}"):
                
                # Column 7 corresponds to the "Received" column in your sheet configuration
                delivery_sheet.update_cell(gs_row, 7, "Yes")
                
                # Clear cached data so the app pulls the fresh sheet structure on refresh
                st.cache_data.clear()
                
                # Set success state and force immediate visual update
                st.session_state.submit_success = True
                st.rerun()

