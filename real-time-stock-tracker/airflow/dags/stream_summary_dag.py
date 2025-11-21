# Bu MongoDB özetleme DAG örneğidir. Spark ile MongoDB'den stream veri okuma scriptini burada çalıştıracağız.

from datetime import datetime
from airflow.decorators import task
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

dag = DAG(
    dag_id="stream_summary_dag",
    doc_md="""
    # Stream Özetleme DAG
    Bu DAG, Spark ile MongoDB'den stream veri okuma işlemini gerçekleştiren bir uygulamayı çalıştırmak için kullanılır.
    """,
    schedule="@daily",
    start_date=datetime(2025, 10, 19),
    catchup=False
)
stream_summary_task = BashOperator(
    task_id="stream_summary",
    # spark-submit Airflow imajında yok; pyspark paketini doğrudan python ile çalıştırıyoruz.
    # İleride cluster submit istenirse docker exec spark-streaming veya SparkSubmitOperator + Spark kurulumu yapılacak.
    bash_command="python /opt/airflow/scripts/stream_summary.py",
    dag=dag
)
stream_summary_task