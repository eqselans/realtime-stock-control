FROM apache/airflow:3.0.0-python3.10
USER root
RUN apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends openjdk-17-jre-headless ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
USER airflow
COPY requirements.txt /
RUN pip install --no-cache-dir -r /requirements.txt


USER airflow
COPY dags/ /opt/airflow/dags/
COPY scripts/ /opt/airflow/scripts/
