import os
import time
import json
import requests
from pathlib import Path
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from subir_imagenes import buscar_producto_por_nombre_y_serpi, cargar_imagen_a_shopify

# -------------------------------------------------------------
# 1. Configuración de Entorno y Conexión API
# -------------------------------------------------------------
base_dir = Path(__file__).parent
load_dotenv(dotenv_path=base_dir / '.env')
load_dotenv(dotenv_path=base_dir / 'Shopify.env')

RAW_SHOP_URL = os.getenv("SHOPIFY_SHOP_URL", "").replace("https://", "").replace("http://", "").strip("/")
API_TOKEN = os.getenv("SHOPIFY_API_TOKEN", "").strip()
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-04").strip()

GRAPHQL_URL = f"https://{RAW_SHOP_URL}/admin/api/{API_VERSION}/graphql.json"
HEADERS = {
    "X-Shopify-Access-Token": API_TOKEN,
    "Content-Type": "application/json"
}

# -------------------------------------------------------------
# 2. Cargar Esquema Dinámico desde shopify_schema.json
# -------------------------------------------------------------
SCHEMA_PATH = base_dir / "shopify_schema.json"
SCHEMA = {"campos_estandar": {}, "metafields": {}}

if SCHEMA_PATH.exists():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        SCHEMA = json.load(f)

# -------------------------------------------------------------
# 3. Funciones Auxiliares de Mapeo y Búsqueda
# -------------------------------------------------------------
def ejecutar_graphql(query, variables=None):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    response = requests.post(GRAPHQL_URL, headers=HEADERS, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"HTTP {response.status_code}: {response.text}")

def obtener_valor_fila(row, lista_columnas_posibles):
    """
    Busca en la fila del DataFrame si existe alguna columna
    coincidente ignorando diferencias de mayúsculas/minúsculas y espacios.
    """
    cols_map = {str(c).strip().lower(): c for c in row.index}
    for col_posible in lista_columnas_posibles:
        col_clean = str(col_posible).strip().lower()
        if col_clean in cols_map:
            col_real = cols_map[col_clean]
            val = row[col_real]
            if pd.notna(val) and str(val).strip() != '' and str(val).lower() != 'nan':
                return str(val).strip()
    return None

def obtener_product_id_por_handle(handle):
    query = """
    query getProductId($query: String!) {
      products(first: 1, query: $query) {
        edges {
          node {
            id
            handle
          }
        }
      }
    }
    """
    data = ejecutar_graphql(query, {"query": f"handle:{handle}"})
    products = data.get("data", {}).get("products", {}).get("edges", [])
    if products:
        return products[0]["node"]["id"]
    return None

