{{ config(
    materialized='external',
    location='s3://weather-datalake-dev/silver/stg_manila_daily.parquet',
    format='parquet'
) }}

with raw_bronze as (
    select *
    from read_parquet('s3://weather-datalake-dev/bronze/manila_daily/*.parquet')
)

select
    -- Primary Keys & Timestamps
    cast(date as date) as record_date,
    
    -- Temperature Metrics
    cast(max_temp as double) as max_temp_celsius,
    cast(min_temp as double) as min_temp_celsius,
    round(cast(max_temp as double) - cast(min_temp as double), 2) as temp_range_celsius,
    
    -- Precipitation Metrics
    cast(precipitation as double) as precipitation_mm,
    case 
        when cast(precipitation as double) > 0 then true 
        else false 
    end as is_rainy_day

from raw_bronze
qualify row_number() over (partition by cast(date as date) order by cast(date as date)) = 1