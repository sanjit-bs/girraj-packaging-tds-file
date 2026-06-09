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
    "Payee"
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
    else:
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

    df["Financial Year"] = df["Financial Year"].astype(str).str.strip()
    df["Month"] = df["Month"].astype(str).str.strip()
    df["Payee"] = df["Payee"].astype(str).str.strip()

    return df


df = load_data()

st.title("GIRRAJ PACKAGING")
st.subheader("Payment Entry and Dashboard")

Payee_list = [
    "PILU MRIDHA",
    "TOTON SARKAR",
    "DEBABRATA BISWAS"
]

st.subheader("New Payment Entry")

with st.form("payment_form", clear_on_submit=True):

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        Payee = st.selectbox("Select Payee", Payee_list)

    with col2:
        payment_date = st.date_input(
            "Payment Date",
            value=date.today()
        )

    month = payment_date.strftime("%B")
    financial_year = get_financial_year(payment_date)

    with col3:
        st.text_input(
            "Month",
            value=month,
            disabled=True
        )

    with col4:
        st.text_input(
            "Financial Year",
            value=financial_year,
            disabled=True
        )

    col5, col6, col7, col8 = st.columns(4)

    with col5:
        cheque_no = st.text_input("Cheque No.")

    with col6:
        bill_amount = st.number_input(
            "Bill Amount",
            min_value=0.0,
            step=0.5,
            format="%.2f"
        )

    tds_amount = bill_amount * 0.01
    net_amount = bill_amount - tds_amount

    with col7:
        st.number_input(
            "TDS Amount 1%",
            value=float(tds_amount),
            disabled=True,
            format="%.2f"
        )

    with col8:
        st.number_input(
            "Net Amount",
            value=float(net_amount),
            disabled=True,
            format="%.2f"
        )

    submitted = st.form_submit_button("Submit Payment")

    if submitted:
        if bill_amount > 0:
            sheet.append_row([
                financial_year,
                month,
                payment_date.strftime("%d/%m/%Y"),
                cheque_no,
                float(bill_amount),
                float(tds_amount),
                float(net_amount),
                Payee
            ])

            st.success("✅ Record submitted successfully")
            st.toast("✅ Record submitted successfully")
        else:
            st.warning("Please enter bill amount greater than 0.")


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

available_Payees = ["All"] + sorted(
    df["Payee"].dropna().astype(str).str.strip().unique().tolist()
)

col9, col10, col11 = st.columns(3)

with col9:
    selected_year = st.selectbox("Financial Year", available_years)

with col10:
    selected_month = st.selectbox("Month", available_months)

with col11:
    selected_Payee = st.selectbox("Payee", available_Payees)

filtered_df = df.copy()

if selected_year != "All":
    filtered_df = filtered_df[
        filtered_df["Financial Year"] == selected_year
    ]

if selected_month != "All":
    filtered_df = filtered_df[
        filtered_df["Month"] == selected_month
    ]

if selected_Payee != "All":
    filtered_df = filtered_df[
        filtered_df["Payee"] == selected_Payee
    ]


# -----------------------------
# Summary Section
# -----------------------------
st.subheader("Summary")

total_bill_amount = filtered_df["Bill Amount"].sum()
total_tds = filtered_df["TDS"].sum()
total_net_amount = filtered_df["Net Amount"].sum()
total_transactions = len(filtered_df)

col12, col13, col14, col15 = st.columns(4)

with col12:
    st.metric("Total Bill Amount", f"₹{total_bill_amount:,.2f}")

with col13:
    st.metric("Total TDS", f"₹{total_tds:,.2f}")

with col14:
    st.metric("Total Net Amount", f"₹{total_net_amount:,.2f}")

with col15:
    st.metric("Total Transactions", total_transactions)


# -----------------------------
# Payee Wise Summary
# -----------------------------
st.subheader("Payee-wise Total")

if not filtered_df.empty:
    Payee_summary = (
        filtered_df.groupby("Payee", as_index=False)[
            ["Bill Amount", "TDS", "Net Amount"]
        ]
        .sum()
        .sort_values("Net Amount", ascending=False)
    )

    st.dataframe(Payee_summary, width="stretch")
else:
    st.info("No data found for selected filter.")


# -----------------------------
# Transaction Table
# -----------------------------
st.subheader("Transaction Records")

display_df = filtered_df.copy()

if not display_df.empty:
    display_df["Payment Date"] = display_df["Payment Date"].dt.strftime("%d/%m/%Y")

st.dataframe(display_df, width="stretch")


# -----------------------------
# Excel Download
# -----------------------------
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
