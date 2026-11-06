@st.cache_data(ttl=3600)
def load_gold_data() -> pd.DataFrame:
    """Connects to DuckDB httpfs using Streamlit secrets to query S3 Gold layer."""
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    
    # Extract credentials from Streamlit secrets
    key_id = st.secrets["aws"]["aws_access_key_id"]
    secret_key = st.secrets["aws"]["aws_secret_access_key"]
    region = st.secrets["aws"]["aws_default_region"]
    
    # Configure explicit S3 secret in DuckDB
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