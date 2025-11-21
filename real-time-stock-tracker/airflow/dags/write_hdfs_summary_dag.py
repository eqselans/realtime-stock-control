# Bu bir HDFS yazma özeti DAG örneğidir. Spark ile HDFS'ye yazma scriptini burada çalıştıracağız.

from datetime import datetime
from airflow.decorators import task
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator


dag = DAG(
    dag_id="write_hdfs_summary_dag",
    doc_md="""
    # HDFS Yazma Özeti DAG
    Bu DAG, Spark ile HDFS'ye yazma işlemini gerçekleştiren bir uygulamayı çalıştırmak için kullanılır.
    """,
    schedule="@daily",
    start_date=datetime(2025, 10, 19),
    catchup=False
)
write_hdfs_summary_task = BashOperator(
    task_id="write_hdfs_summary",
    bash_command="spark-submit /opt/airflow/scripts/write_hdfs_summary.py",
    dag=dag
)

write_hdfs_summary_task