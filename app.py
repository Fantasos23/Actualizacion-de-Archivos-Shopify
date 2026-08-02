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

def obtener_product_id(row):
    """
    Busca el ID del producto en Shopify primero por Handle
    y si no existe, lo busca por el código SERPI.
    """
    # 1. Intentar buscar por Handle
    v_handle = obtener_valor_fila(row, ["Handle", "handle", "URL Handle"])
    if v_handle:
        query_h = """
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
        data = ejecutar_graphql(query_h, {"query": f"handle:'{v_handle}'"})
        products = data.get("data", {}).get("products", {}).get("edges", [])
        if products:
            return products[0]["node"]["id"], v_handle

    # 2. Intentar buscar por Metafield custom.serpi
    v_serpi = obtener_valor_fila(row, ["serpi", "custom.serpi", "serpi (product.metafields.custom.serpi)", "SERPI"])
    if v_serpi:
        query_s = """
        query getProductBySerpi($query: String!) {
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
        data = ejecutar_graphql(query_s, {"query": f"metafields.custom.serpi:'{v_serpi}'"})
        products = data.get("data", {}).get("products", {}).get("edges", [])
        if products:
            return products[0]["node"]["id"], f"SERPI: {v_serpi}"

    return None, None

# -------------------------------------------------------------
# 4. Proceso de Actualización Basado en Esquema
# -------------------------------------------------------------
def actualizar_producto_con_esquema(product_id, row, campos_permitidos=None):
    """
    Actualiza solo los campos especificados en 'campos_permitidos'.
    Si 'campos_permitidos' es None, actualiza todos los campos presentes.
    """
    errores_totales = []
    campos_estandar = SCHEMA.get("campos_estandar", {})
    input_product = {"id": product_id}
    
    # ---------------------------------------------------------
    # 1. CAMPOS ESTÁNDAR A NIVEL DE PRODUCTO
    # ---------------------------------------------------------
    if campos_permitidos is None or "descriptionHtml" in campos_permitidos:
        v_desc = obtener_valor_fila(row, campos_estandar.get("descriptionHtml", {}).get("posibles_columnas_excel", []))
        if v_desc is not None:
            input_product["descriptionHtml"] = str(v_desc)

    if campos_permitidos is None or "vendor" in campos_permitidos:
        v_vendor = obtener_valor_fila(row, campos_estandar.get("vendor", {}).get("posibles_columnas_excel", []))
        if v_vendor is not None:
            input_product["vendor"] = str(v_vendor)

    if campos_permitidos is None or "productType" in campos_permitidos:
        v_type = obtener_valor_fila(row, campos_estandar.get("productType", {}).get("posibles_columnas_excel", []))
        if v_type is not None:
            input_product["productType"] = str(v_type)

    if campos_permitidos is None or "tags" in campos_permitidos:
        v_tags = obtener_valor_fila(row, campos_estandar.get("tags", {}).get("posibles_columnas_excel", []))
        if v_tags is not None:
            input_product["tags"] = [t.strip() for t in str(v_tags).split(',')]

    # ---------------------------------------------------------
    # 2. METAFIELDS A NIVEL DE PRODUCTO
    # ---------------------------------------------------------
    metafields_input = []
    metafields_schema = SCHEMA.get("metafields", {})
    
    for key_meta, info_meta in metafields_schema.items():
        if campos_permitidos is not None and key_meta not in campos_permitidos:
            continue
            
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

    # Ejecutar actualización a nivel de producto si hay cambios
    if len(input_product) > 1:
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
    # 3. CAMPOS A NIVEL DE VARIANTE (REST API - TAXABLE, PRICE, SKU)
    # ---------------------------------------------------------
    v_price = None
    if campos_permitidos is None or "price" in campos_permitidos:
        v_price = obtener_valor_fila(row, campos_estandar.get("price", {}).get("posibles_columnas_excel", []))

    v_sku = None
    if campos_permitidos is None or "sku" in campos_permitidos:
        v_sku = obtener_valor_fila(row, campos_estandar.get("sku", {}).get("posibles_columnas_excel", []))

    v_tax = None
    if campos_permitidos is None or "taxable" in campos_permitidos:
        v_tax = obtener_valor_fila(row, campos_estandar.get("taxable", {}).get("posibles_columnas_excel", []))

    if v_price is not None or v_sku is not None or v_tax is not None:
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

            REST_URL = f"https://{RAW_SHOP_URL}/admin/api/{API_VERSION}"
            url_variant_rest = f"{REST_URL}/variants/{variant_numeric_id}.json"
            
            # Petición a la API REST con reintentos automáticos
            exito_rest = False
            intentos = 0
            
            while not exito_rest and intentos < 3:
                try:
                    res_rest = requests.put(url_variant_rest, json={"variant": variant_payload}, headers=HEADERS, timeout=10)
                    if res_rest.status_code in [200, 201]:
                        exito_rest = True
                    else:
                        errores_totales.append({"field": ["variant"], "message": f"Error REST {res_rest.status_code}: {res_rest.text[:100]}"})
                        break
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                    intentos += 1
                    time.sleep(2)  # Pausa de 2 segundos antes de reintentar
                    if intentos >= 3:
                        errores_totales.append({"field": ["connection"], "message": "Error de conexión persistente con Shopify."})

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
    st.dataframe(df_data.head(10), width="stretch")

    # -------------------------------------------------------------
    # DETECCIÓN DE CAMPOS PRESENTES Y SELECTOR INTERACTIVO
    # -------------------------------------------------------------
    st.subheader("⚙️ Selección de Campos a Actualizar")
    st.write("Selecciona únicamente los campos que deseas enviar a Shopify:")

    campos_detectados = {}
    columnas_excel = list(df_data.columns)

    # 1. Analizar Campos Estándar presentes en el archivo
    for key_std, info_std in SCHEMA.get("campos_estandar", {}).items():
        posibles = info_std.get("posibles_columnas_excel", [])
        if any(col in columnas_excel for col in posibles):
            nombre_mostrar = info_std.get("nombre", key_std)
            campos_detectados[key_std] = f"📌 {nombre_mostrar} (`{key_std}`)"

    # 2. Analizar Metafields presentes en el archivo
    for key_meta, info_meta in SCHEMA.get("metafields", {}).items():
        posibles = info_meta.get("posibles_columnas_excel", [])
        if any(col in columnas_excel for col in posibles):
            nombre_mostrar = info_meta.get("name", key_meta)
            campos_detectados[key_meta] = f"🏷️ Metafield: {nombre_mostrar} (`custom.{key_meta}`)"

    if not campos_detectados:
        st.warning("⚠️ No se detectaron campos reconocibles por el esquema en tu archivo.")
    else:
        seleccionados_keys = st.multiselect(
            "Campos autorizados para actualizar en Shopify:",
            options=list(campos_detectados.keys()),
            default=list(campos_detectados.keys()),
            format_func=lambda k: campos_detectados[k]
        )

        st.caption(f"Se actualizarán únicamente **{len(seleccionados_keys)}** campo(s) seleccionado(s).")

        if st.button("🚀 Actualizar en Shopify vía API"):
            if not seleccionados_keys:
                st.error("❌ Debes seleccionar al menos un campo para actualizar.")
            else:
                st.warning("⚠️ Iniciando actualización masiva según campos seleccionados... No cierres la ventana.")
                
                progreso = st.progress(0)
                status_text = st.empty()
                total = len(df_data)
                exitos = 0
                errores_lista = []

                for idx, row in df_data.iterrows():
                    status_text.text(f"Procesando registro {idx + 1} de {total}...")
                    
                    product_id, handle_or_serpi = obtener_product_id(row)
                    
                    if product_id:
                        errs = actualizar_producto_con_esquema(product_id, row, campos_permitidos=seleccionados_keys)
                        if not errs:
                            exitos += 1
                        else:
                            msg = ", ".join([f"{e.get('field')}: {e.get('message')}" for e in errs])
                            errores_lista.append(f"Fila {idx+1} ({handle_or_serpi}): {msg}")
                    else:
                        errores_lista.append(f"Fila {idx+1}: No se encontró el producto en Shopify.")
                    
                    # Pausa de 0.05 segundos para evitar ConnectionResetError
                    time.sleep(0.05)
                    progreso.progress((idx + 1) / total)

                status_text.empty()
                st.success(f"🎉 Proceso finalizado. Exitosos: {exitos} | Errores: {len(errores_lista)}")

                if errores_lista:
                    with st.expander("Ver detalle de errores"):
                        for err in errores_lista:
                            st.write(f"- {err}")

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

if "busqueda_productos" in st.session_state:
    resultados = st.session_state["busqueda_productos"]
    
    if not resultados:
        st.error("❌ No se encontró ningún producto que coincida con esos criterios.")
    else:
        st.success(f"✅ Se encontraron {len(resultados)} coincidencia(s):")
        
        opciones = {f"{item['title']} | SERPI: {item['serpi']} (ID: {item['id'].split('/')[-1]})": item for item in resultados}
        
        seleccion = st.selectbox("Selecciona el producto exacto al que pertenece la portada:", list(opciones.keys()))
        producto_seleccionado = opciones[seleccion]

        st.info(f"📌 Producto Seleccionado: **{producto_seleccionado['title']}** (SERPI Metafield: `{producto_seleccionado['serpi']}`)")

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