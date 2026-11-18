-- depends_on: {{ ref('dim_location') }}
{{ config(
    materialized='external',
    location="s3://weather-datalake-dev/{{ target.name }}_gold/fct_city_forecast_3h.parquet",
    format='parquet'
) }}

with forecast as (
    select *
    from {{ ref('stg_weather_forecast_3h') }}
),

latest_batch as (
    select max(ingested_at_utc) as max_ingested_at_utc
    from forecast
)

select
    f.city_key,
    l.city_name,
    l.country_code,
    f.forecast_dt,
    f.forecast_time_utc,
    f.forecast_time_utc + to_hours(l.utc_offset_hours) as forecast_time_local,
    f.temp_celsius,
    f.feels_like_celsius,
    f.temp_min_celsius,
    f.temp_max_celsius,
    f.pressure_hpa,
    f.humidity_pct,
    f.wind_speed_ms,
    round(f.wind_speed_ms * 3.6, 1) as wind_speed_kmh,
    f.clouds_pct,
    f.rain_prob_pct,
    f.rain_3h_mm,
    f.condition_main,
    f.condition_desc,
    f.icon_code,
    f.ingested_at_utc,
    f.forecast_time_utc >= (b.max_ingested_at_utc - interval '3 hours') as is_upcoming
from forecast f
inner join read_parquet("s3://weather-datalake-dev/{{ target.name }}_gold/dim_location.parquet") l
    on f.city_key = l.city_key
cross join latest_batch b
order by f.city_key, f.forecast_time_utc