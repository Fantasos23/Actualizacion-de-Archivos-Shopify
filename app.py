import os
import time
import json
import requests
from pathlib import Path
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timedelta
import re
import unicodedata

from subir_imagenes import buscar_producto_por_nombre_y_serpi, cargar_imagen_a_shopify

# -------------------------------------------------------------
# 1. Configuración de Entorno, Conexión API y Página
# -------------------------------------------------------------
st.set_page_config(page_title="Sincronizador SERPI ➔ Shopify", layout="wide", page_icon="📦")

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

SERPI_BASE_URL = os.getenv("SERPI_BASE_URL", "https://apis.serpi.com.co").rstrip("/")
SERPI_HEADERS = {
    "secretkey": os.getenv("SERPI_SECRETKEY", "").strip(),
    "Authorization": f"Bearer {os.getenv('SERPI_TOKEN', '').strip()}",
    "Accept": "application/json"
}

SNAPSHOT_FILE = base_dir / "control_snapshot.json"
SCHEMA_PATH = base_dir / "shopify_schema.json"

SCHEMA = {"campos_estandar": {}, "metafields": {}}
if SCHEMA_PATH.exists():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        SCHEMA = json.load(f)

# -------------------------------------------------------------
# 2. Funciones de Consulta API SERPI
# -------------------------------------------------------------
def consultar_serpi_api(endpoint, params=None):
    url = f"{SERPI_BASE_URL}{endpoint}"
    try:
        res = requests.get(url, headers=SERPI_HEADERS, params=params, timeout=45)
        if res.status_code == 200:
            return res.json().get("result", [])
    except Exception as e:
        st.error(f"Error consultando SERPI ({endpoint}): {e}")
    return []

def consultar_todos_los_registros_serpi(endpoint, params_base=None, tamano_pagina=1000, max_paginas=60):
    if params_base is None:
        params_base = {}
    todos_los_items = []
    pagina = 1
    while pagina <= max_paginas:
        params = {**params_base, "limite": tamano_pagina, "pagina": pagina}
        items = consultar_serpi_api(endpoint, params=params)
        if not items or not isinstance(items, list):
            break
        todos_los_items.extend(items)
        if len(items) < tamano_pagina:
            break
        pagina += 1
        time.sleep(0.05)
    return todos_los_items

def consultar_articulos_modificados(horas=24):
    ahora = datetime.now()
    inicio = ahora - timedelta(hours=horas)
    params = {
        "fechamodificaini": inicio.strftime("%Y-%m-%d"),
        "fechamodificafin": ahora.strftime("%Y-%m-%d"),
        "limite": 500,
        "pagina": 1
    }
    return consultar_serpi_api("/api/v1/Articulo", params=params)

def consultar_inventario_completo():
    hoy = datetime.now().strftime("%Y-%m-%d")
    return consultar_todos_los_registros_serpi("/api/v1/SaldoInventarioSinCosto", {"fechaCorte": hoy})

def consultar_precios_completos():
    return consultar_todos_los_registros_serpi("/api/v1/ListaPrecios")

# -------------------------------------------------------------
# 3. Snapshot / Archivo de Control y Memoria
# -------------------------------------------------------------
def cargar_snapshot_control():
    if SNAPSHOT_FILE.exists():
        try:
            with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def guardar_snapshot_control(data):
    try:
        with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Error guardando archivo de control: {e}")

def actualizar_sku_en_snapshot(codigo, stock=None, precio=None):
    snapshot = cargar_snapshot_control()
    codigo_str = str(codigo).strip()
    if codigo_str not in snapshot:
        snapshot[codigo_str] = {}
    if stock is not None:
        snapshot[codigo_str]["stock"] = int(float(stock))
    if precio is not None:
        snapshot[codigo_str]["precio"] = float(precio)
    snapshot[codigo_str]["ultima_actualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    guardar_snapshot_control(snapshot)

def inicializar_memoria_procesados():
    if "productos_procesados_ids" not in st.session_state:
        st.session_state["productos_procesados_ids"] = set()

def registrar_producto_procesado(codigo_serpi):
    inicializar_memoria_procesados()
    st.session_state["productos_procesados_ids"].add(str(codigo_serpi).strip())

def esta_procesado(codigo_serpi):
    inicializar_memoria_procesados()
    return str(codigo_serpi).strip() in st.session_state["productos_procesados_ids"]
def obtener_precio_puntual_serpi(codigo_sku):
    """Consulta el precio de un SKU específico directamente en SERPI sin recorrer todo el catálogo."""
    try:
        codigo_str = str(codigo_sku).strip()
        # Probar consulta por código o idArticulo
        res = consultar_serpi_api("/api/v1/ListaPrecioDetalle", params={"codigo": codigo_str, "limite": 1})
        if res and isinstance(res, list) and len(res) > 0:
            return float(res[0].get("precio", 0) or 0)
        
        # Fallback a ListaPrecios filtrada
        res_lp = consultar_serpi_api("/api/v1/ListaPrecios", params={"codigo": codigo_str, "limite": 1})
        if res_lp and isinstance(res_lp, list) and len(res_lp) > 0:
            return float(res_lp[0].get("precio", 0) or 0)
    except Exception:
        pass
    return None

def obtener_stock_puntual_serpi(codigo_sku):
    """Consulta las existencias de un SKU específico en la fecha de corte actual."""
    try:
        codigo_str = str(codigo_sku).strip()
        hoy = datetime.now().strftime("%Y-%m-%d")
        res = consultar_serpi_api("/api/v1/SaldoInventarioSinCosto", params={"fechaCorte": hoy, "codigo": codigo_str, "limite": 1})
        if res and isinstance(res, list) and len(res) > 0:
            return int(float(res[0].get("saldo", 0) or 0))
    except Exception:
        pass
    return None
# -------------------------------------------------------------
# 4. Funciones Auxiliares y Mapeo Shopify
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
    if isinstance(row, dict):
        keys_map = {str(k).strip().lower(): k for k in row.keys()}
        for col_posible in lista_columnas_posibles:
            col_clean = str(col_posible).strip().lower()
            if col_clean in keys_map:
                val = row[keys_map[col_clean]]
                if val is not None and str(val).strip() != '' and str(val).lower() != 'nan':
                    return str(val).strip()
    elif isinstance(row, pd.Series):
        cols_map = {str(c).strip().lower(): c for c in row.index}
        for col_posible in lista_columnas_posibles:
            col_clean = str(col_posible).strip().lower()
            if col_clean in cols_map:
                col_real = cols_map[col_clean]
                val = row[col_real]
                if pd.notna(val) and str(val).strip() != '' and str(val).lower() != 'nan':
                    return str(val).strip()
    return None

def limpiar_para_handle(texto):
    if not texto:
        return ""
    texto = unicodedata.normalize('NFD', str(texto))
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9\s-]', '', texto)
    texto = re.sub(r'[\s-]+', '-', texto).strip('-')
    return texto

