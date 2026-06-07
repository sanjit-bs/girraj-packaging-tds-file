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
    "Month",
    "Payment Date",
    "Cheque No",
    "Bill Amount",
    "TDS",
    "Net Amount",
    "Payer"
]


@st.cache_resource
def connect_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )

    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)

    return sheet


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

    df["Payment Date"] = pd.to_datetime(
        df["Payment Date"],
        errors="coerce"
    )

    df["Bill Amount"] = pd.to_numeric(
        df["Bill Amount"],
        errors="coerce"
    ).fillna(0)

    df["TDS"] = pd.to_numeric(
        df["TDS"],
        errors="coerce"
    ).fillna(0)

    df["Net Amount"] = pd.to_numeric(
        df["Net Amount"],
        errors="coerce"
    ).fillna(0)

    return df


df = load_data()

st.title("GIRRAJ PACKAGING")
st.subheader("Payment Entry and Dashboard")

payer_list = [
    "PILU MRIDHA",
    "TOTON SARKAR",
    "DEBABRATA BISWAS"
]

# -----------------------------
# Entry Section
# -----------------------------
st.subheader("New Payment Entry")

col1, col2, col3, col4 = st.columns(4)

with col1:
    payer = st.selectbox("Select Payer", payer_list)

with col2:
    bill_amount = st.number_input(
        "Bill Amount",
        min_value=0.0,
        step=0.5,
        format="%.2f"
    )

with col3:
    cheque_no = st.text_input("Cheque No.")

with col4:
    payment_date = st.date_input(
        "Payment Date",
        value=date.today()
    )

col5, col6, col7 = st.columns(3)

with col5:
    month = st.text_input("Month")

tds_percent = 1
tds_amount = bill_amount * tds_percent / 100
net_amount = bill_amount - tds_amount

with col6:
    st.number_input(
        "TDS Amount 1%",
        value=float(tds_amount),
        disabled=True,
        format="%.2f"
    )

with col7:
    st.number_input(
        "Net Amount",
        value=float(net_amount),
        disabled=True,
        format="%.2f"
    )


if st.button("Submit Payment"):
    if bill_amount > 0:
        sheet.append_row([
            month,
            payment_date.strftime("%Y-%m-%d"),
            cheque_no,
            float(bill_amount),
            float(tds_amount),
            float(net_amount),
            payer
        ])

        st.success("Payment saved successfully.")
        st.rerun()
    else:
        st.warning("Please enter bill amount greater than 0.")


st.divider()

# -----------------------------
# Filter Section
# -----------------------------
st.subheader("Filter Payments")

col8, col9, col10 = st.columns(3)

with col8:
    selected_payers = st.multiselect(
        "Select Payer(s)",
        payer_list,
        default=payer_list
    )

with col9:
    from_date = st.date_input(
        "From Date",
        value=date.today().replace(day=1)
    )

with col10:
    to_date = st.date_input(
        "To Date",
        value=date.today()
    )


if not df.empty:
    from_date_ts = pd.Timestamp(from_date)
    to_date_ts = pd.Timestamp(to_date)

    filtered_df = df[
        (df["Payer"].isin(selected_payers)) &
        (df["Payment Date"] >= from_date_ts) &
        (df["Payment Date"] <= to_date_ts)
    ].copy()
else:
    filtered_df = pd.DataFrame(columns=COLUMNS)


# -----------------------------
# Summary Section
# -----------------------------
st.subheader("Summary")

total_bill_amount = filtered_df["Bill Amount"].sum()
total_tds = filtered_df["TDS"].sum()
total_net_amount = filtered_df["Net Amount"].sum()
total_transactions = len(filtered_df)

col11, col12, col13, col14 = st.columns(4)

with col11:
    st.metric("Total Bill Amount", f"₹{total_bill_amount:,.2f}")

with col12:
    st.metric("Total TDS", f"₹{total_tds:,.2f}")

with col13:
    st.metric("Total Net Amount", f"₹{total_net_amount:,.2f}")

with col14:
    st.metric("Total Transactions", total_transactions)


# -----------------------------
# Payer Wise Summary
# -----------------------------
st.subheader("Payer-wise Total")

if not filtered_df.empty:
    payer_summary = (
        filtered_df.groupby("Payer", as_index=False)[
            ["Bill Amount", "TDS", "Net Amount"]
        ]
        .sum()
        .sort_values("Net Amount", ascending=False)
    )

    st.dataframe(payer_summary, width="stretch")
else:
    st.info("No data found for selected filter.")


# -----------------------------
# Transaction Table
# -----------------------------
st.subheader("Transaction Records")
st.dataframe(filtered_df, width="stretch")


# -----------------------------
# Excel Download
# -----------------------------
def convert_to_excel(dataframe):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(
            writer,
            index=False,
            sheet_name="Payments"
        )

    return output.getvalue()


excel_file = convert_to_excel(filtered_df)

st.download_button(
    label="Download Filtered Excel",
    data=excel_file,
    file_name="Payment_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
