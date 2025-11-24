import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
import io
from datetime import datetime
import os
import plotly.express as px

# --- 1. Konfigürasyon ve API Ayarları ---
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Stok Yönetimi & AI Dashboard", layout="wide", page_icon="📦")

# --- 2. Gelişmiş CSS ---
st.markdown(
    """
<style>
/* Genel Ayarlar */
body, .stApp { background:#0f1116; color:#e0e6ed; font-family: 'Inter', sans-serif; }

/* Metrik Kartlar */
.metric-card { 
    background:#1c212b; padding:15px 20px; border-radius:10px; 
    border-left:5px solid #56b6c2; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
.metric-title { font-size:12px; text-transform:uppercase; letter-spacing:1px; color:#8b95a5; margin-bottom: 5px; }
.metric-value { font-size:26px; font-weight:700; color:#56b6c2; }

/* Tablo Stilleri */
.stDataFrame { border-radius:10px; overflow: hidden; }
.stDataFrame table { background-color: #1c212b !important; color: #e0e6ed !important; }
.stDataFrame table th { background-color: #2b3240 !important; color: #e0e6ed !important; border-bottom: 2px solid #56b6c2; }
.stDataFrame table tbody tr:hover { background:#2b3240 !important; }

/* AI Chat Alanı */
.chat-message { padding: 10px; border-radius: 5px; margin-bottom: 10px; }
.chat-user { background-color: #2b3240; border-left: 3px solid #56b6c2; }
.chat-bot { background-color: #1c212b; border-left: 3px solid #e06c75; }

/* İndirme Butonları Gizleme (Gereksiz tekrarları önlemek için) */
div[data-testid="stDownloadButton"]:nth-child(n+1) { display: none; }
</style>
""",
    unsafe_allow_html=True,
)

# --- 3. Sidebar: Veri Girişi ve Ayarlar ---
st.sidebar.title("⚙️ İşlemler")

# A. Ürün Ekleme / Güncelleme Formu
with st.sidebar.expander("➕ Ürün Ekle / Güncelle", expanded=False):
    with st.form("upsert_form"):
        f_id = st.text_input("Ürün ID")
        f_stock = st.number_input("Yeni Stok Adedi", min_value=0, step=1)
        f_user = st.text_input("Güncelleyen Kişi", value="admin")
        f_cat = st.selectbox("Kategori", ["Elektronik", "Giyim", "Kırtasiye", "Ev", "Aksesuar", "Diğer"])
        f_city = st.selectbox("Şehir", ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Diğer"])
        
        submitted = st.form_submit_button("Kaydet")
        
        if submitted and f_id:
            try:
                # FastAPI endpointi query parameter bekliyor
                params = {
                    "product_id": f_id,
                    "new_stock": f_stock,
                    "updated_by": f_user,
                    "category": f_cat,
                    "city": f_city
                }
                res = requests.post(f"{API_URL}/products/add", params=params)
                if res.status_code == 200:
                    st.success(f"✅ {f_id} güncellendi!")
                else:
                    st.error(f"Hata: {res.text}")
            except Exception as e:
                st.error(f"Bağlantı Hatası: {e}")

# B. Yenileme Ayarları
st.sidebar.markdown("---")
refresh_interval = st.sidebar.slider("Yenileme (sn)", 5, 60, 15)

st.title("📊 Stok Yönetimi & AI Dashboard")

# --- 4. Veri Çekme (Global) ---
@st.cache_data(ttl=5) # 5 saniyelik cache ile anlık veri hissi
def fetch_data():
    try:
        r = requests.get(f"{API_URL}/products", timeout=3)
        if r.ok:
            return pd.DataFrame(r.json())
        return pd.DataFrame()
    except:
        return pd.DataFrame()

df = fetch_data()

# Kritik Stok Mantığı (API'de yoksa biz ekleyelim)
if not df.empty:
    if "is_critical" not in df.columns:
        # Örnek kural: Stok < 20 ise kritik
        df["is_critical"] = df["new_stock"] < 20
    
    # Toplam Değer Hesabı (Eğer API dönmüyorsa simüle edelim veya 0)
    if "unit_price" not in df.columns:
        df["unit_price"] = 0 # API'de unit_price yoksa varsayılan
    if "total_value" not in df.columns:
        df["total_value"] = df["new_stock"] * df["unit_price"]

# --- 5. Sekmeler ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Ürünler", "🔍 Stok Logları", "📈 Analitik", "🤖 AI Asistan", "🚨 Kritik Stok"])

# --- TAB 1: Ürünler ---
with tab1:
    if df.empty:
        st.warning("Veri bulunamadı veya API erişilemez durumda.")
    else:
        # Metrikler
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='metric-card'><div class='metric-title'>Toplam Ürün</div><div class='metric-value'>{len(df)}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'><div class='metric-title'>Kritik Ürün</div><div class='metric-value'>{df['is_critical'].sum()}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card'><div class='metric-title'>Toplam Stok</div><div class='metric-value'>{df['new_stock'].sum():,}</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='metric-card'><div class='metric-title'>Kategoriler</div><div class='metric-value'>{df['category'].nunique()}</div></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Tablo
        def _style_crit(row):
            return ['background-color: #442626' if row.get('is_critical') else '' for _ in row]
        
        st.dataframe(df.style.apply(_style_crit, axis=1), use_container_width=True)

        # Rapor İndirme Butonları (Alt kısım)
        csv = df.to_csv(index=False).encode('utf-8')
        
        def clean_tr(text):
            if not isinstance(text, str):
                text = str(text)
            replacements = {
                "İ": "I", "ı": "i", "Ö": "O", "ö": "o",
                "Ü": "U", "ü": "u", "Ç": "C", "ç": "c",
                "Ğ": "G", "ğ": "g", "Ş": "S", "ş": "s"
            }
            for search, replace in replacements.items():
                text = text.replace(search, replace)
            return text

        # Standart PDF Başlat (Font yükleme yok)
        pdf = FPDF(orientation='L')
        pdf.add_page()
        pdf.set_font("Arial", size=10) # Standart Arial kullanıyoruz
        
        # Başlık (Türkçe karakterleri temizleyerek)
        header_txt = clean_tr(f"Stok Yonetimi Urunler Raporu - {datetime.utcnow().strftime('%Y-%m-%d')}")
        pdf.cell(0, 10, txt=header_txt, ln=True, align="C")
        
        pdf.set_font("Arial", size=7)
        
        cols = df.columns.tolist()
        col_w = 275 / (len(cols) if len(cols) > 0 else 1)

        # Tablo Başlıkları (Temizleyerek)
        for c in cols: 
            pdf.cell(col_w, 8, clean_tr(c)[:20], border=1, align='C')
        pdf.ln()

        # Veri Satırları (Temizleyerek)
        for _, r in df.iterrows():
            for c in cols: 
                # Her hücredeki veriyi clean_tr fonksiyonundan geçiriyoruz
                pdf.cell(col_w, 8, clean_tr(r[c])[:20], border=1)
            pdf.ln()
            
        pdf_buf = io.BytesIO(pdf.output(dest='S'))

        col_d1, col_d2 = st.columns([1, 5])
        col_d1.download_button("📄 PDF İndir", data=pdf_buf, file_name="stok_rapor.pdf", mime="application/pdf")
        col_d2.download_button("🧾 CSV İndir", data=csv, file_name="stok_rapor.csv", mime="text/csv")

# --- TAB 2: Loglar ---
with tab2:
    st.header("Ürün Hareket Logları")
    search_id = st.text_input("Loglarını görmek istediğiniz Ürün ID:", placeholder="Örn: SKU123")
    
    if search_id:
        try:
            r_log = requests.get(f"{API_URL}/stock_logs/{search_id}", timeout=5)
            if r_log.ok:
                df_logs = pd.DataFrame(r_log.json())
                if not df_logs.empty:
                    st.dataframe(df_logs, use_container_width=True)
                else:
                    st.info("Bu ürün için henüz log kaydı yok.")
            else:
                st.error("Loglar alınamadı.")
        except Exception as e:
            st.error(f"Hata: {e}")
    else:
        st.info("Logları görüntülemek için lütfen bir Ürün ID girin.")

# --- TAB 3: Analitik ---
with tab3:
    st.header("Stok Analitiği")
    if not df.empty:
        col_a1, col_a2 = st.columns(2)
        
        with col_a1:
            st.subheader("Kategori Bazlı Stok")
            df_cat = df.groupby("category")["new_stock"].sum().reset_index()
            fig_cat = px.pie(df_cat, values='new_stock', names='category', hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
            fig_cat.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig_cat, use_container_width=True)
            
        with col_a2:
            st.subheader("Şehirlere Göre Dağılım")
            df_city = df.groupby("city")["new_stock"].sum().reset_index()
            fig_city = px.bar(df_city, x='city', y='new_stock', color='new_stock', color_continuous_scale='Teal')
            fig_city.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig_city, use_container_width=True)
    else:
        st.info("Analiz yapılacak veri yok.")

