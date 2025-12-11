import streamlit as st
import json
import os
import glob
import time
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Radar Wallapop - Monitor",
    layout="wide",
    page_icon="🛍️",
    initial_sidebar_state="expanded"
)

# --- LISTA DE PALABRAS SOSPECHOSAS (Sincronizada con poller.py) ---
ALL_SUSPICIOUS_KEYWORDS = [
    "réplica", "replica", "clon", "imitación", "imitacion", "1:1", "AAA", 
    "repro", "copia", "falso", "fake", "tipo rolex", "estilo rolex", "superclon",
    "sin papeles", "sin documentación", "perdida", "herencia", "regalo", 
    "urge", "urgente", "sin caja", "bloqueado", "encontrado", 
    "solo whatsapp", "contactar por", "bizum", "transferencia", "envío gratis", 
    "pago por adelantado", "inglés", "nigeria", "doy correo", "escribeme a", 
    "no funciona wallapay", "abstenerse curiosos"
]

# --- ESTILOS CSS ---
st.markdown("""
<style>
    .product-card {
        background-color: #ffffff;
        border: 1px solid #e6e6e6;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    .product-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .price-tag {
        font-size: 1.5em;
        font-weight: 800;
        color: #13C1AC; 
    }
    .risk-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.85em;
        color: white;
    }
    .risk-high { background-color: #ff4b4b; }
    .risk-med { background-color: #ffa500; }
    .risk-low { background-color: #28a745; }
    
    .metrics-container {
        display: flex;
        justify-content: space-between;
        margin-bottom: 10px;
        font-size: 0.9em;
        color: #666;
    }
    a { text-decoration: none; color: inherit; }
</style>
""", unsafe_allow_html=True)

# --- TÍTULO ---
st.title("🛍️ Radar de Ofertas - Visualizador")

# --- FUNCIÓN DE CARGA DE DATOS ---
def load_latest_data():
    # Busca en la carpeta logs relativa al script
    log_dir = "logs"
    if not os.path.exists(log_dir):
        return [], None
    
    # Patrón de nombre de archivo del poller
    files = glob.glob(os.path.join(log_dir, "wallapop_watches_*.json"))
    
    if not files:
        return [], None
    
    # Obtener el archivo más reciente
    latest_file = max(files, key=os.path.getmtime)
    data = []
    
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            # El poller escribe JSON Lines (un objeto JSON por línea)
            for line in f:
                if line.strip():
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        st.error(f"Error leyendo el archivo: {e}")
        
    # Invertimos para ver lo más nuevo arriba
    return data[::-1], latest_file

# Carga inicial
items, current_file = load_latest_data()

# --- BARRA LATERAL (FILTROS Y ESTADO) ---
with st.sidebar:
    st.header("⚙️ Panel de Control")
    
    if current_file:
        last_mod = datetime.fromtimestamp(os.path.getmtime(current_file)).strftime('%H:%M:%S')
        st.success(f"📂 Leyendo: {os.path.basename(current_file)}")
        st.caption(f"🕒 Última actualización archivo: {last_mod}")
    else:
        st.warning("⚠️ No se encontraron logs. Ejecuta 'poller.py'.")

    # Checkbox para auto-refresh
    if st.checkbox("🔄 Auto-refrescar (5s)", value=True):
        st_autorefresh = True
    else:
        st_autorefresh = False

    st.divider()
    
    st.subheader("Filtros")
    
    # Filtro Precio
    min_price = st.number_input("Precio Mínimo (€)", 0, 50000, 0, step=50)
    max_price = st.number_input("Precio Máximo (€)", 0, 50000, 20000, step=50)
    
    # Filtro Riesgo
    risk_threshold = st.slider("Nivel de Riesgo Mínimo", 0, 100, 0, help="Filtra items con puntuación de riesgo alta")
    
    # Filtro Marca (Extraído de los datos enriquecidos)
    if items:
        all_brands = sorted(list(set(item.get("enrichment", {}).get("brand_detected", "Desconocida") for item in items)))
        selected_brands = st.multiselect("Marcas", all_brands, default=[])
    else:
        selected_brands = []

    # Filtro Palabras Clave (Forense)
    selected_keywords = st.multiselect("Palabras Sospechosas", ALL_SUSPICIOUS_KEYWORDS)

    st.markdown("---")
    st.info(f"Total items cargados: {len(items)}")

