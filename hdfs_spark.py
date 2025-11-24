"""Basit PySpark + HDFS yazım örneği.

findspark KALDIRILDI: Pip ile kurulu pyspark kullanıyoruz. JVM başlatma
hatalarının tipik sebebi JAVA_HOME / JDK yokluğu veya yanlış SPARK_HOME.
Bu dosya ortamı kontrol eder ve basit bir Parquet yazımı yapar.
"""

import os
import shutil
import datetime
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType, TimestampType

# İstenirse ortama HDFS_NN, HDFS_PORT vererek override edebilirsiniz.
HDFS_NAMENODE = os.environ.get("HDFS_NN", "192.168.56.101")
HDFS_PORT = os.environ.get("HDFS_PORT", "8020")
HDFS_BASE_PATH = f"hdfs://{HDFS_NAMENODE}:{HDFS_PORT}/data/stock"

HIVE_METASTORE_URI = f"thrift://{HDFS_NAMENODE}:9083"
HIVE_TABLE_PATH = f"hdfs://{HDFS_NAMENODE}:{HDFS_PORT}/user/hive/warehouse/stock_data"

def check_environment():

    print("=== ORTAM KONTROLÜ ===")
    print(f"Seçilen NameNode: {HDFS_NAMENODE}:{HDFS_PORT}")
    java_in_path = shutil.which("java") is not None
    if not os.environ.get("JAVA_HOME"):
        print("UYARI: JAVA_HOME tanımlı değil.")
    else:
        print(f"JAVA_HOME: {os.environ['JAVA_HOME']}")
    print(f"Java PATH'te bulunuyor mu: {'Evet' if java_in_path else 'Hayır'}")

    spark_home = os.environ.get("SPARK_HOME")
    if spark_home:
        py4j_candidates = []
        python_lib = os.path.join(spark_home, "python", "lib")
        if os.path.isdir(python_lib):
            for name in os.listdir(python_lib):
                if name.startswith("py4j-") and name.endswith(".zip"):
                    py4j_candidates.append(name)
        if py4j_candidates:
            print(f"SPARK_HOME: {spark_home} (py4j bulundu: {py4j_candidates[0]})")
        else:
            print(f"SPARK_HOME: {spark_home} (py4j ZIP bulunamadı - pip pyspark'a düşülecek)")
            # Pip ile gelen pyspark'ı kullanmak için ortamdan SPARK_HOME'u kaldır.
            os.environ.pop("SPARK_HOME", None)
            print("SPARK_HOME geçici olarak temizlendi. Tekrar kurmak için doğru binary (tgz) indirip tam açın.")
    else:
        print("UYARI: SPARK_HOME tanımlı değil (pip pyspark ile devam edilebilir).")

    hadoop_home = os.environ.get("HADOOP_HOME")
    if hadoop_home:
        winutils_path = os.path.join(hadoop_home, "bin", "winutils.exe")
        print(f"HADOOP_HOME: {hadoop_home} (winutils: {'var' if os.path.isfile(winutils_path) else 'yok'})")
    else:
        print("UYARI: HADOOP_HOME tanımlı değil (Windows'ta bazı izin hataları çıkabilir).")
    print("=" * 40)


def write_sample():
    check_environment()
    spark = (
        SparkSession.builder.appName("hdfs-write-sample")
        .config("spark.hadoop.fs.defaultFS", f"hdfs://{HDFS_NAMENODE}:{HDFS_PORT}")
        # Tek düğümlü/mini cluster için replika sayısını düşür
        .config("spark.hadoop.dfs.replication", "1")
        .config("spark.hadoop.hive.metastore.uris", HIVE_METASTORE_URI)
        # AŞAĞIDAKİ SATIRI EKLE:
        .config("spark.hadoop.dfs.client.use.datanode.hostname", "true")
        .enableHiveSupport()
        .getOrCreate()
    )

    # fs.defaultFS değerini doğrula
    try:
        fs_default = spark.sparkContext._jsc.hadoopConfiguration().get("fs.defaultFS")
    except Exception:
        fs_default = None
    print(f"fs.defaultFS: {fs_default or 'Okunamadı'}")

# Örnek Veri Oluşturma
    schema = StructType([
        StructField("symbol", StringType(), True),
        StructField("price", DoubleType(), True),
        StructField("volume", IntegerType(), True), # Burada INT zorluyoruz (Hive INT bekliyor)
        StructField("ts", TimestampType(), True)
    ])

    # Örnek Veri
    now = datetime.datetime.utcnow()
    data = [
        ("META", 325.44, 180, now),
        ("NFLX", 450.11, 90, now),
        ("AMD", 112.55, 200, now),
    ]
    
    # createDataFrame yaparken şemayı veriyoruz.
    # Böylece Spark "180" sayısını Long değil, Integer olarak işler.
    df = spark.createDataFrame(data, schema)

    print("Veri hazırlanıyor (Schema ile)...")
    df.printSchema() # Schema'nın doğru (integer) olduğunu gör
    df.show()

    print(f"Hedef HDFS Yolu: {HIVE_TABLE_PATH}")

    try:
        # --- KRİTİK NOKTA ---
        # saveAsTable: Spark, Metastore'a bağlanır, tablo yerini bulur ve yazar.
        # mode("append"): Tabloyu silmeden altına ekler.
        df.write \
          .mode("append") \
          .parquet(HIVE_TABLE_PATH)
          
        print("\n>>> BAŞARILI: Veriler HDFS'e yazıldı.")
        print(">>> Hive Metastore bypass edildi.")
        print(">>> HUE'ya gidip 'SELECT * FROM stock_data' diyerek yeni verileri (META, NFLX, AMD) görebilirsin.")
          
        print("\n>>> BAŞARILI: Veriler 'stock_data' tablosuna eklendi.")
        print(">>> HUE üzerinden 'SELECT * FROM stock_data' ile kontrol edebilirsin.")
        
    except Exception as e:
        print(f"\n!!! HATA OLUŞTU !!!\n{e}")
        print("-" * 30)
        print("OLASI ÇÖZÜM: Eğer 'Could not connect to meta store' hatası aldıysan,")
        print("Windows makinen VM'in 9083 portuna erişemiyor olabilir.")
        print("Bu durumda koddaki '.saveAsTable' yerine '.parquet(/user/hive/warehouse/stock_data)' kullanman gerekebilir.")

    finally:
        spark.stop()


if __name__ == "__main__":
    write_sample()