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

# -------------------------------------------------------------
# Google Material Design 3 Styling
# -------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600;700&family=Roboto:wght@300;400;500;700&display=swap');

/* Tipografía Base y Suavizado */
html, body, [class*="css"], .stMarkdown, p, span, label, div {
    font-family: 'Google Sans', 'Roboto', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* Layout Principal */
.main .block-container {
    padding-top: 1.8rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

/* Scrollbar Material */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: transparent;
}
::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.18);
    border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.32);
}

/* Contenedores y Tarjetas Material 3 */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #181C24 !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 20px !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2), 0 2px 8px rgba(0, 0, 0, 0.12) !important;
    padding: 1.25rem !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Barra Lateral Material 3 */
[data-testid="stSidebar"] {
    background-color: #13161C !important;
    border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
}

[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    font-family: 'Google Sans', sans-serif !important;
    font-weight: 600 !important;
    color: #E2E8F0 !important;
}

/* Botones Google Material 3 */
button[kind="primary"] {
    background-color: #1A73E8 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 24px !important;
    font-family: 'Google Sans', sans-serif !important;
    font-weight: 500 !important;
    letter-spacing: 0.25px !important;
    padding: 0.55rem 1.4rem !important;
    box-shadow: 0 2px 6px rgba(26, 115, 232, 0.3) !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

button[kind="primary"]:hover {
    background-color: #1765CC !important;
    box-shadow: 0 4px 12px rgba(26, 115, 232, 0.45) !important;
    transform: translateY(-1px) !important;
}

button[kind="primary"]:active {
    transform: translateY(0) !important;
    box-shadow: 0 1px 3px rgba(26, 115, 232, 0.3) !important;
}

button[kind="secondary"] {
    background-color: #222733 !important;
    color: #E2E8F0 !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 24px !important;
    font-family: 'Google Sans', sans-serif !important;
    font-weight: 500 !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

button[kind="secondary"]:hover {
    background-color: #2C3342 !important;
    border-color: rgba(255, 255, 255, 0.22) !important;
    color: #FFFFFF !important;
    transform: translateY(-1px) !important;
}

/* Pestañas Material 3 */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    background: transparent;
    padding-bottom: 4px;
}

[data-testid="stTabs"] [data-baseweb="tab"] {
    border-radius: 16px 16px 0 0;
    font-family: 'Google Sans', sans-serif !important;
    font-weight: 500 !important;
    padding: 10px 20px !important;
    color: #9AA0A6 !important;
    border: none !important;
    background: transparent !important;
    transition: all 0.2s ease !important;
}

[data-testid="stTabs"] [aria-selected="true"] {
    color: #8AB4F8 !important;
    font-weight: 600 !important;
    border-bottom: 3px solid #8AB4F8 !important;
}

/* Campos de Texto y Selectores Material */
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
    border-radius: 14px !important;
    background-color: #1F242E !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    transition: all 0.2s ease !important;
}

div[data-baseweb="input"] > div:focus-within, div[data-baseweb="select"] > div:focus-within {
    border-color: #8AB4F8 !important;
    box-shadow: 0 0 0 2px rgba(138, 180, 248, 0.25) !important;
}

/* Pills / Chips de Filtro */
[data-testid="stPills"] button {
    border-radius: 20px !important;
    font-family: 'Google Sans', sans-serif !important;
    font-weight: 500 !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
}

/* Diálogo Modal */
div[role="dialog"] {
    border-radius: 28px !important;
    background-color: #181C24 !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5) !important;
}

/* Alertas y Notificaciones */
[data-testid="stAlert"] {
    border-radius: 16px !important;
    border: none !important;
    font-family: 'Google Sans', sans-serif !important;
}

/* Métricas Material */
[data-testid="stMetricValue"] {
    font-family: 'Google Sans', sans-serif !important;
    font-weight: 700 !important;
    color: #E2E8F0 !important;
}

[data-testid="stMetricLabel"] {
    font-family: 'Google Sans', sans-serif !important;
    font-weight: 500 !important;
    color: #9AA0A6 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-size: 0.75rem;
}

