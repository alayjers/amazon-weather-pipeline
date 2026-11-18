{{ config(
    materialized='external',
    location="s3://weather-datalake-dev/{{ target.name }}_silver/stg_weather_forecast_3h.parquet",
    format='parquet'
) }}

with raw_forecast as (
    select *
    from read_parquet(
        "s3://weather-datalake-dev/{{ target.name }}_bronze/weather_forecast_3h/*.parquet",
        union_by_name=true
    )
)

select
    cast(city_key as varchar) as city_key,
    cast(forecast_dt as bigint) as forecast_dt,
    cast(forecast_time_utc as timestamp) as forecast_time_utc,
    round(cast(temp_celsius as double), 2) as temp_celsius,
    round(cast(feels_like_celsius as double), 2) as feels_like_celsius,
    round(cast(temp_min_celsius as double), 2) as temp_min_celsius,
    round(cast(temp_max_celsius as double), 2) as temp_max_celsius,
    cast(pressure_hpa as integer) as pressure_hpa,
    cast(humidity_pct as integer) as humidity_pct,
    cast(visibility_m as integer) as visibility_m,
    round(cast(wind_speed_ms as double), 2) as wind_speed_ms,
    cast(wind_deg as integer) as wind_deg,
    round(cast(coalesce(wind_gust_ms, 0.0) as double), 2) as wind_gust_ms,
    cast(clouds_pct as integer) as clouds_pct,
    round(cast(rain_prob_pct as double), 1) as rain_prob_pct,
    round(cast(coalesce(rain_3h_mm, 0.0) as double), 2) as rain_3h_mm,
    cast(weather_id as integer) as weather_id,
    cast(condition_main as varchar) as condition_main,
    cast(condition_desc as varchar) as condition_desc,
    cast(icon_code as varchar) as icon_code,
    cast(ingested_at as timestamp) as ingested_at_utc
from raw_forecast
qualify row_number() over (
    partition by city_key, forecast_dt
    order by cast(ingested_at as timestamp) desc
) = 1