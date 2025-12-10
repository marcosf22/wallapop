import streamlit as st
import json
import os
import glob
import time
from collections import Counter
from datetime import datetime

# Configuración estilo "Wallapop"
st.set_page_config(page_title="Radar Wallapop", layout="wide", page_icon="🛍️")

# --- LISTA COMPLETA DE PALABRAS SOSPECHOSAS ---
ALL_SUSPICIOUS_KEYWORDS = [
    "réplica", "replica", "clon", "imitación", "imitacion", "1:1", "AAA", 
    "sin papeles", "urge", "urgente", "sin caja", "bloqueado", "robado"
]

# --- CSS MEJORADO ---
st.markdown("""
<style>
    .product-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .price-tag {
        font-size: 1.4em;
        font-weight: bold;
        color: #13C1AC; 
    }
    .info-label {
        font-weight: bold;
        color: #555;
    }
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛍️ Radar de Ofertas")

# --- CONTROL DE AUTO-REFRESH ---
if st.sidebar.checkbox("🔄 Actualización en tiempo real (5s)", value=False):
    st_autorefresh = True
else:
    st_autorefresh = False

# --- FUNCIÓN DE CARGA ---
def load_data():
    files = glob.glob(r"c:\Users\artur\OneDrive\Escritorio\logs\wallapop_*.json")
    
    if not files:
        desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Escritorio", "logs", "wallapop_*.json")
        files = glob.glob(desktop)
        
    if not files:
        return []
    
    latest_file = max(files, key=os.path.getmtime)
    data = []
    
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
    except: pass
    
    return data[::-1]

items = load_data()

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("Filtros")

if not items:
    st.warning("⚠️ Esperando datos... Asegúrate de que el 'poller.py' está corriendo.")
else:
    # 1. Filtros Básicos
    st.sidebar.markdown("### 💰 Precio y Riesgo")
    min_price = st.sidebar.number_input("Precio Mínimo (€)", 0, 10000, 0)
    show_only_risky = st.sidebar.checkbox("Ver sospechosos (Riesgo > 30)")
    
    # 2. Filtro de Marca
    st.sidebar.markdown("### 🏷️ Marca")
    all_brands = sorted(list(set(item.get("enrichment", {}).get("brand_detected", "Desconocida") for item in items)))
    selected_brands = st.sidebar.multiselect("Seleccionar Marcas", all_brands, default=all_brands)

    # 3. NUEVO: Filtros de Ubicación
    st.sidebar.markdown("### 📍 Ubicación")
    all_cities = sorted(list(set(item.get("location", {}).get("city", "Desconocida") for item in items)))
    selected_cities = st.sidebar.multiselect("Ciudad", all_cities, placeholder="Todas las ciudades")

    # 4. NUEVO: Filtro por Usuario (Vendedor)
    st.sidebar.markdown("### 👤 Vendedor")
    # Contamos cuántos items tiene cada usuario para mostrarlo en el filtro
    user_counts = Counter(item.get("user_id", "Anónimo") for item in items)
    # Ordenamos: primero los que más venden (más sospechosos de ser tiendas/estafadores)
    sorted_users = sorted(user_counts.keys(), key=lambda x: user_counts[x], reverse=True)
    
    # Creamos una lista bonita para el desplegable: "user_id (5 items)"
    user_options = ["Todos"] + [f"{u} ({user_counts[u]} items)" for u in sorted_users]
    
    selected_user_display = st.sidebar.selectbox("Filtrar por Usuario", user_options)
    
    # Extraemos el ID limpio de la selección
    selected_user_id = "Todos"
    if selected_user_display != "Todos":
        selected_user_id = selected_user_display.split(" (")[0]

    # 5. Filtro Forense
    st.sidebar.markdown("### 🕵️ Filtro Forense")
    selected_bad_words = st.sidebar.multiselect(
        "Palabras Clave", 
        ALL_SUSPICIOUS_KEYWORDS,
        placeholder="Ej: robado, bloqueado..."
    )

    st.sidebar.markdown("---")
    st.sidebar.success(f"Total cargados: {len(items)}")

    # --- FILTRADO DE DATOS (LÓGICA) ---
    filtered_items = []
    for item in items:
        # Extracción de datos
        price = item.get("price", {}).get("amount", 0)
        risk = item.get("enrichment", {}).get("risk_score", 0)
        brand = item.get("enrichment", {}).get("brand_detected", "Desconocida")
        item_bad_words = item.get("enrichment", {}).get("suspicious_keywords", [])
        city = item.get("location", {}).get("city", "Desconocida")
        user = item.get("user_id", "Anónimo")
        
        # 1. Filtro Precio
        if price < min_price: continue
        
        # 2. Filtro Riesgo
        if show_only_risky and risk <= 30: continue
            
        # 3. Filtro Marca
        if brand not in selected_brands: continue
        
        # 4. Filtro Ciudad (NUEVO)
        if selected_cities:
            if city not in selected_cities: continue

        # 5. Filtro Usuario (NUEVO)
        if selected_user_id != "Todos":
            if user != selected_user_id: continue

        # 6. Filtro Palabras
        if selected_bad_words:
            if not any(word in item_bad_words for word in selected_bad_words):
                continue
        
        filtered_items.append(item)

    st.caption(f"Mostrando {len(filtered_items)} productos filtrados")

    # --- PINTAR GRID ---
    cols_per_row = 4
    for i in range(0, len(filtered_items), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(filtered_items):
                item = filtered_items[i + j]
                col = cols[j]
                
                with col:
                    # Datos
                    title = item.get("title", "Sin título")
                    price = item.get("price", {}).get("amount", 0)
                    currency = item.get("price", {}).get("currency", "EUR")
                    img_url = item.get("images", [{}])[0].get("urls", {}).get("medium")
                    risk_score = item.get("enrichment", {}).get("risk_score", 0)
                    brand = item.get("enrichment", {}).get("brand_detected", "")
                    suspicious_list = item.get("enrichment", {}).get("suspicious_keywords", [])
                    
                    desc_raw = item.get("description", "")
                    if isinstance(desc_raw, dict):
                        description = desc_raw.get("original", "Sin descripción")
                    else:
                        description = str(desc_raw)

                    location = item.get("location", {})
                    city_text = location.get("city", "Desconocida")
                    postal = location.get("postal_code", "")
                    user_id = item.get("user_id", "Anónimo")

                    # TARJETA VISUAL
                    with st.container(border=True):
                        if img_url:
                            st.image(img_url, use_container_width=True)
                        else:
                            st.text("📷 Sin foto")
                        
                        st.markdown(f"<div class='price-tag'>{price} {currency}</div>", unsafe_allow_html=True)
                        st.markdown(f"**{title[:50]}...**")
                        
                        if suspicious_list:
                             st.markdown(f"⚠️ **Detectado:** {', '.join(suspicious_list)}")

                        if risk_score > 50:
                            st.error(f"🚨 Riesgo Alto: {risk_score}/100")
                        elif risk_score > 30:
                            st.warning(f"⚠️ Riesgo Medio: {risk_score}/100")
                        else:
                            st.success(f"✅ Riesgo Bajo: {risk_score}/100")
                        
                        # --- SECCIÓN DETALLES ---
                        with st.expander("Ver análisis detallado"):
                            st.markdown("#### 📝 Descripción")
                            st.info(description)
                            
                            st.divider()
                            
                            c1, c2 = st.columns(2)
                            with c1:
                                st.markdown("**📍 Ubicación**")
                                st.write(f"{city_text} ({postal})")
                                
                            with c2:
                                st.markdown("**👤 Vendedor**")
                                st.code(user_id, language=None)

                            st.divider()
                            
                            st.markdown("**🕵️ ¿Por qué es sospechoso?**")
                            factors = item.get('enrichment', {}).get('risk_factors', [])
                            if factors:
                                for f in factors:
                                    if "Anomaly" in f or "Keywords" in f:
                                        st.write(f"- 🔴 {f}")
                                    else:
                                        st.write(f"- 🟡 {f}")
                            else:
                                st.write("✅ Precio y palabras clave dentro de lo normal.")
                            
                            st.markdown("---")
                            if st.checkbox("Ver JSON técnico (Debug)", key=item.get("id")):
                                st.json(item)

# Auto-refresh
if st_autorefresh:
    time.sleep(5)
    st.rerun()