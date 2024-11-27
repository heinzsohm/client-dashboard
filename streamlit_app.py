import streamlit as st
import pandas as pd
from numerize.numerize import numerize
from datetime import datetime


# Get today's date and quarter
today = datetime.today()
current_year = today.year
current_month = today.month
current_quarter = (today.month - 1) // 3 + 1

# Function to get the quarter of a date
def get_quarter(date):
    return (date.month - 1) // 3 + 1

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
st.dataframe(filtered_df, column_order=("payment_date","amount","currency","name","bank_account_identifier","usd_amount"),column_config={"usd_amount":st.column_config.NumberColumn("Dollar values”, format=”$ %d")})