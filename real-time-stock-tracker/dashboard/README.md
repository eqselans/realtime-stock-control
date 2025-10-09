# Dashboard Uygulamaları

Bu klasör, stok yönetim sistemi için iki farklı web uygulaması içermektedir.

## İçerik

### 1. FastAPI Backend (`app_fastapi.py`)
- **Amaç**: RESTful API servisi
- **Teknoloji**: FastAPI
- **Port**: 8000
- **Özellikler**:
  - Ürün CRUD operasyonları
  - Stok sorgulama
  - Stok geçmiş logları
  - MongoDB entegrasyonu
  - AI Agent entegrasyonu (doğal dil sorguları)
  - Swagger UI dokümantasyonu (`/docs`)

**Çalıştırma**:
```bash
cd dashboard
pip install -r requirements.txt
uvicorn app_fastapi:app --reload --host 0.0.0.0 --port 8000
```

### 2. Streamlit Dashboard (`app.py`)
- **Amaç**: Görsel dashboard ve kullanıcı arayüzü
- **Teknoloji**: Streamlit
- **Port**: 8501 (varsayılan)
- **Özellikler**:
  - Ürün listesi görüntüleme (gerçek zamanlı)
  - Stok logları takibi
  - Analitik grafikler (geliştirme aşamasında)
  - Kritik stok alarmları (geliştirme aşamasında)
  - PDF rapor oluşturma

**Çalıştırma**:
```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

## Mimari

```
┌─────────────────┐
│   Streamlit     │  (Frontend - Port 8501)
│     app.py      │
└────────┬────────┘
         │ HTTP Requests
         ↓
┌─────────────────┐
│    FastAPI      │  (Backend API - Port 8000)
│ app_fastapi.py  │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│    MongoDB      │  (Database)
│   (inventory)   │
└─────────────────┘
```

## Neden İki Uygulama?

1. **Separation of Concerns**: API mantığı ve UI mantığı ayrı tutulur
2. **Bağımsız Geliştirme**: Her iki uygulama da bağımsız olarak geliştirilebilir
3. **Ölçeklenebilirlik**: API ve frontend ayrı olarak scale edilebilir
4. **Çoklu Client Desteği**: FastAPI'ye farklı clientlar (web, mobile, diğer servisler) bağlanabilir

## Bağımlılıklar

Tüm bağımlılıklar `requirements.txt` dosyasında tanımlıdır:
- fastapi
- uvicorn
- streamlit
- pymongo
- pandas
- fpdf
- python-dotenv

## Ortam Değişkenleri

`.env` dosyasında tanımlanmalıdır:
```
MONGO_DB_USERNAME=your_username
MONGO_DB_PASSWORD=your_password
MONGO_DB_HOST=your_host
```

## Docker ile Çalıştırma

(Geliştirme aşamasında)

```yaml
# docker-compose.yml örneği
services:
  fastapi:
    build: ./dashboard
    command: uvicorn app_fastapi:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      - MONGO_DB_USERNAME=${MONGO_DB_USERNAME}
      - MONGO_DB_PASSWORD=${MONGO_DB_PASSWORD}
      - MONGO_DB_HOST=${MONGO_DB_HOST}
  
  streamlit:
    build: ./dashboard
    command: streamlit run app.py
    ports:
      - "8501:8501"
    depends_on:
      - fastapi
```

## Geliştirme Notları

- Streamlit uygulaması FastAPI'nin `localhost:8000` adresinde çalıştığını varsayar
- Production ortamında bu adres environment variable olarak yapılandırılmalıdır
- Her iki uygulama da hot-reload desteğine sahiptir (development mode)

## Sonraki Adımlar

- [ ] Analitik sekmesini tamamla
- [ ] Kritik alarm sistemi entegrasyonu
- [ ] Grafik ve visualizasyon iyileştirmeleri
- [ ] Export özelliklerini genişlet (Excel, CSV)
- [ ] Kullanıcı authentication sistemi
- [ ] Rate limiting ve güvenlik iyileştirmeleri
