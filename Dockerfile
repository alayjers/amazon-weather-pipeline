FROM apache/airflow:2.9.1
RUN pip install --no-cache-dir "dlt[s3,parquet]" dbt-duckdb s3fs botocore