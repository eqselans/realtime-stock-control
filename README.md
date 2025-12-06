# Realtime Stock Control System 📦⚡

Gerçek zamanlı stok olaylarını Kafka üzerinden işleyip MongoDB Atlas, FastAPI ve Streamlit katmanlarıyla izleyen; Airflow ve Spark entegrasyonlarıyla zenginleştirilmiş uçtan uca gerçek zaman + yakın gerçek zaman veri platformu.

Temel akış: Producer → Kafka Cluster → Consumer → MongoDB → API (FastAPI) → Dashboard (Streamlit) → (Airflow DAG tetiklemeleri & Spark Structured Streaming) → HDFS / Raporlama.

---

## 🗺️ İçindekiler
1. Bileşenler ve Mimari
2. Servis & Port Haritası
3. Kafka Topic Stratejisi
4. MongoDB Şema & Indexler
5. Hızlı Başlangıç
6. Klasör Yapısı
7. Airflow DAG’leri
8. Spark & HDFS Entegrasyonu
9. API & Dashboard
10. Ekran Görüntüsü Yerleri (Placeholders)
11. Lisans / Kullanım
---

## 🏗️ Bileşenler ve Mimari

> Mimari diyagramı eklenecek (PLACEHOLDER) — `docs/images/architecture.png`

1) **Producer**  
Ürün stok değişimlerini simüle eder ve Kafka’ya `stock_updates` topic’ine yazar.

2) **Kafka Cluster**  
3 broker (external: 9092, 9093, 9094; internal: 29092, 29093, 29094) + Zookeeper (2181). İzleme için Kafka UI kullanılır.

3) **Consumer**  
`stock_updates` mesajlarını okur ve MongoDB’ye idempotent şekilde yazar (`_id = {topic}-{partition}-{offset}`). Koleksiyonlar: `inventory.stock_events`, `inventory.stock_logs`, `inventory.products`, `inventory.product_info`.

4) **MongoDB Atlas**  
Global erişilebilir, güvenli bağlantı (IP allowlist + kullanıcı/parola). Opsiyonel yerel container ileride eklenebilir.

5) **Airflow**  
Orkestrasyon: gerçek zaman veriye dayalı özet/rapor ve Spark job tetikleme DAG’leri. Web arayüzü: http://localhost:8082

6) **FastAPI**  
REST + OpenAPI dokümantasyonu. Dashboard bu katmandan veri tüketir.

7) **Streamlit Dashboard**  
Gerçek zaman envanter ve metrik görselleştirme. Web: http://localhost:8501

8) **Spark Structured Streaming**  
`stock_streaming.py` ile Kafka’dan mikro-batch / continuous processing; özetler için HDFS / Mongo sink hazırlıkları.

9) **HDFS / HDFS Yazma**  
`hdfs_spark.py` & `write_hdfs_summary_dag.py` üzerinden stok olaylarından günlük özetlerin HDFS'e aktarımı (PLACEHOLDER: detaylı kullanım dokümantasyonu eklenecek).

10) **Gözlemleme Araçları**  
Kafka UI (topic & consumer lag), Portainer (container yönetimi). Gelecekte Prometheus + Grafana.

11) **LLM / Agents (Opsiyonel)**  
`agents/stock_agent.py` ile ileri seviye sorgu zincirleri (PLACEHOLDER: örnek kullanım).

---

## 🌐 Servis & Port Haritası
- Zookeeper: 2181
- Kafka broker’ları: 9092, 9093, 9094 (external) / 29092, 29093, 29094 (internal)
- Kafka UI: 8080
- Airflow Web: 8082 (container içi 8080 mapping)
- FastAPI: 8000
- Streamlit: 8501
- Portainer: 9000

---

## 🧩 Kafka Topic Stratejisi
- Topic: `stock_updates`
- Partition: 3 (yük dengeleme & paralel tüketim)
- Replication Factor: 3 (yüksek erişilebilirlik)  
> PLACEHOLDER: Topic creation screen shot — `docs/images/topic-create.png`

---

## 🗄️ MongoDB Şema & Indexler
Database: `inventory`

| Koleksiyon | Amaç | Önemli Alanlar | Index |
|------------|------|----------------|-------|
| `stock_events` | Ham olay | `_id`, `product_id`, `delta`, `ts` | `_id` PK, `product_id` (opsiyonel) |
| `stock_logs` | Ayrıntılı log | `event_id`, `ts`, `source` | `ts` desc |
| `products` | Anlık stok durumu | `product_id`, `quantity`, `updated_at` | `product_id` unique |
| `product_info` | Ürün meta | `product_id`, `name`, `category` | `product_id` unique |

> PLACEHOLDER: MongoDB collection screen — `docs/images/mongo-collections.png`

---

## ⚙️ Hızlı Başlangıç

Önkoşullar:
- Docker Desktop (çalışır durumda)
- Python 3.10+ (producer & consumer’ı lokalde çalıştıracaksanız)

1) `.env` oluştur (`real-time-stock-tracker/.env`):
```env
MONGO_DB_USERNAME=your_user
MONGO_DB_PASSWORD=your_password
MONGO_DB_HOST=your-cluster.mongodb.net
API_URL=http://localhost:8000

# Opsiyonel özellikler
ENABLE_GROQ=false
```  
> PLACEHOLDER: .env example screenshot — `docs/images/env-file.png`

2) Docker altyapısını başlat (PowerShell):
```powershell
cd real-time-stock-tracker\docker
docker compose up -d
```

