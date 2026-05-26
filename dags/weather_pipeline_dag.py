import os
import sys
from airflow.sdk import dag
from airflow.providers.standard.operators.python import PythonOperator
from datetime import timedelta
from pendulum import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from scripts.extract_daily_data import collect_daily_main
from scripts.transform_daily_data import transform_daily_main
from scripts.load_data import load_main
from scripts.analytic_data import analytics_main

default_args = {
    "owner": "data_engineer",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
}

@dag(
    dag_id="weather_data_pipeline",
    default_args=default_args,
    description="Pipeline to collect daily weather data",
    schedule="45 9 * * *",
    start_date=datetime(2026, 5, 16, tz='Europe/Lisbon'),
    end_date=datetime(2026, 12, 31, tz='Europe/Lisbon'),
    max_active_runs=1,
    tags=["weather", "etl"],
    catchup=False,
)
def weather_etl_pipeline():

    def extract_task():
        collect_daily_main()

    def transform_task(**context):
        df = transform_daily_main()
        context["ti"].xcom_push(key="transformed_data", value=df)

    def load_task(**context):
       df_data = context["ti"].xcom_pull(task_ids="transform", key="transformed_data")
       load_main(df_data)

    def analytics_task():
        analytics_main()

    extract = PythonOperator(
        task_id="extract", 
        python_callable=extract_task
    )

    transform = PythonOperator(
        task_id="transform", 
        python_callable=transform_task
    )

    load = PythonOperator(
        task_id="load", 
        python_callable=load_task
    )

    analytics = PythonOperator(
        task_id="analytics", 
        python_callable=analytics_task
    )

    extract >> transform >> load >> analytics
    
    # extract >> transform >> load

weather_etl_pipeline()
