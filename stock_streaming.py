import pyspark
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

from pyspark.sql.functions import from_json, col, expr, window, to_timestamp, sum
from pyspark.sql.types import StructType, StringType, IntegerType, TimestampType

import findspark
findspark.init()

# Findspark'ın bulduğu bilgileri yazdır
print("=== FINDSPARK BİLGİLERİ ===")
print(f"Spark Home: {findspark.find()}")
print(f"Spark Version: {findspark.spark_version if hasattr(findspark, 'spark_version') else 'Belirlenemedi'}")
print(f"Python Path'e eklenen Spark dizinleri:")


import os
import sys

# Sys.path'te Spark ile ilgili yolları bul
spark_paths = [path for path in sys.path if 'spark' in path.lower() or 'pyspark' in path.lower()]
for path in spark_paths:
    print(f"  - {path}")

print("=" * 40)



# PySpark versiyonunu yazdır
print(f"PySpark Version: {pyspark.__version__}")

spark = SparkSession.builder \
    .appName("Chat Program") \
    .master("local[*]") \
    .config(
        "spark.jars.packages",
        "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3,"
        "org.apache.spark:spark-token-provider-kafka-0-10_2.12:3.5.3"
    ) \
    .getOrCreate()
    
    # Spark Context bilgilerini yazdır
print(f"Spark Context Version: {spark.sparkContext.version}")
print(f"Spark Context App Name: {spark.sparkContext.appName}")
print(f"Spark Context Master: {spark.sparkContext.master}")
print("=" * 40)

spark = SparkSession.builder \
    .appName("StockStreamingApp") \
    .getOrCreate()

# Kafka'dan veri oku
raw_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "stock_updates") \
    .option("startingOffsets", "latest") \
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
    
# Şehre Göre Son 5 Dakikada Toplam Delta

events_df = parsed_df.withColumn("event_time", to_timestamp("ts"))
# event_time sütunu, olayın zaman damgasını temsil eder.


city_agg = events_df.groupBy(
    window(col("event_time"), "5 minutes"),
    col("city")
).agg(
    sum("delta").alias("total_delta")
)

# Bu kod parçası, her şehir için son 5 dakikada toplam delta değerini hesaplar.
# Delta, stokta meydana gelen değişiklikleri temsil eder ve bu bilgiler
# stok yönetimi ve talep tahmini için önemlidir.

query = city_agg.writeStream \
    .outputMode("update") \
    .format("console") \
    .option("truncate", "false") \
    .start()
    
query.awaitTermination()