/* Dataframe / Tablas */
[data-testid="stDataFrame"] {
    border-radius: 16px !important;
    overflow: hidden !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
}
</style>
""", unsafe_allow_html=True)

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

MAPEO_GRUPOS_CONTABLES = {
    2: "Librería",
    1: "Papelería",
    3: "Servicios",
    4: "Juguetería",
    5: "Accesorios"
}

def resolver_grupo_contable_articulo(row):
    """
    Obtiene el nombre del Grupo Contable a partir de idgrupocontable o campos similares.
    2 -> Librería
    1 -> Papelería
    3 -> Servicios
    4 -> Juguetería
    5 -> Accesorios
    """
    val_id = None
    if isinstance(row, dict):
        val_id = row.get("idgrupocontable") or row.get("id_grupocontable") or row.get("id_grupo_contable") or row.get("idGrupoContable")
    elif isinstance(row, pd.Series):
        for k in ["idgrupocontable", "id_grupocontable", "id_grupo_contable", "idGrupoContable"]:
            if k in row and pd.notna(row[k]):
                val_id = row[k]
                break

    if val_id is not None:
        try:
            id_num = int(val_id)
            if id_num in MAPEO_GRUPOS_CONTABLES:
                return MAPEO_GRUPOS_CONTABLES[id_num]
            else:
                return f"Grupo {id_num}"
        except (ValueError, TypeError):
            pass

    # Si viene el nombre directamente en texto (por ejemplo desde Excel o campos personalizados)
    val_txt = None
    if isinstance(row, dict):
        val_txt = row.get("grupocontable") or row.get("grupo_contable") or row.get("linea") or row.get("Linea")
        if not val_txt:
            cp = row.get("camposPersonalizados") or {}
            if isinstance(cp, dict):
                val_txt = cp.get("grupocontable") or cp.get("linea")
    elif isinstance(row, pd.Series):
        for k in ["grupocontable", "grupo_contable", "linea", "Linea", "LINEA"]:
            if k in row and pd.notna(row[k]):
                val_txt = row[k]
                break

    if val_txt:
        txt_limpio = str(val_txt).strip()
        txt_lower = txt_limpio.lower()
        if "librer" in txt_lower or "libro" in txt_lower or "literatura" in txt_lower:
            return "Librería"
        elif "papel" in txt_lower:
            return "Papelería"
        elif "serv" in txt_lower:
            return "Servicios"
        elif "juguet" in txt_lower:
            return "Juguetería"
        elif "acces" in txt_lower:
            return "Accesorios"
        return txt_limpio

    return "Librería"

def determinar_taxable_desde_fila(row):
    """
    Determina si el producto cobra impuestos (taxable=True) o no (taxable=False) en Shopify.
    Regla de Negocio:
    - Si grupo contable es LIBRERÍA (idgrupocontable = 2) -> taxable = False (NO cobra impuestos / Exento de IVA).
    - Si es PAPELERÍA (1), SERVICIOS (3), JUGUETERÍA (4), ACCESORIOS (5) o cualquier otro -> taxable = True (SÍ cobra impuestos / Gravado).
    - Si se especifica explícitamente en columna 'taxable'/'impuesto' en Excel, se respeta dicho valor.
    """
    # 1. Si viene un campo directo de taxable / impuesto (en Excel / CSV)
    if isinstance(row, (dict, pd.Series)):
        posibles_imp = ["taxable", "Taxable", "Variant Taxable", "impuesto", "Impuesto", "impuestos", "aplica_impuesto"]
        for p in posibles_imp:
            val = row.get(p) if isinstance(row, dict) else (row[p] if p in row and pd.notna(row[p]) else None)
            if val is not None and str(val).strip() != "":
                val_s = str(val).strip().lower()
                if val_s in ['false', '0', 'no', 'exento', 'f']:
                    return False
                elif val_s in ['true', '1', 'si', 'sí', 's', 't', 'gravado']:
                    return True

    # 2. Evaluar según el Grupo Contable de SERPI
    grupo = resolver_grupo_contable_articulo(row)
    if str(grupo).strip().lower() in ["librería", "libreria"]:
        return False
    else:
        return True

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

def obtener_precio_puntual_serpi(codigo_sku):
    """Consulta el precio de un SKU específico directamente en SERPI o desde el Snapshot."""
    try:
        codigo_str = str(codigo_sku).strip()
        snapshot = cargar_snapshot_control()
        if codigo_str in snapshot and snapshot[codigo_str].get("precio") is not None and float(snapshot[codigo_str]["precio"]) > 0:
            return float(snapshot[codigo_str]["precio"])

        res = consultar_serpi_api("/api/v1/ListaPrecioDetalle", params={"codigo": codigo_str, "limite": 10})
        if res and isinstance(res, list):
            precios_validos = []
            for r in res:
                c = str(r.get("codigo") or r.get("id_articulo", "")).strip()
                if c == codigo_str or not c:
                    p = float(r.get("precio", 0) or 0)
                    if p > 0:
                        precios_validos.append((r.get("id_listaprecio"), p))
            if precios_validos:
                for id_lp, p in precios_validos:
                    if id_lp == 1:
                        return p
                return max(p for _, p in precios_validos)
            if len(res) > 0:
                p_alt = [float(r.get("precio", 0) or 0) for r in res if float(r.get("precio", 0) or 0) > 0]
                if p_alt:
                    return max(p_alt)
    except Exception:
        pass
    return 0.0

def obtener_stock_puntual_serpi(codigo_sku):
    """Consulta las existencias de un SKU específico sumando todas las bodegas en SERPI."""
    try:
        codigo_str = str(codigo_sku).strip()
        snapshot = cargar_snapshot_control()
        if codigo_str in snapshot and snapshot[codigo_str].get("stock") is not None:
            return int(float(snapshot[codigo_str]["stock"]))

        hoy = datetime.now().strftime("%Y-%m-%d")
        res = consultar_serpi_api("/api/v1/SaldoInventarioSinCosto", params={"fechaCorte": hoy, "codigo": codigo_str, "limite": 20})
        if res and isinstance(res, list):
            total_stock = 0.0
            found = False
            for r in res:
                if str(r.get("codigo", "")).strip() == codigo_str:
                    total_stock += float(r.get("saldo", 0) or 0)
                    found = True
            if found:
                return int(total_stock)
            if len(res) > 0:
                return int(sum(float(r.get("saldo", 0) or 0) for r in res))
    except Exception:
        pass
    return 0

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

def obtener_sucursal_principal():
    """Obtiene el GID y el ID numérico de la sucursal de inventario en Shopify."""
    try:
        query_loc = """
        query getLocations {
          locations(first: 5) {
            edges {
              node {
                id
                legacyResourceId
              }
            }
          }
        }
        """
        res = ejecutar_graphql(query_loc)
        edges = res.get("data", {}).get("locations", {}).get("edges", [])
        if edges:
            node = edges[0]["node"]
            loc_gid = node.get("id")
            num_str = node.get("legacyResourceId") or (loc_gid.split("/")[-1] if loc_gid else None)
            if loc_gid and num_str:
                return loc_gid, int(num_str)
    except Exception:
        pass

    env_loc = os.getenv("SHOPIFY_LOCATION_ID", "").strip()
    if env_loc:
        num = int(env_loc.split("/")[-1])
        return f"gid://shopify/Location/{num}", num

    return "gid://shopify/Location/83831882001", 83831882001

def obtener_location_gid_principal():
    """Retorna el GID principal de la sucursal de inventario."""
    loc_gid, _ = obtener_sucursal_principal()
    return loc_gid


def actualizar_stock_shopify(product_id, nueva_cantidad):
    """
    1. Asegura seguimiento de inventario en REST (tracked: True, inventory_management: 'shopify').
    2. Conecta y fija las existencias en la sucursal activa de Shopify sin errores de permisos.
    """
    try:
        prod_numeric_id = str(product_id).split("/")[-1]
        rest_url = f"https://{RAW_SHOP_URL}/admin/api/{API_VERSION}"
        cantidad_int = int(float(nueva_cantidad or 0))

        # 1. Consultar el producto por REST para obtener variante e inventory_item_id
        r_prod = requests.get(f"{rest_url}/products/{prod_numeric_id}.json", headers=HEADERS, timeout=15)
        if r_prod.status_code != 200:
            return [{"field": ["product"], "message": f"Error consultando producto: {r_prod.text[:100]}"}]

        prod_data = r_prod.json().get("product") or {}
        variants = prod_data.get("variants", [])
        if not variants:
            return [{"field": ["variant"], "message": "No se encontraron variantes en el producto."}]

        variant_obj = variants[0]
        variant_id = variant_obj.get("id")
        inv_item_id = variant_obj.get("inventory_item_id")

        if not inv_item_id:
            return [{"field": ["inventory_item"], "message": "No se encontró ID de inventario."}]

        # 2. ACTIVAR SEGUIMIENTO DE INVENTARIO
        requests.put(
            f"{rest_url}/inventory_items/{inv_item_id}.json",
            headers=HEADERS,
            json={"inventory_item": {"id": int(inv_item_id), "tracked": True}},
            timeout=15
        )
        requests.put(
            f"{rest_url}/variants/{variant_id}.json",
            headers=HEADERS,
            json={"variant": {"id": int(variant_id), "inventory_management": "shopify"}},
            timeout=15
        )

        # 3. Obtener la sucursal activa de la tienda
        loc_gid, loc_id_num = obtener_sucursal_principal()
        if not loc_id_num:
            return [{"field": ["location"], "message": "No se pudo determinar la sucursal de inventario."}]

        # 4. Conectar la sucursal al inventory_item (REST connect)
        try:
            requests.post(
                f"{rest_url}/inventory_levels/connect.json",
                headers=HEADERS,
                json={
                    "location_id": int(loc_id_num),
                    "inventory_item_id": int(inv_item_id)
                },
                timeout=15
            )
        except Exception:
            pass

        # 5. Fijar el stock exacto disponible por REST
        r_set = requests.post(
            f"{rest_url}/inventory_levels/set.json",
            headers=HEADERS,
            json={
                "location_id": int(loc_id_num),
                "inventory_item_id": int(inv_item_id),
                "available": cantidad_int
            },
            timeout=15
        )

        if r_set.status_code not in (200, 201):
            return [{"field": ["inventory_levels"], "message": f"Error fijando stock ({r_set.status_code}): {r_set.text[:120]}"}]

        return []

    except Exception as e:
        return [{"field": ["inventory_exception"], "message": str(e)}]

def crear_producto_en_shopify(item_serpi):
    """
    PASO 1: Crea el producto (Título, Handle, Descripción, Tags y Metafields) con GraphQL.
    PASO 2: Asigna SKU, Precio y Seguimiento con REST (/variants/{id}.json).
    PASO 3: Publica en todos los canales de venta.
    PASO 4: Asigna las existencias en la sucursal activa.
    """
    try:
        codigo = str(item_serpi.get("codigo", "")).strip()
        titulo = str(item_serpi.get("descripcion", "")).strip()

        # Recuperar precio y stock consolidados
        precio_val = item_serpi.get("precio")
        if precio_val is None or float(precio_val or 0) == 0:
            precio_val = obtener_precio_puntual_serpi(codigo)
            item_serpi["precio"] = precio_val
        precio_float = float(precio_val or 0)

        stock_val = item_serpi.get("saldo")
        if stock_val is None:
            stock_val = obtener_stock_puntual_serpi(codigo)
            item_serpi["saldo"] = stock_val
        stock_int = int(float(stock_val or 0))

        cp = item_serpi.get("camposPersonalizados", {}) or {}
        handle = limpiar_para_handle(titulo)
        desc_raw = cp.get("descripcion") or item_serpi.get("descripcion_larga") or ""
        desc_html = formatear_descripcion_html(desc_raw)

        # Tags nativos
        tags_raw = cp.get("etiquetas") or cp.get("tags") or ""
        tags_list = []
        if isinstance(tags_raw, list):
            tags_list = [str(t).strip() for t in tags_raw if str(t).strip()]
        elif isinstance(tags_raw, str) and tags_raw.strip():
            tags_list = [t.strip() for t in tags_raw.split(',') if t.strip()]

        # Metafields
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

        # --- PASO 1: Creación del Producto Base ---
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
            return None, [{"field": ["productCreate"], "message": "Shopify no pudo generar el registro."}]

        new_product_id = product_created.get("id")
        v_edges = product_created.get("variants", {}).get("edges", [])

        # --- PASO 2: Asignar SKU, Precio, Taxable y Seguimiento por REST ---
        if v_edges and new_product_id:
            variant_numeric_id = v_edges[0]["node"]["id"].split("/")[-1]
            rest_url = f"https://{RAW_SHOP_URL}/admin/api/{API_VERSION}"
            es_taxable = determinar_taxable_desde_fila(item_serpi)
            
            payload_variant = {
                "variant": {
                    "id": int(variant_numeric_id),
                    "sku": codigo,
                    "price": str(precio_float),
                    "taxable": es_taxable,
                    "inventory_management": "shopify"
                }
            }
            requests.put(
                f"{rest_url}/variants/{variant_numeric_id}.json",
                headers=HEADERS,
                json=payload_variant,
                timeout=15
            )

        # --- PASO 3: Publicar en todos los Canales de Venta ---
        if new_product_id:
            publicar_producto_en_canales(new_product_id)

        # --- PASO 4: Asentar el inventario físico en la sucursal ---
        if new_product_id:
            err_stock = actualizar_stock_shopify(new_product_id, stock_int)
            if err_stock:
                return new_product_id, err_stock

        return new_product_id, []

    except Exception as e:
        return None, [{"field": ["create_exception"], "message": str(e)}]
    
def actualizar_producto_con_esquema(product_id, row, campos_permitidos=None):
    """
    Llena simultáneamente:
    1. Atributos NATIVOS (vendor, productType, tags, descriptionHtml).
    2. METACAMPOS (custom.editorial, custom.autor, custom.paginas, etc.).
    3. VARIANTE (Precio y SKU).
    """
    errores_totales = []
    campos_estandar = SCHEMA.get("campos_estandar", {})
    input_product = {"id": product_id}

    # -------------------------------------------------------------
    # 1. ATRIBUTOS NATIVOS DE SHOPIFY
    # -------------------------------------------------------------
    
    # A. Descripción HTML
    if campos_permitidos is None or "descriptionHtml" in campos_permitidos:
        posibles_desc = campos_estandar.get("descriptionHtml", {}).get(
            "posibles_columnas_excel", ["descriptionHtml", "descripcion", "descripcion_larga", "sinopsis"]
        )
        v_desc = obtener_valor_fila(row, posibles_desc)
        if v_desc is not None:
            input_product["descriptionHtml"] = formatear_descripcion_html(v_desc)

    # B. Vendor / Proveedor / Editorial (NATIVO)
    if campos_permitidos is None or "vendor" in campos_permitidos:
        posibles_vendor = campos_estandar.get("vendor", {}).get(
            "posibles_columnas_excel", ["vendor", "editorial", "proveedor", "marca"]
        )
        v_vendor = obtener_valor_fila(row, posibles_vendor)
        if v_vendor is not None:
            input_product["vendor"] = str(v_vendor).strip()

    # C. Product Type / Categoría / Línea (NATIVO)
    if campos_permitidos is None or "productType" in campos_permitidos:
        posibles_type = campos_estandar.get("productType", {}).get(
            "posibles_columnas_excel", ["productType", "tipo", "categoria", "linea", "genero"]
        )
        v_type = obtener_valor_fila(row, posibles_type)
        if v_type is not None:
            input_product["productType"] = str(v_type).strip()

    # D. Tags / Etiquetas (NATIVO)
    if campos_permitidos is None or "tags" in campos_permitidos:
        posibles_tags = campos_estandar.get("tags", {}).get(
            "posibles_columnas_excel", ["tags", "etiquetas", "Etiquetas", "TAGS"]
        )
        v_tags = obtener_valor_fila(row, posibles_tags)
        if v_tags is not None:
            if isinstance(v_tags, list):
                input_product["tags"] = [str(t).strip() for t in v_tags if str(t).strip()]
            else:
                input_product["tags"] = [t.strip() for t in str(v_tags).split(',') if t.strip()]

    # -------------------------------------------------------------
    # 2. METACAMPOS (custom.*) - Se llenan todos los definidos en el esquema
    # -------------------------------------------------------------
    metafields_input = []
    metafields_schema = SCHEMA.get("metafields", {})

    for key_meta, info_meta in metafields_schema.items():
        if campos_permitidos is not None and key_meta not in campos_permitidos:
            continue

        posibles = info_meta.get("posibles_columnas_excel", [key_meta])
        v_meta = obtener_valor_fila(row, posibles)
        if v_meta is not None:
            v_meta_str = str(v_meta).strip()
            tipo_meta = info_meta.get("type", "single_line_text_field")

            # Tratamiento especial para booleanos
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

    # Ejecutar actualización en Shopify (Nativos + Metacampos)
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
        res_p = ejecutar_graphql(mutation_prod, {"input": input_product})
        err_p = res_p.get("data", {}).get("productUpdate", {}).get("userErrors", [])
        if err_p:
            errores_totales.extend(err_p)

    # -------------------------------------------------------------
    # 3. PRECIO, SKU Y TAXABLE (IMPUESTOS) EN LA VARIANTE
    # -------------------------------------------------------------
    v_price = None
    if campos_permitidos is None or "price" in campos_permitidos:
        v_price = obtener_valor_fila(row, campos_estandar.get("price", {}).get("posibles_columnas_excel", ["price", "precio"]))

    v_sku = None
    if campos_permitidos is None or "sku" in campos_permitidos:
        v_sku = obtener_valor_fila(row, campos_estandar.get("sku", {}).get("posibles_columnas_excel", ["sku", "codigo", "serpi"]))

    v_taxable = None
    if campos_permitidos is None or any(c in (campos_permitidos or []) for c in ["taxable", "impuesto", "impuestos", "linea", "idlinea"]):
        v_taxable = determinar_taxable_desde_fila(row)

    if v_price is not None or v_sku is not None or v_taxable is not None:
        query_var = """
        query getVariantForUpdate($id: ID!) {
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
        res_v = ejecutar_graphql(query_var, {"id": product_id})
        v_edges = res_v.get("data", {}).get("product", {}).get("variants", {}).get("edges", [])
        if v_edges:
            variant_gid = v_edges[0]["node"]["id"]
            
            mutation_bulk = """
            mutation updateVariantBulk($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
              productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                userErrors {
                  field
                  message
                }
              }
            }
            """
            var_item = {"id": variant_gid}
            if v_price is not None:
                var_item["price"] = f"{float(v_price):.2f}"
            if v_sku is not None:
                var_item["sku"] = str(v_sku).strip()
            if v_taxable is not None:
                var_item["taxable"] = bool(v_taxable)

            res_bulk = ejecutar_graphql(mutation_bulk, {
                "productId": product_id,
                "variants": [var_item]
            })
            err_b = res_bulk.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])
            if err_b:
                errores_totales.extend(err_b)

    # -------------------------------------------------------------
    # 4. PUBLICACIÓN EN TODOS LOS CANALES DE VENTA (Online Store, POS, Redes, Apps)
    # -------------------------------------------------------------
    err_pub = publicar_producto_en_canales(product_id)
    if err_pub:
        for ep in err_pub:
            if "publications_permission" not in ep.get("field", []):
                errores_totales.append(ep)

    return errores_totales

