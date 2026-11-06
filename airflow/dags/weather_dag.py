from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

# Default settings for the workflow
default_args = {
    'owner': 'Elijah',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=3),
}

# Define the DAG
with DAG(
    'amazon_weather_lakehouse',
    default_args=default_args,
    description='Automated dlt ingestion and dbt build for S3 Lakehouse',
    schedule_interval='0 2 * * *', # Runs automatically every day at 2:00 AM
    catchup=False,
    tags=['weather', 'aws', 'duckdb'],
) as dag:

    # Task 1: Run the dlt ingestion script
    ingest_bronze = BashOperator(
        task_id='ingest_openmeteo_to_s3_bronze',
        bash_command='python3 /opt/airflow/project/ingest.py',
    )

    # Task 2: Run dbt build (compiles, runs models, and executes tests in one session)
    transform_and_test = BashOperator(
        task_id='dbt_build_silver_and_gold',
        bash_command='cd /opt/airflow/project/weather_transform && dbt build',
    )

    # Set the execution order
    ingest_bronze >> transform_and_test