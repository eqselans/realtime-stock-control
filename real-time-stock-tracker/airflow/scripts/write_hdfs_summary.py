"""MongoDB koleksiyonundan Spark ile FULL yük alıp HDFS'ye parquet yazan script.

Tek seferlik (full load) senaryo:
 - Tüm koleksiyon okunur, HDFS hedefi OVERWRITE edilir.
 - Incremental / partition yok (şimdilik).

Bağımlılık (spark-submit sırasında):
  --packages org.mongodb.spark:mongo-spark-connector_2.12:10.3.0

Gerekli ortam değişkenleri veya Airflow Variables (CLI argümanı yoksa):
  MONGO_DB_USERNAME
  MONGO_DB_PASSWORD
  MONGO_DB_HOST (örn: emrhn-cluster.qmgcy9d.mongodb.net)
  MONGO_DB (örn: stockdb)
  MONGO_COLLECTION (örn: stocks)
  HDFS_OUTPUT_PATH (örn: hdfs://namenode:8020/data/stock/full_load)

İsteğe bağlı:
  SPARK_MASTER_URL (varsayılan: spark://spark-master:7077)

Not: Connection string SRV ise 'mongodb+srv://' ile; standard ise 'mongodb://'
"""

import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import to_timestamp, col


def build_spark_session():
    master = os.environ.get("SPARK_MASTER_URL", "spark://spark-master:7077")
    return (
        SparkSession.builder
        .appName("mongo-full-to-hdfs")
        .config(
            "spark.jars.packages",
            "org.mongodb.spark:mongo-spark-connector_2.12:10.3.0"
        )
        .config("spark.hadoop.dfs.client.use.datanode.hostname", "true")
        .master(master)
        .getOrCreate()
    )


def get_config():
    # CLI argüman ile sadece output path override edilebilsin (opsiyonel)
    cli_args = sys.argv[1:]
    override_output = cli_args[0] if cli_args else None
    # SABİT VARSAYILANLAR (geçici). Üretimde KALDIR ve env/secret kullan.
    defaults = {
        "user": "emrhnaxusoft2",
        "pwd": "u47XgagHHASkKem",
        "host": "emrhn-cluster.qmgcy9d.mongodb.net",
        "db": "inventory",
        "coll": "stock_events",
        "out": "hdfs://192.168.56.101:8020/user/hive/warehouse/stock_movements",
    }
    cfg = {
        "user": os.environ.get("MONGO_DB_USERNAME", defaults["user"]),
        "pwd": os.environ.get("MONGO_DB_PASSWORD", defaults["pwd"]),
        "host": os.environ.get("MONGO_DB_HOST", defaults["host"]),
        "db": os.environ.get("MONGO_DB", defaults["db"]),
        "coll": os.environ.get("MONGO_COLLECTION", defaults["coll"]),
        "out": override_output or os.environ.get("HDFS_OUTPUT_PATH", defaults["out"]),
    }
    missing = [k for k, v in cfg.items() if not v]
    if missing:
        raise SystemExit(f"Eksik zorunlu ayarlar (varsayılana rağmen): {missing}")
    return cfg


def build_mongo_uri(user: str, pwd: str, host: str) -> str:
    # Varsayılan olarak SRV kabul edelim (Atlas)
    prefix = "mongodb+srv://" if host.endswith(".mongodb.net") else "mongodb://"
    return f"{prefix}{user}:{pwd}@{host}/?retryWrites=true&w=majority"


def extract_and_write(cfg):
    spark = build_spark_session()
    uri = build_mongo_uri(cfg["user"], cfg["pwd"], cfg["host"])
    print(f"[INFO] Mongo URI (masked): {uri.split('@')[0]}@***")
    print(f"[INFO] DB: {cfg['db']}  Collection: {cfg['coll']}")
    print(f"[INFO] HDFS Output: {cfg['out']}")

    df = (
        spark.read.format("mongodb")
        .option("spark.mongodb.read.connection.uri", uri)
        .option("spark.mongodb.read.database", cfg["db"])
        .option("spark.mongodb.read.collection", cfg["coll"])
        .load()
    )


    # Varsa olası timestamp alanları dönüştür (örnek: 'timestamp' veya 'ts')
    for ts_col in ["timestamp", "ts", "created_at"]:
        if ts_col in df.columns:
            df = df.withColumn(ts_col, to_timestamp(col(ts_col)))

    df.printSchema()

    # Coalesce ile partition sayısını düşür (opsiyonel)
    df.coalesce(2).write.mode("overwrite").parquet(cfg["out"])
    print("[INFO] FULL LOAD Tamamlandı (overwrite).")
    spark.stop()


if __name__ == "__main__":
    config = get_config()
    extract_and_write(config)