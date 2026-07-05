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
    "Date", "Vehicle No.", "Invoice No.", "Driver", 
    "Owner", "Company & Location", "Invoice Received", "Remark"
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
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME2)

delivery_sheet = connect_delivery_sheet()

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

# ======================================================
# NEW: Helper Function to Calculate Next Invoice No.
# ======================================================
def get_next_invoice_number(df):
    if df.empty or "Invoice No." not in df.columns:
        return "1"
    
    # Get all non-empty values from the Invoice No. column
    valid_invoices = df["Invoice No."].dropna().astype(str).str.strip()
    valid_invoices = [v for v in valid_invoices if v != ""]
    
    if not valid_invoices:
        return "1"
        
    # Pick the absolute last entry in the sheet
    last_invoice = valid_invoices[-1]
    
    # Extract numbers from the trailing edge of the invoice string (e.g., "INV-1002" -> "1002")
    match = re.search(r'(\d+)$', last_invoice)
    if match:
        num_part = match.group(1)
        next_num = int(num_part) + 1
        # Preserve leading zeros if your sequence uses them (e.g., 001 -> 002)
        next_num_str = str(next_num).zfill(len(num_part))
        # Replace the old number with the incremented one
        return last_invoice[:match.start()] + next_num_str
    else:
        # Fallback if the last invoice text contains absolutely no numbers
        return "1"

# Calculate the sequential baseline number
suggested_next_invoice = get_next_invoice_number(delivery_df)

# ======================================================
# Runtime Session States & Initialization
# ======================================================
if "submit_success" not in st.session_state:
    st.session_state.submit_success = False

if "form_key" not in st.session_state:
    st.session_state.form_key = 0

if "current_driver" not in st.session_state:
    st.session_state.current_driver = ""
if "current_owner" not in st.session_state:
    st.session_state.current_owner = ""

# NEW: Invoice tracking state element
if "current_invoice" not in st.session_state:
    st.session_state.current_invoice = suggested_next_invoice

if st.session_state.submit_success:
    st.success("✅ Operation Executed Successfully")
    st.session_state.submit_success = False

# Callback function to directly mutate the text inputs state
def update_vehicle_details():
    sel = st.session_state[f"v_sel_{st.session_state.form_key}"]
    st.session_state.current_driver = VEHICLE_MASTER[sel]["driver"]
    st.session_state.current_owner = VEHICLE_MASTER[sel]["owner"]

# ======================================================
# UI Form: New Delivery Entry
# ======================================================
st.subheader("New Delivery Entry")

key_suffix = st.session_state.form_key

col1, col2 = st.columns(2)
with col1:
    vehicle_selection = st.selectbox(
        "Vehicle No. *", 
        options=list(VEHICLE_MASTER.keys()),
        key=f"v_sel_{key_suffix}",
        on_change=update_vehicle_details
    )
    
    if vehicle_selection == "Others":
        final_vehicle_no = st.text_input(
            "Enter Manual Vehicle No. *", 
            key=f"delivery_entry_vehicle_manual_{key_suffix}"
        )
    else:
        final_vehicle_no = vehicle_selection

with col2:
    # MODIFIED: Controlled component tied to session state for automatic sequence increments
    invoice_no = st.text_input(
        "Invoice Number *", 
        key="current_invoice"
    )

col3, col4 = st.columns(2)
with col3:
    driver_name = st.text_input(
        "Driver Name", 
        key="current_driver"
    )
with col4:
    owner_name = st.text_input(
        "Owner Name", 
        key="current_owner"
    )

company = st.selectbox(
    "Company & Location *", 
    options=COMPANY_OPTIONS,
    key=f"delivery_entry_company_{key_suffix}"
)

remark = st.text_area("Remark", key=f"delivery_entry_remark_{key_suffix}")
delivery_date = st.date_input("Delivery Date", value=date.today(), key=f"delivery_entry_date_input_{key_suffix}")

# -----------------------------
# Submission Process
# -----------------------------
if st.button("Submit Delivery", type="primary"):
    if vehicle_selection == "Select":
        st.warning("Please select a Vehicle Number.")
    elif final_vehicle_no.strip() == "":
        st.warning("Please enter the Manual Vehicle Number.")
    elif invoice_no.strip() == "":
        st.warning("Please enter Invoice Number.")
    elif company == "Select":
        st.warning("Please choose a valid Company & Location.")
    else:
        delivery_sheet.append_row([
            delivery_date.strftime("%d/%m/%Y"),   
            final_vehicle_no.strip().upper(),      
            invoice_no.strip(),                    
            driver_name.strip(),                   
            owner_name.strip(),                    
            company.strip(),                       
            "No",                                  
            remark.strip()                         
        ])

        # Purge data cache and reload dataframe instantly to capture the row we just added
        st.cache_data.clear()
        fresh_df = load_delivery_data()
        
        # Reset tracking entry text fields
        st.session_state.current_driver = ""
        st.session_state.current_owner = ""
        
        # NEW: Automatically compute and set the next sequence number for the user's view
        st.session_state.current_invoice = get_next_invoice_number(fresh_df)
        
        st.session_state.submit_success = True
        st.session_state.form_key += 1
        st.rerun()

# ======================================================
# UI Section: Pending Deliveries Management
# ======================================================
st.markdown("---")
st.subheader("📋 Pending Deliveries (Not Received)")

pending_df = delivery_df[delivery_df["Invoice Received"].str.strip().str.lower() == "no"]

if pending_df.empty:
    st.info("🎉 All deliveries have been successfully received!")
else:
    st.write("Check the box next to an invoice to mark it as **Received (Yes)**:")
    
    col_h1, col_h2, col_h3, col_h4 = st.columns([1.5, 1.5, 3, 1])
    with col_h1: st.markdown("**Invoice No.**")
    with col_h2: st.markdown("**Vehicle No.**")
    with col_h3: st.markdown("**Company & Location**")
    with col_h4: st.markdown("**Action**")
    st.markdown("---")

    for idx, row in pending_df.iterrows():
        gs_row = idx + 2
        
        col_inv, col_veh, col_comp, col_act = st.columns([1.5, 1.5, 3, 1])
        
        with col_inv:
            st.write(row["Invoice No."])
        with col_veh:
            st.write(row["Vehicle No."])
        with col_comp:
            st.write(row["Company & Location"])
        with col_act:
            if st.checkbox("Receive", key=f"recv_approval_act_{gs_row}"):
                delivery_sheet.update_cell(gs_row, 7, "Yes")
                
                # Dynamic update logic for the checkbox loop as well
                st.cache_data.clear()
                fresh_df = load_delivery_data()
                st.session_state.current_invoice = get_next_invoice_number(fresh_df)
                
                st.session_state.submit_success = True
                st.rerun()