def formatear_descripcion_html(texto):
    if not texto or str(texto).strip() == "" or str(texto).lower() == "nan":
        return ""
    lineas = [l.strip() for l in str(texto).splitlines() if l.strip()]
    if not lineas:
        return ""
    return "".join(f"<p>{linea}</p>" for linea in lineas)

def obtener_product_id(row):
    v_serpi_raw = obtener_valor_fila(row, ["serpi", "custom.serpi", "serpi (product.metafields.custom.serpi)", "SERPI", "codigo", "sku"])
    v_desc = obtener_valor_fila(row, ["title", "title (product.title)", "descripcion", "descripcion_articulo", "Nombre", "Título"])

    v_serpi_plano = str(v_serpi_raw).strip() if v_serpi_raw else ""
    v_serpi_num = re.sub(r'[^0-9a-zA-Z]', '', v_serpi_plano) if v_serpi_plano else ""

    if v_serpi_plano:
        query_sku = """
        query getProductBySku($query: String!) {
          products(first: 5, query: $query) {
            edges {
              node {
                id
                title
                handle
              }
            }
          }
        }
        """
        res_sku = ejecutar_graphql(query_sku, {"query": f"sku:'{v_serpi_plano}' OR sku:'{v_serpi_num}'"})
        prods_sku = res_sku.get("data", {}).get("products", {}).get("edges", []) if res_sku.get("data") else []
        if prods_sku:
            return prods_sku[0]["node"]["id"], f"SKU: {v_serpi_plano}"

    handle_busqueda = limpiar_para_handle(v_desc) if v_desc else ""
    if handle_busqueda:
        query_h = """
        query getProductIdByHandle($handle: String!) {
          productByHandle(handle: $handle) {
            id
            handle
            title
          }
        }
        """
        data_h = ejecutar_graphql(query_h, {"handle": handle_busqueda})
        prod_h = data_h.get("data", {}).get("productByHandle") if data_h.get("data") else None
        if prod_h:
            return prod_h["id"], f"Handle: {handle_busqueda}"

    if v_desc:
        palabras = [p for p in re.findall(r'\w+', v_desc) if len(p) > 2]
        query_t_str = " AND ".join(palabras[:3]) if palabras else v_desc

        query_t = """
        query getProductsByTitleScan($query: String!) {
          products(first: 10, query: $query) {
            edges {
              node {
                id
                title
                handle
                metafields(first: 10) {
                  edges {
                    node {
                      key
                      value
                    }
                  }
                }
              }
            }
          }
        }
        """
        res_t = ejecutar_graphql(query_t, {"query": f"title:{query_t_str}"})
        prods_t = res_t.get("data", {}).get("products", {}).get("edges", []) if res_t.get("data") else []

        for edge in prods_t:
            node = edge["node"]
            metafields = {m["node"]["key"]: m["node"]["value"] for m in node.get("metafields", {}).get("edges", [])}
            serpi_val = str(metafields.get("serpi", "")).strip()
            
            if serpi_val and (serpi_val == v_serpi_plano or serpi_val == v_serpi_num):
                return node["id"], f"Metafield custom.serpi: {serpi_val}"

            t_shopify = limpiar_para_handle(node["title"])
            t_serpi = limpiar_para_handle(v_desc)
            if t_shopify and t_serpi and (t_shopify == t_serpi or t_shopify in t_serpi or t_serpi in t_shopify):
                return node["id"], f"Título Coincidente: {node['title'][:25]}"

    return None, None

