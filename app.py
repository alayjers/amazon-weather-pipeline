import streamlit as st
import duckdb
import pandas as pd

st.set_page_config(page_title="Weather ML Engine", page_icon="🌤️", layout="wide")

st.title("🌤️ Manila Weather ML Engine")
st.caption("End-to-End Data Engineering & ML Pipeline")
st.divider()

@st.cache_data(ttl=3600)
def load_lakehouse_data():
    con = duckdb.connect(database=':memory:')
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL aws; LOAD aws;")
    con.execute("CREATE SECRET (TYPE S3, PROVIDER credential_chain);")
    
    # 1. Read Historical (Silver) using SELECT * to bypass column name mismatches
    hist_raw = con.execute("SELECT * FROM read_parquet('s3://weather-datalake-dev/silver/stg_manila_daily.parquet')").df()
    
    # Dynamically map the columns (just like in train_model.py)
    date_col = 'time' if 'time' in hist_raw.columns else 'date' if 'date' in hist_raw.columns else hist_raw.columns[0]
    temp_col = 'max_temp_celsius' if 'max_temp_celsius' in hist_raw.columns else 'temperature_2m_max'
    
    # Standardize names for the dashboard
    hist_df = pd.DataFrame({
        'date': pd.to_datetime(hist_raw[date_col]),
        'temp': hist_raw[temp_col],
        'category': 'Historical'
    })
    
    # 2. Read Forecast (Gold) - XGBoost script specifically set these exact names
    fct_df = con.execute("""
        SELECT forecast_date::TIMESTAMP as date, predicted_max_temp_celsius as temp, 'XGBoost Forecast' as category 
        FROM read_parquet('s3://weather-datalake-dev/gold/fct_ml_forecast.parquet')
    """).df()
    
    return hist_df, fct_df

with st.spinner("Querying S3 Lakehouse..."):
    hist_df, fct_df = load_lakehouse_data()
    
    # Combine and pivot for Streamlit charting
    combined_df = pd.concat([hist_df, fct_df], ignore_index=True)
    chart_data = combined_df.pivot(index='date', columns='category', values='temp')

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Latest Recorded Temp", f"{hist_df['temp'].iloc[-1]:.1f} °C")
with col2:
    st.metric("Peak 7-Day Forecast", f"{fct_df['temp'].max():.1f} °C")
with col3:
    st.metric("Pipeline Status", "🟢 Active (Airflow + dbt + XGBoost)")

st.subheader("Temperature Trend & Forecast")
st.line_chart(chart_data, color=["#f54242", "#4287f5"])