"""Generic stock agent (Groq + Mongo)

Özellikler:
 - Kullanıcı sorgusundan ürün adı fuzzy olarak tespit eder (Mongo distinct listesi üzerinden)
 - Kritik stok niyeti algılar (kritik / az / düştü / threshold kelimeleri)
 - Groq kapalıysa baseline metin üretir
 - Projection optimize (gereken alanlar)
"""

import os, requests, json, re, time, difflib, datetime
from dotenv import load_dotenv
from tools.mongo_tool import MongoQueryTool

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-8b-8192")
ENABLE_GROQ = os.getenv("ENABLE_GROQ", "true").lower() == "true"

MONGO_DB_USERNAME = os.getenv("MONGO_DB_USERNAME")
MONGO_DB_PASSWORD = os.getenv("MONGO_DB_PASSWORD")
MONGO_DB_HOST = os.getenv("MONGO_DB_HOST")
MONGO_DB_APP_NAME = "emrhn-cluster"
MONGO_CONN_STR = (
    f"mongodb+srv://{MONGO_DB_USERNAME}:{MONGO_DB_PASSWORD}"
    f"@{MONGO_DB_HOST}/inventory?retryWrites=true&w=majority&appName={MONGO_DB_APP_NAME}"
)

def call_groq(prompt, temperature=0.2):
    if not ENABLE_GROQ:
        return {"disabled": True}
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "Sen bir stok takip ve envanter danışmanısın. Kısa ve net yanıt ver."},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
    except Exception as e:
        return {"error": f"request-exception: {e}"}
    if resp.status_code == 200:
        try:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return {"error": f"parse-error: {e}", "raw": resp.text[:200]}
    return {"error": f"{resp.status_code} {resp.text[:200]}"}

def parse_tool_json(text: str):
    try:
        match = re.search(r"\{\s*\"tool\".*?\}\s*", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        return None
    return None

def get_distinct_products(mongo: MongoQueryTool):
    try:
        # tools.mongo_tool MongoClient döndürmüyor; bu nedenle hızlı bir manuel erişim gerekirse
        # ileride MongoQueryTool'a distinct fonksiyonu eklenebilir. Şimdilik pymongo import edelim.
        from pymongo import MongoClient
        client = MongoClient(MONGO_CONN_STR)
        return list(client.get_database("inventory").get_collection("products").distinct("product_name"))
    except Exception:
        return []

# Ürün adı çıkarma (fuzzy match)
def infer_product(user_query: str, candidates: list[str]):
    if not candidates:
        return None, []
    # Sorgu içindeki kelimelerle fuzzy match
    tokens = re.findall(r"[A-Za-z0-9_-]+", user_query)
    lowered = [t.lower() for t in tokens]
    best = None
    best_ratio = 0.0
    for cand in candidates:
        for t in lowered:
            ratio = difflib.SequenceMatcher(None, cand.lower(), t).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best = cand
    # Ek olarak full cümle üzerinden en iyi eşleşme
    ratios = {cand: difflib.SequenceMatcher(None, cand.lower(), user_query.lower()).ratio() for cand in candidates}
    top_sentence = max(ratios, key=ratios.get) if ratios else best
    if ratios.get(top_sentence, 0) > best_ratio:
        best = top_sentence
        best_ratio = ratios[top_sentence]
    # Alternatif öneriler
    suggestions = sorted(ratios, key=ratios.get, reverse=True)[:5]
    return best if best_ratio >= 0.45 else None, suggestions

def detect_critical_intent(user_query: str):
    kw = ["kritik", "az", "düştü", "threshold", "alarm", "kritiğe", "kritiğe" ]
    return any(k in user_query.lower() for k in kw)

def run_agent(user_query: str):
    mongo = MongoQueryTool(MONGO_CONN_STR)
    products = get_distinct_products(mongo)
    product, suggestions = infer_product(user_query, products)
    is_critical_intent = detect_critical_intent(user_query)

    if not product:
        msg = {
            "status": "not_found",
            "message": "Ürün bulunamadı",
            "candidates_sample": suggestions
        }
        if ENABLE_GROQ:
            prompt = (
                f"Bilinen ürünler: {products}. Soru: '{user_query}'. Ürün bulunamadı."
                " Kullanıcıya nazikçe ürünün mevcut olmadığını ve listeden birini seçmesini öner."
            )
            model_resp = call_groq(prompt)
        else:
            model_resp = "Ürün bulunamadı. Mevcutlardan birini sorabilirsiniz: " + ", ".join(products[:5])
        return {
            "tool_call": None,
            "data": msg,
            "model_answer": model_resp
        }

    filt = {"product_name": product}
    if is_critical_intent:
        filt["is_critical"] = True
    tool_call = {
        "tool": "MongoQueryTool",
        "params": {
            "collection": "products",
            "filter": filt,
            "projection": {"product_name":1, "new_stock":1, "is_critical":1, "critical_threshold":1, "updated_at":1},
            "limit": 1
        }
    }
    result = mongo.run(tool_call["params"])

    docs = result.payload.get('docs') or []
    if not docs:
        # Ürün listede ama kayıt yok (senkron sorunu) -> kullanıcıya bildir
        msg = {
            "status": "no_document",
            "product": product,
            "message": "Ürün listede ama stok kaydı bulunamadı (henüz event gelmemiş olabilir)."
        }
        model_resp = call_groq(
            f"Ürün {product} için stok kaydı yok. Kullanıcıya bekleyebileceğini veya yeni stok eventi oluşturabileceğini söyle." 
        ) if ENABLE_GROQ else msg["message"]
        return {"tool_call": tool_call, "data": msg, "model_answer": model_resp}

    first = docs[0]
    # JSON safe copy
    def to_jsonable(v):
        from bson import ObjectId  # lazy import
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, (datetime.datetime, datetime.date)):
            return v.isoformat()
        return v
    safe_first = {k: to_jsonable(v) for k,v in first.items()}
    pn = first.get('product_name','?')
    ns = first.get('new_stock','?')
    crit = first.get('is_critical')
    ct = first.get('critical_threshold')

    if ENABLE_GROQ:
        answer_prompt = (
            "Veri:" + json.dumps(safe_first, ensure_ascii=False) + 
            "\nKullanıcı sorusu:" + user_query +
            "\nKısa ve net Türkçe yanıt ver; kritikse uyarı ekle; rakamları belirt." )
        model_answer = call_groq(answer_prompt)
    else:
        if crit:
            model_answer = f"{pn} kritik seviyede! Stok {ns} (eşik {ct})."
        else:
            model_answer = f"{pn} stok {ns}."

    return {"tool_call": tool_call, "data": result.payload, "model_answer": model_answer}

if __name__ == "__main__":
    # Kullanıcı sorusu ile agent çalıştır
    question = input("Stok sorusu: ")
    answer = run_agent(question)

    print(question)
    print("Product :", answer.get("data", {}).get("docs", [{}])[0].get("product_name"))
    print("Agent cevabı:", answer.get("model_answer"))