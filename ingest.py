import dlt
import requests
import os

# Update with your exact S3 bucket name if different
os.environ["DESTINATION__FILESYSTEM__BUCKET_URL"] = "s3://weather-datalake-dev"

def fetch_weather_data():
    url = "https://archive-api.open-meteo.com/v1/archive?latitude=14.60&longitude=120.98&start_date=2024-01-01&end_date=2024-01-31&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=Asia%2FSingapore"
    response = requests.get(url)
    data = response.json()
    
    daily = data.get("daily", {})
    
    for i in range(len(daily.get("time", []))):
        yield {
            "date": daily["time"][i],
            "max_temp": daily["temperature_2m_max"][i],
            "min_temp": daily["temperature_2m_min"][i],
            "precipitation": daily["precipitation_sum"][i]
        }

pipeline = dlt.pipeline(
    pipeline_name='open_meteo_ingest',
    destination='filesystem',
    dataset_name='bronze'
)

load_info = pipeline.run(
    fetch_weather_data(), 
    table_name="manila_daily",
    loader_file_format="parquet"
)
print(load_info)