{{ config(
    materialized='external',
    location='s3://weather-datalake-dev/gold/fct_monthly_weather_summary.parquet',
    format='parquet'
) }}

with silver_daily as (
    select * 
    from {{ ref('stg_manila_daily') }}
)

select
    -- Date Aggregations
    date_trunc('month', record_date) as month_start_date,
    count(*) as total_days_recorded,
    
    -- Temperature Summary Metrics
    round(avg(max_temp_celsius), 2) as avg_max_temp_celsius,
    round(avg(min_temp_celsius), 2) as avg_min_temp_celsius,
    round(max(max_temp_celsius), 2) as peak_temp_celsius,
    round(min(min_temp_celsius), 2) as lowest_temp_celsius,
    
    -- Rainfall Aggregations
    round(sum(precipitation_mm), 2) as total_precipitation_mm,
    count_if(is_rainy_day) as rainy_days_count,
    round(avg(precipitation_mm), 2) as avg_daily_precipitation_mm

from silver_daily
group by 1
order by month_start_date asc

