import streamlit as st
import duckdb
import plotly.graph_objects as go
import pandas as pd

# Page setup
st.set_page_config(
    page_title="Manila Weather Analytics Lakehouse",
    page_icon="🌤️",
    layout="wide"
)

st.title("🌤️ Manila Weather Summary Dashboard")
st.markdown("Gold Layer Analytics direct from `s3://weather-datalake-dev/gold/fct_monthly_weather_summary.parquet`")

@st.cache_data(ttl=3600)
def load_gold_data() -> pd.DataFrame:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    
    key_id = st.secrets["aws"]["aws_access_key_id"]
    secret_key = st.secrets["aws"]["aws_secret_access_key"]
    region = st.secrets["aws"]["aws_default_region"]
    
    con.execute(f"""
        CREATE SECRET (
            TYPE S3,
            KEY_ID '{key_id}',
            SECRET '{secret_key}',
            REGION '{region}'
        );
    """)
    
    query = """
        SELECT 
            CAST(month_start_date AS DATE) AS month_start_date,
            total_days_recorded,
            avg_max_temp_celsius,
            avg_min_temp_celsius,
            peak_temp_celsius,
            lowest_temp_celsius,
            total_precipitation_mm,
            rainy_days_count,
            avg_daily_precipitation_mm
        FROM read_parquet('s3://weather-datalake-dev/gold/fct_monthly_weather_summary.parquet')
        ORDER BY month_start_date ASC
    """
    df = con.execute(query).df()
    con.close()
    return df