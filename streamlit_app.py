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

with st.form(f"payment_form_{key_suffix}", clear_on_submit=True):

    # -------------------------
    # Date Section
    # -------------------------
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

    # -------------------------
    # Bill Amount
    # -------------------------
    col_bill, col_tds, col_net = st.columns(3)

    with col_bill:
        bill_amount = st.number_input(
            "Bill Amount *",
            min_value=0.0,
            step=100.0,
            format="%.2f"
        )

    tds_amount = bill_amount * 0.01
    net_amount = bill_amount - tds_amount

    with col_tds:
        st.text_input(
            "TDS Amount (1%)",
            value=f"{tds_amount:.2f}",
            disabled=True
        )

    with col_net:
        st.text_input(
            "Net Amount",
            value=f"{net_amount:.2f}",
            disabled=True
        )

    # -------------------------
    # Other Details
    # -------------------------
    col1, col2, col3 = st.columns(3)

    with col1:
        payee = st.selectbox(
            "Select Payee *",
            [""] + payee_list
        )

    with col2:
        cheque_no = st.text_input("Cheque No. *")

    with col3:
        category = st.selectbox(
            "Category *",
            [""] + category_list
        )

    remark = st.text_area(
        "Remark",
        placeholder="Enter remark here..."
    )

    submitted = st.form_submit_button("Submit Payment")

    if submitted:

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
