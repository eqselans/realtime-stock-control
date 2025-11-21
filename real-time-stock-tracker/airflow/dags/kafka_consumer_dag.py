from datetime import datetime
from airflow.decorators import task
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

# Bu bir Kafka tüketici DAG örneğidir. Consumer scriptini burada çalıştıracağız.

dag = DAG(
    dag_id="kafka_consumer_dag",
    doc_md="""
    # Kafka Consumer DAG
    Bu DAG, Kafka'dan mesaj alan tüketici uygulamasını çalıştırmak için kullanılır.
    Sürekli (@continuous) tetikleme kaldırıldı; manuel tetikleme için schedule=None kullanıyoruz.
    """,
    schedule=None,  # Manuel çalıştır; en basit yaklaşımda elle veya Triggered Run ile paralel baskıyı azaltır
    start_date=datetime(2025, 10, 19),
    catchup=False,
    max_active_runs=1
)

run_consumer_task = BashOperator(
    task_id="run_kafka_consumer",
    bash_command="python /opt/airflow/scripts/kafka_consumer.py",
    dag=dag
)

run_consumer_task