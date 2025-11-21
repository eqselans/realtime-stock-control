# PDF/Excel raporları tetikleyen DAG

from datetime import datetime
from airflow.decorators import task
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

dag = DAG(
    dag_id="report_generation_dag",
    doc_md="""
    # Rapor Oluşturma DAG
    Bu DAG, PDF ve Excel raporlarını oluşturmak için kullanılır.
    """,
    schedule="@daily",
    start_date=datetime(2025, 10, 19),
    catchup=False
)

generate_report_task = BashOperator(
    task_id="generate_reports",
    bash_command="python /opt/airflow/scripts/generate_reports.py",
    dag=dag
)
generate_report_task