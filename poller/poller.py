import requests
import json
from datetime import datetime
import time
import os

# --- CONFIGURACIÓN ---
CATEGORY_ID = "9562" # Relojes
REFERENCE_PRICES = {
    "Rolex": 4000, "Omega": 2500, "Breitling": 2200, "Hublot": 4500,
    "Patek Philippe": 15000, "Audemars Piguet": 12000, "Vacheron Constantin": 8000,
    "Jaeger-LeCoultre": 4000, "IWC": 3000, "Panerai": 3500, "Cartier": 2500,
    "Tudor": 2000, "Zenith": 3000, "Tag Heuer": 1000, "Longines": 800,
    
    # Modelos Específicos (para detección cruzada)
    "Submariner": 7000, "Daytona": 12000, "Speedmaster": 3000, "Seamaster": 2500,
    "Nautilus": 20000, "Royal Oak": 15000, "Tank": 1500, "Santos": 3000,
    "Black Bay": 2200, "Carrera": 1500, "Monaco": 3000,
    
    # Gama Media / Entrada (para volumen)
    "Seiko": 200, "Tissot": 250, "Hamilton": 400, "Citizen": 150
}
TARGET_KEYWORDS = list(REFERENCE_PRICES.keys())
POLL_INTERVAL_MINUTES = 20

SUSPICIOUS_KEYWORDS = [
    # Falsificaciones
    "réplica", "replica", "clon", "imitación", "imitacion", "1:1", "AAA", 
    "repro", "copia", "falso", "fake", "tipo rolex", "estilo rolex", "superclon",
    
    # Estado / Origen dudoso
    "sin papeles", "sin documentación", "perdida", "perdido", "herencia", "regalo", 
    "urge", "urgente", "sin caja", "bloqueado", "encontrado", 
    
    # Modus Operandi Estafa
    "solo whatsapp", "contactar por", "6*", "7*", # Intentos de sacar del chat
    "bizum", "transferencia", "envío gratis", "pago por adelantado", 
    "inglés", "doy correo", "escribeme a", "no funciona wallapay",
    "abstenerse curiosos"
]

HEADERS = {"Host": "api.wallapop.com", "X-DeviceOS": "0"}
URL = "https://api.wallapop.com/api/v3/search"
SEEN_IDS = set()

def get_daily_filename():
    today_str = datetime.now().strftime("%Y%m%d")
    if not os.path.exists("logs"):
        os.makedirs("logs")
    return f"logs/wallapop_watches_{today_str}.json"

def calculate_risk(item, seller_count, brand):
    score = 0
    reasons = []
    
    # CORRECCIÓN AQUÍ: Manejar la descripción correctamente
    title = item.get("title", "")
    desc_raw = item.get("description", "")
    # Si es diccionario (API Detalle), saca 'original', si es texto (API Search), úsalo tal cual
    if isinstance(desc_raw, dict):
        desc = desc_raw.get("original", "")
    else:
        desc = str(desc_raw)
        
    text = (str(title) + " " + desc).lower()
    
    # 1. Keywords
    found = [w for w in SUSPICIOUS_KEYWORDS if w in text]
    if found: 
        score += 20
        reasons.append(f"Keywords: {found}")

    # 2. Precio
    price = float(item.get("price", {}).get("amount", 0))
    ref = REFERENCE_PRICES.get(brand, 500)
    rel_index = price / ref if ref else 1.0
    if (rel_index < 0.3) or (0 < price < 50):
        score += 40
        reasons.append(f"Price anomaly (Index: {rel_index:.2f})")

    # 3. Vendedor
    if seller_count > 20:
        score += 20
        reasons.append(f"High activity ({seller_count})")

    return min(score, 100), reasons, found, rel_index

def fetch_items(keyword):
    params = {
        "source": "search_box",
        "keywords": keyword,
        "category_ids": CATEGORY_ID,
        "time_filter": "today",
        "order_by": "newest",
        "latitude": "40.41956", "longitude": "-3.69196"
    }
    try:
        r = requests.get(URL, headers=HEADERS, params=params, timeout=10)
        return r.json().get("data", {}).get("section", {}).get("payload", {}).get("items", [])
    except: return []

def poll_cycle():
    print(f"\n--- Ciclo: {datetime.now().strftime('%H:%M:%S')} ---")
    filename = get_daily_filename()
    
    current_items = []
    seller_counts = {}
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        doc = json.loads(line)
                        current_items.append(doc)
                        SEEN_IDS.add(doc.get("id"))
                        uid = doc.get("user_id")
                        if uid: seller_counts[uid] = seller_counts.get(uid, 0) + 1
                    except: pass
        except Exception as e:
            print(f"Error leyendo archivo previo: {e}")

    new_count = 0
    for brand in TARGET_KEYWORDS:
        print(f"Busca: {brand}...", end="\r")
        items = fetch_items(brand)
        for item in items:
            iid = item.get("id")
            if iid in SEEN_IDS: continue
            
            SEEN_IDS.add(iid)
            uid = item.get("user_id")
            s_count = seller_counts.get(uid, 0) + 1
            seller_counts[uid] = s_count
            
            risk, reasons, kws, rel = calculate_risk(item, s_count, brand)
            
            ts = item.get("created_at")
            if ts: item["created_at"] = datetime.fromtimestamp(ts/1000.0).isoformat()
            
            item["enrichment"] = {
                "risk_score": risk, "risk_factors": reasons,
                "suspicious_keywords": kws, "relative_price_index": rel,
                "brand_detected": brand
            }
            current_items.append(item)
            new_count += 1
        time.sleep(1)

    if new_count > 0:
        with open(filename, "w") as f:
            for item in current_items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"\n[OK] +{new_count} nuevos. Total: {len(current_items)}")
    else:
        print(f"\n[INFO] Sin novedades. Total: {len(current_items)}")

def main():
    print(f"[*] RADAR RELOJES ACTIVO - Grabando en {get_daily_filename()}")
    while True:
        try: poll_cycle()
        except Exception as e: print(f"Error: {e}")
        time.sleep(POLL_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    main()
