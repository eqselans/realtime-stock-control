# Realtime Stock Control System 📦⚡

Gerçek zamanlı stok olaylarını Kafka üzerinden işleyip MongoDB’ye kaydeden uçtan uca bir sistem. Mevcut kurulum, gözlemleme (Kafka UI, Portainer), orkestrasyon (Airflow), API (FastAPI) ve dashboard (Streamlit) bileşenlerini içerir.

Temel akış: Producer → Kafka Cluster → Consumer → MongoDB (+ API & Dashboard, ETL/DAG’ler, Spark işleri).

—

## � Bileşenler ve Mimari

1) Producer
- Ürün stok değişimlerini simüle eder ve Kafka’ya `stock_updates` topic’ine yazar.

2) Kafka Cluster
- 3 broker (external: 9092, 9093, 9094; internal: 29092, 29093, 29094) + Zookeeper (2181).
- İzleme için Kafka UI (provectuslabs/kafka-ui) kullanılır.

3) Consumer
- `stock_updates` mesajlarını okur ve MongoDB’ye yazar.
- İdempotent kayıt için `_id = {topic}-{partition}-{offset}` kullanır.
- Aşağıdaki koleksiyonları yönetir: `inventory.stock_events`, `inventory.stock_logs`, `inventory.products`, `inventory.product_info`.

4) MongoDB (Atlas)
- Ortam değişkenleriyle Atlas’a bağlanır. Yerel Mongo konteyneri bu sürümde compose’da yoktur.

5) Airflow (Web UI + Scheduler + Triggerer + Dag Processor)
- DAG klasörü: `real-time-stock-tracker/airflow/dags` (örn. `hello_dag.py`, `daily_batch_etl.py`, `report_generation.py`).
- Web arayüzü: http://localhost:8082 (ilk kullanıcı admin/admin olarak oluşturulur).

6) FastAPI
- Servis: http://localhost:8000, Swagger: http://localhost:8000/docs
- Streamlit uygulaması bu API’yi tüketir.

7) Streamlit Dashboard
- Servis: http://localhost:8501
- API_URL env değişkeni ile FastAPI’ye bağlanır.

8) Portainer
- Docker yönetimi: http://localhost:9000

—

## 🌐 Servis ve Portlar (docker-compose)

- Zookeeper: 2181
- Kafka broker’ları: 9092, 9093, 9094 (external) — internal: 29092, 29093, 29094
- Kafka UI: 8080
- Airflow Web: 8082 (konteyner içi 8080)
- FastAPI: 8000
- Streamlit: 8501
- Portainer: 9000

—

## 🧩 Kafka Topic ve Partitions

- Topic adı: `stock_updates`
- Önerilen yapı: 3 partition, replication factor 3 (tüm broker’lar ayakta olmalı).
- Topic’i Kafka UI üzerinden oluşturabilir veya auto-create açıksa otomatik üretilebilir.

—

## 🗄️ MongoDB Şeması ve Index’ler

Database: `inventory`

- `stock_events`
   - İdempotent `_id = topic-partition-offset`
   - `ts` ve `source` alanları ile izlenebilirlik
- `stock_logs`
   - Her olay ayrıca log’lanır; `ts` üzerinde azalan index
- `products`
   - Güncel stok durumu; `product_id` üzerinde unique index
- `product_info`
   - Ürün sabit bilgisi; `product_id` üzerinde unique index

—

## ⚙️ Hızlı Başlangıç

Önkoşullar
- Docker Desktop (çalışır durumda)
- Python 3.10+ (producer/consumer’ı yerelde çalıştıracaksanız)

1) Ortam değişkenlerini ayarlayın (`real-time-stock-tracker/.env`)

```
MONGO_DB_USERNAME=your_user
MONGO_DB_PASSWORD=your_password
MONGO_DB_HOST=your-cluster.mongodb.net

# Opsiyonel
ENABLE_GROQ=false
```

2) Altyapıyı başlatın (Windows PowerShell)

```powershell
cd real-time-stock-tracker\docker
docker compose up -d
```

3) Topic’i doğrulayın/oluşturun
- http://localhost:8080 (Kafka UI) → Clusters → Topics → `stock_updates`
- Partitions: 3, Replication: 3 (opsiyonel; auto-create açıksa gerekmez)

4) Consumer’ı yerelde çalıştırın

```powershell
cd ..\consumer
python -m venv .venv ; .\.venv\Scripts\Activate.ps1 ; pip install -r requirements.txt ; python consumer.py
```

