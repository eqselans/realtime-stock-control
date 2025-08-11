# Realtime Stock Control System 📦⚡

Bu proje, Kafka ile gerçek zamanlı stok verilerini işleyip MongoDB'ye kaydeden bir **Realtime Stock Control System**'dir.  
Mimari, **Producer → Kafka Cluster → Consumer → MongoDB** akışı üzerine kuruludur.

---

## 📌 Mimarinin Genel Görünümü

1. **Producer**  
   - Ürün stok değişimlerini simüle eden Python script’i.
   - Kafka’ya `stock_updates` isimli topic üzerinden veri gönderir.

2. **Kafka Cluster**  
   - 3 broker’lı (9092, 9093, 9094 portlarında çalışan) yapı.
   - **Zookeeper** ile cluster koordinasyonu.
   - `provectuslabs/kafka-ui` ile broker, topic ve consumer’ların izlenmesi.

3. **Consumer**  
   - Kafka’dan gelen mesajları alır.
   - Verileri işleyip MongoDB’ye yazar.
   - İdempotent kayıt için `_id=topic-partition-offset` yapısı kullanılır.

4. **MongoDB**  
   - `inventory` database altında `stock_events` koleksiyonunda stok kayıtları tutulur.
   - Her kayıt, zaman damgası (`ts`) ve veri kaynağı bilgisi (`source`) içerir.

---


Kafka Broker, Topic ve Consumerların izlenmesi için <b>provectuslabs/kafka-ui</b> docker imajı kullanıldı.
<img width="100%" height="100%" alt="image" src="https://github.com/user-attachments/assets/0f71fe7f-4100-4c37-b116-15f029c23ae4" />


Mongo DB üzerinde Kafka'dan gelen verilerden product_id filtresi ve azalan zaman sıralamalı sorgu:
<img width="100%" height="100%" alt="image" src="https://github.com/user-attachments/assets/79d6c124-af61-4584-80ec-cfb8c92b2d3f" />


