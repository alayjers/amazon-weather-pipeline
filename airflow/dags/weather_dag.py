from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

# Default arguments applied to all tasks
default_args = {
    'owner': 'elijah',
    'depends_on_past': False,
    'start_date': datetime(2026, 11, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='weather_pipeline_production',
    default_args=default_args,
    description='Automated production ingestion from Open-Meteo API to S3 and dbt transformation',
    schedule_interval='0 2 * * *',  # Runs daily at 02:00 UTC
    catchup=False,
    max_active_runs=1,
    tags=['production', 'weather', 'dbt'],
) as dag:

    # Task 1: Ingest dynamic weather data into S3 prod_bronze
    ingest_production_data = BashOperator(
        task_id='ingest_production_data',
        bash_command='PIPELINE_ENV=prod python3 /opt/airflow/project/ingest.py',
    )

    # Task 2: Transform raw records into S3 prod_silver and prod_gold via dbt
    dbt_prod_build = BashOperator(
        task_id='dbt_prod_build',
        bash_command=(
            'cd /opt/airflow/project/weather_transform && '
            'dbt build --target prod --profiles-dir /home/airflow/.dbt'
        ),
    )

    # Define task execution order
    ingest_production_data >> dbt_prod_build