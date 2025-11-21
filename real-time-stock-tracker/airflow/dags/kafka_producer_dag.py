from datetime import datetime
from airflow.decorators import task
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

# Bu bir Kafka üretici DAG örneğidir. Producer scriptini burada çalıştıracağız.

dag = DAG(
    dag_id="kafka_producer_dag",
    doc_md="""
    # Kafka Producer DAG
    Bu DAG, Kafka'ya sürekli mesaj gönderen bir üretici uygulamasını çalıştırmak için kullanılır.
    """,
    schedule="* * * * *",  # Her dakika bir kez çalıştır (en basit periyodik yaklaşım)
    start_date=datetime(2025, 10, 19),
    catchup=False,
    max_active_runs=1
)

run_producer_task = BashOperator(
    task_id="run_kafka_producer",
    bash_command="python /opt/airflow/scripts/kafka_producer.py",
    dag=dag
)

run_producer_task