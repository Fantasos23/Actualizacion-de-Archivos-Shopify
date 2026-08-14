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
# Configuración SERPI API
# -------------------------------------------------------------
SERPI_BASE_URL = os.getenv("SERPI_BASE_URL", "https://apis.serpi.com.co").rstrip("/")
SERPI_HEADERS = {
    "secretkey": os.getenv("SERPI_SECRETKEY", "").strip(),
    "Authorization": f"Bearer {os.getenv('SERPI_TOKEN', '').strip()}",
    "Accept": "application/json"
}

def consultar_serpi_api(endpoint, params=None):
    url = f"{SERPI_BASE_URL}{endpoint}"
    try:
        res = requests.get(url, headers=SERPI_HEADERS, params=params, timeout=45)
        if res.status_code == 200:
            return res.json().get("result", [])
    except Exception as e:
        st.error(f"Error consultando SERPI ({endpoint}): {e}")
    return []

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

def obtener_product_id(row):
    """
    Busca el ID del producto en Shopify con un sistema de 3 capas de tolerancia:
    1. Búsqueda por SKU exacto o Handle limpio
    2. Búsqueda por Título exacto/parcial en Shopify
    3. Inspección directa de Metafields en los candidatos
    """
    v_serpi_raw = obtener_valor_fila(row, ["serpi", "custom.serpi", "serpi (product.metafields.custom.serpi)", "SERPI", "codigo", "sku"])
    v_desc = obtener_valor_fila(row, ["title", "title (product.title)", "descripcion", "descripcion_articulo", "Nombre", "Título"])

    v_serpi_plano = str(v_serpi_raw).strip() if v_serpi_raw else ""
    v_serpi_num = re.sub(r'[^0-9a-zA-Z]', '', v_serpi_plano) if v_serpi_plano else ""

    # 1. BÚSQUEDA DIRECTA POR SKU
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

    # 2. BÚSQUEDA DIRECTA POR HANDLE
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

    # 3. BÚSQUEDA DIFUSA POR TÍTULO CON SCAN DE METAFIELDS
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

def obtener_fecha_inicio_rango(horas):
    fecha_dt = datetime.now() - timedelta(hours=horas)
    return fecha_dt.strftime("%Y-%m-%d"), fecha_dt.strftime("%d-%m-%Y")

def consultar_inventario_serpi(horas=24):
    fecha_iso, _ = obtener_fecha_inicio_rango(horas)
    hoy_iso = datetime.now().strftime("%Y-%m-%d")
    params = {
        "fechaCorte": hoy_iso,
        "fechamodificaini": fecha_iso,
        "limite": 500,
        "pagina": 1
    }
    return consultar_serpi_api("/api/v1/SaldoInventarioSinCosto", params=params)

def consultar_precios_serpi(horas=24):
    fecha_iso, _ = obtener_fecha_inicio_rango(horas)
    params = {
        "fechamodificaini": fecha_iso,
        "limite": 500,
        "pagina": 1
    }
    return consultar_serpi_api("/api/v1/ListaPrecioDetalle", params=params)