# -------------------------------------------------------------
# 4. Proceso de Actualización Basado en Esquema
# -------------------------------------------------------------
def actualizar_producto_con_esquema(product_id, row):
    errores_totales = []
    campos_estandar = SCHEMA.get("campos_estandar", {})
    
    input_product = {"id": product_id}
    
    # ---------------------------------------------------------
    # 1. CAMPOS ESTÁNDAR A NIVEL DE PRODUCTO
    # ---------------------------------------------------------
    v_desc = obtener_valor_fila(row, campos_estandar.get("descriptionHtml", {}).get("posibles_columnas_excel", []))
    if v_desc is not None:
        input_product["descriptionHtml"] = str(v_desc)

    v_vendor = obtener_valor_fila(row, campos_estandar.get("vendor", {}).get("posibles_columnas_excel", []))
    if v_vendor is not None:
        input_product["vendor"] = str(v_vendor)

    v_type = obtener_valor_fila(row, campos_estandar.get("productType", {}).get("posibles_columnas_excel", []))
    if v_type is not None:
        input_product["productType"] = str(v_type)

    v_tags = obtener_valor_fila(row, campos_estandar.get("tags", {}).get("posibles_columnas_excel", []))
    if v_tags is not None:
        input_product["tags"] = [t.strip() for t in str(v_tags).split(',')]

    # ---------------------------------------------------------
    # 2. METAFIELDS A NIVEL DE PRODUCTO
    # ---------------------------------------------------------
    metafields_input = []
    metafields_schema = SCHEMA.get("metafields", {})
    
    for key_meta, info_meta in metafields_schema.items():
        v_meta = obtener_valor_fila(row, info_meta.get("posibles_columnas_excel", []))
        if v_meta is not None:
            v_meta_str = str(v_meta).strip()
            tipo_meta = info_meta.get("type", "single_line_text_field")
            if "metaobject_reference" in tipo_meta and not v_meta_str.startswith("gid://shopify/"):
                continue

            if tipo_meta == "boolean":
                val_bool = v_meta_str.lower() in ['true', '1', 'si', 'sí', 'yes']
                val_str = "true" if val_bool else "false"
            else:
                val_str = v_meta_str

            metafields_input.append({
                "namespace": info_meta["namespace"],
                "key": info_meta["key"],
                "value": val_str,
                "type": tipo_meta
            })

    if metafields_input:
        input_product["metafields"] = metafields_input

    # ---------------------------------------------------------
    # 3. ACTUALIZAR PRODUCTO PRINCIPAL (GraphQL)
    # ---------------------------------------------------------
    mutation_prod = """
    mutation productUpdate($input: ProductInput!) {
      productUpdate(input: $input) {
        userErrors {
          field
          message
        }
      }
    }
    """
    res_prod = ejecutar_graphql(mutation_prod, {"input": input_product})
    err_p = res_prod.get("data", {}).get("productUpdate", {}).get("userErrors", [])
    if err_p:
        errores_totales.extend(err_p)

    # ---------------------------------------------------------
    # 4. CAMPOS A NIVEL DE VARIANTE (REST API - TAXABLE, PRICE, SKU)
    # ---------------------------------------------------------
    v_price = obtener_valor_fila(row, campos_estandar.get("price", {}).get("posibles_columnas_excel", []))
    v_sku = obtener_valor_fila(row, campos_estandar.get("sku", {}).get("posibles_columnas_excel", []))
    v_tax = obtener_valor_fila(row, campos_estandar.get("taxable", {}).get("posibles_columnas_excel", []))

    if v_price is not None or v_sku is not None or v_tax is not None:
        # Obtener ID de la primera variante vía GraphQL
        query_var = """
        query getVariantId($id: ID!) {
          product(id: $id) {
            variants(first: 1) {
              edges {
                node {
                  id
                }
              }
            }
          }
        }
        """
        res_var = ejecutar_graphql(query_var, {"id": product_id})
        v_edges = res_var.get("data", {}).get("product", {}).get("variants", {}).get("edges", [])

        if v_edges:
            variant_gid = v_edges[0]["node"]["id"]
            variant_numeric_id = variant_gid.split("/")[-1]
            
            variant_payload = {}

            if v_price is not None:
                variant_payload["price"] = str(v_price).strip()

            if v_sku is not None:
                variant_payload["sku"] = str(v_sku).strip()

            if v_tax is not None:
                val_str = str(v_tax).strip().upper()
                es_taxable = val_str in ["TRUE", "1", "SI", "SÍ", "YES"]
                variant_payload["taxable"] = es_taxable

            # Petición a la API REST de Variantes
            REST_URL = f"https://{RAW_SHOP_URL}/admin/api/{API_VERSION}"
            url_variant_rest = f"{REST_URL}/variants/{variant_numeric_id}.json"
            
            res_rest = requests.put(url_variant_rest, json={"variant": variant_payload}, headers=HEADERS)
            
            if res_rest.status_code not in [200, 201]:
                errores_totales.append({"field": ["variant"], "message": f"Error REST {res_rest.status_code}: {res_rest.text[:100]}"})

    return errores_totales

# -------------------------------------------------------------
# 5. Interfaz Visual Streamlit
# -------------------------------------------------------------
st.set_page_config(page_title="Gestor de Inventario Shopify / SERPI", layout="wide")
st.title("📦 Gestor Local de Inventario y Productos")

st.sidebar.header("Conexión API")
if API_TOKEN:
    st.sidebar.success(f"Conectado a: {RAW_SHOP_URL}")
else:
    st.sidebar.error("Verifica tus credenciales en el .env")

st.sidebar.divider()
st.sidebar.header("Esquema Cargado")
st.sidebar.info(f"Campos Estándar: {len(SCHEMA.get('campos_estandar', {}))}\nMetafields: {len(SCHEMA.get('metafields', {}))}")

st.subheader("1. Cargar catálogo de productos")
uploaded_file = st.file_uploader("Selecciona tu archivo Excel (.xlsx) o CSV", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file, dtype=str)
        else:
            df_raw = pd.read_excel(uploaded_file, dtype=str)
        
        st.success(f"Archivo **{uploaded_file.name}** cargado con éxito. Total registros: {len(df_raw)}")

        st.divider()
        st.subheader("2. Confirmar Origen del Archivo")
        origen_archivo = st.radio("¿Cuál es el origen del archivo?", ["Shopify", "SERPI"], horizontal=True)

        if st.button("🔄 Procesar y Estructurar Datos"):
            st.session_state["procesado"] = True
            st.session_state["origen"] = origen_archivo
            st.session_state["df_raw"] = df_raw

    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")

