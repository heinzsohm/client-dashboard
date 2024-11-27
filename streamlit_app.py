import streamlit as st
import pandas as pd
from numerize.numerize import numerize

st.title("Client Portal")

conn = st.connection("postgresql", type="sql")

# Perform query.
df = conn.query('SELECT * FROM clients;', ttl="10m")

df_contracts = conn.query('SELECT A.*,b.name FROM client_contracts A JOIN clients B on A.client_uuid=B.uuid;', ttl="10m")
df_payments = conn.query("SELECT a.amount,a.currency,TO_CHAR(payment_date,'yyyy-mm')  as payment_date,a.bank_account_identifier,a.uuid,b.name FROM client_payments a JOIN clients b on a.client_uuid = b.uuid;", ttl="10m")
df_payments['usd_amount'] = df_payments.apply(lambda x: x['amount']/4000  if x['currency']=='COP' else x['amount']/20 if x['currency']=='MXN' else x['amount'], axis=1)
clients = df['uuid'].nunique()
clients_with_contracts = df_contracts['client_uuid'].nunique()
clients_with_payments = df_payments['name'].nunique()
col1, col2, col3 = st.columns(3)
col1.metric(label="Total Clients", value=clients)
col2.metric(label="Clients with Contract", value=clients_with_contracts)
col3.metric(label="Clients with Payments", value=clients_with_payments)
st.line_chart(df_payments,x="payment_date",y=["usd_amount"])
st.metric(label="Total Payments", value=numerize(df_payments['usd_amount'].sum()))