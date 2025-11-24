# Bu bir HDFS yazma özeti DAG örneğidir. Spark ile HDFS'ye yazma scriptini burada çalıştıracağız.

from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.models import Variable

# Airflow Variables ile konfigürasyon (UI > Admin > Variables):
#   INPUT_PATH           : /opt/airflow/data/hourly_json  (örnek)
#   HDFS_OUTPUT_PATH     : hdfs://namenode:8020/data/stock/hourly_summary
# Alternatif olarak docker-compose environment içinde de tanımlanabilir.

# Variablelar Airflow UI'de tanımlanmışsa kullanılacak.
MONGO_DB_USERNAME_VAR = Variable.get("MONGO_DB_USERNAME", "")
MONGO_DB_PASSWORD_VAR = Variable.get("MONGO_DB_PASSWORD", "")
MONGO_DB_HOST_VAR = Variable.get("MONGO_DB_HOST", "")
MONGO_DB_VAR = Variable.get("MONGO_DB", "")
MONGO_COLLECTION_VAR = Variable.get("MONGO_COLLECTION", "")
HDFS_OUTPUT_PATH_VAR = Variable.get("HDFS_OUTPUT_PATH", "")

dag = DAG(
    dag_id="write_hdfs_summary_dag",
    doc_md="""
    # Mongo FULL -> HDFS DAG (Overwrite)
    spark-submit binary konteynerda olmadığı için job doğrudan
    `python` ile çalıştırılır; pip ile gelen pyspark driver localde
    başlar ve Spark cluster'a (spark://spark-master:7077) bağlanır.

    Script sabit varsayılanları içerir (geçici):
      user=emrhnaxusoft2, host=emrhn-cluster.qmgcy9d.mongodb.net,
      db=inventory, coll=stock_events,
      out=hdfs://192.168.56.101:8020/user/hive/warehouse/stock_movements

    Override:
      - Airflow Variables tanımlanırsa kullanılacak.
      - HDFS_OUTPUT_PATH Variable eklenirse çıktı path'i değişir.
      - CLI arg (bash_command sonuna path) verilebilir; burada kullanılmıyor.

    Mongo Spark connector jar paketi artık SparkSession içinde
    `spark.jars.packages` konfigi ile yükleniyor.
    """,
    schedule=None,
    start_date=datetime(2025, 11, 21),
    catchup=False,
    tags=["hdfs", "spark", "mongo", "full-load"]
)

write_hdfs_summary_task = BashOperator(
    task_id="mongo_full_to_hdfs",
    bash_command=(
        "python /opt/airflow/scripts/write_hdfs_summary.py"
    ),
    env={
        "MONGO_DB_USERNAME": "{{ var.value.MONGO_DB_USERNAME | default('') }}",
        "MONGO_DB_PASSWORD": "{{ var.value.MONGO_DB_PASSWORD | default('') }}",
        "MONGO_DB_HOST": "{{ var.value.MONGO_DB_HOST | default('') }}",
        "MONGO_DB": "{{ var.value.MONGO_DB | default('') }}",
        "MONGO_COLLECTION": "{{ var.value.MONGO_COLLECTION | default('') }}",
        "HDFS_OUTPUT_PATH": "{{ var.value.HDFS_OUTPUT_PATH | default('') }}",
        "SPARK_MASTER_URL": "spark://spark-master:7077"
    },
    dag=dag
)

write_hdfs_summary_task