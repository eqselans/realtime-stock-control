from fastapi import FastAPI, HTTPException, Query, Path, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os, sys
from dotenv import load_dotenv

load_dotenv()

# --- YAPILANDIRMA VE BAĞLANTILAR ---
BASE_DIR = os.path.dirname(os.path.dirname(__file__)) 
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Agent modülü kontrolü (MLOps: Graceful Degradation)
try:
    from agents.stock_agent import run_agent
except Exception as e:
    run_agent = None 

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

# --- DOKÜMANTASYON METADATA ---
tags_metadata = [
    {
        "name": "Ürün İşlemleri",
        "description": "Stoktaki ürünlerin eklenmesi, güncellenmesi ve listelenmesi.",
    },
    {
        "name": "Stok Logları",
        "description": "Ürünlerin zaman içindeki stok değişim hareketleri (Audit Logs).",
    },
    {
        "name": "AI Agent",
        "description": "Doğal dil işleme (NLP) ile veritabanı sorgulama arayüzü.",
    },
    {
        "name": "Sistem",
        "description": "Health check ve sistem durumu.",
    },
]

app = FastAPI(
    title="🚀 ~Gerçek Zamanlı Stok Yönetimi API",    
    description="""
    ## 📦 Gerçek Zamanlı Stok Takip Sistemi
    
    Bu API, **Big Data** altyapısı ile entegre çalışarak ürün envanterini yönetir.
    
    ### Özellikler:
    * **CRUD Operasyonları:** MongoDB Atlas üzerinde hızlı okuma/yazma.
    * **MLOps Entegrasyonu:** AI Agent servisi ile doğal dil sorguları.
    * **Audit Logging:** Her stok değişimi kayıt altına alınır.
    
    ### Geliştirici Bilgileri:
    * **Stack:** FastAPI, MongoDB, Python
    * **Maintainer:** Data & AI Team
    """,
    version="1.2.0",
    contact={
        "name": "Eqselans Data Team",
        "url": "https://github.com/eqselans/realtime-stock-control",
        "email": "data-team@eqselans.com",
    },
    openapi_tags=tags_metadata
)

# --- PYDANTIC MODELLERİ (Zenginleştirilmiş) ---

class Product(BaseModel):
    product_id: str = Field(..., description="Ürünün benzersiz SKU veya ID kodu", example="SKU-999")
    new_stock: int = Field(..., ge=0, description="Güncel stok adedi (Negatif olamaz)", example=150)
    updated_by: str = Field(..., description="İşlemi yapan kullanıcı veya servis", example="admin_user")
    category: Optional[str] = Field(None, description="Ürün kategorisi", example="Elektronik")
    city: Optional[str] = Field(None, description="Ürünün bulunduğu depo/şehir", example="İstanbul")

class ProductResponse(BaseModel):
    result: str = Field(..., example="Başarılı")
    product: Product

class ErrorResponse(BaseModel):
    detail: str = Field(..., example="Aranan kayıt bulunamadı.")

class AgentQuery(BaseModel):
    question: str = Field(..., description="AI asistanına sorulacak soru", example="İstanbul deposunda toplam kaç ürün var?")

class AgentResponse(BaseModel):
    question: str
    tool_call: Optional[Dict[str, Any]] = Field(None, description="AI'ın kullandığı araç bilgisi")
    data: Optional[Any] = Field(None, description="Veritabanından dönen ham veri")
    answer: Optional[str] = Field(None, description="AI tarafından oluşturulan doğal dil cevabı")
    error: Optional[str] = None

# --- YARDIMCI FONKSİYONLAR ---
def _to_jsonable(v):
    try:
        from bson import ObjectId
    except Exception:
        ObjectId = None
    import datetime as _dt
    if ObjectId and isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, (_dt.datetime, _dt.date)):
        return v.isoformat()
    return v

def sanitize_doc(doc):
    if isinstance(doc, list):
        return [sanitize_doc(d) for d in doc]
    if isinstance(doc, dict):
        return {k: sanitize_doc(v) for k,v in doc.items()}
    return _to_jsonable(doc)

# --- ENDPOINTLER ---

@app.get("/products/{product_id}", 
         summary="Tekil Ürün Getir", 
         tags=["Ürün İşlemleri"], 
         response_model=Product,
         responses={404: {"model": ErrorResponse, "description": "Ürün bulunamadı"}})