3) Topic kontrolü:
- http://localhost:8080 → Clusters → Topics → `stock_updates`


1) Doğrulama:
- Kafka UI: http://localhost:8080
- FastAPI Swagger: http://localhost:8000/docs
- Streamlit: http://localhost:8501
- Airflow: http://localhost:8082 (admin/admin)
- Portainer: http://localhost:9000

> MongoDB Atlas kullanılmakta: IP allowlist & kullanıcı yetkilerini kontrol edin.

---

## 📁 Klasör Yapısı (Özet)
```text
real-time-stock-tracker/
   docker/
      docker-compose.yml
   producer/
      producer.py  requirements.txt
   consumer/
      consumer.py  requirements.txt
   fastapi-app/
      app_fastapi.py  Dockerfile  requirements.txt
   streamlit-app/
      app.py  Dockerfile  requirements.txt
   airflow/
      Dockerfile  dags/*.py
   spark_jobs/
      stock_streaming.py  aggregations.py  alerts.py  schemas.py
   agents/
      stock_agent.py  query_chain.py
   tools/
      mongo_tool.py
   hdfs_spark.py (HDFS entegrasyonu)
```

> PLACEHOLDER: Repository tree screenshot — `docs/images/repo-tree.png`

---

## 🧪 Airflow DAG’leri
| DAG | Amaç | Frekans | Not |
|-----|------|---------|-----|
| `hello_dag.py` | Örnek / sağlık kontrolü | Dakikalık | Basit print task |
| `kafka_producer_dag.py` | Producer tetikleme (opsiyonel) | Dakikalık / manuel | Lokal script entegrasyonu |
| `kafka_consumer_dag.py` | Consumer kontrol / tetikleme | Dakikalık / manuel | Lag gözlemine uyarlanabilir |
| `spark_streaming_submit_dag.py` | Spark job submit | Manuel / periyodik | Structured Streaming başlatma |
| `stream_summary_dag.py` | Akış özet metrik üretimi | Dakikalık | Kafka → Özet dokümantasyon |
| `write_hdfs_summary_dag.py` | HDFS’e özet yazımı | Günlük | HDFS sink |
| `report_generation.py` | Rapor PDF/CSV üretimi | Günlük | Metrik derleme |

> PLACEHOLDER: Airflow UI screenshot — `docs/images/airflow-ui.png`

---

## 🔥 Spark & HDFS Entegrasyonu
- `spark_streaming_submit_dag.py` DAG’i, `spark_jobs/stock_streaming.py` script’ini tetikler.
- HDFS yazımı için: `write_hdfs_summary_dag.py` + `hdfs_spark.py` (Kafka’dan gelen olayların günlük agregasyonu).  
> PLACEHOLDER: Spark job run log screenshot — `docs/images/spark-run.png`

Gelecek adımlar: Spark cluster (master/worker) container’ları, checkpoint directory stratejisi, schema evolution.

---

## 🔌 API & Dashboard
- FastAPI endpoint’leri: `fastapi-app/app_fastapi.py` (OpenAPI docs: `/docs`)  
- Streamlit: `streamlit-app/app.py` → `API_URL` env ile FastAPI bağlantısı.  
> PLACEHOLDER: FastAPI docs screenshot — `/real-time-stock-tracker/docs/images/fastapi-docs.png`  
> PLACEHOLDER: Streamlit dashboard screenshot — `docs/images/streamlit-dashboard.png`

---

## 🧯 Sorun Giderme
- Kafka UI bağlanmıyor: 3 broker container’larının ayakta olduğundan emin olun; network alias’ları doğru mu?
- MongoDB bağlantı hatası: Atlas kullanıcı bilgileri + IP allowlist + `.env` doğrula.
- Sanal ortam aktivasyonu (PowerShell): `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
- Port çakışması: 8080/8082/8000/8501/9000 kullanan başka servisleri kapatın.
- Airflow DAG görünmüyor: Dosya adı, `.py` uzantısı ve `dag_id` tanımı kontrol edin, container yeniden başlatın.

> PLACEHOLDER: Error log screenshot — `docs/images/error-log.png`

---


## 🖼️ Ekran Görüntüsü Yerleri (Placeholders)
| Açıklama | Dosya Yolu Önerisi | Not |
|----------|--------------------|------|
| Mimari Diyagram | `docs/images/architecture.png` | Genel akış |
| Topic Oluşturma | `docs/images/topic-create.png` | Kafka UI |
| Mongo Koleksiyon Görünümü | `docs/images/mongo-collections.png` | Atlas |
| Repository Tree | `docs/images/repo-tree.png` | Güncel klasör yapısı |
| Airflow UI | `docs/images/airflow-ui.png` | DAG listesi |
| Spark Çalışma Logu | `docs/images/spark-run.png` | Streaming submit |
| FastAPI Docs | `docs/images/fastapi-docs.png` | Swagger |
| Streamlit Dashboard | `docs/images/streamlit-dashboard.png` | Metrikler |
| HDFS Output | `docs/images/hdfs-output.png` | Günlük özet dosyası |
| Hata Logu | `docs/images/error-log.png` | Sorun giderme |

--

## 📄 Lisans / Kullanım
Tamamen açık kaynaklıdır. Emirhan AKSU tarafından geliştirilmiştir. Ticari olmayan projelerde serbestçe kullanılabilir.

---


### Teşekkürler 🙌
Sorular için: https://www.linkedin.com/in/emirhan-aksu/.


