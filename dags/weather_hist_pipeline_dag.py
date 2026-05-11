import os
import sys
from airflow.sdk import dag
from airflow.providers.standard.operators.python import PythonOperator
from airflow.exceptions import AirflowSkipException
from datetime import timedelta
from pendulum import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from scripts.extract_hist_data import collect_hist_main
from scripts.transform_hist_data import transform_hist_main
from scripts.load_data import load_main

default_args = {
    "owner": "data_engineer",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
}

@dag(
    dag_id="weather_historical_data_pipeline",
    default_args=default_args,
    description="Pipeline to collect historical weather data",
    schedule=None,
    start_date=datetime(2026, 5, 6, tz='Europe/Lisbon'),
    # end_date=datetime(2026, 12, 31, tz='Europe/Lisbon'),
    max_active_runs=1,
    tags=["weather", "historical", "etl"],
    catchup=False,
)
def weather_etl_pipeline():

    def extract_task(**context):
        conf = context["dag_run"].conf
        start = conf.get("start_date")
        end = conf.get("end_date")
        collect_hist_main(start, end)

    def transform_task(**context):
        try:
            df = transform_hist_main()
            context["ti"].xcom_push(key="transformed_data", value=df)
        except Exception as e:
            print(f"Data processinig failed {e}")
            raise AirflowSkipException("Data processinig failed, skipping...")

    def load_task(**context):
       df_data = context["ti"].xcom_pull(task_ids="transform", key="transformed_data")
       load_main(df_data)

    # def analytics_task():
    #     analytics_main()

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

    extract >> transform >> load

weather_etl_pipeline()
