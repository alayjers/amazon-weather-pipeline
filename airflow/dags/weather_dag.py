from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'elijah',
    'depends_on_past': False,
    'start_date': datetime(2026, 11, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=3),
}

with DAG(
    dag_id='weather_pipeline_production',
    default_args=default_args,
    description='Multi-city APAC OpenWeather ingestion to S3 and dbt Star Schema build',
    schedule_interval='0 */3 * * *',
    catchup=False,
    max_active_runs=1,
    tags=['production', 'openweather', 'dbt', 'apac'],
) as dag:

    ingest_production_data = BashOperator(
        task_id='ingest_production_data',
        bash_command='cd /opt/airflow/project && PIPELINE_ENV=prod python3 /opt/airflow/project/ingest.py',
    )

    dbt_prod_build = BashOperator(
        task_id='dbt_prod_build',
        bash_command=(
            'cd /opt/airflow/project/weather_transform && '
            'dbt build --target prod --profiles-dir /opt/airflow/project/weather_transform'
        ),
    )

    ingest_production_data >> dbt_prod_build