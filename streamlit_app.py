import streamlit as st
import pandas as pd

st.title("Client Portal")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)

dict_d = [{'a':100,'b':18,'c':'March'}, {'a':150,'b':28,'c':'April'},{'a':200,'b':10,'c':'May'}]
df = pd.DataFrame.from_dict(dict_d)
st.bar_chart(df,x="c",y=["a", "b"])

conn = st.connection("postgresql", type="sql")

# Perform query.
df = conn.query('SELECT * FROM clients;', ttl="10m")

df_contracts = conn.query('SELECT A.*,b.name FROM client_contracts A JOIN clients B on A.client_uuid=B.uuid;', ttl="10m")
df_payments = conn.query('SELECT a.amount,a.currency,a.payment_date,a.bank_account_identifier,a.uuid,b.name FROM client_payments a JOIN clients b on a.client_uuid = b.uuid;', ttl="10m")
df_payments['usd_amount'] = df_payments.apply(lambda x: x['amount']/4000  if x['currency']=='COP' else x['amount']/20 if x['currency']=='MXN' else x['amount'], axis=1)
st.bar_chart(df_payments,x="payment_date",y=["usd_amount"])