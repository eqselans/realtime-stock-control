import streamlit as st
import requests
import pandas as pd
import time
from fpdf import FPDF
import io
import os


API_URL = os.getenv("API_URL", "http://localhost:8000")  # Allow override via env

st.set_page_config(page_title="Stok Dashboard", layout="wide")

st.title("📊 Stok Yönetimi Dashboard")

tab1, tab2, tab3, tab4 = st.tabs(["Ürünler", "Stok Logları", "Analitik", "Kritik Alarmlar"])

with tab1:
    st.header("Tüm Ürünler")
    refresh_rate = st.slider("Yenileme Sıklığı (sn)", min_value=5, max_value=60, value=10)
    placeholder = st.empty()
    pdf_buffer = None
    while True:
        resp = requests.get(f"{API_URL}/products")
        if resp.ok:
            df = pd.DataFrame(resp.json())
            placeholder.dataframe(df)
            # PDF oluştur
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            # Başlık
            pdf.cell(200, 10, txt="Ürünler Tablosu", ln=True, align="C")
            col_names = df.columns.tolist()
            pdf.set_font("Arial", size=10)
            for col in col_names:
                pdf.cell(40, 10, col, border=1)
            pdf.ln()
            for _, row in df.iterrows():
                for col in col_names:
                    pdf.cell(40, 10, str(row[col]), border=1)
                pdf.ln()
            # FPDF'in output(dest='S') çıktısı bazı sürümlerde str, bazılarında bytes/bytearray olabilir
            pdf_out = pdf.output(dest='S')
            # Çıkışı her durumda bytes'a dönüştür (bytearray/bytes/str hepsi desteklenir)
            try:
                pdf_bytes = bytes(pdf_out)
            except TypeError:
                # str ise encode et
                pdf_bytes = pdf_out.encode('latin-1')
            pdf_buffer = io.BytesIO(pdf_bytes)
        else:
            placeholder.error("Ürünler alınamadı.")
        if pdf_buffer:
            st.download_button(
                label="PDF Olarak İndir",
                data=pdf_buffer,
                file_name="urunler.pdf",
                mime="application/pdf",
                key=f"pdf_download_{int(time.time())}"
            )
        time.sleep(refresh_rate)

with tab2:
    st.header("Stok Logları")
    product_id = st.text_input("Ürün ID ile logları getir", "")
    refresh_rate2 = st.slider("Yenileme Sıklığı (sn)", min_value=5, max_value=60, value=15, key="log_refresh")
    placeholder2 = st.empty()
    while product_id:
        resp = requests.get(f"{API_URL}/stock_logs/{product_id}")
        if resp.ok:
            df = pd.DataFrame(resp.json())
            placeholder2.dataframe(df)
        else:
            placeholder2.error("Loglar alınamadı.")
        time.sleep(refresh_rate2)

with tab3:
    st.header("Analitik (Şehir/Kategori)")
    st.info("Bu sekmede FastAPI'den analitik endpointleri eklenirse gösterilebilir.")
    refresh_rate3 = st.slider("Yenileme Sıklığı (sn)", min_value=5, max_value=60, value=20, key="analytics_refresh")
    placeholder3 = st.empty()
    # Example placeholder for future analytics endpoints

with tab4:
    st.header("Kritik Stok Alarmlar")
    st.info("Kritik stok endpointi eklenirse burada gösterilebilir.")
    refresh_rate4 = st.slider("Yenileme Sıklığı (sn)", min_value=5, max_value=60, value=30, key="alert_refresh")
    placeholder4 = st.empty()
    # Example placeholder for future alerts endpoints
