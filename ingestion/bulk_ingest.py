import json
import requests
import os
from datetime import datetime
import urllib3

# Desactivar avisos de certificado (porque usamos HTTPS local)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN ---
ES_URL = "https://localhost:9200"
INDEX_ALIAS = "lab2.wallapop"
AUTH = ('elastic', 'mlJZP3AuDE0pr4q1Rwq8')

def get_filename():
    today_str = datetime.now().strftime("%Y%m%d")
    return f"logs/wallapop_watches_{today_str}.json"

def ingest():
    json_file = get_filename()
    
    if not os.path.exists(json_file):
        print(f"[ERROR] No encuentro el archivo de hoy: {json_file}")
        return

    print(f"[*] Leyendo archivo: {json_file}...")
    
    bulk_data = []
    count = 0
    
    with open(json_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            try:
                # 1. Parseamos la línea para extraer el ID original del anuncio
                doc = json.loads(line)
                item_id = doc.get("id")
                
                # 2. Especificamos el "_id" en la cabecera de acción
                # Si el ID ya existe, 'index' lo sobrescribe (actualiza).
                action = {
                    "index": {
                        "_index": INDEX_ALIAS,
                        "_id": item_id  # <--- ESTO EVITA LOS DUPLICADOS
                    }
                }
                
                bulk_data.append(json.dumps(action))
                bulk_data.append(line)
                count += 1
            except Exception as e:
                print(f"[WARN] Error procesando línea: {e}")

    if count == 0:
        print("[INFO] El archivo está vacío.")
        return

    bulk_payload = "\n".join(bulk_data) + "\n"

    print(f"[*] Enviando {count} documentos a Elastic...")
    
    try:
        response = requests.post(
            f"{ES_URL}/_bulk",
            data=bulk_payload.encode('utf-8'),
            headers={"Content-Type": "application/x-ndjson"},
            verify=False, 
            auth=AUTH
        )
        
        if response.status_code == 200:
            resp = response.json()
            if resp.get("errors"):
                print("[!] Elastic aceptó el paquete pero hubo errores.")
                print(f"Detalle primer error: {resp['items'][0]}")
            else:
                print("[OK] Ingesta completada (idempotente).")
        else:
            print(f"[ERROR] Fallo en el servidor: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"[ERROR] Conectando a Elastic: {e}")

if __name__ == "__main__":
    ingest()