def actualizar_stock_shopify(product_id, nueva_cantidad):
    """
    Activa el seguimiento de inventario (Tracked: True) y actualiza 
    la cantidad física de la primera variante del producto.
    """
    try:
        # 1. Obtener la Variante, su InventoryItem y su Location ID
        query_var = """
        query getProductInventoryDetails($id: ID!) {
          product(id: $id) {
            variants(first: 1) {
              edges {
                node {
                  id
                  inventoryItem {
                    id
                    tracked
                  }
                }
              }
            }
          }
          locations(first: 1) {
            edges {
              node {
                id
              }
            }
          }
        }
        """
        res = ejecutar_graphql(query_var, {"id": product_id})
        if not res or "data" not in res or not res["data"].get("product"):
            return [{"field": ["product"], "message": "No se encontró el producto en Shopify."}]

        variants = res["data"]["product"].get("variants", {}).get("edges", [])
        locations = res["data"].get("locations", {}).get("edges", [])
        
        if not variants:
            return [{"field": ["variant"], "message": "No se encontró ninguna variante."}]
        if not locations:
            return [{"field": ["location"], "message": "No se encontró ninguna ubicación de inventario."}]
            
        variant_node = variants[0]["node"]
        inventory_item_id = variant_node["inventoryItem"]["id"]
        location_id = locations[0]["node"]["id"]
        variant_gid = variant_node["id"]
        variant_numeric_id = variant_gid.split("/")[-1]

        # 2. Forzar que el InventoryItem tenga activo el rastreo de inventario
        mutation_track = """
        mutation activateTracking($id: ID!, $input: InventoryItemInput!) {
          inventoryItemUpdate(id: $id, input: $input) {
            inventoryItem {
              id
              tracked
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        ejecutar_graphql(mutation_track, {
            "id": inventory_item_id,
            "input": {"tracked": True}
        })

        # 3. Asignar el stock usando la API REST de variantes
        REST_URL = f"https://{RAW_SHOP_URL}/admin/api/{API_VERSION}"
        url_variant_rest = f"{REST_URL}/variants/{variant_numeric_id}.json"
        
        payload_variant = {
            "variant": {
                "id": int(variant_numeric_id),
                "inventory_management": "shopify",
                "inventory_quantity": int(float(nueva_cantidad))
            }
        }
        res_rest = requests.put(url_variant_rest, json=payload_variant, headers=HEADERS, timeout=15)
        
        if res_rest.status_code in [200, 201]:
            return []
        else:
            return [{"field": ["rest_api"], "message": f"Error REST {res_rest.status_code}: {res_rest.text[:150]}"}]

    except Exception as e:
        return [{"field": ["inventory_exception"], "message": str(e)}]

def actualizar_producto_con_esquema(product_id, row, campos_permitidos=None):
    errores_totales = []
    campos_estandar = SCHEMA.get("campos_estandar", {})
    input_product = {"id": product_id}
    
    # 1. Descripción HTML
    if campos_permitidos is None or "descriptionHtml" in campos_permitidos:
        posibles_desc = campos_estandar.get("descriptionHtml", {}).get("posibles_columnas_excel", ["descriptionHtml", "descripcion", "descripcion_larga"])
        v_desc = obtener_valor_fila(row, posibles_desc)
        if v_desc is not None:
            input_product["descriptionHtml"] = formatear_descripcion_html(v_desc)

    # 2. Vendor / Proveedor
    if campos_permitidos is None or "vendor" in campos_permitidos:
        posibles_vendor = campos_estandar.get("vendor", {}).get("posibles_columnas_excel", ["vendor", "proveedor", "editorial"])
        v_vendor = obtener_valor_fila(row, posibles_vendor)
        if v_vendor is not None:
            input_product["vendor"] = str(v_vendor)

    # 3. Product Type / Categoría
    if campos_permitidos is None or "productType" in campos_permitidos:
        posibles_type = campos_estandar.get("productType", {}).get("posibles_columnas_excel", ["productType", "tipo", "categoria", "linea"])
        v_type = obtener_valor_fila(row, posibles_type)
        if v_type is not None:
            input_product["productType"] = str(v_type)

    # 4. Tags / Etiquetas (Nativo de Shopify)
    if campos_permitidos is None or "tags" in campos_permitidos:
        posibles_tags = campos_estandar.get("tags", {}).get("posibles_columnas_excel", ["tags", "etiquetas", "Etiquetas", "TAGS"])
        v_tags = obtener_valor_fila(row, posibles_tags)
        if v_tags is not None:
            # Soporta strings separados por coma o listas
            if isinstance(v_tags, list):
                input_product["tags"] = [str(t).strip() for t in v_tags if str(t).strip()]
            else:
                input_product["tags"] = [t.strip() for t in str(v_tags).split(',') if t.strip()]

    # 5. Metafields (custom.*)
    metafields_input = []
    metafields_schema = SCHEMA.get("metafields", {})
    
    for key_meta, info_meta in metafields_schema.items():
        if campos_permitidos is not None and key_meta not in campos_permitidos:
            continue
        
        # Ignorar si es el campo de etiquetas o descripción ya procesado como nativo
        if key_meta.lower() in ["etiquetas", "tags", "descripcion", "descripcionhtml"]:
            continue
            
        posibles = info_meta.get("posibles_columnas_excel", [key_meta])
        v_meta = obtener_valor_fila(row, posibles)
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
                "namespace": info_meta.get("namespace", "custom"),
                "key": info_meta.get("key", key_meta),
                "value": val_str,
                "type": tipo_meta
            })

    if metafields_input:
        input_product["metafields"] = metafields_input

    # Ejecutar actualización de Producto y Metafields
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

    # 6. Variantes (Precio, SKU, Taxable)
    v_price = None
    if campos_permitidos is None or "price" in campos_permitidos:
        v_price = obtener_valor_fila(row, campos_estandar.get("price", {}).get("posibles_columnas_excel", ["price", "precio"]))

    v_sku = None
    if campos_permitidos is None or "sku" in campos_permitidos:
        v_sku = obtener_valor_fila(row, campos_estandar.get("sku", {}).get("posibles_columnas_excel", ["sku", "codigo", "serpi"]))

    v_tax = None
    if campos_permitidos is None or "taxable" in campos_permitidos:
        v_tax = obtener_valor_fila(row, campos_estandar.get("taxable", {}).get("posibles_columnas_excel", ["taxable", "impuesto", "iva"]))

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
                variant_payload["taxable"] = val_str in ["TRUE", "1", "SI", "SÍ", "YES"]

            REST_URL = f"https://{RAW_SHOP_URL}/admin/api/{API_VERSION}"
            url_variant_rest = f"{REST_URL}/variants/{variant_numeric_id}.json"
            
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
                    time.sleep(2)
                    if intentos >= 3:
                        errores_totales.append({"field": ["connection"], "message": "Error de conexión persistente con Shopify."})

    return errores_totales

def crear_producto_en_shopify(item_serpi):
    try:
        codigo = str(item_serpi.get("codigo", "")).strip()
        titulo = str(item_serpi.get("descripcion", "")).strip()
        precio = float(item_serpi.get("precio", 0) or 0)
        stock = float(item_serpi.get("saldo", 0) or 0)
        cp = item_serpi.get("camposPersonalizados", {}) or {}

        handle = limpiar_para_handle(titulo)
        desc_raw = cp.get("descripcion") or item_serpi.get("descripcion_larga") or ""
        desc_html = formatear_descripcion_html(desc_raw)

        tags_raw = cp.get("etiquetas") or cp.get("tags") or ""
        tags_list = []
        if isinstance(tags_raw, list):
            tags_list = [str(t).strip() for t in tags_raw if str(t).strip()]
        elif isinstance(tags_raw, str) and tags_raw.strip():
            tags_list = [t.strip() for t in tags_raw.split(',') if t.strip()]

        metafields_input = [{
            "namespace": "custom",
            "key": "serpi",
            "value": codigo,
            "type": "single_line_text_field"
        }]

        for k_meta, v_meta in cp.items():
            if k_meta.lower() in ["descripcion", "etiquetas", "tags"]:
                continue
            if v_meta is not None and str(v_meta).strip():
                val_limpio = str(v_meta).strip()
                tipo_campo = "multi_line_text_field" if "\n" in val_limpio or "\r" in val_limpio else "single_line_text_field"
                metafields_input.append({
                    "namespace": "custom",
                    "key": k_meta,
                    "value": val_limpio,
                    "type": tipo_campo
                })

        input_product = {
            "title": titulo,
            "handle": handle,
            "descriptionHtml": desc_html,
            "tags": tags_list,
            "status": "ACTIVE",
            "metafields": metafields_input
        }

        mutation_create = """
        mutation productCreate($input: ProductInput!) {
          productCreate(input: $input) {
            product {
              id
              handle
              variants(first: 1) {
                edges {
                  node {
                    id
                  }
                }
              }
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        res = ejecutar_graphql(mutation_create, {"input": input_product})
        if not res or "data" not in res:
            return None, [{"field": ["graphql"], "message": "Respuesta vacía o error de red en Shopify."}]

        data = res.get("data", {}).get("productCreate", {})
        errs = data.get("userErrors", [])
        if errs:
            return None, errs

        product_created = data.get("product")
        if not product_created:
            return None, [{"field": ["productCreate"], "message": "Shopify no pudo crear el registro."}]

        new_product_id = product_created.get("id")

        # 1. Configurar SKU, Precio y Activar seguimiento en la Variante
        v_edges = product_created.get("variants", {}).get("edges", [])
        if v_edges and new_product_id:
            variant_gid = v_edges[0]["node"]["id"]
            variant_numeric_id = variant_gid.split("/")[-1]
            REST_URL = f"https://{RAW_SHOP_URL}/admin/api/{API_VERSION}"
            url_variant_rest = f"{REST_URL}/variants/{variant_numeric_id}.json"
            
            payload_variant = {
                "variant": {
                    "id": int(variant_numeric_id),
                    "sku": codigo,
                    "price": str(precio),
                    "inventory_management": "shopify"
                }
            }
            requests.put(url_variant_rest, json=payload_variant, headers=HEADERS, timeout=15)

        # 2. Forzar el rastreo y asignar el stock inicial (aunque sea 0)
        if new_product_id:
            actualizar_stock_shopify(new_product_id, stock)

        return new_product_id, []
    except Exception as e:
        return None, [{"field": ["create_exception"], "message": str(e)}]
    
# -------------------------------------------------------------
# 5. MODAL DE PREVISUALIZACIÓN UNIFICADO
# -------------------------------------------------------------
@st.dialog("🔍 Inspector de Sincronización SERPI ➔ Shopify", width="large")
def mostrar_modal_previsualizacion_unificado(item_consolidado):
    codigo_serpi = item_consolidado.get("codigo")
    titulo_serpi = item_consolidado.get("descripcion", "")
    cp_serpi = item_consolidado.get("camposPersonalizados", {}) or {}
    
    nuevo_stock = item_consolidado.get("saldo")
    nuevo_precio = item_consolidado.get("precio")
    
    if nuevo_precio is None:
        nuevo_precio = obtener_precio_puntual_serpi(codigo_serpi)
        item_consolidado["precio"] = nuevo_precio

    if nuevo_stock is None:
        nuevo_stock = obtener_stock_puntual_serpi(codigo_serpi)
        item_consolidado["saldo"] = nuevo_stock

    with st.container(border=True):
        st.subheader(f"📖 {titulo_serpi}")
        c_head1, c_head2, c_head3 = st.columns(3)
        c_head1.metric("Código SERPI / SKU", str(codigo_serpi))
        c_head2.metric("Stock en ERP", f"{int(float(nuevo_stock))} unid." if nuevo_stock is not None else "0 unid.")
        c_head3.metric("Precio ERP", f"${nuevo_precio:,.0f}" if nuevo_precio is not None else "No asignado")

    with st.spinner("Verificando coincidencia en tienda Shopify..."):
        fila_virtual = pd.Series({
            "serpi": codigo_serpi,
            "descripcion": titulo_serpi,
            "price": nuevo_precio,
            **cp_serpi
        })
        
        product_id, match_origen = obtener_product_id(fila_virtual)
        
        # ---------------------------------------------------------
        # CASO A: EL PRODUCTO NO EXISTE EN SHOPIFY (CREAR)
        # ---------------------------------------------------------
        if not product_id:
            st.error("⚠️ Este producto no se encuentra registrado en el catálogo de Shopify.")
            
            with st.container(border=True):
                st.markdown("#### 📝 Ficha Técnica a Crear")
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Título:** {titulo_serpi}")
                    st.write(f"**Handle generado:** `{limpiar_para_handle(titulo_serpi)}`")
                    st.write(f"**SKU / Metafield SERPI:** `{codigo_serpi}`")
                with c2:
                    autor = cp_serpi.get("autor") or "No especificado"
                    editorial = cp_serpi.get("editorial") or "No especificado"
                    paginas = cp_serpi.get("paginas") or "N/A"
                    st.write(f"**Autor:** {autor}")
                    st.write(f"**Editorial:** {editorial}")
                    st.write(f"**Páginas:** {paginas}")
            
            st.write("")
            if st.button("✨ Dar de Alta y Crear Producto en Shopify", type="primary", use_container_width=True, key="btn_create_modal"):
                with st.spinner("Creando producto y configurando inventario..."):
                    new_id, errs = crear_producto_en_shopify(item_consolidado)
                    if new_id:
                        registrar_producto_procesado(codigo_serpi)
                        actualizar_sku_en_snapshot(codigo_serpi, stock=nuevo_stock, precio=nuevo_precio)
                        st.session_state[f"creado_{codigo_serpi}"] = new_id
                        st.success(f"🎉 ¡Producto creado exitosamente! (ID: `{new_id}`)")
                    else:
                        st.error(f"Error al crear: {errs}")

            # Desplegar carga de imagen si se acaba de crear
            id_activo = st.session_state.get(f"creado_{codigo_serpi}")
            if id_activo:
                st.divider()
                with st.container(border=True):
                    st.markdown("#### 🖼️ Asignar Portada al Producto Recién Creado")
                    up_img = st.file_uploader("Selecciona la imagen de la portada", type=["jpg", "png", "webp", "jpeg"], key=f"up_img_modal_{codigo_serpi}")
                    if up_img and st.button("🚀 Subir e Integrar Portada", type="primary", use_container_width=True, key=f"btn_up_modal_{codigo_serpi}"):
                        with st.spinner("Subiendo portada a Shopify CDN..."):
                            ok, msg = cargar_imagen_a_shopify(id_activo, up_img.read(), up_img.name)
                            if ok:
                                st.balloons()
                                st.success("🎉 ¡Portada asignada e integrada a la galería de Shopify!")
                            else:
                                st.error(f"Error al subir imagen: {msg}")

        # ---------------------------------------------------------
        # CASO B: EL PRODUCTO YA EXISTE (ACTUALIZAR / PORTADA)
        # ---------------------------------------------------------
        else:
            query_detalles = """
            query getProductFullDetails($id: ID!) {
              product(id: $id) {
                id
                title
                handle
                variants(first: 1) {
                  edges {
                    node {
                      price
                      inventoryQuantity
                    }
                  }
                }
                metafields(first: 20) {
                  edges {
                    node {
                      key
                      value
                    }
                  }
                }
              }
            }
            """
            res = ejecutar_graphql(query_detalles, {"id": product_id})
            prod_sp = res.get("data", {}).get("product", {}) if res.get("data") else {}
            var_sp = prod_sp.get("variants", {}).get("edges", [])[0]["node"] if prod_sp.get("variants", {}).get("edges") else {}
            
            stock_sp = var_sp.get("inventoryQuantity", 0)
            precio_sp = var_sp.get("price", "0.00")
            meta_sp_dict = {edge["node"]["key"]: edge["node"]["value"] for edge in prod_sp.get("metafields", {}).get("edges", [])}

            st.success(f"🔗 Vinculado a producto en Shopify vía: **{match_origen}**")
            
            col_comp1, col_comp2 = st.columns(2)
            with col_comp1:
                with st.container(border=True):
                    st.markdown("##### 📦 Existencias y Precios")
                    cambios_list = []
                    if nuevo_stock is not None:
                        cambios_list.append({
                            "Atributo": "Inventario",
                            "Shopify": f"{stock_sp} unid.",
                            "SERPI": f"{int(float(nuevo_stock))} unid.",
                            "Impacto": "🔄 Cambia" if str(stock_sp) != str(int(float(nuevo_stock))) else "✅ Al día"
                        })
                    if nuevo_precio is not None:
                        cambios_list.append({
                            "Atributo": "Precio",
                            "Shopify": f"${float(precio_sp):,.0f}",
                            "SERPI": f"${nuevo_precio:,.0f}",
                            "Impacto": "🔄 Cambia" if str(precio_sp) != str(nuevo_precio) else "✅ Al día"
                        })
                    st.dataframe(pd.DataFrame(cambios_list), hide_index=True, use_container_width=True)

            with col_comp2:
                with st.container(border=True):
                    st.markdown("##### 🏷️ Metafields / Información del Libro")
                    meta_comp = []
                    for k_cp in ["autor", "editorial", "paginas", "presentacion"]:
                        v_erp = str(cp_serpi.get(k_cp, "") or "").strip()
                        v_sh = str(meta_sp_dict.get(k_cp, "") or "").strip()
                        if v_erp or v_sh:
                            meta_comp.append({
                                "Campo": k_cp.capitalize(),
                                "Shopify": v_sh if v_sh else "—",
                                "SERPI": v_erp if v_erp else "—"
                            })
                    if meta_comp:
                        st.dataframe(pd.DataFrame(meta_comp), hide_index=True, use_container_width=True)
                    else:
                        st.caption("Sin diferencias de metafields registradas.")

            st.write("")
            if st.button("🚀 Aplicar Cambios a este Producto en Shopify", type="primary", use_container_width=True, key="btn_update_modal"):
                with st.spinner("Sincronizando con Shopify..."):
                    errs_totales = []
                    if nuevo_stock is not None:
                        err_st = actualizar_stock_shopify(product_id, nuevo_stock)
                        if err_st: errs_totales.extend(err_st)
                    err_pr = actualizar_producto_con_esquema(product_id, fila_virtual)
                    if err_pr: errs_totales.extend(err_pr)
                    
                    if not errs_totales:
                        registrar_producto_procesado(codigo_serpi)
                        actualizar_sku_en_snapshot(codigo_serpi, stock=nuevo_stock, precio=nuevo_precio)
                        st.success(f"🎉 ¡Producto '{prod_sp.get('title')}' actualizado con éxito!")
                    else:
                        st.error(f"Errores al sincronizar: {errs_totales}")

            # Subida de portada integrada para productos existentes
            with st.expander("🖼️ Actualizar o Añadir Portada a este Libro", expanded=False):
                up_img_ex = st.file_uploader("Selecciona archivo de imagen", type=["jpg", "png", "webp", "jpeg"], key=f"up_ex_{codigo_serpi}")
                if up_img_ex and st.button("🚀 Cargar Imagen a Galería de Shopify", type="secondary", use_container_width=True, key=f"btn_up_ex_{codigo_serpi}"):
                    with st.spinner("Subiendo portada..."):
                        ok, msg = cargar_imagen_a_shopify(product_id, up_img_ex.read(), up_img_ex.name)
                        if ok:
                            st.balloons()
                            st.success("🎉 ¡Portada agregada exitosamente!")
                        else:
                            st.error(f"Error: {msg}")

# -------------------------------------------------------------
# 6. Interfaz Principal Streamlit
# -------------------------------------------------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2897/2897818.png", width=50)
    st.title("Conexión & Estado")
    
    # 1. Estado de Conexión Shopify
    if API_TOKEN and RAW_SHOP_URL:
        st.success(f"**Shopify Conectado**\n\n`{RAW_SHOP_URL}`")
    else:
        st.error("**Shopify Desconectado**\n\nVerifica las credenciales en el archivo `.env`")
    
    st.write("")
    
    # 2. Estado de Conexión ERP SERPI
    serpi_key = SERPI_HEADERS.get("secretkey")
    serpi_token = SERPI_HEADERS.get("Authorization", "").replace("Bearer ", "").strip()
    
    if serpi_key and serpi_token:
        st.success(f"**SERPI Conectado**\n\n`{SERPI_BASE_URL}`")
    else:
        st.error("**SERPI Desconectado**\n\nFalta SecretKey o Token en el archivo `.env`")
    

st.title("📦 Centro de Sincronización SERPI ➔ Shopify")
st.caption("Automatización y auditoría de inventarios, precios y catálogo en tiempo real.")

tab_unificado, tab_excel, tab_portadas = st.tabs([
    "⚡ Sincronización Automática", 
    "📄 Carga Manual (Excel/CSV)",
    "🖼️ Galería de Portadas"
])

# =============================================================
# PESTAÑA 1: SINCRONIZACIÓN AUTOMÁTICA
# =============================================================
with tab_unificado:
    inicializar_memoria_procesados()
    cant_procesados = len(st.session_state["productos_procesados_ids"])

    with st.container(border=True):
        col_ctrl1, col_ctrl2, col_ctrl3, col_ctrl4 = st.columns([2, 2, 2, 1])
        with col_ctrl1:
            rango_unificado = st.pills("Ventana ERP", [24, 48, 72], format_func=lambda x: f"Últimas {x}h", default=24, key="rango_unificado")
        with col_ctrl2:
            st.write("")
            btn_fast_sync = st.button("⚡ Auditoría Rápida (Nuevos/Modificados)", type="primary", use_container_width=True, key="btn_fast_sync")
        with col_ctrl3:
            st.write("")
            btn_full_snapshot = st.button("📦 Reconstruir Control Global (40k)", use_container_width=True, key="btn_full_snapshot")
        with col_ctrl4:
            st.write("")
            if cant_procesados > 0:
                if st.button(f"🧹 ({cant_procesados})", help="Limpiar productos procesados", use_container_width=True):
                    st.session_state["productos_procesados_ids"] = set()
                    st.rerun()

    # --- FLUJO 1: Auditoría Rápida (Sin sobrecarga) ---
    if btn_fast_sync:
        snapshot_previo = cargar_snapshot_control()
        with st.spinner("Consultando artículos modificados recientemente en SERPI..."):
            articulos_raw = consultar_articulos_modificados(horas=rango_unificado)
            mapa_novedades = {}
            
            for art in articulos_raw:
                cod = str(art.get("codigo", "")).strip()
                if cod:
                    stock_snap = snapshot_previo.get(cod, {}).get("stock")
                    precio_snap = snapshot_previo.get(cod, {}).get("precio")
                    
                    mapa_novedades[cod] = {
                        "codigo": cod,
                        "descripcion": art.get("descripcion", ""),
                        "camposPersonalizados": art.get("camposPersonalizados", {}) or {},
                        "saldo": stock_snap,
                        "precio": precio_snap,
                        "motivo": "📝 Ficha Modificada Recientemente"
                    }
            
            lista_final = list(mapa_novedades.values())
            if lista_final:
                st.session_state["cache_unificado"] = lista_final
                st.session_state["filtro_kpi_activo"] = "TODOS"
                st.success(f"🎯 Se detectaron **{len(lista_final)}** productos modificados en las últimas {rango_unificado}h.")
            else:
                st.session_state.pop("cache_unificado", None)
                st.info("✅ Sin modificaciones de catálogo en el rango horario seleccionado.")

    # --- FLUJO 2: Reconstrucción Global Opcional (Snapshot Completo) ---
    if btn_full_snapshot:
        snapshot_previo = cargar_snapshot_control()
        with st.spinner("Paginando catálogo completo de SERPI (40.000 ítems)..."):
            saldos_raw = consultar_inventario_completo()
            precios_raw = consultar_precios_completos()
            
            nuevo_snapshot = dict(snapshot_previo)
            for item in saldos_raw:
                cod = str(item.get("codigo", "")).strip()
                if cod:
                    if cod not in nuevo_snapshot:
                        nuevo_snapshot[cod] = {}
                    nuevo_snapshot[cod]["stock"] = int(float(item.get("saldo", 0) or 0))
                    
            for item in precios_raw:
                cod = str(item.get("codigo") or item.get("id_articulo", "")).strip()
                if cod:
                    if cod not in nuevo_snapshot:
                        nuevo_snapshot[cod] = {}
                    nuevo_snapshot[cod]["precio"] = float(item.get("precio", 0) or 0)
                    
            guardar_snapshot_control(nuevo_snapshot)
            st.success(f"🎉 Base de control global actualizada con **{len(nuevo_snapshot)}** productos.")

    # -------------------------------------------------------------
    # RENDERIZADO INTERACTIVO: KPIS COMO BOTONES, BUSCADOR Y MATRIZ
    # -------------------------------------------------------------
    if "cache_unificado" in st.session_state and st.session_state["cache_unificado"]:
        lista_cache = st.session_state["cache_unificado"]

        if "filtro_kpi_activo" not in st.session_state:
            st.session_state["filtro_kpi_activo"] = "TODOS"

        total_art = len(lista_cache)
        con_stock = sum(1 for p in lista_cache if "📦 Stock" in str(p.get("motivo", "")))
        con_precio = sum(1 for p in lista_cache if "💰 Precio" in str(p.get("motivo", "")))
        pendientes_count = sum(1 for p in lista_cache if not esta_procesado(p.get("codigo")))

        # 1. BOTONES INTERACTIVOS DE KPI
        st.write("")
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

        with kpi_col1:
            is_active = st.session_state["filtro_kpi_activo"] == "TODOS"
            if st.button(
                f"📦 Total Novedades\n### {total_art}", 
                type="primary" if is_active else "secondary", 
                use_container_width=True,
                key="btn_kpi_todos"
            ):
                st.session_state["filtro_kpi_activo"] = "TODOS"
                st.rerun()

        with kpi_col2:
            is_active = st.session_state["filtro_kpi_activo"] == "STOCK"
            if st.button(
                f"🔄 Con Cambio Stock\n### {con_stock}", 
                type="primary" if is_active else "secondary", 
                use_container_width=True,
                key="btn_kpi_stock"
            ):
                st.session_state["filtro_kpi_activo"] = "STOCK"
                st.rerun()

        with kpi_col3:
            is_active = st.session_state["filtro_kpi_activo"] == "PRECIO"
            if st.button(
                f"💰 Con Cambio Precio\n### {con_precio}", 
                type="primary" if is_active else "secondary", 
                use_container_width=True,
                key="btn_kpi_precio"
            ):
                st.session_state["filtro_kpi_activo"] = "PRECIO"
                st.rerun()

        with kpi_col4:
            is_active = st.session_state["filtro_kpi_activo"] == "PENDIENTES"
            if st.button(
                f"⏳ Pendientes por Aplicar\n### {pendientes_count}", 
                type="primary" if is_active else "secondary", 
                use_container_width=True,
                key="btn_kpi_pendientes"
            ):
                st.session_state["filtro_kpi_activo"] = "PENDIENTES"
                st.rerun()

        filtro_actual = st.session_state["filtro_kpi_activo"]
        if filtro_actual != "TODOS":
            st.info(f"🔍 Vista filtrada por: **{filtro_actual}** — Mostrando productos de esta categoría.")

        st.divider()

        # Filtrar elementos según el KPI activo
        libros_segmentados = []
        for p in lista_cache:
            cod = str(p.get("codigo", "")).strip()
            motivo = str(p.get("motivo", ""))
            procesado = esta_procesado(cod)

            if filtro_actual == "STOCK" and "📦 Stock" not in motivo:
                continue
            elif filtro_actual == "PRECIO" and "💰 Precio" not in motivo:
                continue
            elif filtro_actual == "PENDIENTES" and procesado:
                continue

            libros_segmentados.append(p)

        # 2. INSPECTOR INDIVIDUAL CON BUSCADOR EN VIVO
        with st.container(border=True):
            st.markdown("#### 🔎 Inspección y Actualización Focalizada")
            
            col_search, col_filt = st.columns([3, 1])
            with col_search:
                filtro_texto = st.text_input(
                    "Buscar por Título, Código SKU, Autor o Editorial:",
                    placeholder="Escribe para filtrar la lista instantáneamente...",
                    key="search_inspector_input"
                ).strip().lower()
            with col_filt:
                st.write("")
                ocultar_completados = st.toggle("Ocultar ya procesados", value=False)
            
            libros_disponibles = []
            for p in libros_segmentados:
                cod = str(p.get("codigo", "")).lower()
                tit = str(p.get("descripcion", "")).lower()
                cp = p.get("camposPersonalizados", {}) or {}
                aut = str(cp.get("autor", "")).lower()
                edt = str(cp.get("editorial", "")).lower()
                
                if ocultar_completados and esta_procesado(p.get("codigo")):
                    continue
                
                if not filtro_texto or (filtro_texto in cod or filtro_texto in tit or filtro_texto in aut or filtro_texto in edt):
                    libros_disponibles.append(p)

            opciones_unificadas = {
                f"{'✅ ' if esta_procesado(p.get('codigo')) else '⏳ '}[{p.get('codigo')}] {p.get('descripcion')}": p 
                for p in libros_disponibles
            }
            
            col_drop, col_btn_modal = st.columns([4, 2])
            with col_drop:
                if opciones_unificadas:
                    prod_u_key = st.selectbox(
                        "Selecciona un producto para auditar:", 
                        list(opciones_unificadas.keys()), 
                        label_visibility="collapsed",
                        key="select_focalizado_dropdown"
                    )
                else:
                    st.warning("🔍 No se encontraron productos que coincidan con la búsqueda o filtro actual.")
                    prod_u_key = None

            with col_btn_modal:
                if prod_u_key and st.button("🔍 Abrir Inspector", type="primary", use_container_width=True, key="btn_open_inspector_search"):
                    mostrar_modal_previsualizacion_unificado(opciones_unificadas[prod_u_key])

        # 3. MATRIZ DE NOVEDADES
        st.write("")
        st.markdown(f"#### 📊 Matriz de Novedades ({len(libros_disponibles)} productos)")
        
        resumen_tabla = []
        for p in libros_disponibles:
            cod = str(p.get("codigo")).strip()
            ya_listo = esta_procesado(cod)
            cp = p.get("camposPersonalizados", {}) or {}
            
            resumen_tabla.append({
                "Estado": "✅ PROCESADO" if ya_listo else "⏳ PENDIENTE",
                "Código SKU": cod,
                "Título del Libro": p.get("descripcion"),
                "Motivo / Variación": p.get("motivo", "—"),
                "Stock SERPI": f"{int(float(p.get('saldo')))}" if p.get("saldo") is not None else "—",
                "Precio SERPI": f"${p.get('precio'):,.0f}" if p.get("precio") is not None else "—",
                "Autor": cp.get("autor", "—"),
                "Editorial": cp.get("editorial", "—")
            })
            
        df_resumen = pd.DataFrame(resumen_tabla)
        if not df_resumen.empty:
            st.dataframe(
                df_resumen, 
                width="stretch", 
                height=320, 
                hide_index=True,
                column_config={
                    "Estado": st.column_config.TextColumn("Estado", width="small"),
                    "Código SKU": st.column_config.TextColumn("Código SKU", width="small"),
                    "Título del Libro": st.column_config.TextColumn("Título del Libro", width="medium"),
                    "Motivo / Variación": st.column_config.TextColumn("Motivo / Variación", width="medium")
                }
            )

        # 4. SINCRONIZACIÓN MASIVA EN LOTE
        st.write("")
        with st.container(border=True):
            col_mas_info, col_mas_btn = st.columns([3, 2])
            with col_mas_info:
                st.markdown("##### ⚡ Sincronización en Lote")
                st.caption(f"Se actualizarán todos los **{pendientes_count}** productos pendientes en Shopify.")
            with col_mas_btn:
                st.write("")
                if st.button("🚀 Aplicar Todo el Lote en Shopify", type="primary", use_container_width=True, key="btn_masivo_global"):
                    progreso = st.progress(0)
                    status = st.empty()
                    pendientes = [p for p in lista_cache if not esta_procesado(p.get("codigo"))]
                    total_p = len(pendientes)
                    exitos, errores = 0, 0
                    
                    if total_p == 0:
                        st.info("No hay productos pendientes por sincronizar en la lista.")
                    else:
                        for idx, item in enumerate(pendientes):
                            cod_serpi = item.get("codigo")
                            tit_serpi = item.get("descripcion", "")
                            cp_serpi = item.get("camposPersonalizados", {}) or {}
                            stk_serpi = item.get("saldo")
                            prc_serpi = item.get("precio")
                            
                            status.text(f"[{idx+1}/{total_p}] Sincronizando: {tit_serpi[:30]}...")
                            fila_v = pd.Series({"serpi": cod_serpi, "descripcion": tit_serpi, "price": prc_serpi, **cp_serpi})
                            
                            p_id, _ = obtener_product_id(fila_v)
                            if p_id:
                                if stk_serpi is not None:
                                    actualizar_stock_shopify(p_id, stk_serpi)
                                actualizar_producto_con_esquema(p_id, fila_v)
                                registrar_producto_procesado(cod_serpi)
                                actualizar_sku_en_snapshot(cod_serpi, stock=stk_serpi, precio=prc_serpi)
                                exitos += 1
                            else:
                                errores += 1
                                
                            time.sleep(0.05)
                            progreso.progress((idx + 1) / total_p)
                            
                        status.empty()
                        st.success(f"🎉 Lote finalizado. Sincronizados: {exitos} | No encontrados: {errores}")
                        st.rerun()
# =============================================================
# PESTAÑA 2: CARGA MANUAL VÍA EXCEL/CSV
# =============================================================
with tab_excel:
    st.subheader("📄 Carga y Mapeo Manual de Archivos")
    st.caption("Actualiza productos subiendo un archivo Excel o CSV exportado.")
    
    uploaded_file = st.file_uploader("Arrastra tu archivo aquí", type=["csv", "xlsx"], key="file_uploader_excel")
    
    if uploaded_file is not None:
        try:
            df_raw = pd.read_csv(uploaded_file, dtype=str) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file, dtype=str)
            st.success(f"Archivo cargado: **{uploaded_file.name}** ({len(df_raw)} filas)")
            st.dataframe(df_raw.head(5), width="stretch")
            
            campos_detectados = {}
            columnas_excel = list(df_raw.columns)
            
            for key_std, info_std in SCHEMA.get("campos_estandar", {}).items():
                if any(col in columnas_excel for col in info_std.get("posibles_columnas_excel", [])):
                    campos_detectados[key_std] = f"📌 {info_std.get('nombre', key_std)}"

            for key_meta, info_meta in SCHEMA.get("metafields", {}).items():
                if any(col in columnas_excel for col in info_meta.get("posibles_columnas_excel", [])):
                    campos_detectados[key_meta] = f"🏷️ {info_meta.get('name', key_meta)}"

            if campos_detectados:
                seleccionados = st.multiselect("Campos a actualizar:", options=list(campos_detectados.keys()), default=list(campos_detectados.keys()), format_func=lambda k: campos_detectados[k])
                if st.button("🚀 Procesar Archivo en Shopify", type="primary"):
                    progreso = st.progress(0)
                    total = len(df_raw)
                    exitos = 0
                    for idx, row in df_raw.iterrows():
                        p_id, _ = obtener_product_id(row)
                        if p_id:
                            actualizar_producto_con_esquema(p_id, row, campos_permitidos=seleccionados)
                            exitos += 1
                        time.sleep(0.05)
                        progreso.progress((idx + 1) / total)
                    st.success(f"🎉 Procesados {exitos} de {total} productos.")
        except Exception as e:
            st.error(f"Error: {e}")

# =============================================================
# PESTAÑA 3: ASIGNACIÓN DE PORTADAS
# =============================================================
with tab_portadas:
    st.subheader("🖼️ Asignador Asistido de Portadas")
    st.caption("Localiza el libro en Shopify y adjunta su portada en alta resolución.")
    
    with st.container(border=True):
        c_p1, c_p2, c_p3 = st.columns([3, 3, 2])
        with c_p1:
            nombre_input = st.text_input("📖 Título del Libro", placeholder="Ej: El Principito", key="in_p_nom")
        with c_p2:
            serpi_input = st.text_input("🔢 Código SKU / SERPI", placeholder="Ej: 9789561209275", key="in_p_cod")
        with c_p3:
            st.write("")
            btn_b_portada = st.button("🔍 Buscar Libro", type="primary", use_container_width=True, key="btn_b_port")

    if btn_b_portada and (nombre_input or serpi_input):
        with st.spinner("Buscando en Shopify..."):
            st.session_state["busqueda_productos"] = buscar_producto_por_nombre_y_serpi(nombre_input, serpi_input)

    if "busqueda_productos" in st.session_state:
        resultados = st.session_state["busqueda_productos"]
        if not resultados:
            st.warning("No se encontraron coincidencias en Shopify con esos términos.")
        else:
            opciones = {f"{item['title']} (SERPI: {item['serpi']})": item for item in resultados}
            seleccion = st.selectbox("Selecciona la coincidencia exacta:", list(opciones.keys()))
            prod_sel = opciones[seleccion]
            
            with st.container(border=True):
                st.info(f"Asignando imagen a: **{prod_sel['title']}**")
                up_img = st.file_uploader("Selecciona archivo de imagen", type=["jpg", "png", "webp", "jpeg"])
                if up_img and st.button("🚀 Subir e Integrar Portada", type="primary"):
                    with st.spinner("Subiendo a CDN de Shopify..."):
                        ok, msg = cargar_imagen_a_shopify(prod_sel["id"], up_img.read(), up_img.name)
                        if ok:
                            st.balloons()
                            st.success(f"🎉 Portada asignada a '{prod_sel['title']}'")
                        else:
                            st.error(f"Error: {msg}")