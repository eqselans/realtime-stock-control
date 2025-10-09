from datetime import datetime
from airflow.decorators import task
from airflow import DAG
from airflow.operators.bash import BashOperator

dag = DAG(
    dag_id="hello_dag",
    schedule="* * * * *",  # every minute
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["sanity", "example"],
)

hello_task = BashOperator(
    task_id="hello_task",
    bash_command="echo 'Hello world!'",
    dag=dag,
)

hi_task = BashOperator(
    task_id="hi_task",
    bash_command="echo 'Hi there!'",
    dag=dag,
)

hello_task >> hi_task