{{ config(
    materialized='external',
    location="s3://weather-datalake-dev/{{ target.name }}_silver/stg_locations.parquet",
    format='parquet'
) }}

with raw_locations as (
    select *
    from read_parquet(
        "s3://weather-datalake-dev/{{ target.name }}_bronze/locations/*.parquet",
        union_by_name=true
    )
)

select
    cast(city_key as varchar) as city_key,
    cast(city_name as varchar) as city_name,
    cast(country_code as varchar) as country_code,
    cast(region as varchar) as region,
    cast(latitude as double) as latitude,
    cast(longitude as double) as longitude,
    cast(climate_zone as varchar) as climate_zone,
    cast(utc_offset_hours as integer) as utc_offset_hours,
    cast(ingested_at as timestamp) as ingested_at_utc
from raw_locations
qualify row_number() over (partition by city_key order by cast(ingested_at as timestamp) desc) = 1