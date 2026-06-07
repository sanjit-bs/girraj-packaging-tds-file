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

@st.cache_resource
def connect_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )

    client = gspread.authorize(creds)

    sheet = client.open_by_key(
        "1PCJ3BWAj6Wz1N-55XpuWltvfvYd7KD1q194D3N7MzIg"
    ).worksheet("Tds_file")

    return sheet


sheet = connect_sheet()


def load_data():
    records = sheet.get_all_records()

    if not records:
        return pd.DataFrame(columns=["Date", "Payer", "Amount"])

    df = pd.DataFrame(records)

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

    return df


df = load_data()

st.title("GIRRAJ PACKAGING")
st.subheader("Payment Entry and Dashboard")

payer_list = [
    "PILU MRIDHA",
    "TOTON SARKAR",
    "DEBABRATA BISWAS"
]

st.subheader("New Payment Entry")

col1, col2, col3 = st.columns(3)

with col1:
    payer = st.selectbox("Select Payer", payer_list)

with col2:
    amount = st.number_input(
        "Amount Paid",
        min_value=0.0,
        step=0.5,
        format="%.2f"
    )

with col3:
    payment_date = st.date_input("Payment Date", value=date.today())


if st.button("Submit Payment"):
    if amount > 0:
        sheet.append_row([
            payment_date.strftime("%Y-%m-%d"),
            payer,
            float(amount)
        ])

        st.success("Payment saved successfully.")
        st.cache_data.clear()
        st.rerun()
    else:
        st.warning("Please enter amount greater than 0.")


st.divider()

st.subheader("Filter Payments")

col4, col5, col6 = st.columns(3)

with col4:
    selected_payers = st.multiselect(
        "Select Payer(s)",
        payer_list,
        default=payer_list
    )

with col5:
    from_date = st.date_input("From Date", value=date.today().replace(day=1))

with col6:
    to_date = st.date_input("To Date", value=date.today())


if not df.empty:
    filtered_df = df[
        (df["Payer"].isin(selected_payers)) &
        (df["Date"].dt.date >= from_date) &
        (df["Date"].dt.date <= to_date)
    ]
else:
    filtered_df = pd.DataFrame(columns=["Date", "Payer", "Amount"])


st.subheader("Summary")

total_amount = filtered_df["Amount"].sum()
total_transactions = len(filtered_df)

col7, col8 = st.columns(2)

with col7:
    st.metric("Total Paid Amount", f"₹{total_amount:,.2f}")

with col8:
    st.metric("Total Transactions", total_transactions)


st.subheader("Payer-wise Total")

if not filtered_df.empty:
    payer_summary = (
        filtered_df.groupby("Payer", as_index=False)["Amount"]
        .sum()
        .sort_values("Amount", ascending=False)
    )

    st.dataframe(payer_summary, width=True)
else:
    st.info("No data found for selected filter.")


st.subheader("Transaction Records")
st.dataframe(filtered_df, width=True)


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
