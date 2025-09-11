# Kafka producer kodunuzu buraya taşıyın.
from kafka import KafkaProducer
import json, time, random
from datetime import datetime

# Ürünler (genişletilmiş)
PRODUCTS = {
	"SKU123": {"name": "Laptop", "stock": 50, "category": "Electronics", "supplier": "Teknosa"},
	"SKU456": {"name": "Headphones", "stock": 120, "category": "Electronics", "supplier": "MediaMarkt"},
	"SKU789": {"name": "Mouse", "stock": 80, "category": "Accessories", "supplier": "Vatan"},
	"SKU012": {"name": "Desk Lamp", "stock": 60, "category": "Home", "supplier": "IKEA"},
	"SKU999": {"name": "Notebook", "stock": 200, "category": "Stationery", "supplier": "D&R"}
}

WAREHOUSES = ["IST-WH-01", "ANK-WH-02", "IZM-WH-03"]
CITIES = {"IST-WH-01": "Istanbul", "ANK-WH-02": "Ankara", "IZM-WH-03": "Izmir"}
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
	city = CITIES[warehouse]

	# Yeni stok hesapla (minimum 0)
	new_stock = max(0, product["stock"] + delta)
	real_delta = new_stock - product["stock"]  # Gerçek delta (stok -3 istendi ama -1 düştü)
	product["stock"] = new_stock  # Güncelle

	event = {
		"event_type": "stock_update",
		"product_id": product_id,
		"product_name": product["name"],
		"category": product["category"],
		"supplier": product["supplier"],
		"delta": real_delta,
		"new_stock": new_stock,
		"warehouse_id": warehouse,
		"city": city,
		"updated_by": source,
		"ts": datetime.utcnow().isoformat() + "Z"
	}

	producer.send("stock_updates", key=product_id, value=event)
	producer.flush()
	print("Sent:", event)
	time.sleep(random.uniform(0, 2))  # 0-2 saniye arasında rastgele bekle
# Kafka producer kodunuzu buraya taşıyın.
