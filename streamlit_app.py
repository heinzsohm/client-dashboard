import streamlit as st
import pandas as pd
from numerize.numerize import numerize
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta

# Get today's date and quarter
today = datetime.today()
current_year = today.year
current_month = today.month
current_quarter = (today.month - 1) // 3 + 1

# Function to get the quarter of a date
def get_quarter(date):
    return (date.month - 1) // 3 + 1


def diff_month(d1, d2):
    return (d1.year - d2.year) * 12 + d1.month - d2.month

st.title("Client Portal")

conn = st.connection("postgresql", type="sql")

# Perform query.
df = conn.query('SELECT * FROM clients;', ttl="10m")

df_contracts = conn.query('SELECT A.*,b.name FROM client_contracts A JOIN clients B on A.client_uuid=B.uuid;', ttl="10m")
df_payments = conn.query("SELECT a.amount,a.currency,TO_CHAR(payment_date,'yyyy-mm')  as month_date,a.payment_date,a.bank_account_identifier,a.uuid,b.name FROM client_payments a JOIN clients b on a.client_uuid = b.uuid;", ttl="10m")
df_payments['usd_amount'] = df_payments.apply(lambda x: x['amount']/4000  if x['currency']=='COP' else x['amount']/20 if x['currency']=='MXN' else x['amount'], axis=1)
df_payments.payment_date = pd.to_datetime(df_payments.payment_date)
df_payments['same_quarter'] = df_payments['payment_date'].apply(lambda x: x.year == current_year and get_quarter(x) == current_quarter)
df_payments['same_month'] = df_payments['payment_date'].apply(lambda x: x.year == current_year and x.month == current_month)
clients = df['uuid'].nunique()
clients_with_contracts = df_contracts['client_uuid'].nunique()
clients_with_payments = df_payments['name'].nunique()
col1, col2, col3 = st.columns(3)
col1.metric(label="Total Clients", value=clients)
col2.metric(label="Clients with Contract", value=clients_with_contracts)
col3.metric(label="Clients with Payments", value=clients_with_payments)
st.bar_chart(df_payments,x="month_date",y=["usd_amount"],stack=True)
col1.metric(label="Total Payments", value=numerize(df_payments['usd_amount'].sum()))
sales_this_month = df_payments['usd_amount'].where(df_payments['same_month']).sum()
sales_this_q = df_payments['usd_amount'].where(df_payments['same_quarter']).sum()
col2.metric(label="This Quarter", value=numerize(sales_this_q))
col3.metric(label="This Month", value=numerize(sales_this_month))
client_list = st.multiselect("Selecciona Cliente",df['name'].unique())
filtered_df = df_payments[df_payments['name'].isin(client_list)]
st.dataframe(filtered_df, column_order=("payment_date","amount","currency","name","bank_account_identifier","usd_amount"),column_config = {"usd_amount":st.column_config.NumberColumn(
            "Amount (in USD)",
            format="$ %.2f",
        ),"amount":st.column_config.NumberColumn(
            "Amount",
            format="$ %.2f",
        ),"payment_date":st.column_config.DateColumn(
            "Payment Date",
            format="YYYY-MM-DD"
        )})
filtered_payments = filtered_df['usd_amount'].sum()
col4, col5, col6 = st.columns(3)
col4.metric("Total Payments",numerize(filtered_payments))
month_options = st.multiselect("Selecciona Fecha",df_payments['month_date'].unique(),['2024-11'])
datefiltered_df = df_payments[df_payments['month_date'].isin(month_options)]
st.dataframe(datefiltered_df, column_order=("payment_date","amount","currency","name","bank_account_identifier","usd_amount"),column_config = {"usd_amount":st.column_config.NumberColumn(
            "Amount (in USD)",
            format="$ %.2f",
        ),"amount":st.column_config.NumberColumn(
            "Amount",
            format="$ %.2f",
        ),"payment_date":st.column_config.DateColumn(
            "Payment Date",
            format="YYYY-MM-DD"
        )})
datefiltered_payments = datefiltered_df['usd_amount'].sum()
st.metric("Total Payments",numerize(datefiltered_payments))

st.markdown('''Payment Schedule''')
client_contracts = df_contracts[df_contracts['name'].isin(client_list)]
payment_schedule = []
for index, row in client_contracts.iterrows():
    start_date = row['contract_start_date']
    name = row['name']
    mrr = row['mrr']
    payment_cycle = int(row['payment_cycle'])
    months_since_today = diff_month(today,start_date)
    count = 0
    while count < months_since_today:
        next_date = start_date + relativedelta(months=count)
        mod = count % payment_cycle if payment_cycle > 1 else 0
        count += 1
        if mod == 0:
            payment_schedule.append({'payment_date':next_date,'payment_amount':mrr*payment_cycle})
    count = 0

expected_payments = 0
for i in payment_schedule:
    expected_payments += i['payment_amount']
col5.metric("Expected Payments",numerize(expected_payments))
col6.metric("Payment Difference",numerize(filtered_payments - expected_payments))
payment_schedule

min_values = df_payments.groupby('name')['payment_date'].min().reset_index()
# Convert 'payment_date' to datetime
min_values['payment_date'] = pd.to_datetime(min_values['payment_date'])

# Extract month and year for grouping
min_values['year_month'] = min_values['payment_date'].dt.to_period('M')

# Count occurrences per month
monthly_counts = min_values.groupby('year_month').size().reset_index(name='count')

# Prepare data for Streamlit
monthly_counts['year_month'] = monthly_counts['year_month'].astype(str)

# Streamlit app
st.title("Payment Counts Per Month")

# Bar chart
st.bar_chart(monthly_counts.set_index('year_month'))