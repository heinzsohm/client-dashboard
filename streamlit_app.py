import streamlit as st
import pandas as pd
from numerize.numerize import numerize
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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

df_clients_with_pending_payments = conn.query("SELECT c.name, b.client_uuid, CASE WHEN a.payment_date is null THEN 'PENDING' ELSE a.payment_date::TEXT END  FROM client_contracts b LEFT JOIN client_payments a on a.client_uuid = b.client_uuid and TO_CHAR(a.payment_date,'yyyy-mm')  = TO_CHAR(NOW(),'yyyy-mm') JOIN clients c on b.client_uuid = c.uuid WHERE b.payment_cycle = '1' AND b.status is null AND b.mrr > 0 ;", ttl="10m")

st.markdown('''Monthy Active Clients''')
st.write(df_clients_with_pending_payments)

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
    end_date = row['contract_end_date']
    name = row['name']
    mrr = row['mrr']
    payment_cycle = int(row['payment_cycle'])
    if end_date is not None:
        months_since_today = diff_month(end_date,start_date)
    else:
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
st.title("New Clients Per Month")

# Bar chart
st.bar_chart(monthly_counts.set_index('year_month'))

df_cohorts = conn.query('''WITH cohorts as (
    SELECT client_uuid, min(TO_CHAR(payment_date,'yyyy-mm')) as cohort FROM client_payments GROUP BY 1 
    )
    SELECT b.cohort,ROUND(SUM(CASE WHEN A.CURRENCY = 'USD' THEN a.amount WHEN a.currency = 'MXN' THEN a.amount/20  WHEN a.currency ='COP' THEN a.amount/4200 ELSE a.amount END ),2) as total_amount, count(distinct a.client_uuid) as num_clients
    FROM client_payments a 
    JOIN cohorts b on a.client_uuid = b.client_uuid
    GROUP BY 1 ''', ttl="10m")

df_cohorts['avg_amount'] = df_cohorts['total_amount'] / df_cohorts['num_clients']
df_cohorts
filtered_cont = df_contracts[df_contracts['name'].isin(client_list)]
filtered_cont

st.title("Payments by Sales Rep")
df_sales_by_manager = conn.query('''SELECT CONCAT(u.first_name,' ',U.LAST_NAME) as full_name, ROUND(SUM(case when a.currency = 'USD' then a.amount when a.currency = 'MXN' then a.amount/20 WHEN a.currency = 'COP' THEN a.amount/4200 ELSE A.AMOUNT END),2) as total_payments FROM client_payments a JOIN clients b on a.client_uuid = b.uuid JOIN users u on b.sales_manager_id = u.id
    GROUP BY 1''',ttl='10m')
df_sales_by_manager

st.title("MRR per Month (Contract)")
df_contracts_sales = conn.query('''WITH interest_dates as (
    SELECT * FROM (VALUES (1, '2024-12-01'), (2, '2024-11-01'), (3, '2024-10-01'), (4, '2024-09-01'),(5, '2024-08-01'),(6, '2024-07-01'), (7, '2024-06-01'), (8, '2024-05-01'), (9, '2024-04-01'), (10, '2024-03-01'), (11, '2024-02-01'), (12, '2024-01-01')) AS t (num,d_date)
    ) 
    SELECT d_date AS month_sales, sum(mrr) FROM client_contracts A  JOIN interest_dates B on A.contract_start_date::TEXT <= B.d_date AND (A.contract_end_date::text >= B.d_date or A.contract_end_date is null) GROUP BY 1 ORDER BY 1 DESC''',ttl='10m')

st.bar_chart(df_contracts_sales.set_index('month_sales'))

df_sales_per_quarter = conn.query('''SELECT extract(year from contract_start_date) as year ,extract(quarter from contract_start_date) as q , sum(mrr) as total_mrr, count(*) as total_accounts, sum(case when contract_end_date is null then mrr else 0 end) as total_active_mrr, sum(case when contract_end_date is null then 1 else 0 end) as active_accounts FROM client_contracts group by 1,2  order by 1,2''',ttl='10m')
df_sales_per_quarter

df_sales_per_quarter['year_q'] = df_sales_per_quarter['year'].astype(str) + ' Q' + df_sales_per_quarter['q'].astype(str)

# Create the figure with secondary y-axis
fig = make_subplots(specs=[[{"secondary_y": True}]])

# Add bars for total and active accounts
fig.add_trace(
    go.Bar(
        name="Total Accounts",
        x=df_sales_per_quarter['year_q'],
        y=df_sales_per_quarter['total_accounts'],
        offsetgroup=0,
    ),
    secondary_y=False,
)

fig.add_trace(
    go.Bar(
        name="Active Accounts",
        x=df_sales_per_quarter['year_q'],
        y=df_sales_per_quarter['active_accounts'],
        offsetgroup=1,
    ),
    secondary_y=False,
)

# Add lines for MRR
fig.add_trace(
    go.Scatter(
        name="Total MRR",
        x=df_sales_per_quarter['year_q'],
        y=df_sales_per_quarter['total_mrr'],
        line=dict(color='rgb(255, 127, 14)'),
    ),
    secondary_y=True,
)

fig.add_trace(
    go.Scatter(
        name="Active MRR",
        x=df_sales_per_quarter['year_q'],
        y=df_sales_per_quarter['total_active_mrr'],
        line=dict(color='rgb(44, 160, 44)'),
    ),
    secondary_y=True,
)

# Update layout
fig.update_layout(
    title="Accounts and NEW MRR Over Time",
    barmode='group',
    xaxis_title="Year Quarter",
    yaxis_title="Number of Accounts",
    yaxis2_title="MRR ($)",
    legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01
    ),
    hovermode='x unified'
)

# Display the chart in Streamlit
st.plotly_chart(fig, use_container_width=True)