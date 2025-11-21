FROM apache/spark:3.5.3

USER root

# Ek Python paketleri + findspark (PySpark local debug) yükle
RUN apt-get update && apt-get install -y python3 python3-pip && \
    pip3 install --no-cache-dir pymongo pandas findspark && \
    rm -rf /var/lib/apt/lists/*

# Airflow scripts klasöründeki güncel streaming job dosyasını kopyalamak için
# build context'i üst dizin olacak (compose içinde ayarlanacak). Bu nedenle yol relative.
COPY airflow/scripts/stream_summary.py /app/app.py

WORKDIR /app

# Gerekli Kafka paketlerini eklemek için --packages parametresi yerine
# script içindeki builder config kullanılıyor; burada sadece submit yapıyoruz.
# Resmi apache/spark imajında spark-submit /opt/spark/bin altında.
CMD ["/opt/spark/bin/spark-submit", "--master", "spark://spark-master:7077", "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3,org.apache.spark:spark-token-provider-kafka-0-10_2.12:3.5.3", "/app/app.py"]
