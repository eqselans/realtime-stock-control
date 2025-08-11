from kafka import KafkaProducer
import json, time, random
from datetime import datetime

# Başlangıç stokları
PRODUCTS = {
    "SKU123": {"name": "Laptop", "stock": 50},
    "SKU456": {"name": "Headphones", "stock": 120},
    "SKU789": {"name": "Mouse", "stock": 80}
}

WAREHOUSES = ["IST-WH-01", "ANK-WH-02", "IZM-WH-03"]
EVENT_SOURCES = ["checkout", "restock", "damaged", "admin_adjustment"]

producer = KafkaProducer(
    bootstrap_servers=["localhost:9092", "localhost:9093", "localhost:9094"],
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    key_serializer=str.encode
)

def get_delta(source):
    if source == "checkout":
        return -random.randint(1, 5)
    elif source == "restock":
        return random.randint(5, 20)
    elif source == "damaged":
        return -random.randint(1, 3)
    elif source == "admin_adjustment":
        return random.randint(-5, 5)
    return 0

while True:
    product_id = random.choice(list(PRODUCTS.keys()))
    product = PRODUCTS[product_id]
    source = random.choice(EVENT_SOURCES)
    delta = get_delta(source)
    warehouse = random.choice(WAREHOUSES)

    # Yeni stok hesapla (minimum 0)
    new_stock = max(0, product["stock"] + delta)
    real_delta = new_stock - product["stock"]  # Gerçek delta (örneğin stok -3 istendi ama -1 düştü)
    product["stock"] = new_stock  # Güncelle

    event = {
        "event_type": "stock_update",
        "product_id": product_id,
        "delta": real_delta,
        "new_stock": new_stock,
        "warehouse_id": warehouse,
        "updated_by": source,
        "ts": datetime.utcnow().isoformat() + "Z"
    }

    producer.send("stock_updates", key=product_id, value=event)
    producer.flush()
    print("Sent:", event)
    time.sleep(random.uniform(0.1, 0.5))  # 0.1 ila 0.5 saniye arasında rastgele bekleme