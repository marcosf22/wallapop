import requests
import json
from datetime import datetime
import time
import os

# --- CONFIGURACIÓN ---
CATEGORY_ID = "9562"
TARGET_KEYWORDS = ["Rolex", "Omega", "Tag Heuer", "Breitling", "Hublot", "Seiko", "Tissot"]
POLL_INTERVAL_MINUTES = 20  # Frecuencia de sondeo

SUSPICIOUS_KEYWORDS = [
    "réplica", "replica", "clon", "clone", "imitación", "imitacion",
    "1:1", "AAA", "grado a", "superclon", "sin papeles", "sin documentación",
    "perdida documentación", "urge", "urgente", "sin caja", "bloqueado", 
    "no funciona", "para piezas"
]

HEADERS = {
    "Host": "api.wallapop.com",
    "X-DeviceOS": "0"
}

URL = "https://api.wallapop.com/api/v3/search"

# Variable global para recordar qué hemos visto hoy
SEEN_IDS = set()

def clean_timestamp(ts):
    if ts and isinstance(ts, (int, float)):
        try:
            return datetime.fromtimestamp(ts / 1000.0).isoformat()
        except:
            return None
    return ts

def calculate_risk(item):
    score = 0
    reasons = []
    title = item.get("title", "")
    desc = item.get("description", "")
    if isinstance(desc, dict): desc = desc.get("original", "")
    text = (str(title) + " " + str(desc)).lower()
    
    found_keywords = []
    for word in SUSPICIOUS_KEYWORDS:
        if word in text:
            score += 20
            found_keywords.append(word)
    
    if found_keywords:
        reasons.append(f"Keywords found: {found_keywords}")

    try:
        price = float(item.get("price", {}).get("amount", 0))
        if 0 < price < 50: 
            score += 10
            reasons.append("Very low price (<50)")
    except:
        pass

    return min(score, 100), reasons, found_keywords

def get_daily_filename():
    today_str = datetime.now().strftime("%Y%m%d")
    return f"wallapop_watches_{today_str}.json"

def load_existing_data():
    """Carga los IDs que ya tenemos en el fichero para no duplicar"""
    filename = get_daily_filename()
    current_data = []
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                # Intentamos cargar, si está vacío o mal formado, devolvemos lista vacía
                try:
                    current_data = json.load(f)
                    for item in current_data:
                        if "id" in item:
                            SEEN_IDS.add(item["id"])
                except json.JSONDecodeError:
                    current_data = []
            print(f"[INFO] Cargados {len(SEEN_IDS)} anuncios previos del fichero de hoy.")
        except Exception as e:
            print(f"[ERROR] Leyendo fichero existente: {e}")
    return current_data

def fetch_items_for_brand(keyword):
    """Descarga solo la primera página (lo más reciente)"""
    params = {
        "source": "search_box",
        "keywords": keyword,
        "category_ids": CATEGORY_ID,
        "time_filter": "today",
        "order_by": "newest",
        "latitude": "40.41956",
        "longitude": "-3.69196"
    }
    try:
        response = requests.get(URL, headers=HEADERS, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "data" in data and "section" in data["data"]:
                 return data["data"]["section"]["payload"].get("items", [])
    except Exception as e:
        print(f"    Error buscando {keyword}: {e}")
    return []

def poll_cycle():
    print(f"\n--- [INICIO CICLO] Hora: {datetime.now().strftime('%H:%M:%S')} ---")
    
    # 1. Cargar lo que ya tenemos
    current_items = load_existing_data()
    new_items_count = 0
    
    # 2. Buscar novedades
    for brand in TARGET_KEYWORDS:
        print(f"    --> Buscando novedades de: {brand}...", end="\r")
        items = fetch_items_for_brand(brand)
        
        for item in items:
            item_id = item.get("id")
            
            if item_id in SEEN_IDS:
                continue
                
            SEEN_IDS.add(item_id)
            new_items_count += 1
            
            doc = item.copy()
            if "created_at" in doc: doc["created_at"] = clean_timestamp(doc["created_at"])
            if "modified_at" in doc: doc["modified_at"] = clean_timestamp(doc["modified_at"])

            risk_score, risk_factors, sus_keywords = calculate_risk(item)
            
            doc["crawl_date"] = datetime.now().isoformat()
            doc["enrichment"] = {
                "risk_score": risk_score,
                "risk_factors": risk_factors,
                "suspicious_keywords": sus_keywords,
                "brand_detected": brand
            }
            
            current_items.append(doc)
            
        time.sleep(1)

    # 3. Guardar
    if new_items_count > 0:
        filename = get_daily_filename()
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(current_items, f, ensure_ascii=False, indent=4)
            print(f"\n[OK] {new_items_count} anuncios NUEVOS guardados. Total hoy: {len(current_items)}")
        except Exception as e:
            print(f"\n[ERROR] Guardando fichero: {e}")
    else:
        print(f"\n[INFO] No hay novedades. Total hoy: {len(current_items)}")

def main():
    print(f"[*] Iniciando Servicio de Monitorizacion de Relojes")
    print(f"[*] Frecuencia: Cada {POLL_INTERVAL_MINUTES} minutos")
    print(f"[*] Archivo objetivo: {get_daily_filename()}")
    
    while True:
        poll_cycle()
        
        next_run = time.time() + (POLL_INTERVAL_MINUTES * 60)
        print(f"[DURMIENDO]... Proximo escaneo a las {datetime.fromtimestamp(next_run).strftime('%H:%M:%S')}")
        
        try:
            time.sleep(POLL_INTERVAL_MINUTES * 60)
        except KeyboardInterrupt:
            print("\n[STOP] Deteniendo servicio...")
            break

if __name__ == "__main__":
    main()