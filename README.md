# Detector de fraudes en Wallapop: Data Pipeline & Anomaly Detection

<p align="center">
  <img src="https://media.tenor.com/Yg_KkXqg0qMAAAAj/hacking-hacker.gif" alt="Banner del Proyecto" width="150"/>
</p>

> Este proyecto simula una colaboración con la BCIT (Brigada Central de Investigación Tecnológica) para detectar patrones de fraude en Wallapop. Implementa un pipeline completo que monitoriza una categoría de productos, calcula puntuaciones de riesgo y genera alertas automáticas sobre anuncios sospechosos (estafas, precios anómalos, etc.) en lugar de requerir una revisión manual.

---

## 🌟 Las principales características del proyecto son:

* Poller en Python para la adquisición periódica de datos desde la API pública de Wallapop.
* Normalización y enriquecimiento de datos (cálculo de *Risk Score* y detección de *keywords* sospechosas).
* Ingesta y almacenamiento eficiente en Elasticsearch.
* Visualización operativa mediante Dashboards en Kibana (histogramas de precios, mapas, actividad de vendedores).
* Sistema de alertas proactivas mediante Elastalert2 (notificaciones por umbrales de precio o riesgo).

---

## 📂 Archivos necesarios y estructura:

* **poller/poller.py** Este script es el núcleo de la recolección. Se encarga de consultar la API, filtrar por "items del día", aplicar la lógica de sospecha y generar los ficheros JSON diarios.

* **ingestion/bulk_ingest.py** (O configuración de Filebeat/Fleet) Encargado de leer los logs diarios y enviarlos al clúster de Elasticsearch aplicando los *templates* definidos.

* **kibana/dashboard_export.ndjson** Archivo de exportación que contiene todos los "Saved Objects" necesarios para replicar las visualizaciones y el Dashboard del Radar de Fraude.

<p align="center">
  <img src="./kibana/screenshots/dashboard_preview.png" alt="Captura del Dashboard de Kibana" width="600"/>
</p>

* **elastalert/rules/*.yaml** Definiciones de las reglas de alerta. Aquí se establecen los criterios de disparo (ej. precio < 50% de la media o score > 80) y el método de notificación.

<p align="center">
  <img src="./elastalert/screenshots/alert_example.png" alt="Ejemplo de Alerta Disparada" width="500"/>
</p>

* **report/Report.pdf** Informe con el proceso de desarrollo de los scripts, el reparto de tareas y el proceso de desarrollo con la IA.

* **poller/viewer.py** EXTRA: Interfaz web que sirve para ver en claro de forma visual el contenido capturado por el poller.py y almacenado en el JSON.
---

## 🚀 Instalación y uso:

1. **Configurar el Poller:** Instalar dependencias, en caso de no tenerlas y ajustar la busqueda de la categoría deseada.
2. **Desplegar Elastic Stack:** Asegurar que Elasticsearch y Kibana están corriendo (v8.x).
3. **Ejecutar Ingesta:** Correr el script de ingestión o iniciar el agente Elastic/.
4. **Importar Dashboards:** Cargar el archivo ndjson en Kibana.
5. **Activar Alertas:** Ejecutar Elastalert2 apuntando a las reglas definidas.
6. **EXTRA: Interfaz:** Para ejecutar la interfaz hay que poner por consola "streamlit run viewer.py".
