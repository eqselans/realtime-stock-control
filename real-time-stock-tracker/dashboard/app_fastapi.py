from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv

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


app = FastAPI(
    title="Stock API",
    description="""
    <b>Stok Yönetimi API</b><br>
    Bu API ile ürün ekleme, güncelleme, stok sorgulama ve geçmiş loglara erişim sağlayabilirsiniz.<br>
    <ul>
      <li>Gerçek zamanlı stok takibi</li>
      <li>MongoDB ile tam entegrasyon</li>
      <li>Swagger üzerinden test ve dokümantasyon</li>
    </ul>
    """,
    version="1.0.0",
    contact={
        "name": "Eqselans Data Team",
        "url": "https://github.com/eqselans/realtime-stock-control",
        "email": "info@eqselans.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    },
    openapi_tags=[
        {"name": "Ürün", "description": "Ürün ekleme, güncelleme ve sorgulama işlemleri."},
        {"name": "Stok Logları", "description": "Ürün geçmiş stok hareketleri."}
    ]
)



class Product(BaseModel):
    product_id: str
    new_stock: int
    updated_by: str
    category: Optional[str] = None
    city: Optional[str] = None


@app.get("/products/{product_id}", summary="Ürün detayını getir", tags=["Ürün"], response_model=Product, responses={
    200: {"description": "Ürün bulundu", "content": {"application/json": {"example": {"product_id": "123", "new_stock": 50, "updated_by": "admin", "category": "elektronik", "city": "istanbul"}}}},
    404: {"description": "Ürün bulunamadı"}
})
def get_product(product_id: str):
    """Belirtilen ürünün detaylarını getirir."""
    prod = db["products"].find_one({"product_id": product_id}, {"_id": 0})
    if prod:
        return prod
    return {"error": "Ürün bulunamadı"}


# JSON yerine parametre ile ürün ekleme/güncelleme
from fastapi import Query


@app.post("/products/add", summary="Yeni ürün ekle/güncelle (parametre ile)", tags=["Ürün"], responses={
    200: {"description": "Başarılı ekleme/güncelleme", "content": {"application/json": {"example": {"result": "Başarılı", "product": {"product_id": "123", "new_stock": 50, "updated_by": "admin", "category": "elektronik", "city": "istanbul"}}}}}
})
def upsert_product_param(
    product_id: str = Query(..., description="Ürün ID"),
    new_stock: int = Query(..., description="Yeni stok miktarı"),
    updated_by: str = Query(..., description="Güncelleyen kişi"),
    category: str = Query(None, description="Kategori"),
    city: str = Query(None, description="Şehir")
):
    """Parametre ile yeni ürün ekler veya günceller."""
    prod = {
        "product_id": product_id,
        "new_stock": new_stock,
        "updated_by": updated_by,
        "category": category,
        "city": city
    }
    db["products"].update_one({"product_id": product_id}, {"$set": prod}, upsert=True)
    return {"result": "Başarılı", "product": prod}


@app.get("/products", summary="Tüm ürünleri getir", tags=["Ürün"], response_model=list[Product], responses={
    200: {"description": "Tüm ürünler listelendi", "content": {"application/json": {"example": [{"product_id": "123", "new_stock": 50, "updated_by": "admin", "category": "elektronik", "city": "istanbul"}]}}}
})
def list_products():
    """Tüm ürünleri listeler."""
    return list(db["products"].find({}, {"_id": 0}))


@app.get("/stock_logs/{product_id}", summary="Ürün geçmiş loglarını getir", tags=["Stok Logları"], responses={
    200: {"description": "Ürün geçmiş logları", "content": {"application/json": {"example": [{"product_id": "123", "new_stock": 40, "updated_by": "admin", "category": "elektronik", "city": "istanbul", "ts": "2025-09-12T12:00:00"}]}}}
})
def get_stock_logs(product_id: str):
    """Belirtilen ürünün geçmiş stok hareketlerini getirir."""
    logs = list(db["stock_logs"].find({"product_id": product_id}, {"_id": 0}))
    return logs

@app.get("/docs", include_in_schema=True)
def custom_swagger():
    from fastapi.openapi.docs import get_swagger_ui_html
    return get_swagger_ui_html(openapi_url=app.openapi_url, title=app.title + " - Swagger UI")
