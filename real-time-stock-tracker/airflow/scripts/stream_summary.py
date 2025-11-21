"""Streaming özet jobu

Bu dosya önceki `spark_jobs/stock_streaming.py` içeriğinin taşınmış halidir.
Airflow DAG `stream_summary_dag` içinde `spark-submit /opt/airflow/scripts/stream_summary.py` ile çağrılacak.

Notlar:
 - Konteyner içinden Kafka için `localhost` yerine `kafka:29092` kullanıldı.
 - İki ayrı SparkSession tanımı vardı; tekleştirildi.
 - Structured Streaming console output (update mode) devam ediyor.
 - Gereksinimler: pyspark, findspark (bunları airflow/requirements.txt içine eklemelisin).
 - Apache Spark runtime (binari) Airflow imajında yoksa bu job çalışmaz; ya ayrı Spark konteyneri ya da imaja Spark eklenmesi gerekir.
"""

import time
import os
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
	col, from_json, window, to_timestamp, sum as _sum
)
from pyspark.sql.types import (
	StructType, StringType, IntegerType, TimestampType
)

import findspark
findspark.init()

print("=== SPARK ORTAM BİLGİLERİ ===")
print(f"PySpark Version: {pyspark.__version__}")
print(f"findspark Spark Home: {findspark.find()}")
print("==============================")

spark = SparkSession.builder \
	.appName("StockStreamingApp") \
	.master("spark://spark-master:7077") \
	.config(
		"spark.jars.packages",
		"org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3,org.apache.spark:spark-token-provider-kafka-0-10_2.12:3.5.3"
	) \
	.getOrCreate()

print(f"Spark Version (Context): {spark.sparkContext.version}")
print(f"Spark Master: {spark.sparkContext.master}")  # Beklenen: spark://spark-master:7077 (cluster)

# Kafka'dan veri oku (container içi broker hostunu kullan)
raw_df = spark.readStream \
	.format("kafka") \
	.option("kafka.bootstrap.servers", "kafka:29092,kafka2:29093,kafka3:29094") \
	.option("kafka.security.protocol", "PLAINTEXT") \
	.option("subscribe", "stock_updates") \
	.option("startingOffsets", "earliest") \
	.load()

schema = StructType() \
	.add("event_type", StringType()) \
	.add("product_id", StringType()) \
	.add("product_name", StringType()) \
	.add("category", StringType()) \
	.add("supplier", StringType()) \
	.add("delta", IntegerType()) \
	.add("new_stock", IntegerType()) \
	.add("warehouse_id", StringType()) \
	.add("city", StringType()) \
	.add("updated_by", StringType()) \
	.add("ts", TimestampType())

parsed_df = raw_df.selectExpr("CAST(value AS STRING) as json_str") \
	.select(from_json(col("json_str"), schema).alias("data")) \
	.select("data.*")

events_df = parsed_df.withColumn("event_time", to_timestamp("ts"))

# Şehre göre son 5 dakikada toplam delta
city_agg = events_df.groupBy(
	window(col("event_time"), "5 minutes"),
	col("city")
).agg(
	_sum("delta").alias("total_delta")
)

# Kategori bazlı son 5 dakikalık delta eğilimi
category_agg = events_df.groupBy(
	window(col("event_time"), "5 minutes"),
	col("category")
).agg(
	_sum("delta").alias("category_total_delta")
)

# Kritik stok alarmı: new_stock < 10
critical_alerts = parsed_df.filter(col("new_stock") < 10)

city_query = city_agg.writeStream \
	.outputMode("update") \
	.format("console") \
	.option("truncate", "false") \
	.start()

category_query = category_agg.writeStream \
	.outputMode("update") \
	.format("console") \
	.option("truncate", "false") \
	.option("numRows", 30) \
	.start()

alert_query = critical_alerts.writeStream \
	.outputMode("update") \
	.format("console") \
	.option("truncate", "false") \
	.option("numRows", 30) \
	.start()

try:
	while city_query.isActive and category_query.isActive and alert_query.isActive:
		time.sleep(1)
except KeyboardInterrupt:
	print("Streaming sonlandırılıyor...")
finally:
	for q in [city_query, category_query, alert_query]:
		if q.isActive:
			q.stop()
	spark.stop()