def verificar_permisos_canales_shopify():
    """Verifica si el token de Shopify tiene permisos para publicar en canales externos."""
    try:
        res = ejecutar_graphql("""
        query {
          currentAppInstallation {
            accessScopes {
              handle
            }
          }
        }
        """)
        scopes = [s["handle"] for s in res.get("data", {}).get("currentAppInstallation", {}).get("accessScopes", [])]
        has_read = "read_publications" in scopes
        has_write = "write_publications" in scopes
        return (has_read and has_write), scopes
    except Exception:
        return False, []

def publicar_producto_en_canales(product_id):
    """
    Publica el producto en todos los canales de venta activos:
    1. Asegura que el producto esté publicado y activo vía REST (Tienda Online / Global).
    2. Publica en todos los canales externos (POS, Facebook & Instagram, Google & YouTube, TikTok, Shop) vía GraphQL.
    """
    errores = []
    try:
        prod_numeric_id = str(product_id).split("/")[-1]
        prod_gid = product_id if str(product_id).startswith("gid://") else f"gid://shopify/Product/{product_id}"
        rest_url = f"https://{RAW_SHOP_URL}/admin/api/{API_VERSION}"

        # 1. Asegurar estado activo y publicación global vía REST (Online Store)
        try:
            requests.put(
                f"{rest_url}/products/{prod_numeric_id}.json",
                headers=HEADERS,
                json={
                    "product": {
                        "id": int(prod_numeric_id),
                        "published": True,
                        "published_scope": "global",
                        "status": "active"
                    }
                },
                timeout=15
            )
        except Exception:
            pass

        # 2. Consultar todos los canales de venta (Publications)
        query_pubs = """
        query getStorePublications {
          publications(first: 30) {
            edges {
              node {
                id
                name
              }
            }
          }
        }
        """
        res_pubs = ejecutar_graphql(query_pubs)
        if res_pubs and isinstance(res_pubs, dict):
            # Si hay error por falta de permisos en Shopify
            if "errors" in res_pubs and res_pubs.get("errors"):
                err_msg = res_pubs["errors"][0].get("message", "")
                if "access scope" in err_msg.lower() or "denied" in err_msg.lower():
                    return [{
                        "field": ["publications_permission"],
                        "message": "Faltan los permisos 'read_publications' y 'write_publications' en la App de Shopify para publicar en Facebook, Google, TikTok y POS."
                    }]

            pubs = res_pubs.get("data", {}).get("publications", {}).get("edges", [])
            if pubs:
                mutation_pub = """
                mutation publishToAllSalesChannels($id: ID!, $input: [PublicationInput!]!) {
                  publishablePublish(id: $id, input: $input) {
                    userErrors {
                      field
                      message
                    }
                  }
                }
                """
                input_list = [{"publicationId": p["node"]["id"]} for p in pubs if p.get("node", {}).get("id")]
                if input_list:
                    res_p = ejecutar_graphql(mutation_pub, {"id": prod_gid, "input": input_list})
                    err_user = res_p.get("data", {}).get("publishablePublish", {}).get("userErrors", [])
                    if err_user:
                        errores.extend(err_user)

        return errores
    except Exception as e:
        return [{"field": ["publish_exception"], "message": str(e)}]

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
    
    if nuevo_precio is None or float(nuevo_precio or 0) == 0:
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
            "idgrupocontable": item_consolidado.get("idgrupocontable"),
            "grupocontable": item_consolidado.get("grupocontable"),
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
                    grupo_nombre = resolver_grupo_contable_articulo(item_consolidado)
                    es_tax = determinar_taxable_desde_fila(item_consolidado)
                    st.write(f"**Autor:** {autor}")
                    st.write(f"**Editorial:** {editorial}")
                    st.write(f"**Grupo Contable:** {grupo_nombre} ({'✅ Cobra IVA' if es_tax else '❌ Exento de IVA'})")
            
            st.write("")
            if st.button("✨ Dar de Alta y Crear Producto en Shopify", type="primary", use_container_width=True, key="btn_create_modal"):
                with st.spinner("Creando producto y configurando inventario..."):
                    new_id, errs = crear_producto_en_shopify(item_consolidado)
                    if new_id:
                        registrar_producto_procesado(codigo_serpi)
                        actualizar_sku_en_snapshot(codigo_serpi, stock=item_consolidado.get("saldo", nuevo_stock), precio=item_consolidado.get("precio", nuevo_precio))
                        st.session_state[f"creado_{codigo_serpi}"] = new_id
                        st.balloons()
                        stock_final = int(float(item_consolidado.get("saldo", nuevo_stock) or 0))
                        if errs:
                            st.warning(f"⚠️ ¡Producto creado (ID: `{new_id}`), pero hubo un aviso en inventario: {errs}")
                        else:
                            st.success(f"🎉 ¡Producto creado y publicado exitosamente con {stock_final} unidades de inventario! (ID: `{new_id}`)")
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
                      taxable
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
            taxable_sp = var_sp.get("taxable", False)
            meta_sp_dict = {edge["node"]["key"]: edge["node"]["value"] for edge in prod_sp.get("metafields", {}).get("edges", [])}

            st.success(f"🔗 Vinculado a producto en Shopify vía: **{match_origen}**")
            
            col_comp1, col_comp2 = st.columns(2)
            with col_comp1:
                with st.container(border=True):
                    st.markdown("##### 📦 Existencias, Precios e Impuestos")
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
                    
                    taxable_nuevo = determinar_taxable_desde_fila(fila_virtual)
                    grupo_serpi = resolver_grupo_contable_articulo(fila_virtual)
                    cambios_list.append({
                        "Atributo": "Impuestos (IVA)",
                        "Shopify": "✅ Cobra IVA (19%)" if taxable_sp else "❌ Exento de IVA",
                        "SERPI": f"{'✅ Cobra IVA' if taxable_nuevo else '❌ Exento'} ({grupo_serpi})",
                        "Impacto": "🔄 Cambia" if taxable_sp != taxable_nuevo else "✅ Al día"
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
                        st.balloons()
                        st.success(f"🎉 ¡Producto '{prod_sp.get('title')}' actualizado con éxito!")
                    else:
                        st.error(f"Errores al sincronizar: {errs_totales}")

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
    st.image("https://cdn-icons-png.flaticon.com/512/2897/2897818.png", width=44)
    st.markdown("### **Panel de Control**")
    st.caption("Estado de integración de servicios")
    
    if API_TOKEN and RAW_SHOP_URL:
        st.success(f"**Shopify Conectado**\n\n`{RAW_SHOP_URL}`")
    else:
        st.error("**Shopify Desconectado**\n\nVerifica las credenciales en `.env`")
    
    st.write("")
    
    serpi_key = SERPI_HEADERS.get("secretkey")
    serpi_token = SERPI_HEADERS.get("Authorization", "").replace("Bearer ", "").strip()
    
    if serpi_key and serpi_token:
        st.success(f"**SERPI ERP Conectado**\n\n`{SERPI_BASE_URL}`")
    else:
        st.error("**SERPI Desconectado**\n\nFalta SecretKey o Token en `.env`")

st.markdown("## 📦 Centro de Sincronización SERPI ➔ Shopify")
st.markdown("<p style='color: #9AA0A6; margin-top: -8px; margin-bottom: 20px; font-size: 14px;'>Automatización y auditoría de inventarios, precios y catálogo multicanal en tiempo real.</p>", unsafe_allow_html=True)

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
        col_ctrl1, col_ctrl2, col_ctrl3, col_ctrl4 = st.columns([2, 2.2, 2.2, 1])
        with col_ctrl1:
            rango_unificado = st.pills("Ventana ERP", [24, 48, 72], format_func=lambda x: f"Últimas {x}h", default=24, key="rango_unificado")
        with col_ctrl2:
            st.write("")
            btn_fast_sync = st.button("⚡ Auditoría Rápida", type="primary", use_container_width=True, key="btn_fast_sync")
        with col_ctrl3:
            st.write("")
            btn_full_snapshot = st.button("📦 Control Global (40k)", type="secondary", use_container_width=True, key="btn_full_snapshot")
        with col_ctrl4:
            st.write("")
            if cant_procesados > 0:
                if st.button(f"🧹 ({cant_procesados})", help="Limpiar productos procesados", use_container_width=True):
                    st.session_state["productos_procesados_ids"] = set()
                    st.rerun()

    # --- FLUJO 1: Auditoría Rápida ---
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
                        "idgrupocontable": art.get("idgrupocontable"),
                        "grupocontable": resolver_grupo_contable_articulo(art),
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

    # --- FLUJO 2: Reconstrucción Global Opcional ---
    if btn_full_snapshot:
        snapshot_previo = cargar_snapshot_control()
        with st.spinner("Paginando catálogo completo de SERPI (40.000 ítems)..."):
            saldos_raw = consultar_inventario_completo()
            precios_raw = consultar_precios_completos()
            
            nuevo_snapshot = dict(snapshot_previo)
            # 1. Sumar existencias de todas las bodegas
            for item in saldos_raw:
                cod = str(item.get("codigo", "")).strip()
                if cod:
                    if cod not in nuevo_snapshot:
                        nuevo_snapshot[cod] = {}
                    stock_act = nuevo_snapshot[cod].get("stock", 0)
                    nuevo_snapshot[cod]["stock"] = stock_act + int(float(item.get("saldo", 0) or 0))
                    
            # 2. Asignar precios válidos (priorizando LISTA PP)
            for item in precios_raw:
                cod = str(item.get("codigo") or item.get("id_articulo", "")).strip()
                if cod:
                    p_val = float(item.get("precio", 0) or 0)
                    if p_val > 0:
                        if cod not in nuevo_snapshot:
                            nuevo_snapshot[cod] = {}
                        if "precio" not in nuevo_snapshot[cod] or nuevo_snapshot[cod]["precio"] == 0 or item.get("id_listaprecio") == 1:
                            nuevo_snapshot[cod]["precio"] = p_val
                    
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

        st.write("")
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

        with kpi_col1:
            is_active = st.session_state["filtro_kpi_activo"] == "TODOS"
            if st.button(f"📦 Total Novedades ({total_art})", type="primary" if is_active else "secondary", use_container_width=True, key="btn_kpi_todos"):
                st.session_state["filtro_kpi_activo"] = "TODOS"
                st.rerun()

        with kpi_col2:
            is_active = st.session_state["filtro_kpi_activo"] == "STOCK"
            if st.button(f"🔄 Con Cambio Stock ({con_stock})", type="primary" if is_active else "secondary", use_container_width=True, key="btn_kpi_stock"):
                st.session_state["filtro_kpi_activo"] = "STOCK"
                st.rerun()

        with kpi_col3:
            is_active = st.session_state["filtro_kpi_activo"] == "PRECIO"
            if st.button(f"💰 Con Cambio Precio ({con_precio})", type="primary" if is_active else "secondary", use_container_width=True, key="btn_kpi_precio"):
                st.session_state["filtro_kpi_activo"] = "PRECIO"
                st.rerun()

        with kpi_col4:
            is_active = st.session_state["filtro_kpi_activo"] == "PENDIENTES"
            if st.button(f"⏳ Pendientes ({pendientes_count})", type="primary" if is_active else "secondary", use_container_width=True, key="btn_kpi_pendientes"):
                st.session_state["filtro_kpi_activo"] = "PENDIENTES"
                st.rerun()

        filtro_actual = st.session_state["filtro_kpi_activo"]
        if filtro_actual != "TODOS":
            st.info(f"🔍 Vista filtrada por: **{filtro_actual}** — Mostrando productos de esta categoría.")

        st.divider()

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

        st.write("")
        st.markdown(f"#### 📊 Matriz de Novedades ({len(libros_disponibles)} productos)")
        
        resumen_tabla = []
        for p in libros_disponibles:
            cod = str(p.get("codigo")).strip()
            ya_listo = esta_procesado(cod)
            cp = p.get("camposPersonalizados", {}) or {}
            grupo_nom = p.get("grupocontable") or resolver_grupo_contable_articulo(p)
            
            resumen_tabla.append({
                "Estado": "✅ PROCESADO" if ya_listo else "⏳ PENDIENTE",
                "Código SKU": cod,
                "Título del Libro": p.get("descripcion"),
                "Grupo Contable": grupo_nom,
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
                    "Grupo Contable": st.column_config.TextColumn("Grupo Contable", width="small"),
                    "Motivo / Variación": st.column_config.TextColumn("Motivo / Variación", width="medium")
                }
            )

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
                            id_gc = item.get("idgrupocontable")
                            nom_gc = item.get("grupocontable") or resolver_grupo_contable_articulo(item)
                            
                            if stk_serpi is None:
                                stk_serpi = obtener_stock_puntual_serpi(cod_serpi)
                            if prc_serpi is None or float(prc_serpi or 0) == 0:
                                prc_serpi = obtener_precio_puntual_serpi(cod_serpi)
                            
                            status.text(f"[{idx+1}/{total_p}] Sincronizando: {tit_serpi[:30]}...")
                            fila_v = pd.Series({
                                "serpi": cod_serpi, 
                                "descripcion": tit_serpi, 
                                "price": prc_serpi, 
                                "idgrupocontable": id_gc,
                                "grupocontable": nom_gc,
                                **cp_serpi
                            })
                            
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