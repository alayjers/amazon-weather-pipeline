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
    
    # Read Historical (Silver)
    hist_df = con.execute("""
        SELECT time::TIMESTAMP as date, max_temp_celsius as temp, 'Historical' as category 
        FROM read_parquet('s3://weather-datalake-dev/silver/stg_manila_daily.parquet')
    """).df()
    
    # Read Forecast (Gold)
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