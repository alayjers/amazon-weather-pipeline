-- depends_on: {{ ref('dim_location') }}
{{ config(
    materialized='external',
    location="s3://weather-datalake-dev/{{ target.name }}_gold/fct_city_current_conditions.parquet",
    format='parquet'
) }}

with weather as (
    select
        *,
        date_trunc('hour', observed_at_utc) as observed_hour_utc
    from {{ ref('stg_current_weather') }}
),

air_hourly as (
    select
        *,
        date_trunc('hour', observed_at_utc) as observed_hour_utc
    from {{ ref('stg_air_pollution') }}
    qualify row_number() over (
        partition by city_key, date_trunc('hour', observed_at_utc)
        order by observed_at_utc desc
    ) = 1
),

joined as (
    select
        w.city_key,
        l.city_name,
        l.country_code,
        l.climate_zone,
        w.observed_dt,
        w.observed_at_utc,
        w.observed_at_utc + to_hours(l.utc_offset_hours) as observed_at_local,
        w.temp_celsius,
        w.feels_like_celsius,
        w.pressure_hpa,
        w.humidity_pct,
        w.visibility_m,
        w.wind_speed_ms,
        round(w.wind_speed_ms * 3.6, 1) as wind_speed_kmh,
        w.wind_deg,
        w.clouds_pct,
        w.rain_1h_mm,
        w.condition_main,
        w.condition_desc,
        w.icon_code,
        coalesce(a.aqi_score, 1) as aqi_score,
        coalesce(a.pm2_5_ugm3, 0.0) as pm2_5_ugm3,
        coalesce(a.pm10_ugm3, 0.0) as pm10_ugm3,
        coalesce(a.o3_ugm3, 0.0) as o3_ugm3,
        coalesce(a.no2_ugm3, 0.0) as no2_ugm3,
        (w.temp_celsius * 1.8) + 32.0 as temp_f,
        cast(w.humidity_pct as double) as rh,
        row_number() over (partition by w.city_key order by w.observed_at_utc desc) = 1 as is_latest_observation
    from weather w
    inner join read_parquet("s3://weather-datalake-dev/{{ target.name }}_gold/dim_location.parquet") l
        on w.city_key = l.city_key
    left join air_hourly a
        on w.city_key = a.city_key
        and w.observed_hour_utc = a.observed_hour_utc
),

heat_index_calc as (
    select
        *,
        case
            when temp_f < 80.0 then
                0.5 * (temp_f + 61.0 + ((temp_f - 68.0) * 1.2) + (rh * 0.094))
            else
                -42.379
                + (2.04901523 * temp_f)
                + (10.14333127 * rh)
                - (0.22475541 * temp_f * rh)
                - (0.00683783 * power(temp_f, 2))
                - (0.05481717 * power(rh, 2))
                + (0.00122874 * power(temp_f, 2) * rh)
                + (0.00085282 * temp_f * power(rh, 2))
                - (0.00000199 * power(temp_f, 2) * power(rh, 2))
        end as heat_index_f
    from joined
)

select
    city_key,
    city_name,
    country_code,
    climate_zone,
    observed_dt,
    observed_at_utc,
    observed_at_local,
    temp_celsius,
    feels_like_celsius,
    round((heat_index_f - 32.0) / 1.8, 1) as heat_index_celsius,
    case
        when round((heat_index_f - 32.0) / 1.8, 1) >= 52.0 then 'Extreme Danger'
        when round((heat_index_f - 32.0) / 1.8, 1) >= 42.0 then 'Danger'
        when round((heat_index_f - 32.0) / 1.8, 1) >= 33.0 then 'Extreme Caution'
        when round((heat_index_f - 32.0) / 1.8, 1) >= 27.0 then 'Caution'
        else 'Not Hazardous'
    end as heat_advisory_level,
    pressure_hpa,
    humidity_pct,
    visibility_m,
    wind_speed_ms,
    wind_speed_kmh,
    wind_deg,
    clouds_pct,
    rain_1h_mm,
    condition_main,
    condition_desc,
    icon_code,
    aqi_score,
    case aqi_score
        when 1 then 'Good'
        when 2 then 'Fair'
        when 3 then 'Moderate'
        when 4 then 'Poor'
        when 5 then 'Very Poor'
        else 'Unknown'
    end as aqi_label,
    pm2_5_ugm3,
    pm10_ugm3,
    o3_ugm3,
    no2_ugm3,
    is_latest_observation
from heat_index_calc