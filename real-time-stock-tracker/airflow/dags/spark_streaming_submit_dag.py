"""Spark Streaming submit DAG

Airflow üzerinden Spark cluster'a (spark-master) streaming job gönderir.
Alternatif olarak mevcut BashOperator DAG'ı korunabilir. Bu DAG SparkSubmitOperator
mevcut sağlayıcı (apache-airflow-providers-apache-spark) ile çalışır.

Not: spark_default connection yoksa BashOperator fallback kullanın veya UI'da
Conn ekleyin (Conn Id: spark_default, Host: spark-master, Port: 7077).
"""

from datetime import datetime
from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

default_args = {
    "depends_on_past": False,
}

dag = DAG(
    dag_id="spark_streaming_submit_dag",
    description="Spark Structured Streaming job submit DAG",
    start_date=datetime(2025, 11, 21),
    schedule=None,  # Manuel tetikleme; sürekli job olduğundan periyodik değil
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    doc_md="""
    # Spark Streaming Submit DAG
    Bu DAG, Kafka'dan veri okuyup pencere agregasyonları yapan uzun süreli
    streaming job'u Spark cluster'a submit eder.
    """,
)

spark_streaming = SparkSubmitOperator(
    task_id="spark_streaming_job",
    application="/opt/airflow/scripts/stream_summary.py",
    conn_id="spark_default",  # UI'da bu bağlantıyı tanımlamalısınız.
    name="StockStreamingApp",
    verbose=True,
    packages="org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3,org.apache.spark:spark-token-provider-kafka-0-10_2.12:3.5.3",
    # Yürütme parametreleri - basit kaynak sınırları
    executor_cores=1,
    executor_memory="1G",
    driver_memory="1G",
    dag=dag,
)

spark_streaming