if st.session_state.get("procesado"):
    origen = st.session_state["origen"]
    df_data = st.session_state["df_raw"]

    st.divider()
    st.subheader(f"3. Datos Listos para Actualizar (Origen: {origen})")
    st.dataframe(df_data.head(10), use_container_width=True)

    if st.button("📤 Actualizar en Shopify vía GraphQL API"):
        st.warning("⚠️ Iniciando actualización masiva según esquema... No cierres la ventana.")
        
        progreso = st.progress(0)
        status_text = st.empty()
        total = len(df_data)
        exitosos = 0
        errores = 0

        for i, row in df_data.iterrows():
            handle = obtener_valor_fila(row, ['Handle', 'handle', 'product_handle'])
            
            if not handle:
                continue

            try:
                product_id = obtener_product_id_por_handle(handle)
                if product_id:
                    user_errors = actualizar_producto_con_esquema(product_id, row)
                    if not user_errors:
                        exitosos += 1
                    else:
                        msg_err = ", ".join([e["message"] for e in user_errors])
                        st.error(f"❌ Error en {handle}: {msg_err}")
                        errores += 1
                else:
                    st.error(f"❌ Handle '{handle}' no encontrado en Shopify.")
                    errores += 1

            except Exception as e:
                if "429" in str(e) or "THROTTLED" in str(e):
                    time.sleep(2)
                st.error(f"❌ Error de procesamiento en {handle}: {e}")
                errores += 1

            time.sleep(0.05)
            progreso.progress((i + 1) / total)
            status_text.text(f"Procesando {i + 1} de {total}... (Éxitos: {exitosos} | Errores: {errores})")

        st.success(f"🎉 Proceso completado. Exitosos: {exitosos} | Errores: {errores}")
# -------------------------------------------------------------
# SECCIÓN: Subida Asistida de Portadas por Nombre y Código SERPI
# -------------------------------------------------------------
st.divider()
st.header("🖼️ Asignación Asistida de Portadas")
st.write("Escribe el nombre del libro y/o su código SERPI para localizar exactamente el producto en Shopify antes de subir la imagen.")

col_nom, col_serpi = st.columns(2)

with col_nom:
    nombre_input = st.text_input("📖 Nombre o Título del Libro", placeholder="Ej: El principito")

with col_serpi:
    serpi_input = st.text_input("🔢 Código SERPI", placeholder="Ej: 9780785396901")

if st.button("🔍 Buscar Producto en Shopify"):
    if not nombre_input.strip() and not serpi_input.strip():
        st.warning("⚠️ Debes ingresar al menos el Nombre o el Código SERPI para realizar la búsqueda.")
    else:
        with st.spinner("Buscando coincidencias en Shopify..."):
            resultados = buscar_producto_por_nombre_y_serpi(nombre_input, serpi_input)
            st.session_state["busqueda_productos"] = resultados

# Mostrar resultados encontrados si existen
if "busqueda_productos" in st.session_state:
    resultados = st.session_state["busqueda_productos"]
    
    if not resultados:
        st.error("❌ No se encontró ningún producto que coincida con esos criterios.")
    else:
        st.success(f"✅ Se encontraron {len(resultados)} coincidencia(s):")
        
        # Mapear opciones para el selector
        opciones = {f"{item['title']} | SERPI: {item['serpi']} (ID: {item['id'].split('/')[-1]})": item for item in resultados}
        
        seleccion = st.selectbox("Selecciona el producto exacto al que pertenece la portada:", list(opciones.keys()))
        producto_seleccionado = opciones[seleccion]

        st.info(f"📌 Producto Seleccionado: **{producto_seleccionado['title']}** (SERPI Metafield: `{producto_seleccionado['serpi']}`)")

        # Selector de imagen para el producto confirmado
        uploaded_image = st.file_uploader(
            "Selecciona la imagen de la portada desde tu equipo",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=False
        )

        if uploaded_image and st.button("🚀 Subir Imagen y Asignar a este Producto"):
            with st.spinner("Subiendo portada e integrando a la galería de Shopify..."):
                file_bytes = uploaded_image.read()
                ok, msg = cargar_imagen_a_shopify(producto_seleccionado["id"], file_bytes, uploaded_image.name)
                
                if ok:
                    st.success(f"🎉 ¡Portada asignada exitosamente al libro **{producto_seleccionado['title']}**!")
                else:
                    st.error(f"❌ Error al subir la imagen: {msg}")