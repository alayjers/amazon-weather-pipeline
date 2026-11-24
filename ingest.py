import os
import time
from datetime import datetime, timezone
import dlt
import requests

OPENWEATHER_API_KEY = os.environ["OPENWEATHER_API_KEY"]
BASE_URL = "https://api.openweathermap.org/data/2.5"

CITIES = [
    {
        "city_key": "manila",
        "city_name": "Manila",
        "country_code": "PH",
        "region": "Southeast Asia",
        "latitude": 14.5995,
        "longitude": 120.9842,
        "climate_zone": "Tropical Monsoon",
        "utc_offset_hours": 8,
    },
    {
        "city_key": "singapore",
        "city_name": "Singapore",
        "country_code": "SG",
        "region": "Southeast Asia",
        "latitude": 1.3521,
        "longitude": 103.8198,
        "climate_zone": "Tropical Rainforest",
        "utc_offset_hours": 8,
    },
    {
        "city_key": "tokyo",
        "city_name": "Tokyo",
        "country_code": "JP",
        "region": "East Asia",
        "latitude": 35.6762,
        "longitude": 139.6503,
        "climate_zone": "Humid Subtropical",
        "utc_offset_hours": 9,
    },
    {
        "city_key": "seoul",
        "city_name": "Seoul",
        "country_code": "KR",
        "region": "East Asia",
        "latitude": 37.5665,
        "longitude": 126.9780,
        "climate_zone": "Humid Continental",
        "utc_offset_hours": 9,
    },
    {
        "city_key": "taipei",
        "city_name": "Taipei",
        "country_code": "TW",
        "region": "East Asia",
        "latitude": 25.0330,
        "longitude": 121.5654,
        "climate_zone": "Humid Subtropical",
        "utc_offset_hours": 8,
    },
    {
        "city_key": "sydney",
        "city_name": "Sydney",
        "country_code": "AU",
        "region": "Oceania",
        "latitude": -33.8688,
        "longitude": 151.2093,
        "climate_zone": "Temperate Oceanic",
        "utc_offset_hours": 11,
    },
]


def _get_json(endpoint: str, lat: float, lon: float) -> dict:
    params = {
        "lat": lat,
        "lon": lon,
        "units": "metric",
        "appid": OPENWEATHER_API_KEY,
    }
    resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=15)
    resp.raise_for_status()
    time.sleep(0.25)
    return resp.json()


@dlt.resource(
    table_name="locations",
    write_disposition="replace",
    primary_key="city_key",
)
def locations_resource():
    ingested_at = datetime.now(timezone.utc).isoformat()
    for city in CITIES:
        yield {**city, "ingested_at": ingested_at}


@dlt.resource(
    table_name="current_weather",
    write_disposition="merge",
    primary_key=["city_key", "observed_dt"],
)
def current_weather_resource():
    ingested_at = datetime.now(timezone.utc).isoformat()
    for city in CITIES:
        data = _get_json("weather", city["latitude"], city["longitude"])
        weather_meta = data.get("weather", [{}])[0]
        main = data.get("main", {})
        wind = data.get("wind", {})
        sys_info = data.get("sys", {})

        yield {
            "city_key": city["city_key"],
            "observed_dt": int(data["dt"]),
            "temp_celsius": float(main["temp"]),
            "feels_like_celsius": float(main["feels_like"]),
            "temp_min_celsius": float(main["temp_min"]),
            "temp_max_celsius": float(main["temp_max"]),
            "pressure_hpa": int(main["pressure"]),
            "humidity_pct": int(main["humidity"]),
            "visibility_m": int(data.get("visibility", 10000)),
            "wind_speed_ms": float(wind.get("speed", 0.0)),
            "wind_deg": int(wind.get("deg", 0)),
            "wind_gust_ms": float(wind.get("gust", 0.0)),
            "clouds_pct": int(data.get("clouds", {}).get("all", 0)),
            "rain_1h_mm": float(data.get("rain", {}).get("1h", 0.0)),
            "weather_id": int(weather_meta.get("id", 0)),
            "condition_main": str(weather_meta.get("main", "Unknown")),
            "condition_desc": str(weather_meta.get("description", "unknown")),
            "icon_code": str(weather_meta.get("icon", "01d")),
            "sunrise_dt": int(sys_info.get("sunrise", 0)),
            "sunset_dt": int(sys_info.get("sunset", 0)),
            "ingested_at": ingested_at,
        }