5) Producer’ı yerelde çalıştırın

```powershell
cd ..\producer
python -m venv .venv ; .\.venv\Scripts\Activate.ps1 ; pip install -r requirements.txt ; python producer.py
```

6) Doğrulama
- Kafka UI’da topic mesaj akışını izleyin: http://localhost:8080
- FastAPI: http://localhost:8000/docs
- Streamlit: http://localhost:8501
- Airflow: http://localhost:8082 (admin/admin)
- Portainer: http://localhost:9000

Not: Bu sürümde MongoDB konteyneri yok; Atlas’a bağlanmanız gerekir (IP allowlist ve kullanıcı/parola).

—

## 📁 Klasör Yapısı (özet)

```
real-time-stock-tracker/
   docker/docker-compose.yml
   producer/ (producer.py, requirements.txt)
   consumer/ (consumer.py, requirements.txt)
   fastapi-app/ (app_fastapi.py, Dockerfile)
   streamlit-app/ (app.py, Dockerfile)
   airflow/ (Dockerfile, dags/…)
   spark_jobs/ (stock_streaming.py, aggregations.py, alerts.py, schemas.py)
   shared/ (logger.py, settings.py, utils.py)
   agents/ (stock_agent.py, query_chain.py)
```

—

## 🧪 Airflow DAG’leri

- `hello_dag.py`: Örnek DAG
- `daily_batch_etl.py`: Günlük toplu iş akışı (örnek)
- `report_generation.py`: Rapor üretimi (örnek)

Airflow, docker-compose ile web + scheduler + triggerer + dag-processor servisleriyle gelir. İlk kullanıcı otomatik oluşturulur (admin/admin).

—

## 🔌 API ve Dashboard

- FastAPI: `fastapi-app/app_fastapi.py` → http://localhost:8000/docs
- Streamlit: `streamlit-app/app.py` → http://localhost:8501 (API_URL env ile FastAPI’ye bağlanır)

—

## 🔥 Spark (Geliştirme Aşaması)

`spark_jobs/` altında Structured Streaming ve toplulaştırma örnekleri mevcut. Şu an docker-compose’a dahil değil. Sonraki adımda Spark master/worker ve bağlantılar eklenecek.

—

## 🧯 Sorun Giderme

- Kafka UI bağlanmıyor: Tüm broker’ların (9092/9093/9094) ayakta olduğundan emin olun; replication factor 3 için 3 broker gerekir.
- MongoDB bağlantı hatası: Atlas kullanıcı bilgileri ve IP allowlist’i kontrol edin; `.env` değişkenlerinin yüklendiğinden emin olun.
- PowerShell sanal ortam aktivasyonu engellenirse: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
- Port çakışmaları: 8080/8082/8000/8501/9000 portlarını başka servislerin kullanmadığından emin olun.

—

## ✅ Yapılacaklar (Backlog)

- Producer ve Consumer için docker servisleri ekle (compose’a dahil et)
- Yerel geliştirme için opsiyonel MongoDB konteyneri ekle veya Docker Volume ile yapılandır
- Schema Registry + Avro/JSON Schema doğrulama (compatibility checks)
- Spark konteyner(ler)i ekle ve Kafka ↔ Mongo/S3 sink kaynaklarını tanımla
- Airflow DAG’lerini gerçek ETL adımlarıyla zenginleştir (Spark job tetikleme, rapor üretimi)
- Testler ve CI (GitHub Actions) + kod kalite (ruff/black, pre-commit)
- Gizli bilgileri `.env.example` ve gizli yönetimi (örn. Secret Manager) ile düzenle
- Gözlemleme: Prometheus + Grafana + Kafka Exporter + app metrikleri
- FastAPI için yetkilendirme, oran sınırlama, input doğrulama ve tip güvenliği
- KRaft moduna geçiş (opsiyonel) veya mevcut Zookeeper’ı harden et

—

## 🖼️ Ekran Görüntüleri

Kafka Broker, Topic ve Consumer’ların izlenmesi için Kafka UI (provectuslabs/kafka-ui) kullanıldı.
<img width="100%" height="100%" alt="image" src="https://github.com/user-attachments/assets/0f71fe7f-4100-4c37-b116-15f029c23ae4" />

MongoDB üzerinde Kafka’dan gelen verilerde product_id filtresi ve azalan zaman sıralamalı sorgu:
<img width="100%" height="100%" alt="image" src="https://github.com/user-attachments/assets/79d6c124-af61-4584-80ec-cfb8c92b2d3f" />