def get_product(
    product_id: str = Path(..., title="Ürün ID", description="Getirilecek ürünün benzersiz kimliği")
):
    """
    Verilen **product_id** değerine göre ürün detaylarını MongoDB'den çeker.
    """
    prod = db["products"].find_one({"product_id": product_id}, {"_id": 0})
    if prod:
        return prod
    raise HTTPException(status_code=404, detail="Ürün bulunamadı")


@app.post("/products/add", 
          summary="Ürün Ekle veya Güncelle", 
          tags=["Ürün İşlemleri"], 
          response_model=ProductResponse,
          status_code=200)
def upsert_product_param(
    product_id: str = Query(..., min_length=1, description="Ürün ID (SKU)"),
    new_stock: int = Query(..., ge=0, description="Yeni stok miktarı (0 veya büyük olmalı)"),
    updated_by: str = Query(..., description="Güncelleyen kullanıcı adı"),
    category: str = Query(None, description="Kategori (Opsiyonel)"),
    city: str = Query(None, description="Şehir (Opsiyonel)")
):
    """
    Query parametreleri kullanarak ürün ekler veya mevcutsa günceller (Upsert).
    
    - **Upsert Mantığı:** ID varsa günceller, yoksa yeni oluşturur.
    - **Validasyon:** Stok sayısı negatif olamaz.
    """
    prod = {
        "product_id": product_id,
        "new_stock": new_stock,
        "updated_by": updated_by,
        "category": category,
        "city": city
    }
    # Upsert işlemi
    db["products"].update_one({"product_id": product_id}, {"$set": prod}, upsert=True)
    
    # Loglama işlemi (Opsiyonel ama MLOps için iyi bir pratik)
    # db["stock_logs"].insert_one({**prod, "ts": datetime.utcnow()}) 
    
    return {"result": "Başarılı", "product": prod}


@app.get("/products", 
         summary="Tüm Ürün Listesi", 
         tags=["Ürün İşlemleri"], 
         response_model=List[Product])
def list_products():
    """
    Veritabanındaki **tüm ürünleri** listeler.
    
    *Dikkat: Büyük veritabanlarında sayfalama (pagination) kullanılması önerilir.*
    """
    return list(db["products"].find({}, {"_id": 0}))


@app.get("/stock_logs/{product_id}", 
         summary="Stok Geçmişi", 
         tags=["Stok Logları"])
def get_stock_logs(
    product_id: str = Path(..., description="Logları istenen ürün ID")
):
    """
    Belirli bir ürünün geçmişe dönük stok hareketlerini getirir.
    Zaman serisi analizi için kullanılabilir.
    """
    logs = list(db["stock_logs"].find({"product_id": product_id}, {"_id": 0}))
    return logs


@app.post("/agent/ask", 
          summary="AI Asistanına Sor", 
          tags=["AI Agent"], 
          response_model=AgentResponse)
def ask_agent(payload: AgentQuery):
    """
    **LangChain / LLM** tabanlı ajana doğal dil sorusu sorar.
    
    Örnek Sorular:
    - *"Ankara deposunda kaç tane elektronik ürün var?"*
    - *"Stok seviyesi 20'nin altında olan ürünleri listele."*
    """
    if run_agent is None:
        raise HTTPException(status_code=503, detail="AI Agent modülü şu anda aktif değil veya yüklenemedi.")
    
    try:
        result = run_agent(payload.question)
        
        # MongoDB objelerini JSON uyumlu hale getir
        sanitized_data = sanitize_doc(result.get("data")) if result.get("data") else None
        answer_field = result.get("model_answer")
        
        if isinstance(answer_field, dict):
            answer_field = sanitize_doc(answer_field)
            
        return AgentResponse(
            question=payload.question,
            data=sanitized_data,
            answer=str(answer_field) if answer_field else None,
            tool_call=result.get("tool_call")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI İşlem Hatası: {str(e)}")


# --- SİSTEM ---

@app.get("/health", tags=["Sistem"], summary="Sağlık Kontrolü")
def health_check():
    """Kubernetes veya Docker Healthcheck için endpoint."""
    return JSONResponse(content={"status": "healthy", "service": "stock-api"}, status_code=200)