@dlt.resource(
    table_name="weather_forecast_3h",
    write_disposition="merge",
    primary_key=["city_key", "forecast_dt"],
)
def weather_forecast_resource():
    ingested_at = datetime.now(timezone.utc).isoformat()
    for city in CITIES:
        data = _get_json("forecast", city["latitude"], city["longitude"])
        for slot in data.get("list", []):
            weather_meta = slot.get("weather", [{}])[0]
            main = slot.get("main", {})
            wind = slot.get("wind", {})

            yield {
                "city_key": city["city_key"],
                "forecast_dt": int(slot["dt"]),
                "forecast_time_utc": str(slot["dt_txt"]),
                "temp_celsius": float(main["temp"]),
                "feels_like_celsius": float(main["feels_like"]),
                "temp_min_celsius": float(main["temp_min"]),
                "temp_max_celsius": float(main["temp_max"]),
                "pressure_hpa": int(main["pressure"]),
                "humidity_pct": int(main["humidity"]),
                "visibility_m": int(slot.get("visibility", 10000)),
                "wind_speed_ms": float(wind.get("speed", 0.0)),
                "wind_deg": int(wind.get("deg", 0)),
                "wind_gust_ms": float(wind.get("gust", 0.0)),
                "clouds_pct": int(slot.get("clouds", {}).get("all", 0)),
                "rain_prob_pct": round(float(slot.get("pop", 0.0)) * 100.0, 1),
                "rain_3h_mm": float(slot.get("rain", {}).get("3h", 0.0)),
                "weather_id": int(weather_meta.get("id", 0)),
                "condition_main": str(weather_meta.get("main", "Unknown")),
                "condition_desc": str(weather_meta.get("description", "unknown")),
                "icon_code": str(weather_meta.get("icon", "01d")),
                "ingested_at": ingested_at,
            }


@dlt.resource(
    table_name="air_pollution",
    write_disposition="merge",
    primary_key=["city_key", "observed_dt"],
)
def air_pollution_resource():
    ingested_at = datetime.now(timezone.utc).isoformat()
    for city in CITIES:
        data = _get_json("air_pollution", city["latitude"], city["longitude"])
        entry = data.get("list", [{}])[0]
        comp = entry.get("components", {})

        yield {
            "city_key": city["city_key"],
            "observed_dt": int(entry["dt"]),
            "aqi_score": int(entry.get("main", {}).get("aqi", 1)),
            "co_ugm3": float(comp.get("co", 0.0)),
            "no_ugm3": float(comp.get("no", 0.0)),
            "no2_ugm3": float(comp.get("no2", 0.0)),
            "o3_ugm3": float(comp.get("o3", 0.0)),
            "so2_ugm3": float(comp.get("so2", 0.0)),
            "pm2_5_ugm3": float(comp.get("pm2_5", 0.0)),
            "pm10_ugm3": float(comp.get("pm10", 0.0)),
            "nh3_ugm3": float(comp.get("nh3", 0.0)),
            "ingested_at": ingested_at,
        }


@dlt.source
def openweather_apac_source():
    return [
        locations_resource(),
        current_weather_resource(),
        weather_forecast_resource(),
        air_pollution_resource(),
    ]


if __name__ == "__main__":
    env = os.getenv("PIPELINE_ENV", "dev")
    bucket_url = os.getenv("DESTINATION__FILESYSTEM__BUCKET_URL", "s3://weather-datalake-dev")

    pipeline = dlt.pipeline(
        pipeline_name=f"openweather_apac_{env}",
        destination=dlt.destinations.filesystem(bucket_url=bucket_url),
        dataset_name=f"{env}_bronze",
    )
    load_info = pipeline.run(openweather_apac_source(), loader_file_format="parquet")
    print(load_info)