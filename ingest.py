import os
import requests
import dlt

# 1. Environment Routing (dev vs prod)
ENV = os.getenv("PIPELINE_ENV", "dev")
print(f"Executing ingestion for environment: {ENV.upper()}")

# Set S3 destination bucket
os.environ["DESTINATION__FILESYSTEM__BUCKET_URL"] = "s3://weather-datalake-dev"

def fetch_weather_data():
    """
    Fetches past 7 days of actuals + next 7 days of forecasted weather metrics
    from Open-Meteo for Manila.
    """
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=14.60&longitude=120.98"
        "&past_days=7&forecast_days=7"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
        "&timezone=Asia%2FManila"
    )
    
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    daily = data.get("daily", {})
    dates = daily.get("time", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_sum", [])
    
    for i in range(len(dates)):
        yield {
            "date": dates[i],
            "max_temp": max_temps[i],
            "min_temp": min_temps[i],
            "precipitation": precip[i]
        }

# 2. Pipeline definition targeted at {ENV}_bronze
pipeline = dlt.pipeline(
    pipeline_name=f"open_meteo_ingest_{ENV}",
    destination="filesystem",
    dataset_name=f"{ENV}_bronze"
)

# 3. Run with 'merge' disposition using 'date' as primary key for upserts
load_info = pipeline.run(
    fetch_weather_data(),
    table_name="manila_daily",
    loader_file_format="parquet",
    write_disposition="merge",
    primary_key="date"
)

print(load_info)