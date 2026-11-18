{{ config(
    materialized='external',
    location="s3://weather-datalake-dev/{{ target.name }}_gold/dim_location.parquet",
    format='parquet'
) }}

select
    city_key,
    city_name,
    country_code,
    region,
    latitude,
    longitude,
    climate_zone,
    utc_offset_hours
from {{ ref('stg_locations') }}
order by city_name