# Bu MongoDB'den alınan saatlik veriyi Spark ile HDFS'ye yazan bir script örneğidir.

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_timestamp, date_format
import sys


def write_hdfs_summary(input_path, output_path):
    spark = SparkSession.builder \
        .appName("HDFS Summary Writer") \
        .getOrCreate()
    # Veriyi oku
    df = spark.read.json(input_path)
    # Veriyi işleme
    df = df.select(
        col("symbol"),
        col("price"),
        to_timestamp(col("timestamp")).alias("timestamp")
    )
    # Veriyi yaz (tablo adı değil, path olduğu için save/parquet kullan)
    df.write.mode("overwrite").format("parquet").save(output_path)
    spark.stop()

if __name__ == "__main__":
    input_path = sys.argv[1]  # Girdi yolu örn: mongodb://host:port/db.collection
    output_path = sys.argv[2]  # Çıktı yolu örn: hdfs://path/to/output
    write_hdfs_summary(input_path, output_path)