def crear_producto_en_shopify(item_serpi):
    """Crea un nuevo producto en Shopify de forma robusta."""
    try:
        codigo = str(item_serpi.get("codigo", "")).strip()
        titulo = str(item_serpi.get("descripcion", "")).strip()
        precio = float(item_serpi.get("precio", 0) or 0)
        stock = float(item_serpi.get("saldo", 0) or 0)
        cp = item_serpi.get("camposPersonalizados", {}) or {}

        handle = limpiar_para_handle(titulo)

        metafields_input = [{
            "namespace": "custom",
            "key": "serpi",
            "value": codigo,
            "type": "single_line_text_field"
        }]

        for k_meta, v_meta in cp.items():
            if v_meta and str(v_meta).strip():
                metafields_input.append({
                    "namespace": "custom",
                    "key": k_meta,
                    "value": str(v_meta).strip(),
                    "type": "single_line_text_field"
                })

        input_product = {
            "title": titulo,
            "handle": handle,
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
            return None, [{"field": ["productCreate"], "message": f"Shopify no pudo procesar el producto."}]

        new_product_id = product_created.get("id")

        # Asignar SKU y Precio
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

        if new_product_id and stock > 0:
            actualizar_stock_shopify(new_product_id, stock)

        return new_product_id, []

    except Exception as e:
        return None, [{"field": ["create_exception"], "message": str(e)}]

# -------------------------------------------------------------
# GESTIÓN DE CACHÉ / MEMORIA DE PRODUCTOS PROCESADOS
# -------------------------------------------------------------
def inicializar_memoria_procesados():
    if "productos_procesados_ids" not in st.session_state:
        st.session_state["productos_procesados_ids"] = set()

def registrar_producto_procesado(codigo_serpi):
    inicializar_memoria_procesados()
    st.session_state["productos_procesados_ids"].add(str(codigo_serpi).strip())

def esta_procesado(codigo_serpi):
    inicializar_memoria_procesados()
    return str(codigo_serpi).strip() in st.session_state["productos_procesados_ids"]

# -------------------------------------------------------------
# 4. Funciones de Actualización en Shopify
# -------------------------------------------------------------
def actualizar_stock_shopify(product_id, nueva_cantidad):
    try:
        query_var = """
        query getProductVariant($id: ID!) {
          product(id: $id) {
            variants(first: 1) {
              edges {
                node {
                  id
                  inventoryQuantity
                }
              }
            }
          }
        }
        """
        res = ejecutar_graphql(query_var, {"id": product_id})
        if not res or "data" not in res or not res["data"].get("product"):
            return [{"field": ["product"], "message": "No se encontró el producto en Shopify o el ID es inválido."}]

        variants = res["data"]["product"].get("variants", {}).get("edges", [])
        if not variants:
            return [{"field": ["variant"], "message": "No se encontró ninguna variante para este producto."}]
            
        variant_gid = variants[0]["node"]["id"]
        variant_numeric_id = variant_gid.split("/")[-1]

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

    v_price = None
    if campos_permitidos is None or "price" in campos_permitidos:
        v_price = obtener_valor_fila(row, campos_estandar.get("price", {}).get("posibles_columnas_excel", ["price", "precio"]))

    v_sku = None
    if campos_permitidos is None or "sku" in campos_permitidos:
        v_sku = obtener_valor_fila(row, campos_estandar.get("sku", {}).get("posibles_columnas_excel", ["sku"]))

    v_tax = None
    if campos_permitidos is None or "taxable" in campos_permitidos:
        v_tax = obtener_valor_fila(row, campos_estandar.get("taxable", {}).get("posibles_columnas_excel", ["taxable"]))

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

# -------------------------------------------------------------
# 5. MODAL DE PREVISUALIZACIÓN UNIFICADO
# -------------------------------------------------------------
@st.dialog("🔍 Previsualización Unificada de Cambio en Shopify", width="large")
def mostrar_modal_previsualizacion_unificado(item_consolidado):
    codigo_serpi = item_consolidado.get("codigo")
    titulo_serpi = item_consolidado.get("descripcion", "")
    cp_serpi = item_consolidado.get("camposPersonalizados", {}) or {}
    
    nuevo_stock = item_consolidado.get("saldo")
    nuevo_precio = item_consolidado.get("precio")
    
    st.markdown(f"### 📖 Libro SERPI: **{titulo_serpi}**")
    st.caption(f"Código SERPI / SKU: `{codigo_serpi}`")
    
    with st.spinner("Comparando datos completos con Shopify..."):
        fila_virtual = pd.Series({
            "serpi": codigo_serpi,
            "descripcion": titulo_serpi,
            "price": nuevo_precio,
            **cp_serpi
        })
        
        product_id, match_origen = obtener_product_id(fila_virtual)
        
        if not product_id:
            st.error("❌ **Este producto no existe en Shopify.**")
            st.info("💡 Haz clic en el botón a continuación para darlo de alta automáticamente con toda la información de SERPI.")
            
            st.markdown("#### 📋 Datos a enviar para la creación:")
            st.write(f"**Título:** {titulo_serpi}")
            st.write(f"**SKU / Metafield custom.serpi:** `{codigo_serpi}`")
            st.write(f"**Precio Inicial:** `${nuevo_precio if nuevo_precio is not None else 0}`")
            st.write(f"**Stock Inicial:** `{nuevo_stock if nuevo_stock is not None else 0}` unidades")
            
            if cp_serpi:
                st.write("**Campos Personalizados:**")
                st.json(cp_serpi)

            st.divider()
            
            if st.button("✨ Crear este producto en Shopify", key="btn_create_modal_action"):
                with st.spinner("Creando producto en Shopify..."):
                    new_id, errs = crear_producto_en_shopify(item_consolidado)
                    if new_id:
                        registrar_producto_procesado(codigo_serpi)
                        st.balloons()
                        st.success(f"🎉 ¡Producto **'{titulo_serpi}'** creado con éxito en Shopify! (ID: `{new_id}`)")
                    else:
                        st.error(f"❌ Error al crear el producto: {errs}")

        else:
            query_detalles = """
            query getProductFullDetails($id: ID!) {
              product(id: $id) {
                id
                title
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
                      namespace
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
            
            stock_sp = var_sp.get("inventoryQuantity", "N/A")
            precio_sp = var_sp.get("price", "N/A")
            
            meta_sp_dict = {edge["node"]["key"]: edge["node"]["value"] for edge in prod_sp.get("metafields", {}).get("edges", [])}

            st.success(f"✅ Coincidencia encontrada en Shopify por **{match_origen}**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📊 Comparativa Básica")
                cambios_basicos = []
                
                if nuevo_stock is not None:
                    cambios_basicos.append({
                        "Campo": "Stock / Existencias",
                        "Shopify": stock_sp,
                        "SERPI": int(float(nuevo_stock)),
                        "Acción": "🔄 Actualizar" if str(stock_sp) != str(int(float(nuevo_stock))) else "⏸️ Igual"
                    })
                if nuevo_precio is not None:
                    cambios_basicos.append({
                        "Campo": "Precio",
                        "Shopify": f"${precio_sp}",
                        "SERPI": f"${nuevo_precio}",
                        "Acción": "🔄 Actualizar" if str(precio_sp) != str(nuevo_precio) else "⏸️ Igual"
                    })
                st.dataframe(pd.DataFrame(cambios_basicos), hide_index=True)
                
            with col2:
                st.markdown("#### 🏷️ Campos Personalizados / Metafields")
                cambios_meta = []
                
                for key_cp, val_cp in cp_serpi.items():
                    val_cp_str = str(val_cp).strip() if val_cp is not None else ""
                    val_sp_str = str(meta_sp_dict.get(key_cp, "")).strip()
                    
                    if val_cp_str:
                        cambios_meta.append({
                            "Metafield": f"custom.{key_cp}",
                            "Shopify": val_sp_str if val_sp_str else "(Vacío)",
                            "SERPI": val_cp_str,
                            "Acción": "🔄 Actualizar" if val_sp_str != val_cp_str else "⏸️ Igual"
                        })
                
                if cambios_meta:
                    st.dataframe(pd.DataFrame(cambios_meta), hide_index=True)
                else:
                    st.caption("Sin datos en campos personalizados de SERPI.")

            st.divider()
            if st.button("🚀 Confirmar y Aplicar TODOS los cambios a este producto", key="btn_update_modal_action"):
                with st.spinner("Sincronizando producto en Shopify..."):
                    errs_totales = []
                    
                    if nuevo_stock is not None:
                        err_st = actualizar_stock_shopify(product_id, nuevo_stock)
                        if err_st: errs_totales.extend(err_st)
                        
                    err_pr = actualizar_producto_con_esquema(product_id, fila_virtual)
                    if err_pr: errs_totales.extend(err_pr)
                    
                    if not errs_totales:
                        registrar_producto_procesado(codigo_serpi)
                        st.balloons()
                        st.success(f"🎉 ¡Producto '{prod_sp.get('title')}' sincronizado con éxito!")
                    else:
                        st.error(f"Errores durante la actualización: {errs_totales}")

# -------------------------------------------------------------
# 6. Interfaz Principal Streamlit con Pestañas
# -------------------------------------------------------------
st.set_page_config(page_title="Gestor de Inventario Shopify / SERPI", layout="wide")
st.title("📦 Sincronizador de Inventario y Productos (SERPI ➡️ Shopify)")

st.sidebar.header("Conexión API")
if API_TOKEN:
    st.sidebar.success(f"Conectado a: {RAW_SHOP_URL}")
else:
    st.sidebar.error("Verifica tus credenciales en el .env")

st.sidebar.divider()
st.sidebar.header("Esquema Cargado")
st.sidebar.info(f"Campos Estándar: {len(SCHEMA.get('campos_estandar', {}))}\nMetafields: {len(SCHEMA.get('metafields', {}))}")

# INICIALIZACIÓN DE LAS PESTAÑAS PRINCIPALES
tab_unificado, tab_excel, tab_portadas = st.tabs([
    "⚡ Super Sincronización Unificada", 
    "📄 Carga Manual vía Excel/CSV",
    "🖼️ Asignación de Portadas"
])

# -------------------------------------------------------------
# PESTAÑA 1: SUPER SINCRONIZACIÓN UNIFICADA
# -------------------------------------------------------------
with tab_unificado:
    st.header("⚡ Super Sincronización Unificada (SERPI ➡️ Shopify)")
    st.caption("Consulta Stock, Precios y Campos Personalizados con memoria de procesamiento visual.")

    inicializar_memoria_procesados()

    cant_procesados = len(st.session_state["productos_procesados_ids"])
    col_m1, col_m2 = st.columns([3, 1])
    with col_m1:
        if cant_procesados > 0:
            st.info(f"🧠 Memoria activa: **{cant_procesados}** producto(s) procesado(s) exitosamente en esta sesión.")
        else:
            st.caption("🧠 Memoria activa: Aún no has procesado productos en esta sesión.")
    with col_m2:
        if cant_procesados > 0 and st.button("🧹 Limpiar Memoria"):
            st.session_state["productos_procesados_ids"] = set()
            st.rerun()

    st.divider()

    col_rango_u, col_btn_u = st.columns([2, 1])
    with col_rango_u:
        rango_unificado = st.radio("Ventana de tiempo de consulta (SERPI):", [24, 48, 72], format_func=lambda x: f"Últimas {x} Horas", key="rango_unificado", horizontal=True)

    with col_btn_u:
        st.write("")
        btn_master_sync = st.button("🚀 Auditar y Consolidar Cambios Globales", key="btn_master_sync")

    if btn_master_sync:
        fecha_iso, fecha_fmt = obtener_fecha_inicio_rango(rango_unificado)
        with st.spinner(f"Consultando APIs de SERPI desde {fecha_fmt}..."):
            saldos_raw = consultar_inventario_serpi(horas=rango_unificado)
            precios_raw = consultar_precios_serpi(horas=rango_unificado)
            articulos_raw = consultar_serpi_api("/api/v1/Articulo", params={"fechamodificaini": fecha_fmt, "limite": 200, "pagina": 1})
            
            mapa_consolidado = {}
            for art in articulos_raw:
                cod = art.get("codigo")
                if cod:
                    mapa_consolidado[cod] = {
                        "codigo": cod,
                        "descripcion": art.get("descripcion", ""),
                        "camposPersonalizados": art.get("camposPersonalizados", {}) or {},
                        "saldo": None,
                        "precio": None
                    }
                    
            for item in saldos_raw:
                cod = item.get("codigo")
                if cod:
                    if cod not in mapa_consolidado:
                        mapa_consolidado[cod] = {
                            "codigo": cod,
                            "descripcion": item.get("descripcion", ""),
                            "camposPersonalizados": {},
                            "saldo": item.get("saldo"),
                            "precio": None
                        }
                    else:
                        mapa_consolidado[cod]["saldo"] = item.get("saldo")

            for item in precios_raw:
                cod = str(item.get("codigo") or item.get("id_articulo", ""))
                if cod:
                    if cod not in mapa_consolidado:
                        mapa_consolidado[cod] = {
                            "codigo": cod,
                            "descripcion": item.get("descripcion_articulo") or item.get("descripcion", ""),
                            "camposPersonalizados": {},
                            "saldo": None,
                            "precio": item.get("precio")
                        }
                    else:
                        mapa_consolidado[cod]["precio"] = item.get("precio")

            lista_final = list(mapa_consolidado.values())
            if lista_final:
                st.session_state["cache_unificado"] = lista_final
                st.success(f"Se detectaron **{len(lista_final)}** productos con movimientos/cambios en SERPI.")
            else:
                st.session_state.pop("cache_unificado", None)
                st.warning("No se detectaron cambios en SERPI dentro del rango seleccionado.")

    if "cache_unificado" in st.session_state and st.session_state["cache_unificado"]:
        lista_cache = st.session_state["cache_unificado"]
        
        st.write("### 📊 Matriz Consolidada de Cambios")
        
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            ocultar_completados = st.checkbox("👁️‍🗨️ Ocultar productos ya procesados / actualizados", value=False)
        
        resumen_tabla = []
        for p in lista_cache:
            cod = str(p.get("codigo")).strip()
            ya_listo = esta_procesado(cod)
            
            if ocultar_completados and ya_listo:
                continue
                
            cp = p.get("camposPersonalizados", {}) or {}
            resumen_tabla.append({
                "Estado": "✅ PROCESADO" if ya_listo else "⏳ PENDIENTE",
                "Código SERPI": cod,
                "Título": p.get("descripcion"),
                "Nuevo Stock": p.get("saldo") if p.get("saldo") is not None else "Sin cambio",
                "Nuevo Precio": f"${p.get('precio')}" if p.get("precio") is not None else "Sin cambio",
                "Autor (SERPI)": cp.get("autor", ""),
                "Editorial (SERPI)": cp.get("editorial", "")
            })
            
        df_resumen = pd.DataFrame(resumen_tabla)
        
        def resaltar_procesados(val):
            return 'background-color: #d4edda; color: #155724; font-weight: bold;' if val == '✅ PROCESADO' else ''

        if not df_resumen.empty:
            df_styled = df_resumen.style.map(resaltar_procesados, subset=['Estado'])
            st.dataframe(df_styled, width="stretch", height=300)
        else:
            st.success("🎉 ¡Todos los productos devueltos por SERPI han sido procesados!")

        st.divider()
        st.markdown("### 🔎 Inspector de Coincidencia Unificado")
        st.write("Selecciona cualquier producto para previsualizarlo o ejecutarlo individualmente:")
        
        libros_disponibles = [p for p in lista_cache if not (ocultar_completados and esta_procesado(p.get("codigo")))]
        
        opciones_unificadas = {
            f"{'✅ ' if esta_procesado(p.get('codigo')) else ''}SERPI: {p.get('codigo')} | {p.get('descripcion')}": p 
            for p in libros_disponibles
        }
        
        if opciones_unificadas:
            col_sel_u, col_btn_u = st.columns([3, 1])
            with col_sel_u:
                prod_u_key = st.selectbox("Selecciona un producto:", list(opciones_unificadas.keys()), key="sel_unificado_dropdown")
            with col_btn_u:
                st.write("")
                st.write("")
                if st.button("🔍 Inspector Flotante Unificado", key="btn_open_unificado"):
                    mostrar_modal_previsualizacion_unificado(opciones_unificadas[prod_u_key])
        else:
            st.info("No hay productos pendientes por inspeccionar con el filtro actual.")

        st.divider()
        st.markdown("### 🚀 Sincronización Masiva Global")
        if st.button("⚡ Sincronizar TODOS los datos pendientes en Shopify", key="btn_masivo_global"):
            progreso = st.progress(0)
            status = st.empty()
            exitos, errores = 0, 0
            
            pendientes = [p for p in lista_cache if not esta_procesado(p.get("codigo"))]
            total_p = len(pendientes)
            
            if total_p == 0:
                st.info("No hay productos pendientes por sincronizar en la lista.")
            else:
                for idx, item in enumerate(pendientes):
                    cod_serpi = item.get("codigo")
                    tit_serpi = item.get("descripcion", "")
                    cp_serpi = item.get("camposPersonalizados", {}) or {}
                    stk_serpi = item.get("saldo")
                    prc_serpi = item.get("precio")
                    
                    status.text(f"Sincronizando {idx+1}/{total_p}: {cod_serpi} | {tit_serpi[:25]}")
                    
                    fila_v = pd.Series({
                        "serpi": cod_serpi,
                        "descripcion": tit_serpi,
                        "price": prc_serpi,
                        **cp_serpi
                    })
                    
                    p_id, _ = obtener_product_id(fila_v)
                    if p_id:
                        if stk_serpi is not None:
                            actualizar_stock_shopify(p_id, stk_serpi)
                        actualizar_producto_con_esquema(p_id, fila_v)
                        registrar_producto_procesado(cod_serpi)
                        exitos += 1
                    else:
                        errores += 1
                        
                    time.sleep(0.05)
                    progreso.progress((idx + 1) / total_p)
                    
                status.empty()
                st.success(f"🎉 Sincronización completada. Exitosos: {exitos} | Errores: {errores}")
                st.rerun()

# -------------------------------------------------------------
# PESTAÑA 2: CARGA MANUAL VÍA EXCEL/CSV
# -------------------------------------------------------------
with tab_excel:
    st.subheader("📄 Cargar y Actualizar manualmente vía Archivo")
    uploaded_file = st.file_uploader("Selecciona tu archivo Excel (.xlsx) o CSV", type=["csv", "xlsx"], key="file_uploader_excel")

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_raw = pd.read_csv(uploaded_file, dtype=str)
            else:
                df_raw = pd.read_excel(uploaded_file, dtype=str)
            
            st.success(f"Archivo **{uploaded_file.name}** cargado con éxito. Total registros: {len(df_raw)}")
            st.dataframe(df_raw.head(10), width="stretch")

            campos_detectados = {}
            columnas_excel = list(df_raw.columns)

            for key_std, info_std in SCHEMA.get("campos_estandar", {}).items():
                posibles = info_std.get("posibles_columnas_excel", [])
                if any(col in columnas_excel for col in posibles):
                    campos_detectados[key_std] = f"📌 {info_std.get('nombre', key_std)} (`{key_std}`)"

            for key_meta, info_meta in SCHEMA.get("metafields", {}).items():
                posibles = info_meta.get("posibles_columnas_excel", [])
                if any(col in columnas_excel for col in posibles):
                    campos_detectados[key_meta] = f"🏷️ Metafield: {info_meta.get('name', key_meta)} (`custom.{key_meta}`)"

            if campos_detectados:
                seleccionados_keys = st.multiselect(
                    "Campos autorizados para actualizar en Shopify desde este archivo:",
                    options=list(campos_detectados.keys()),
                    default=list(campos_detectados.keys()),
                    format_func=lambda k: campos_detectados[k],
                    key="multiselect_excel"
                )

                if st.button("🚀 Actualizar Archivo en Shopify vía API", key="btn_update_excel"):
                    progreso = st.progress(0)
                    status_text = st.empty()
                    total = len(df_raw)
                    exitos, errores_lista = 0, []

                    for idx, row in df_raw.iterrows():
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
                        
                        time.sleep(0.05)
                        progreso.progress((idx + 1) / total)

                    status_text.empty()
                    st.success(f"🎉 Proceso finalizado. Exitosos: {exitos} | Errores: {len(errores_lista)}")
        except Exception as e:
            st.error(f"Error al procesar archivo: {e}")

# -------------------------------------------------------------
# PESTAÑA 3: ASIGNACIÓN DE PORTADAS E IMÁGENES
# -------------------------------------------------------------
with tab_portadas:
    st.header("🖼️ Asignación Asistida de Portadas")
    st.write("Escribe el nombre del libro y/o su código SERPI para localizar el producto en Shopify antes de subir la imagen.")

    col_nom, col_serpi = st.columns(2)
    with col_nom:
        nombre_input = st.text_input("📖 Nombre o Título del Libro", placeholder="Ej: El principito", key="input_portada_nombre")
    with col_serpi:
        serpi_input = st.text_input("🔢 Código SERPI", placeholder="Ej: 9780785396901", key="input_portada_serpi")

    if st.button("🔍 Buscar Producto en Shopify", key="btn_buscar_portada"):
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
            
            seleccion = st.selectbox("Selecciona el producto exacto al que pertenece la portada:", list(opciones.keys()), key="select_producto_portada")
            producto_seleccionado = opciones[seleccion]

            st.info(f"📌 Producto Seleccionado: **{producto_seleccionado['title']}** (SERPI Metafield: `{producto_seleccionado['serpi']}`)")

            uploaded_image = st.file_uploader(
                "Selecciona la imagen de la portada desde tu equipo",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=False,
                key="uploader_portada_file"
            )

            if uploaded_image and st.button("🚀 Subir Imagen y Asignar a este Producto", key="btn_upload_portada_file"):
                with st.spinner("Subiendo portada e integrando a la galería de Shopify..."):
                    file_bytes = uploaded_image.read()
                    ok, msg = cargar_imagen_a_shopify(producto_seleccionado["id"], file_bytes, uploaded_image.name)
                    
                    if ok:
                        st.success(f"🎉 ¡Portada asignada exitosamente al libro **{producto_seleccionado['title']}**!")
                    else:
                        st.error(f"❌ Error al subir la imagen: {msg}")