FROM bitnami/spark:3.2.1

USER root

# Ek Python paketleri yükle
RUN apt-get update && apt-get install -y python3-pip && \
    pip3 install pymongo pandas

# Spark uygulamanı kopyala
COPY stock_streaming.py /app/app.py

WORKDIR /app

CMD ["spark-submit", "--master", "spark://spark-master:7077", "app.py"]