# --- LÓGICA DE FILTRADO Y VISUALIZACIÓN ---
if not items:
    st.info("Esperando datos del poller...")
else:
    count_shown = 0
    
    for item in items:
        # 1. Extracción segura de datos
        price_data = item.get("price", {})
        price_amount = price_data.get("amount", 0)
        currency = price_data.get("currency", "EUR")
        
        enrichment = item.get("enrichment", {})
        risk_score = enrichment.get("risk_score", 0)
        brand = enrichment.get("brand_detected", "N/A")
        factors = enrichment.get("risk_factors", [])
        item_keywords = enrichment.get("suspicious_keywords", [])
        
        location = item.get("location", {})
        city = location.get("city", "Desconocido")
        postal = location.get("postal_code", "")
        
        title = item.get("title", "Sin título")
        description = item.get("description", "")
        item_id = item.get("id", "")
        web_slug = item.get("web_slug", "")
        
        # Link al producto
        wallapop_url = f"https://es.wallapop.com/item/{web_slug}" if web_slug else "#"

        # 2. Aplicar Filtros
        if price_amount < min_price or (max_price > 0 and price_amount > max_price):
            continue
        if risk_score < risk_threshold:
            continue
        if selected_brands and brand not in selected_brands:
            continue
        # Filtro forense: si el usuario selecciona keywords, el item debe tener AL MENOS una de ellas
        if selected_keywords:
            # Comprobamos si las keywords detectadas por el poller coinciden con las seleccionadas
            if not any(k in item_keywords for k in selected_keywords):
                # También buscamos en texto por si acaso el poller no lo pilló pero el usuario lo busca
                full_text = (title + " " + description).lower()
                if not any(k.lower() in full_text for k in selected_keywords):
                    continue

        count_shown += 1

        # 3. Renderizado de la Tarjeta
        with st.container():
            st.markdown(f"""<div class="product-card">""", unsafe_allow_html=True)
            
            cols = st.columns([1, 2, 1])
            
            # Columna Imagen
            with cols[0]:
                images = item.get("images", [])
                if images:
                    # Intentamos coger la imagen mediana
                    img_url = images[0].get("urls", {}).get("medium", "")
                    if img_url:
                        st.image(img_url, use_container_width=True)
                    else:
                        st.text("Sin imagen")
                else:
                    st.text("Sin imagen")
            
            # Columna Detalles
            with cols[1]:
                st.markdown(f"#### [{title}]({wallapop_url})")
                st.caption(f"📍 {city} ({postal}) | 👤 {item.get('user_id', 'Anónimo')}")
                
                # Descripción truncada
                desc_preview = (description[:200] + '...') if len(description) > 200 else description
                st.write(desc_preview)
                
                # Mostrar factores de riesgo si existen
                if factors or item_keywords:
                    st.markdown("---")
                    for f in factors:
                        st.markdown(f"🔴 **Alerta:** {f}")
                    if item_keywords:
                        st.markdown(f"⚠️ **Keywords:** {', '.join(item_keywords)}")

            # Columna Precio y Score
            with cols[2]:
                st.markdown(f"<div class='price-tag'>{price_amount} {currency}</div>", unsafe_allow_html=True)
                
                # Badge de Riesgo
                if risk_score >= 50:
                    badge_class = "risk-high"
                    label = "ALTO RIESGO"
                elif risk_score >= 20:
                    badge_class = "risk-med"
                    label = "SOSPECHOSO"
                else:
                    badge_class = "risk-low"
                    label = "OK"
                
                st.markdown(f"""
                    <div style="margin-top:10px;">
                        <span class="risk-badge {badge_class}">
                            {label}: {risk_score}/100
                        </span>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"**Marca:** {brand}")
                
                if st.button("Ver JSON", key=f"btn_{item_id}"):
                    st.json(item)

            st.markdown("</div>", unsafe_allow_html=True)

    if count_shown == 0:
        st.warning("No hay items que coincidan con los filtros actuales.")

# --- AUTO-REFRESH ---
if st_autorefresh:
    time.sleep(5)
    st.rerun()