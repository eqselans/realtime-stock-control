from kafka import KafkaConsumer
import json, os, time
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
from datetime import datetime
import traceback

load_dotenv()

MONGO_DB_USERNAME = os.getenv("MONGO_DB_USERNAME")
MONGO_DB_PASSWORD = os.getenv("MONGO_DB_PASSWORD")
MONGO_DB_HOST = os.getenv("MONGO_DB_HOST")
MONGO_DB_APP_NAME = "emrhn-cluster"

uri = (
    f"mongodb+srv://{MONGO_DB_USERNAME}:{MONGO_DB_PASSWORD}"
    f"@{MONGO_DB_HOST}/?retryWrites=true&w=majority&appName={MONGO_DB_APP_NAME}"
)


client = MongoClient(uri, server_api=ServerApi('1'))
db = client["inventory"]
collection = db["stock_events"]
stock_logs = db["stock_logs"]      # geçmiş loglar
products = db["products"]          # güncel stok durumu
product_info = db["product_info"]  # sabit ürün bilgisi

db.stock_logs.create_index([("ts", -1)])
db.products.create_index("product_id", unique=True)
db.product_info.create_index("product_id", unique=True)

# Bootstrap sunucularını container ağına uygun biçimde al
bootstrap_env = os.getenv("KAFKA_BOOTSTRAP")
if bootstrap_env:
    BOOTSTRAP_SERVERS = [s.strip() for s in bootstrap_env.split(",") if s.strip()]
else:
    # Varsayılan olarak TÜM broker'ları listele (metadata erişimi daha stabil)
    BOOTSTRAP_SERVERS = ["kafka:29092", "kafka2:29093", "kafka3:29094"]

KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "stock_updates")
GROUP_ID = os.getenv("KAFKA_GROUP", "stock-consumer")
FORCE_NEW_GROUP = os.getenv("FORCE_NEW_GROUP", "true").lower() == "true"
if FORCE_NEW_GROUP:
    # Zaman damgası ile yeni group id => önceki offset'leri yok sayar, earliest'ten okur
    GROUP_ID = f"{GROUP_ID}-{int(time.time())}"

print(1)
print(BOOTSTRAP_SERVERS)
print(KAFKA_TOPIC)
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=BOOTSTRAP_SERVERS,
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    key_deserializer=lambda k: k.decode("utf-8") if k is not None else None,
    group_id=GROUP_ID,
    enable_auto_commit=True,
    auto_offset_reset="earliest",
    request_timeout_ms=30000,
    connections_max_idle_ms=540000,
)

print(f"[DEBUG] Bootstrap Servers: {BOOTSTRAP_SERVERS}")
print(f"[DEBUG] Topic: {KAFKA_TOPIC}")
print(f"[DEBUG] Group ID: {GROUP_ID}")
print(f"[DEBUG] Consumer bootstrap connected: {consumer.bootstrap_connected()}")
print(f"[DEBUG] Subscription: {consumer.subscription()}")
try:
    print(f"[DEBUG] Available topics: {consumer.topics()}")
    print(f"[DEBUG] Partitions for {KAFKA_TOPIC}: {consumer.partitions_for_topic(KAFKA_TOPIC)}")
except Exception:
    print("[WARN] Topic metadata alınamadı:")
    traceback.print_exc()

print(consumer)

def process_event(event: dict):
    # KeyError önlemek için .get kullan
    print(f"Received event: {event}")
    print(
        "Product ID: {pid}, New Stock: {ns}, User: {uid}, Type: {ut}, Timestamp: {ts}".format(
            pid=event.get("product_id"),
            ns=event.get("new_stock"),
            ub=event.get("updated_by"),
            uid=event.get("user_id"),
            ut=event.get("user_type"),
            ts=event.get("ts"),
        )
    )

    # 1. Geçmiş log: Her olayı ekle
    log_doc = {
        **event,
        "recieved_at": datetime.utcnow(),
        "source": "kafka_consumer",
    }
    stock_logs.insert_one(log_doc)

    # 2. Güncel stok: product_id ile upsert
    prod_doc = {
        "product_id": event.get("product_id"),
        "product_name": event.get("product_name"),
        "category": event.get("category"),
        "supplier": event.get("supplier"),
        "warehouse_id": event.get("warehouse_id"),
        "city": event.get("city"),
        "new_stock": event.get("new_stock"),
        "stock_before": event.get("stock_before"),
        "delta": event.get("delta"),
        "unit_price": event.get("unit_price"),
        "total_value": event.get("total_value"),
        "critical_threshold": event.get("critical_threshold"),
        "is_critical": event.get("is_critical"),
        "last_update": event.get("timestamp"),
        "user_id": event.get("user_id"),
        "user_type": event.get("user_type"),
        "operation_type": event.get("operation_type"),
        "source_system": event.get("source_system"),
        "device_info": event.get("device_info"),
        "ip_address": event.get("ip_address"),
        "batch_id": event.get("batch_id"),
    }
    if prod_doc["product_id"] is not None:
        products.update_one({"product_id": prod_doc["product_id"]}, {"$set": prod_doc}, upsert=True)

    # 3. Sabit ürün bilgisi: product_info'ya sadece yeni ürün ekle
    info_doc = {
        "product_id": event.get("product_id"),
        "product_name": event.get("product_name"),
        "category": event.get("category"),
        "supplier": event.get("supplier"),
        "unit_price": event.get("unit_price"),
        "critical_threshold": event.get("critical_threshold"),
        "created_at": event.get("timestamp"),
    }
    if info_doc["product_id"] is not None:
        # Sadece yeni ürünler eklenir, varsa eklenmez
        product_info.update_one({"product_id": info_doc["product_id"]}, {"$setOnInsert": info_doc}, upsert=True)


LOOP_IDLE_LOG_INTERVAL = 30  # saniye
last_msg_ts = time.time()

try:
    while True:
        msg_pack = consumer.poll(timeout_ms=1000, max_records=10)
        if not msg_pack:
            if time.time() - last_msg_ts > LOOP_IDLE_LOG_INTERVAL:
                print("[INFO] Henüz yeni mesaj gelmedi (poll idle).")
                last_msg_ts = time.time()
            continue
        for tp, messages in msg_pack.items():
            for message in messages:
                event = message.value
                process_event(event)
                print(f"Key: {message.key} | Partition: {message.partition} | Offset: {message.offset}")
                print(f"Message timestamp(ms): {message.timestamp}")
                if event:
                    doc = {
                        **event,
                        "ts": datetime.utcnow(),
                        "source": "kafka_consumer",
                        "_id": f"{message.topic}-{message.partition}-{message.offset}",
                    }
                    collection.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
        last_msg_ts = time.time()
except KeyboardInterrupt:
    print("[INFO] Kapatma isteği alındı.")
except Exception:
    print("[ERROR] Tüketim döngüsünde hata:")
    traceback.print_exc()
finally:
    try:
        consumer.close()
    except Exception:
        pass
    client.close()
    print("Consumer closed and MongoDB client disconnected.")
