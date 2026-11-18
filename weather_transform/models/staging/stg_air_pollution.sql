{{ config(
    materialized='external',
    location="s3://weather-datalake-dev/{{ target.name }}_silver/stg_air_pollution.parquet",
    format='parquet'
) }}

with raw_air as (
    select *
    from read_parquet(
        "s3://weather-datalake-dev/{{ target.name }}_bronze/air_pollution/*.parquet",
        union_by_name=true
    )
)

select
    cast(city_key as varchar) as city_key,
    cast(observed_dt as bigint) as observed_dt,
    cast(to_timestamp(cast(observed_dt as double)) as timestamp) as observed_at_utc,
    cast(aqi_score as integer) as aqi_score,
    round(cast(co_ugm3 as double), 2) as co_ugm3,
    round(cast(no_ugm3 as double), 2) as no_ugm3,
    round(cast(no2_ugm3 as double), 2) as no2_ugm3,
    round(cast(o3_ugm3 as double), 2) as o3_ugm3,
    round(cast(so2_ugm3 as double), 2) as so2_ugm3,
    round(cast(pm2_5_ugm3 as double), 2) as pm2_5_ugm3,
    round(cast(pm10_ugm3 as double), 2) as pm10_ugm3,
    round(cast(nh3_ugm3 as double), 2) as nh3_ugm3,
    cast(ingested_at as timestamp) as ingested_at_utc
from raw_air
qualify row_number() over (
    partition by city_key, observed_dt
    order by cast(ingested_at as timestamp) desc
) = 1