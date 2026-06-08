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


def load_data():
    records = sheet.get_all_records()

    if not records:
        return pd.DataFrame(columns=COLUMNS)

    df = pd.DataFrame(records)
    df.columns = df.columns.str.strip()

    for col in COLUMNS:
        if col not in df.columns:
            df[col] = None

    df = df[COLUMNS]

    df["Payment Date"] = pd.to_datetime(df["Payment Date"], errors="coerce")
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

financial_year_list = [
    "2024-2025",
    "2025-2026",
    "2026-2027",
    "2027-2028"
]

month_list = [
    "April", "May", "June", "July", "August", "September",
    "October", "November", "December", "January", "February", "March"
]

st.subheader("New Payment Entry")

col1, col2, col3, col4 = st.columns(4)

with col1:
    financial_year = st.selectbox("Financial Year", financial_year_list)

with col2:
    month = st.selectbox("Month", month_list)

with col3:
    Payee = st.selectbox("Select Payee", Payee_list)

with col4:
    payment_date = st.date_input("Payment Date", value=date.today())

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

tds_percent = 1
tds_amount = bill_amount * tds_percent / 100
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


if st.button("Submit Payment"):
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

        st.success("Payment saved successfully.")
        st.rerun()
    else:
        st.warning("Please enter bill amount greater than 0.")


st.divider()

st.subheader("Filter Payments")

# Make dropdown values from actual sheet data
available_years = sorted(df["Financial Year"].dropna().astype(str).str.strip().unique())
available_months = sorted(df["Month"].dropna().astype(str).str.strip().unique())
available_Payees = sorted(df["Payee"].dropna().astype(str).str.strip().unique())

col9, col10, col11 = st.columns(3)

with col9:
    selected_financial_years = st.multiselect(
        "Select Financial Year",
        available_years,
        default=available_years
    )

with col10:
    selected_months = st.multiselect(
        "Select Month",
        available_months,
        default=available_months
    )

with col11:
    selected_Payees = st.multiselect(
        "Select Payee(s)",
        available_Payees,
        default=available_Payees
    )

if not df.empty:
    filtered_df = df[
        (df["Financial Year"].astype(str).str.strip().isin(selected_financial_years)) &
        (df["Month"].astype(str).str.strip().isin(selected_months)) &
        (df["Payee"].astype(str).str.strip().isin(selected_Payees))
    ].copy()
else:
    filtered_df = pd.DataFrame(columns=COLUMNS)

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


st.subheader("Transaction Records")
st.dataframe(filtered_df, width="stretch")


def convert_to_excel(dataframe):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Payments")

    return output.getvalue()


excel_file = convert_to_excel(filtered_df)

st.download_button(
    label="Download Filtered Excel",
    data=excel_file,
    file_name="Payment_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
