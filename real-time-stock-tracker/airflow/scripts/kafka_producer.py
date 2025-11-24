from kafka import KafkaProducer
import json, time, random, uuid, os
from datetime import datetime

# Ürünler (genişletilmiş)
PRODUCTS = {
    "SKU123": {"name": "Laptop", "stock": 50, "category": "Electronics", "supplier": "Teknosa","unit_price": 16000,"critical_threshold":10},
    "SKU456": {"name": "Headphones", "stock": 120, "category": "Electronics", "supplier": "MediaMarkt","unit_price": 2000,"critical_threshold":15},
    "SKU789": {"name": "Mouse", "stock": 80, "category": "Accessories", "supplier": "Vatan","unit_price": 500,"critical_threshold":5},
    "SKU012": {"name": "Desk Lamp", "stock": 60, "category": "Home", "supplier": "IKEA","unit_price": 1500,"critical_threshold":8},
    "SKU999": {"name": "Notebook", "stock": 200, "category": "Stationery", "supplier": "D&R","unit_price": 12000,"critical_threshold":30}
}

WAREHOUSES = ["IST-WH-01", "ANK-WH-02", "IZM-WH-03"]
CITIES = {"IST-WH-01": "Istanbul", "ANK-WH-02": "Ankara", "IZM-WH-03": "Izmir"}
EVENT_SOURCES = ["checkout", "restock", "damaged", "admin_adjustment","transfer","return"]
USER_TYPES = ["admin", "customer","supplier"]
SOURCE_SYSTEMS = ["web","mobile_app","pos_system"]
DEVICES = ["Windows-PC", "iPhone-14", "Android-Tablet", "Linux-Server"]
BATCH_IDS = [f"BATCH-{datetime.utcnow().strftime('%Y%m%d')}-{i}" for i in range(1, 6)]

# Container ağına uygun bootstrap'ı ENV'den oku; yoksa kafka service isimlerini kullan
bootstrap_env = os.getenv("KAFKA_BOOTSTRAP")
if bootstrap_env:
    BOOTSTRAP_SERVERS = [s.strip() for s in bootstrap_env.split(",") if s.strip()]
else:
    BOOTSTRAP_SERVERS = ["kafka:29092", "kafka2:29093", "kafka3:29094"]

TOPIC = os.getenv("KAFKA_TOPIC", "stock_updates")

producer = KafkaProducer(
    bootstrap_servers=BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    key_serializer=str.encode,
    linger_ms=50,
    retries=3,
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

print(f"Producing to {BOOTSTRAP_SERVERS} topic={TOPIC}")
while True:
    product_id = random.choice(list(PRODUCTS.keys()))
    product = PRODUCTS[product_id]
    operation_type = random.choice(EVENT_SOURCES)
    delta = get_delta(operation_type)
    warehouse = random.choice(WAREHOUSES)
    city = CITIES[warehouse]

    user_id = f"user_{random.randint(1,100)}"
    user_type = random.choice(USER_TYPES)
    source_system = random.choice(SOURCE_SYSTEMS)
    device_info = random.choice(DEVICES)
    ip_address = f"192.168.{random.randint(0,255)}.{random.randint(1,254)}"
    batch_id = random.choice(BATCH_IDS)
 
    stock_before = product["stock"]
    new_stock = max(0, stock_before + delta)
    real_delta = new_stock - stock_before  # Gerçek delta (stok -3 istendi ama -1 düştü)
    product["stock"] = new_stock  # Güncelle
    unit_price = product.get("unit_price", 0)
    total_value = new_stock * unit_price
    critical_threshold = product.get("critical_threshold", 10)
    is_critical = new_stock < critical_threshold

    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp" : datetime.utcnow().isoformat() + "Z",
        "product_id": product_id,
        "product_name": product["name"],
        "category": product["category"],
        "supplier": product["supplier"],
        "stock_before": stock_before,
        "unit_price" : unit_price,
        "total_value": total_value,
        "user_id": user_id,
        "user_type": user_type,
        "operation_type": operation_type,
        "source_system": source_system,
        "device_info": device_info,
        "ip_address": ip_address,
        "critical_threshold": critical_threshold,
        "is_critical": is_critical,
        "batch_id": batch_id,
        "delta": real_delta,
        "new_stock": new_stock,
        "warehouse_id": warehouse,
        "city": city,
        "ts": datetime.utcnow().isoformat() + "Z"
    }

    producer.send(TOPIC, key=product_id, value=event)
    producer.flush()
    print("Sent:", event)
    time.sleep(random.uniform(0, 2))  # 0-2 saniye arasında rastgele bekle