# --- TAB 4: AI Asistan (Yeni) ---
with tab4:
    st.header("🤖 Stok Yapay Zeka Asistanı")
    st.caption("Veritabanındaki stok durumunu doğal dil ile sorgulayın.")
    
    with st.form("ai_form"):
        user_q = st.text_input("Sorunuzu yazın:", placeholder="Örn: Ankara deposunda toplam kaç ürün var?")
        ask_btn = st.form_submit_button("GROQ Agent")
    
    if ask_btn and user_q:
        with st.spinner("AI Yanıtlıyor..."):
            try:
                # FastAPI Agent Endpoint
                payload = {"question": user_q}
                res_ai = requests.post(f"{API_URL}/agent/ask", json=payload, timeout=30)
                
                if res_ai.ok:
                    data = res_ai.json()
                    answer = data.get("answer") or data.get("question") # Yapıya göre değişebilir
                    raw_data = data.get("data")
                    
                    # Cevabı Göster
                    st.markdown(f"""
                    <div class="chat-message chat-bot">
                        <b>🤖 AI:</b> {answer if answer else "İşlem tamamlandı, sonuçlar aşağıda."}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Eğer veri döndüyse tablo olarak göster
                    if raw_data:
                        st.subheader("Bulunan Veriler:")
                        if isinstance(raw_data, list):
                            st.dataframe(pd.DataFrame(raw_data), use_container_width=True)
                        elif isinstance(raw_data, dict):
                            st.json(raw_data)
                else:
                    st.error(f"AI Servis Hatası: {res_ai.status_code} - {res_ai.text}")
            except Exception as e:
                st.error(f"Bağlantı Hatası: {e}")

# --- TAB 5: Kritik Stok ---
with tab5:
    st.header("🚨 Kritik Stok Alarmları (< 20 Adet)")
    if not df.empty:
        crit_df = df[df["is_critical"] == True]
        if not crit_df.empty:
            st.error(f"Dikkat! {len(crit_df)} adet üründe stok seviyesi kritik düzeyde.")
            st.dataframe(crit_df, use_container_width=True)
            
            # Aksiyon Butonu (Örnek)
            if st.button("Otomatik Sipariş Oluştur (Demo)"):
                st.success("Tedarikçilere sipariş emirleri gönderildi! (Simülasyon)")
        else:
            st.success("Harika! Kritik seviyede ürün bulunmuyor.")
    else:
        st.info("Veri yok.")