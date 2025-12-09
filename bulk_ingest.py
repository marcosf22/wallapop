import json
import requests
import os
from datetime import datetime
import urllib3

# Desactivar avisos de certificado (porque usamos HTTPS local)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN ---
ES_URL = "https://localhost:9200"
INDEX_ALIAS = "lab1.wallapop"  # <--- Asegúrate de que coincida con lo que pusiste en Kibana
AUTH = ('elastic', 'mlJZP3AuDE0pr4q1Rwq8') # <--- CAMBIA ESTO si tu contraseña es distinta

def get_filename():
    # Busca el archivo con fecha de HOY
    today_str = datetime.now().strftime("%Y%m%d")
    return f"logs/wallapop_watches_{today_str}.json"

def ingest():
    json_file = get_filename()
    
    # Comprobación de seguridad
    if not os.path.exists(json_file):
        print(f"[ERROR] No encuentro el archivo de hoy: {json_file}")
        print("¿Está corriendo el poller? ¿Ha pasado suficiente tiempo?")
        return

    print(f"[*] Leyendo archivo: {json_file}...")
    
    bulk_data = []
    count = 0
    
    # Leer el fichero línea a línea
    with open(json_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            # 1. Cabecera de acción para Elastic
            action = {"index": {"_index": INDEX_ALIAS}}
            bulk_data.append(json.dumps(action))
            
            # 2. El dato en sí
            bulk_data.append(line)
            count += 1

    if count == 0:
        print("[INFO] El archivo está vacío (aún no hay anuncios nuevos).")
        return

    # Preparar el paquete para enviar (NDJSON requiere saltos de línea)
    bulk_payload = "\n".join(bulk_data) + "\n"

    print(f"[*] Enviando {count} documentos a Elastic...")
    
    try:
        # Enviar a Elastic usando HTTPS e ignorando el certificado SSL local
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
                print("[!] Elastic aceptó el paquete pero hubo errores individuales.")
                print(f"Detalle primer error: {resp['items'][0]}")
            else:
                print("[OK] Ingesta completada con éxito.")
        else:
            print(f"[ERROR] Fallo en el servidor: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"[ERROR] Conectando a Elastic: {e}")

if __name__ == "__main__":
    ingest()