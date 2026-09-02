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

def consultar_todos_los_registros_serpi(endpoint, params_base=None, tamano_pagina=1000, max_paginas=60, status_callback=None):
    if params_base is None:
        params_base = {}
    todos_los_items = []
    pagina = 1
    while pagina <= max_paginas:
        if status_callback:
            status_callback(f"Página {pagina} ({len(todos_los_items):,} registros descargados)...")
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
    10: "Papelería / Gravado (Con IVA)",
    2: "Librería (Exento IVA)",
    12: "Otros (Exento IVA)",
    1: "Papelería",
    3: "Servicios",
    4: "Juguetería",
    5: "Accesorios"
}

def resolver_grupo_contable_articulo(row):
    """
    Obtiene el nombre del Grupo Contable a partir de idgrupocontable o campos similares.
    10 -> Papelería / Gravado (Con IVA)
    2 -> Librería (Exento)
    Cualquier otro -> Exento
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
            id_num = int(float(val_id))
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
        if "10" in txt_lower:
            return "Papelería / Gravado (Con IVA)"
        elif "librer" in txt_lower or "libro" in txt_lower:
            return "Librería (Exento IVA)"
        return txt_limpio

    return "Librería (Exento IVA)"

def determinar_taxable_desde_fila(row):
    """
    Determina si el producto cobra impuestos (taxable=True) o no (taxable=False) en Shopify.
    Regla de Negocio Oficial:
    - Si el producto tiene como grupo contable el número 10 -> DEBE cobrar impuestos en Shopify (taxable = True).
    - Si el número es diferente a 10 (o no está definido) -> NO DEBE cobrar impuestos (taxable = False / Exento de IVA).
    - Si se especifica explícitamente en columna 'taxable'/'impuesto' en Excel/CSV, se respeta dicho valor si existe.
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

    # 2. Evaluar según el Grupo Contable de SERPI:
    # Regla: idgrupocontable == 10 -> cobra IVA (True). Diferente a 10 -> no cobra IVA (False).
    val_id = None
    if isinstance(row, dict):
        val_id = row.get("idgrupocontable") or row.get("id_grupocontable") or row.get("id_grupo_contable") or row.get("idGrupoContable")
    elif isinstance(row, pd.Series):
        for k in ["idgrupocontable", "id_grupocontable", "id_grupo_contable", "idGrupoContable"]:
            if k in row and pd.notna(row[k]):
                val_id = row[k]
                break

    if val_id is not None and str(val_id).strip() != "":
        try:
            return int(float(val_id)) == 10
        except (ValueError, TypeError):
            pass

    return False


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

def consultar_inventario_completo(status_callback=None):
    hoy = datetime.now().strftime("%Y-%m-%d")
    return consultar_todos_los_registros_serpi("/api/v1/SaldoInventarioSinCosto", {"fechaCorte": hoy}, status_callback=status_callback)

def consultar_precios_completos(status_callback=None):
    """Consulta la lista de precios oficial (LISTA PP / id_listaprecio=1) de SERPI con precios por artículo."""
    return consultar_todos_los_registros_serpi("/api/v1/ListaPrecioDetalle", params_base={"id_listaprecio": 1}, tamano_pagina=1000, max_paginas=130, status_callback=status_callback)

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

def obtener_stock_puntual_serpi(codigo_sku, forzar_en_vivo=False):
    """Consulta las existencias de un SKU específico sumando todas las bodegas en SERPI."""
    try:
        codigo_str = str(codigo_sku).strip()
        if not forzar_en_vivo:
            snapshot = cargar_snapshot_control()
            if codigo_str in snapshot and snapshot[codigo_str].get("stock") is not None:
                stk_val = int(float(snapshot[codigo_str]["stock"]))
                if stk_val > 0:
                    return stk_val

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
                val = int(total_stock)
                actualizar_sku_en_snapshot(codigo_str, stock=val)
                return val
            if len(res) > 0:
                val = int(sum(float(r.get("saldo", 0) or 0) for r in res))
                actualizar_sku_en_snapshot(codigo_str, stock=val)
                return val
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

def consultar_articulos_completos_serpi(status_callback=None):
    """Consulta la totalidad de artículos y fichas técnicas de SERPI con paginación máxima."""
    return consultar_todos_los_registros_serpi("/api/v1/Articulo", tamano_pagina=1000, max_paginas=60, status_callback=status_callback)

def enriquecer_snapshot_serpi_completo(status_callback=None, incluir_recalculo_stock=False):
    """
    Descarga el catálogo maestro de SERPI:
    1. Fichas técnicas (/api/v1/Articulo) con autor, editorial, presentación, estado, idgrupocontable y descripción (~45 seg).
    2. Lista de precios oficial (/api/v1/ListaPrecioDetalle con id_listaprecio=1) con precios por artículo (~45 seg).
    Si incluir_recalculo_stock=True, también pagina SaldoInventarioSinCosto (~15-20 min).
    Almacena todo consolidado en el archivo de control local 'control_snapshot.json'.
    """
    snapshot = cargar_snapshot_control()
    
    # 1. Paginación de artículos y fichas técnicas (/api/v1/Articulo)
    if status_callback: status_callback("Paginando catálogo y fichas de SERPI (/api/v1/Articulo)...")
    articulos_raw = consultar_articulos_completos_serpi(
        status_callback=lambda msg: status_callback(f"Fichas SERPI: {msg}") if status_callback else None
    )
    
    # 2. Paginación de precios oficiales (/api/v1/ListaPrecioDetalle - LISTA PP)
    if status_callback: status_callback("Paginando lista de precios oficiales SERPI (LISTA PP)...")
    precios_raw = consultar_precios_completos(
        status_callback=lambda msg: status_callback(f"Precios SERPI: {msg}") if status_callback else None
    )
    
    # Mapeo de precios por id_articulo interno (priorizando LISTA PP / id_listaprecio=1)
    id_to_precio = {}
    for p in precios_raw:
        id_art = p.get("id_articulo")
        prc = float(p.get("precio", 0) or 0)
        id_lp = p.get("id_listaprecio")
        if id_art and prc > 0:
            if id_lp == 1 or id_art not in id_to_precio:
                id_to_precio[id_art] = prc

    # 3. Si se solicitó explícitamente recalcular inventario físico completo
    saldos_map = {}
    if incluir_recalculo_stock:
        if status_callback: status_callback("Recalculando existencias en SERPI (/api/v1/SaldoInventarioSinCosto)...")
        saldos_raw = consultar_inventario_completo(
            status_callback=lambda msg: status_callback(f"Existencias SERPI: {msg}") if status_callback else None
        )
        for item in saldos_raw:
            cod = str(item.get("codigo", "")).strip()
            if cod:
                saldos_map[cod] = saldos_map.get(cod, 0) + int(float(item.get("saldo", 0) or 0))

    # 4. Consolidar catálogo con Ficha Técnica, Precios y Stock en Snapshot
    for art in articulos_raw:
        cod = str(art.get("codigo", "")).strip()
        if not cod:
            continue
        art_id = art.get("id")
        cp = art.get("camposPersonalizados", {}) or {}
        stk = saldos_map.get(cod, snapshot.get(cod, {}).get("stock", 0))
        prc = id_to_precio.get(art_id, snapshot.get(cod, {}).get("precio", 0.0))
        
        snapshot[cod] = {
            "id": art_id,
            "codigo": cod,
            "descripcion": art.get("descripcion", ""),
            "idgrupocontable": art.get("idgrupocontable"),
            "grupocontable": resolver_grupo_contable_articulo(art),
            "idlinea": art.get("idlinea"),
            "activo": art.get("activo", True),
            "autor": cp.get("autor", "") or "",
            "editorial": cp.get("editorial", "") or "",
            "presentacion": cp.get("presentacion", "") or "",
            "estado": cp.get("estado", "") or "",
            "paginas": cp.get("paginas", "") or "",
            "categoria": cp.get("categoria", "") or "",
            "camposPersonalizados": cp,
            "stock": stk,
            "precio": prc,
            "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # Conservar saldos de ítems que vinieron en saldos
    for cod, stk in saldos_map.items():
        if cod not in snapshot:
            snapshot[cod] = {"stock": stk, "precio": 0.0}
        else:
            snapshot[cod]["stock"] = stk

    guardar_snapshot_control(snapshot)
    return snapshot

def descargar_catalogo_completo_shopify_bulk(status_callback=None, forzar_nueva_extraccion=False):
    """
    Ejecuta una consulta masiva por GraphQL Bulk Operation en Shopify.
    Descarga los 29.125 productos con sus variantes y metacampos en ~30 segundos.
    Retorna (productos_por_sku, total_productos, lista_sin_sku).
    """
    status_q = """
    query {
      currentBulkOperation {
        id
        status
        errorCode
        objectCount
        url
      }
    }
    """
    
    # 1. Verificar si hay una operación activa o completada recientemente
    res_status = ejecutar_graphql(status_q)
    curr = res_status.get("data", {}).get("currentBulkOperation")
    
    download_url = None
    if not forzar_nueva_extraccion and curr and curr.get("status") == "COMPLETED" and curr.get("url"):
        download_url = curr.get("url")
        if status_callback: status_callback("Encontrada extracción previa completada. Descargando datos...")
    elif curr and curr.get("status") == "RUNNING":
        if status_callback: status_callback(f"Extracción en curso en servidores de Shopify ({curr.get('objectCount', 0)} objetos)...")
    else:
        mutation_bulk = """
        mutation {
          bulkOperationRunQuery(
            query: \"\"\"
            {
              products {
                edges {
                  node {
                    id
                    title
                    status
                    descriptionHtml
                    variants {
                      edges {
                        node {
                          id
                          sku
                          barcode
                          price
                          inventoryQuantity
                          taxable
                        }
                      }
                    }
                    metafields {
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
              }
            }
            \"\"\"
          ) {
            bulkOperation {
              id
              status
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        res_launch = ejecutar_graphql(mutation_bulk)
        errs = res_launch.get("data", {}).get("bulkOperationRunQuery", {}).get("userErrors", [])
        if errs:
            raise Exception(f"Error iniciando Bulk Operation en Shopify: {errs}")
        if status_callback: status_callback("Extracción masiva iniciada en servidores de Shopify...")

    # 2. Esperar a que complete si aún no tenemos URL
    if not download_url:
        max_wait = 180
        start_time = time.time()
        while time.time() - start_time < max_wait:
            time.sleep(3)
            s = ejecutar_graphql(status_q).get("data", {}).get("currentBulkOperation", {})
            st_op = s.get("status")
            objs = s.get("objectCount", 0)
            if status_callback: status_callback(f"Procesando en Shopify: {objs} objetos ({st_op})...")
            if st_op == "COMPLETED":
                download_url = s.get("url")
                break
            elif st_op in ["FAILED", "CANCELED"]:
                raise Exception(f"La operación masiva en Shopify falló con estado: {st_op}")

    if not download_url:
        raise Exception("Tiempo de espera agotado esperando la extracción de Shopify.")

    # 3. Descargar y parsear el archivo JSONL en memoria
    if status_callback: status_callback("Descargando e indexando catálogo de Shopify en memoria...")
    res_dl = requests.get(download_url, stream=True, timeout=90)
    
    productos_por_id = {}
    for line in res_dl.iter_lines():
        if not line:
            continue
        item = json.loads(line.decode('utf-8'))
        item_id = item.get("id", "")
        
        if "ProductVariant" in item_id:
            p_id = item.get("__parentId")
            if p_id in productos_por_id:
                productos_por_id[p_id]["variant"] = item
                sku_clean = limpiar_identificador_codigo(item.get("sku"))
                barcode_clean = limpiar_identificador_codigo(item.get("barcode"))
                if sku_clean:
                    productos_por_id[p_id]["sku"] = sku_clean
                if barcode_clean:
                    productos_por_id[p_id]["barcode"] = barcode_clean
        elif item.get("namespace") == "custom":
            p_id = item.get("__parentId")
            if p_id in productos_por_id:
                k = item.get("key")
                v = item.get("value")
                productos_por_id[p_id]["metafields"][k] = v
                if k == "serpi" and v:
                    serpi_clean = limpiar_identificador_codigo(v)
                    if serpi_clean:
                        productos_por_id[p_id]["serpi"] = serpi_clean
        elif "Product" in item_id:
            productos_por_id[item_id] = {
                "id": item_id,
                "title": item.get("title", ""),
                "status": item.get("status", ""),
                "descriptionHtml": item.get("descriptionHtml", ""),
                "variant": None,
                "metafields": {},
                "sku": None,
                "barcode": None,
                "serpi": None
            }

    productos_por_sku = {}
    sin_sku = []
    for p_id, p_data in productos_por_id.items():
        # Cascada inteligente de identificadores (SKU -> Barcode -> Metacampo serpi)
        cod_principal = p_data.get("sku") or p_data.get("barcode") or p_data.get("serpi")
        if cod_principal:
            cod_str = str(cod_principal).strip()
            p_data["_codigo_principal"] = cod_str
            productos_por_sku[cod_str] = p_data

            # Multi-indexación: Indexar también por barcode o custom.serpi si difieren para búsqueda instantánea
            bc = p_data.get("barcode")
            if bc and str(bc).strip() != cod_str:
                productos_por_sku[str(bc).strip()] = p_data
            sp_m = p_data.get("serpi")
            if sp_m and str(sp_m).strip() != cod_str:
                productos_por_sku[str(sp_m).strip()] = p_data
        else:
            sin_sku.append(p_data)

    return productos_por_sku, len(productos_por_id), sin_sku

def comparar_serpi_vs_shopify(snapshot_serpi, productos_shopify):
    """
    Compara SKU por SKU el catálogo de Shopify vs el archivo de control SERPI.
    Retorna métricas y lista de discrepancias detalladas.
    """
    total_shopify = len(productos_shopify)
    identicos = []
    desfasados = []
    sin_sku_o_no_serpi = []
    
    cnt_diff_stock = 0
    cnt_diff_precio = 0
    cnt_diff_iva = 0
    cnt_diff_ficha = 0

    for sku, p_data in productos_shopify.items():
        sku_limpio = str(sku).strip()
        if not sku_limpio or sku_limpio not in snapshot_serpi:
            v = p_data.get("variant") or {}
            meta = p_data.get("metafields") or {}
            
            causa = "No registrado en archivo local SERPI"
            if not sku_limpio or sku_limpio in ["0", "00", "000", "None", "nan"]:
                causa = "⚠️ Código '0' o vacío en Shopify"
            elif len(sku_limpio) < 6:
                causa = "⚠️ Código demasiado corto"
            elif p_data.get("status") != "ACTIVE":
                causa = "💤 Producto inactivo / borrador"
                
            sin_sku_o_no_serpi.append({
                "SKU / Código": sku_limpio or "(Sin código)",
                "Título en Shopify": p_data.get("title", ""),
                "Estado": p_data.get("status", ""),
                "Stock Shopify": int(v.get("inventoryQuantity") or 0),
                "Precio Shopify": f"${float(v.get('price') or 0):,.0f}",
                "Variant SKU": str(v.get("sku") or "(Vacío)").strip(),
                "Barcode": str(v.get("barcode") or p_data.get("barcode") or "(Vacío)").strip(),
                "custom.serpi": str(meta.get("serpi") or "(Vacío)").strip(),
                "Diagnóstico": causa,
                "_product_id": p_data.get("id"),
                "_sku": sku_limpio,
                "_raw": p_data
            })
            continue
            
        serpi_item = snapshot_serpi[sku_limpio]
        
        # 1. Stock
        sp_stock = int(p_data.get("variant", {}).get("inventoryQuantity") or 0) if p_data.get("variant") else 0
        erp_stock = int(float(serpi_item.get("stock") or 0))
        diff_stock = (sp_stock != erp_stock)
        
        # 2. Precio
        sp_price = float(p_data.get("variant", {}).get("price") or 0) if p_data.get("variant") else 0.0
        erp_price = float(serpi_item.get("precio") or 0)
        diff_precio = (erp_price > 0 and abs(sp_price - erp_price) >= 1.0)
        
        # 3. IVA / Taxable
        sp_taxable = bool(p_data.get("variant", {}).get("taxable", False)) if p_data.get("variant") else False
        erp_taxable = determinar_taxable_desde_fila(serpi_item)
        diff_iva = (sp_taxable != erp_taxable)
        
        # 4. Ficha / Metafield
        sp_meta = p_data.get("metafields", {})
        cp_serpi = serpi_item.get("camposPersonalizados", {}) or {}
        
        erp_autor = str(serpi_item.get("autor") or cp_serpi.get("autor") or "").strip()
        sp_autor = str(sp_meta.get("autor") or "").strip()
        diff_autor = bool(erp_autor and erp_autor.lower() != sp_autor.lower())
        
        erp_editorial = str(serpi_item.get("editorial") or cp_serpi.get("editorial") or "").strip()
        sp_editorial = str(sp_meta.get("editorial") or "").strip()
        diff_editorial = bool(erp_editorial and erp_editorial.lower() != sp_editorial.lower())
        
        erp_pres = str(serpi_item.get("presentacion") or cp_serpi.get("presentacion") or "").strip()
        sp_pres = str(sp_meta.get("presentacion") or "").strip()
        diff_pres = bool(erp_pres and erp_pres.lower() != sp_pres.lower())
        
        erp_estado = str(serpi_item.get("estado") or cp_serpi.get("estado") or "").strip()
        sp_estado = str(sp_meta.get("estado") or "").strip()
        diff_estado = bool(erp_estado and erp_estado.lower() != sp_estado.lower())
        
        diff_ficha = (diff_autor or diff_editorial or diff_pres or diff_estado)
        
        if diff_stock or diff_precio or diff_iva or diff_ficha:
            tipos = []
            detalles = []
            if diff_stock:
                tipos.append("📦 Stock")
                detalles.append(f"Stock: Shopify={sp_stock} | SERPI={erp_stock}")
                cnt_diff_stock += 1
            if diff_precio:
                tipos.append("💰 Precio")
                detalles.append(f"Precio: Shopify=${sp_price:,.0f} | SERPI=${erp_price:,.0f}")
                cnt_diff_precio += 1
            if diff_iva:
                tipos.append("⚖️ IVA")
                grupo_nom = serpi_item.get("grupocontable") or resolver_grupo_contable_articulo(serpi_item)
                detalles.append(f"IVA: Shopify={'Sí' if sp_taxable else 'No'} | SERPI={'Sí' if erp_taxable else 'No'} ({grupo_nom})")
                cnt_diff_iva += 1
            if diff_ficha:
                tipos.append("📝 Ficha")
                f_det = []
                if diff_autor: f_det.append(f"Autor ('{sp_autor}' vs '{erp_autor}')")
                if diff_editorial: f_det.append(f"Editorial ('{sp_editorial}' vs '{erp_editorial}')")
                if diff_pres: f_det.append(f"Presentación ('{sp_pres}' vs '{erp_pres}')")
                if diff_estado: f_det.append(f"Estado ('{sp_estado}' vs '{erp_estado}')")
                detalles.append("Ficha: " + ", ".join(f_det))
                cnt_diff_ficha += 1
                
            desfasados.append({
                "SKU": sku_limpio,
                "Título": p_data.get("title") or serpi_item.get("descripcion", ""),
                "Tipos": ", ".join(tipos),
                "Detalle de Discrepancias": "  •  ".join(detalles),
                "Stock Shopify": sp_stock,
                "Stock SERPI": erp_stock,
                "Precio Shopify": f"${sp_price:,.0f}",
                "Precio SERPI": f"${erp_price:,.0f}",
                "IVA Shopify": "Sí (19%)" if sp_taxable else "No (Exento)",
                "IVA SERPI": f"{'Sí (19%)' if erp_taxable else 'No (Exento)'} (Grupo {serpi_item.get('idgrupocontable')})",
                "_product_id": p_data["id"],
                "_variant_id": p_data.get("variant", {}).get("id") if p_data.get("variant") else None,
                "_erp_stock": erp_stock,
                "_erp_price": erp_price,
                "_serpi_item": serpi_item,
                "_diff_stock": diff_stock,
                "_diff_precio": diff_precio,
                "_diff_iva": diff_iva,
                "_diff_ficha": diff_ficha
            })
        else:
            identicos.append(sku_limpio)
            
    resumen = {
        "total_shopify": total_shopify,
        "total_identicos": len(identicos),
        "total_desfasados": len(desfasados),
        "total_sin_serpi": len(sin_sku_o_no_serpi),
        "cnt_diff_stock": cnt_diff_stock,
        "cnt_diff_precio": cnt_diff_precio,
        "cnt_diff_iva": cnt_diff_iva,
        "cnt_diff_ficha": cnt_diff_ficha
    }
    return desfasados, identicos, sin_sku_o_no_serpi, resumen

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

def limpiar_identificador_codigo(val):
    """
    Limpia y normaliza códigos de SKU, Barcode o custom.serpi:
    - Remueve comillas simples ('1000014244 -> 1000014244)
    - Remueve sufijos de Excel como .0 (1000014832.0 -> 1000014832)
    - Remueve espacios en blanco
    """
    if val is None:
        return ""
    s = str(val).strip()
    if not s or s.lower() in ("none", "nan", "null"):
        return ""
    # Quitar comillas simples o dobles iniciales o finales
    s = s.strip("'\"")
    # Quitar sufijo .0 proveniente de formatos flotantes de Excel
    s = re.sub(r'\.0$', '', s)
    return s.strip()

def validar_compatibilidad_titulos(titulo_serpi, titulo_shopify):
    """
    Verifica que dos títulos sean razonablemente compatibles para evitar
    emparejamientos erróneos si un código fue mal digitado históricamente.
    Retorna True si son compatibles o si alguno es vacío.
    """
    if not titulo_serpi or not titulo_shopify:
        return True
    
    t1 = limpiar_para_handle(titulo_serpi).replace("-", " ")
    t2 = limpiar_para_handle(titulo_shopify).replace("-", " ")
    
    palabras_comunes = {"de", "la", "el", "los", "las", "en", "un", "una", "unos", "unas", "y", "o", "a", "del", "al", "con", "por", "para"}
    p1 = set(w for w in t1.split() if len(w) > 2 and w not in palabras_comunes)
    p2 = set(w for w in t2.split() if len(w) > 2 and w not in palabras_comunes)
    
    if not p1 or not p2:
        return True
    
    coincidencias = p1.intersection(p2)
    # Deben compartir al menos 1 palabra clave relevante y una proporción razonable
    ratio = len(coincidencias) / min(len(p1), len(p2))
    return len(coincidencias) >= 1 and ratio >= 0.25

def obtener_product_id(row):
    """
    Empareja un artículo de SERPI con un producto de Shopify mediante Cascada Jerárquica:
    1. SKU exacto (normalizado, sin comillas).
    2. Barcode exacto (Código de barras).
    3. Metacampo custom.serpi (normalizado sin .0).
    4. Validación cruzada de coherencia de título.
    NUNCA empareja solo por título o handle sin coincidencia de código.
    """
    v_serpi_raw = obtener_valor_fila(row, ["serpi", "custom.serpi", "serpi (product.metafields.custom.serpi)", "SERPI", "codigo", "sku"])
    v_desc = obtener_valor_fila(row, ["title", "title (product.title)", "descripcion", "descripcion_articulo", "Nombre", "Título"])

    cod_limpio = limpiar_identificador_codigo(v_serpi_raw)
    if not cod_limpio:
        return None, None

    # -------------------------------------------------------------
    # 1. BÚSQUEDA POR SKU LIMPIO (incluyendo variaciones con comilla)
    # -------------------------------------------------------------
    query_sku = """
    query getProductBySku($query: String!) {
      productVariants(first: 5, query: $query) {
        edges {
          node {
            sku
            barcode
            product {
              id
              title
            }
          }
        }
      }
    }
    """
    res_sku = ejecutar_graphql(query_sku, {"query": f"sku:'{cod_limpio}' OR sku:'\\'{cod_limpio}'"})
    variants_sku = res_sku.get("data", {}).get("productVariants", {}).get("edges", []) if res_sku.get("data") else []
    for edge in variants_sku:
        v_node = edge.get("node", {})
        prod = v_node.get("product", {})
        sku_var = limpiar_identificador_codigo(v_node.get("sku"))
        if sku_var == cod_limpio:
            if validar_compatibilidad_titulos(v_desc, prod.get("title")):
                return prod.get("id"), f"SKU: {cod_limpio}"

    # -------------------------------------------------------------
    # 2. BÚSQUEDA POR CÓDIGO DE BARRAS (BARCODE)
    # -------------------------------------------------------------
    query_barcode = """
    query getProductByBarcode($query: String!) {
      productVariants(first: 5, query: $query) {
        edges {
          node {
            sku
            barcode
            product {
              id
              title
            }
          }
        }
      }
    }
    """
    res_barcode = ejecutar_graphql(query_barcode, {"query": f"barcode:'{cod_limpio}'"})
    variants_barcode = res_barcode.get("data", {}).get("productVariants", {}).get("edges", []) if res_barcode.get("data") else []
    for edge in variants_barcode:
        v_node = edge.get("node", {})
        prod = v_node.get("product", {})
        bc_var = limpiar_identificador_codigo(v_node.get("barcode"))
        if bc_var == cod_limpio:
            if validar_compatibilidad_titulos(v_desc, prod.get("title")):
                return prod.get("id"), f"Barcode: {cod_limpio}"

    # -------------------------------------------------------------
    # 3. BÚSQUEDA POR METACAMPO custom.serpi
    # -------------------------------------------------------------
    query_meta = """
    query getProductByMetafield($query: String!) {
      products(first: 5, query: $query) {
        edges {
          node {
            id
            title
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
    res_meta = ejecutar_graphql(query_meta, {"query": f"'{cod_limpio}'"})
    prods_meta = res_meta.get("data", {}).get("products", {}).get("edges", []) if res_meta.get("data") else []
    for edge in prods_meta:
        prod = edge.get("node", {})
        metas = {m["node"]["key"]: m["node"]["value"] for m in prod.get("metafields", {}).get("edges", [])}
        val_serpi_meta = limpiar_identificador_codigo(metas.get("serpi"))
        if val_serpi_meta == cod_limpio:
            if validar_compatibilidad_titulos(v_desc, prod.get("title")):
                return prod.get("id"), f"Metafield custom.serpi: {cod_limpio}"

    # REGLA DE ORO: Si no hubo coincidencia por código, RECHAZAR.
    # NUNCA emparejar basándose solo en título o handle para evitar corromper homónimos.
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
    if campos_permitidos is None or any(c in (campos_permitidos or []) for c in ["taxable", "impuesto", "impuestos", "idgrupocontable", "grupocontable", "linea", "idlinea"]):
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
                try:
                    p_val = float(v_price)
                    if p_val > 0:
                        var_item["price"] = f"{p_val:.2f}"
                except (ValueError, TypeError):
                    pass
            if v_sku is not None:
                cod_limpio = limpiar_identificador_codigo(v_sku)
                if cod_limpio:
                    var_item["barcode"] = cod_limpio
                    var_item["inventoryItem"] = {"sku": cod_limpio}
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

    if nuevo_stock is None or int(float(nuevo_stock or 0)) == 0:
        fresco = obtener_stock_puntual_serpi(codigo_serpi, forzar_en_vivo=True)
        if fresco > 0 or nuevo_stock is None:
            nuevo_stock = fresco
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

tab_unificado, tab_reconciliacion, tab_excel, tab_portadas = st.tabs([
    "⚡ Sincronización Rápida", 
    "🔄 Reconciliación Global (29k)",
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

    # --- FLUJO 1: Auditoría Rápida con Cruce Automático contra Shopify ---
    if btn_fast_sync:
        snapshot_previo = cargar_snapshot_control()
        with st.spinner("Consultando artículos modificados recientemente en SERPI y auditando contra Shopify..."):
            articulos_raw = consultar_articulos_modificados(horas=rango_unificado)
            
            # Obtener catálogo de Shopify (desde cache de sesión o descarga bulk rápida)
            if "shopify_catalogo_cache" in st.session_state and st.session_state["shopify_catalogo_cache"]:
                prods_shopify = st.session_state["shopify_catalogo_cache"]
            else:
                prods_shopify, _, _ = descargar_catalogo_completo_shopify_bulk()
                st.session_state["shopify_catalogo_cache"] = prods_shopify
            
            mapa_novedades = {}
            for art in articulos_raw:
                cod = str(art.get("codigo", "")).strip()
                if not cod:
                    continue
                
                # Obtener stock y precio oficial desde snapshot
                snap_item = snapshot_previo.get(cod, {})
                stock_snap = snap_item.get("stock")
                precio_snap = snap_item.get("precio")
                
                # Ficha técnica SERPI
                cp_serpi = art.get("camposPersonalizados", {}) or {}
                id_gc = art.get("idgrupocontable")
                nom_gc = art.get("grupocontable") or resolver_grupo_contable_articulo(art)
                erp_taxable = determinar_taxable_desde_fila(art)
                
                # Datos de Shopify para este SKU
                p_data = prods_shopify.get(cod)
                
                tipos = []
                detalles = []
                
                if p_data:
                    # 1. Stock
                    sp_stock = int(p_data.get("variant", {}).get("inventoryQuantity") or 0) if p_data.get("variant") else 0
                    erp_stock = int(float(stock_snap or 0)) if stock_snap is not None else None
                    if erp_stock is not None and sp_stock != erp_stock:
                        tipos.append("📦 Stock")
                        detalles.append(f"Stock: Shopify={sp_stock} | SERPI={erp_stock}")
                        
                    # 2. Precio
                    sp_price = float(p_data.get("variant", {}).get("price") or 0) if p_data.get("variant") else 0.0
                    erp_price = float(precio_snap or 0) if precio_snap is not None else 0.0
                    if erp_price > 0 and abs(sp_price - erp_price) >= 1.0:
                        tipos.append("💰 Precio")
                        detalles.append(f"Precio: Shopify=${sp_price:,.0f} | SERPI=${erp_price:,.0f}")
                        
                    # 3. IVA
                    sp_taxable = bool(p_data.get("variant", {}).get("taxable", False)) if p_data.get("variant") else False
                    if sp_taxable != erp_taxable:
                        tipos.append("⚖️ IVA")
                        detalles.append(f"IVA: Shopify={'Sí' if sp_taxable else 'No'} | SERPI={'Sí' if erp_taxable else 'No'} ({nom_gc})")
                        
                    # 4. Ficha Técnica
                    sp_meta = p_data.get("metafields", {})
                    erp_autor = str(cp_serpi.get("autor") or "").strip()
                    sp_autor = str(sp_meta.get("autor") or "").strip()
                    diff_aut = bool(erp_autor and erp_autor.lower() != sp_autor.lower())
                    
                    erp_edit = str(cp_serpi.get("editorial") or "").strip()
                    sp_edit = str(sp_meta.get("editorial") or "").strip()
                    diff_edit = bool(erp_edit and erp_edit.lower() != sp_edit.lower())
                    
                    erp_pres = str(cp_serpi.get("presentacion") or "").strip()
                    sp_pres = str(sp_meta.get("presentacion") or "").strip()
                    diff_pres = bool(erp_pres and erp_pres.lower() != sp_pres.lower())
                    
                    erp_est = str(cp_serpi.get("estado") or "").strip()
                    sp_est = str(sp_meta.get("estado") or "").strip()
                    diff_est = bool(erp_est and erp_est.lower() != sp_est.lower())
                    
                    if diff_aut or diff_edit or diff_pres or diff_est:
                        tipos.append("📝 Ficha")
                        f_sub = []
                        if diff_aut: f_sub.append(f"Autor ('{sp_autor}' vs '{erp_autor}')")
                        if diff_edit: f_sub.append(f"Editorial ('{sp_edit}' vs '{erp_edit}')")
                        if diff_pres: f_sub.append(f"Presentación ('{sp_pres}' vs '{erp_pres}')")
                        if diff_est: f_sub.append(f"Estado ('{sp_est}' vs '{erp_est}')")
                        detalles.append("Ficha: " + ", ".join(f_sub))
                        
                    motivo_str = ", ".join(tipos) if tipos else "✅ 100% Al día"
                    prod_shopify_id = p_data.get("id")
                else:
                    motivo_str = "🆕 Nuevo en SERPI (No creado en Shopify)"
                    detalles.append("Este producto modificado en SERPI aún no existe en Shopify.")
                    prod_shopify_id = None
                
                mapa_novedades[cod] = {
                    "codigo": cod,
                    "descripcion": art.get("descripcion", ""),
                    "idgrupocontable": id_gc,
                    "grupocontable": nom_gc,
                    "camposPersonalizados": cp_serpi,
                    "saldo": stock_snap,
                    "precio": precio_snap,
                    "motivo": motivo_str,
                    "detalles": "  •  ".join(detalles) if detalles else "Coincide exactamente con Shopify",
                    "_product_id": prod_shopify_id
                }
            
            lista_final = list(mapa_novedades.values())
            if lista_final:
                st.session_state["cache_unificado"] = lista_final
                st.session_state["filtro_kpi_activo"] = "TODOS"
                desfasados_cant = sum(1 for p in lista_final if "✅" not in p.get("motivo", ""))
                st.success(f"🎯 Auditados **{len(lista_final)}** productos modificados en las últimas {rango_unificado}h frente a Shopify: **{desfasados_cant}** requieren sincronización.")
            else:
                st.session_state.pop("cache_unificado", None)
                st.info("✅ Sin modificaciones de catálogo en el rango horario seleccionado.")


    # --- FLUJO 2: Reconstrucción Global Opcional ---
    if btn_full_snapshot:
        with st.spinner("Paginando catálogo completo, fichas, precios oficiales y saldos de SERPI..."):
            prog_full = st.empty()
            nuevo_snapshot = enriquecer_snapshot_serpi_completo(
                status_callback=lambda msg: prog_full.text(f"SERPI: {msg}"),
                incluir_recalculo_stock=True
            )
            prog_full.empty()
            st.success(f"🎉 Base de control global actualizada exitosamente con **{len(nuevo_snapshot):,}** productos consolidados.")


    # -------------------------------------------------------------
    # RENDERIZADO INTERACTIVO: KPIS COMO BOTONES, BUSCADOR Y MATRIZ
    # -------------------------------------------------------------
    if "cache_unificado" in st.session_state and st.session_state["cache_unificado"]:
        lista_cache = st.session_state["cache_unificado"]

        if "filtro_kpi_activo" not in st.session_state:
            st.session_state["filtro_kpi_activo"] = "TODOS"

        total_art = len(lista_cache)
        con_desfase = sum(1 for p in lista_cache if any(icon in str(p.get("motivo", "")) for icon in ["📦", "💰", "⚖️", "📝", "🆕"]))
        con_stock = sum(1 for p in lista_cache if "📦 Stock" in str(p.get("motivo", "")))
        con_precio = sum(1 for p in lista_cache if "💰 Precio" in str(p.get("motivo", "")))
        con_iva = sum(1 for p in lista_cache if "⚖️ IVA" in str(p.get("motivo", "")))
        con_ficha = sum(1 for p in lista_cache if "📝 Ficha" in str(p.get("motivo", "")))
        con_nuevo = sum(1 for p in lista_cache if "🆕" in str(p.get("motivo", "")))
        al_dia = sum(1 for p in lista_cache if "✅ 100% Al día" in str(p.get("motivo", "")))
        pendientes_count = sum(1 for p in lista_cache if not esta_procesado(p.get("codigo")))

        st.write("")
        kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5, kpi_col6 = st.columns(6)

        with kpi_col1:
            is_active = st.session_state["filtro_kpi_activo"] == "TODOS"
            if st.button(f"📦 Total ({total_art})", type="primary" if is_active else "secondary", use_container_width=True, key="btn_kpi_todos"):
                st.session_state["filtro_kpi_activo"] = "TODOS"
                st.rerun()

        with kpi_col2:
            is_active = st.session_state["filtro_kpi_activo"] == "DESFASADOS"
            if st.button(f"🚨 Desfasados ({con_desfase})", type="primary" if is_active else "secondary", use_container_width=True, key="btn_kpi_desfasados"):
                st.session_state["filtro_kpi_activo"] = "DESFASADOS"
                st.rerun()

        with kpi_col3:
            is_active = st.session_state["filtro_kpi_activo"] == "STOCK"
            if st.button(f"🔄 Stock ({con_stock})", type="primary" if is_active else "secondary", use_container_width=True, key="btn_kpi_stock"):
                st.session_state["filtro_kpi_activo"] = "STOCK"
                st.rerun()

        with kpi_col4:
            is_active = st.session_state["filtro_kpi_activo"] == "PRECIO"
            if st.button(f"💰 Precio ({con_precio})", type="primary" if is_active else "secondary", use_container_width=True, key="btn_kpi_precio"):
                st.session_state["filtro_kpi_activo"] = "PRECIO"
                st.rerun()

        with kpi_col5:
            is_active = st.session_state["filtro_kpi_activo"] == "IVA"
            if st.button(f"⚖️ IVA ({con_iva})", type="primary" if is_active else "secondary", use_container_width=True, key="btn_kpi_iva"):
                st.session_state["filtro_kpi_activo"] = "IVA"
                st.rerun()

        with kpi_col6:
            is_active = st.session_state["filtro_kpi_activo"] == "AL_DIA"
            if st.button(f"✅ Al día ({al_dia})", type="primary" if is_active else "secondary", use_container_width=True, key="btn_kpi_aldia"):
                st.session_state["filtro_kpi_activo"] = "AL_DIA"
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
            elif filtro_actual == "IVA" and "⚖️ IVA" not in motivo:
                continue
            elif filtro_actual == "DESFASADOS" and not any(icon in motivo for icon in ["📦", "💰", "⚖️", "📝", "🆕"]):
                continue
            elif filtro_actual == "AL_DIA" and "✅ 100% Al día" not in motivo:
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
                "Diferencias": p.get("motivo", "—"),
                "Detalle de Discrepancias": p.get("detalles", "—"),
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
                    "Diferencias": st.column_config.TextColumn("Diferencias", width="medium"),
                    "Detalle de Discrepancias": st.column_config.TextColumn("Detalle de Discrepancias", width="large")
                }
            )

        st.write("")
        with st.container(border=True):
            col_mas_info, col_mas_btn = st.columns([3, 2])
            with col_mas_info:
                st.markdown("##### ⚡ Sincronización en Lote")
                st.caption(f"Se sincronizarán todos los productos pendientes con discrepancias en Shopify.")
            with col_mas_btn:
                st.write("")
                if st.button("🚀 Aplicar Lote de Desfasados en Shopify", type="primary", use_container_width=True, key="btn_masivo_global"):
                    progreso = st.progress(0)
                    status = st.empty()
                    pendientes = [
                        p for p in lista_cache 
                        if not esta_procesado(p.get("codigo")) 
                        and ("✅ 100% Al día" not in str(p.get("motivo", "")))
                    ]
                    total_p = len(pendientes)
                    exitos, errores = 0, 0
                    
                    if total_p == 0:
                        st.info("No hay productos con diferencias pendientes por sincronizar en la lista.")
                    else:
                        for idx, item in enumerate(pendientes):
                            cod_serpi = item.get("codigo")
                            tit_serpi = item.get("descripcion", "")
                            cp_serpi = item.get("camposPersonalizados", {}) or {}
                            stk_serpi = item.get("saldo")
                            prc_serpi = item.get("precio")
                            id_gc = item.get("idgrupocontable")
                            nom_gc = item.get("grupocontable") or resolver_grupo_contable_articulo(item)
                            
                            if stk_serpi is None or int(float(stk_serpi or 0)) == 0:
                                stk_serpi = obtener_stock_puntual_serpi(cod_serpi, forzar_en_vivo=True)
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
                            
                            p_id = item.get("_product_id") or obtener_product_id(fila_v)[0]
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
# PESTAÑA 2: RECONCILIACIÓN GLOBAL DE CATÁLOGO (SERPI vs SHOPIFY 29K)
# =============================================================
with tab_reconciliacion:
    st.markdown("### 🔄 Reconciliación Global de Catálogo (SERPI vs Shopify)")
    st.markdown(
        "<p style='color: #9AA0A6; margin-top: -8px; font-size: 14px;'>"
        "Auditoría masiva de los 29.125 productos de Shopify contra el ERP SERPI. "
        "Permite detectar y sincronizar discrepancias de Stock, Precios, IVA (según Grupo Contable) y Ficha Técnica."
        "</p>", 
        unsafe_allow_html=True
    )
    
    snapshot_control_actual = cargar_snapshot_control()
    tiene_fichas_actual = bool(snapshot_control_actual) and any(bool(v.get("autor") or v.get("editorial")) for v in list(snapshot_control_actual.values())[:100])
    
    with st.container(border=True):
        st.markdown("#### ⚡ Parámetros de Auditoría y Reconciliación")
        
        if not tiene_fichas_actual:
            st.warning(
                "⚠️ **Aviso de Fichas Técnicas:** El archivo de control local (`control_snapshot.json`) contiene existencias de inventario pero aún no tiene almacenadas las **Fichas Técnicas (Autor, Editorial, Presentación, Estado)** ni los **Precios Oficiales de SERPI**.<br>"
                "La casilla de actualización de catálogo maestro está marcada automáticamente para descargar y almacenar esta información (~1.5 min) y habilitar la detección de discrepancias técnicas.",
                icon="⚠️"
            )
        else:
            st.info("💡 **Modo Rápido Disponible:** El archivo de control local ya tiene fichas técnicas y precios. La auditoría cruzará los **29.125 productos de Shopify** en memoria en **~30 a 45 segundos**.")
        
        col_rec_cfg1, col_rec_cfg2 = st.columns([3, 2])
        with col_rec_cfg1:
            chk_enriquecer_fichas = st.checkbox(
                "📝 Descargar/Actualizar Fichas Técnicas y Precios Oficiales desde SERPI (~1.5 min)",
                value=(not tiene_fichas_actual),
                help="Descarga todas las fichas técnicas maestro (/api/v1/Articulo) y la lista de precios oficial (LISTA PP) de SERPI y las guarda permanentemente en el archivo de control local."
            )
            with st.expander("⚙️ Opciones avanzadas adicionales", expanded=False):
                chk_recalcular_saldos = st.checkbox(
                    "⚠️ Recalcular inventario físico completo en SERPI (~15-20 min)",
                    value=False,
                    help="Consulta saldo por saldo en todas las bodegas de SERPI. Proceso pesado, solo usar en mantenimiento o fuera de horario."
                )
                chk_forzar_shopify = st.checkbox(
                    "⚡ Forzar nueva extracción desde servidores de Shopify",
                    value=False,
                    help="Si está desmarcado y existe una extracción reciente (< 2h), se reutiliza para máxima velocidad (~20 segundos)."
                )
        with col_rec_cfg2:
            st.write("")
            btn_iniciar_reconciliacion = st.button(
                "🔎 Iniciar Auditoría Global (SERPI vs Shopify 29k)",
                type="primary",
                use_container_width=True,
                key="btn_iniciar_reconciliacion"
            )

    # --- FLUJO DE AUDITORÍA ---
    if btn_iniciar_reconciliacion:
        prog_bar = st.progress(0)
        status_rec = st.empty()
        try:
            # 1. SERPI
            snapshot_serpi = cargar_snapshot_control()
            necesita_fichas = chk_enriquecer_fichas or chk_recalcular_saldos or (not tiene_fichas_actual)
            
            if necesita_fichas:
                status_rec.text("Fase 1/3: Descargando fichas técnicas y precios oficiales desde SERPI (~1.5 min)...")
                snapshot_serpi = enriquecer_snapshot_serpi_completo(
                    status_callback=lambda msg: status_rec.text(f"SERPI: {msg}"),
                    incluir_recalculo_stock=chk_recalcular_saldos
                )
            else:
                status_rec.text(f"Fase 1/3: Archivo de control SERPI listo ({len(snapshot_serpi):,} SKUs con fichas y precios)...")
            prog_bar.progress(35)
            
            # 2. SHOPIFY BULK
            status_rec.text("Fase 2/3: Consultando los 29.125 productos de Shopify...")
            prods_shopify, total_sp, sin_sku = descargar_catalogo_completo_shopify_bulk(
                status_callback=lambda msg: status_rec.text(f"Shopify: {msg}"),
                forzar_nueva_extraccion=chk_forzar_shopify
            )
            st.session_state["shopify_catalogo_cache"] = prods_shopify
            prog_bar.progress(75)
            
            # 3. COMPARAR EN MEMORIA
            status_rec.text("Fase 3/3: Comparando discrepancias SKU por SKU en memoria...")
            desfasados, identicos, sin_serpi, resumen = comparar_serpi_vs_shopify(snapshot_serpi, prods_shopify)
            prog_bar.progress(100)
            
            st.session_state["reconciliacion_resultados"] = {
                "desfasados": desfasados,
                "identicos": identicos,
                "sin_serpi": sin_serpi,
                "resumen": resumen,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            st.session_state["filtro_reconciliacion"] = "TODOS"
            status_rec.empty()
            prog_bar.empty()
            st.success(f"🎉 ¡Auditoría completada exitosamente! Se analizaron {total_sp:,} productos en Shopify.")
            st.rerun()
            
        except Exception as e:
            status_rec.empty()
            prog_bar.empty()
            st.error(f"Error durante la auditoría global: {e}")

    # --- RESULTADOS Y MATRIZ DE AUDITORÍA ---
    res_rec = st.session_state.get("reconciliacion_resultados")
    if res_rec:
        resumen = res_rec["resumen"]
        desfasados = res_rec["desfasados"]
        
        st.write("")
        col_meta_info, col_meta_clear = st.columns([4, 1])
        with col_meta_info:
            st.caption(f"📅 Auditoría ejecutada el: **{res_rec.get('fecha')}**")
        with col_meta_clear:
            if st.button("🔄 Nueva Auditoría", type="secondary", use_container_width=True, key="btn_nueva_auditoria"):
                st.session_state.pop("reconciliacion_resultados", None)
                st.rerun()
        
        # Tarjetas de Métricas Principales
        c_rec1, c_rec2, c_rec3, c_rec4 = st.columns(4)
        c_rec1.metric("🏪 Total en Shopify", f"{resumen['total_shopify']:,}")
        c_rec2.metric("✅ 100% al Día", f"{resumen['total_identicos']:,}")
        c_rec3.metric("🔄 Desfasados (Diff)", f"{resumen['total_desfasados']:,}")
        c_rec4.metric("⚠️ Sin Match SERPI", f"{resumen['total_sin_serpi']:,}")
        
        # Selector de Vista Principal: Desfasados vs Sin Match
        vista_reconciliacion = st.radio(
            "Seleccionar Vista de Auditoría:",
            [
                f"🔄 Productos Desfasados con Diferencias ({resumen['total_desfasados']:,})",
                f"⚠️ Productos en Shopify Sin Match en SERPI ({resumen['total_sin_serpi']:,})"
            ],
            horizontal=True,
            key="radio_vista_reconciliacion"
        )

        if vista_reconciliacion.startswith("🔄"):
            # Desglose de Tipos de Discrepancias
            st.markdown(
                f"<div style='background: #181C22; border-radius: 12px; padding: 12px 16px; margin: 12px 0; font-size: 13px; color: #C4C7C5; border: 1px solid #2B313A;'>"
                f"<b>Discrepancias detectadas:</b> &nbsp;"
                f"📦 Stock: <span style='color: #8AB4F8; font-weight: bold;'>{resumen['cnt_diff_stock']}</span> &nbsp;|&nbsp; "
                f"💰 Precio: <span style='color: #81C995; font-weight: bold;'>{resumen['cnt_diff_precio']}</span> &nbsp;|&nbsp; "
                f"⚖️ IVA / Grupo: <span style='color: #FDD663; font-weight: bold;'>{resumen['cnt_diff_iva']}</span> &nbsp;|&nbsp; "
                f"📝 Ficha Técnica: <span style='color: #FF8BCB; font-weight: bold;'>{resumen['cnt_diff_ficha']}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
            
            # Filtros de visualización
            col_fil1, col_fil2 = st.columns([3, 2])
            with col_fil1:
                filtro_rec = st.pills(
                    "Filtrar Discrepancias",
                    ["TODOS", "STOCK", "PRECIO", "IVA", "FICHA"],
                    format_func=lambda x: {
                        "TODOS": f"Todos ({resumen['total_desfasados']})",
                        "STOCK": f"📦 Stock ({resumen['cnt_diff_stock']})",
                        "PRECIO": f"💰 Precio ({resumen['cnt_diff_precio']})",
                        "IVA": f"⚖️ IVA ({resumen['cnt_diff_iva']})",
                        "FICHA": f"📝 Ficha ({resumen['cnt_diff_ficha']})"
                    }.get(x, x),
                    default=st.session_state.get("filtro_reconciliacion", "TODOS"),
                    key="pills_rec_filtro"
                )
                st.session_state["filtro_reconciliacion"] = filtro_rec
                
            with col_fil2:
                txt_buscar_rec = st.text_input("🔍 Buscar por SKU o Título", "", key="buscar_rec_input")
                
            items_filtrados = desfasados
            if filtro_rec == "STOCK":
                items_filtrados = [d for d in items_filtrados if d.get("_diff_stock")]
            elif filtro_rec == "PRECIO":
                items_filtrados = [d for d in items_filtrados if d.get("_diff_precio")]
            elif filtro_rec == "IVA":
                items_filtrados = [d for d in items_filtrados if d.get("_diff_iva")]
            elif filtro_rec == "FICHA":
                items_filtrados = [d for d in items_filtrados if d.get("_diff_ficha")]
                
            if txt_buscar_rec.strip():
                tb = txt_buscar_rec.strip().lower()
                items_filtrados = [d for d in items_filtrados if tb in str(d.get("SKU", "")).lower() or tb in str(d.get("Título", "")).lower()]
                
            cols_mostrar = [
                "SKU", "Título", "Tipos", "Stock Shopify", "Stock SERPI", 
                "Precio Shopify", "Precio SERPI", "IVA Shopify", "IVA SERPI", "Detalle de Discrepancias"
            ]
            df_rec_mostrar = pd.DataFrame(items_filtrados)
            if not df_rec_mostrar.empty:
                st.dataframe(
                    df_rec_mostrar[cols_mostrar],
                    width="stretch",
                    height=350,
                    hide_index=True,
                    column_config={
                        "SKU": st.column_config.TextColumn("Código SKU", width="small"),
                        "Título": st.column_config.TextColumn("Título", width="medium"),
                        "Tipos": st.column_config.TextColumn("Diferencias", width="small"),
                        "Detalle de Discrepancias": st.column_config.TextColumn("Detalle", width="large")
                    }
                )
            else:
                st.info("No hay productos con los filtros seleccionados.")
        else:
            # VISTA: PRODUCTOS DE SHOPIFY SIN MATCH EN SERPI
            sin_serpi_raw = res_rec.get("sin_serpi", [])
            sin_serpi_norm = []
            for item in sin_serpi_raw:
                if isinstance(item, dict) and "SKU / Código" in item:
                    sin_serpi_norm.append(item)
                elif isinstance(item, dict):
                    cod = str(item.get("sku") or item.get("serpi") or "").strip()
                    v = item.get("variant") or {}
                    meta = item.get("metafields") or {}
                    causa = "No registrado en archivo local SERPI"
                    if not cod or cod in ["0", "00", "000", "None", "nan"]:
                        causa = "⚠️ Código '0' o vacío en Shopify"
                    elif len(cod) < 6:
                        causa = "⚠️ Código demasiado corto"
                    elif item.get("status") != "ACTIVE":
                        causa = "💤 Producto inactivo / borrador"
                        
                    sin_serpi_norm.append({
                        "SKU / Código": cod or "(Sin código)",
                        "Título en Shopify": item.get("title", ""),
                        "Estado": item.get("status", ""),
                        "Stock Shopify": int(v.get("inventoryQuantity") or 0),
                        "Precio Shopify": f"${float(v.get('price') or 0):,.0f}",
                        "Variant SKU": str(v.get("sku") or "(Vacío)").strip(),
                        "custom.serpi": str(meta.get("serpi") or "(Vacío)").strip(),
                        "Diagnóstico": causa,
                        "_product_id": item.get("id"),
                        "_sku": cod
                    })

            st.markdown(
                f"<div style='background: #1C1917; border-radius: 12px; padding: 12px 16px; margin: 12px 0; font-size: 13px; color: #F59E0B; border: 1px solid #78350F;'>"
                f"<b>⚠️ Productos en Shopify no encontrados en el archivo de control local de SERPI ({len(sin_serpi_norm):,}):</b><br>"
                f"Estos artículos están creados en tu tienda Shopify pero no coinciden con el snapshot local de SERPI. "
                f"<b>Razones principales:</b><br>"
                f"1. <b>Tienen saldo 0 en SERPI:</b> Muchos libros existen en el catálogo maestro de SERPI pero al no tener existencias físicas no figuraban en el corte de saldos.<br>"
                f"2. <b>Error de digitación en Shopify:</b> El SKU o código de barras fue ingresado con algún error tipográfico.<br>"
                f"3. <b>Artículos propios de la tienda web:</b> Creados directamente en Shopify (servicios, promociones, bonos) sin contraparte en ERP."
                f"</div>",
                unsafe_allow_html=True
            )
            
            col_sm_fil1, col_sm_fil2, col_sm_fil3 = st.columns([2.5, 2.5, 1.5])
            with col_sm_fil1:
                filtro_sm_est = st.pills(
                    "Filtrar por Estado",
                    ["TODOS", "ACTIVOS", "BORRADORES", "SKU_CERO"],
                    format_func=lambda x: {
                        "TODOS": f"Todos ({len(sin_serpi_norm):,})",
                        "ACTIVOS": "Activos",
                        "BORRADORES": "Borradores / Archivados",
                        "SKU_CERO": "SKU '0' o Vacío"
                    }.get(x, x),
                    default="TODOS",
                    key="pills_sm_estado"
                )
            with col_sm_fil2:
                txt_buscar_sm = st.text_input("🔍 Buscar por SKU o Título en Sin Match", "", key="buscar_sm_input")
            with col_sm_fil3:
                st.write("")
                df_sm_all = pd.DataFrame(sin_serpi_norm)
                cols_export = ["SKU / Código", "Título en Shopify", "Estado", "Stock Shopify", "Precio Shopify", "Variant SKU", "custom.serpi", "Diagnóstico"]
                if not df_sm_all.empty:
                    csv_data = df_sm_all[cols_export].to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Descargar CSV",
                        data=csv_data,
                        file_name=f"shopify_sin_match_serpi_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
            items_sm_filtrados = sin_serpi_norm
            if filtro_sm_est == "ACTIVOS":
                items_sm_filtrados = [d for d in items_sm_filtrados if d.get("Estado") == "ACTIVE"]
            elif filtro_sm_est == "BORRADORES":
                items_sm_filtrados = [d for d in items_sm_filtrados if d.get("Estado") != "ACTIVE"]
            elif filtro_sm_est == "SKU_CERO":
                items_sm_filtrados = [d for d in items_sm_filtrados if d.get("SKU / Código") in ["0", "00", "000", "(Sin código)", "None"]]
                
            if txt_buscar_sm.strip():
                tb_sm = txt_buscar_sm.strip().lower()
                items_sm_filtrados = [d for d in items_sm_filtrados if tb_sm in str(d.get("SKU / Código", "")).lower() or tb_sm in str(d.get("Título en Shopify", "")).lower()]
                
            df_sm_mostrar = pd.DataFrame(items_sm_filtrados)
            if not df_sm_mostrar.empty:
                st.dataframe(
                    df_sm_mostrar[cols_export],
                    width="stretch",
                    height=380,
                    hide_index=True,
                    column_config={
                        "SKU / Código": st.column_config.TextColumn("Código SKU", width="small"),
                        "Título en Shopify": st.column_config.TextColumn("Título en Shopify", width="medium"),
                        "Estado": st.column_config.TextColumn("Estado", width="small"),
                        "Stock Shopify": st.column_config.NumberColumn("Stock", width="small"),
                        "Precio Shopify": st.column_config.TextColumn("Precio", width="small"),
                        "Diagnóstico": st.column_config.TextColumn("Diagnóstico", width="medium")
                    }
                )
            else:
                st.info("No hay productos con los filtros seleccionados.")
                
            # Herramienta de Diagnóstico en Vivo puntual
            st.write("")
            with st.container(border=True):
                st.markdown("#### 🔍 Diagnosticar un Producto Puntual contra SERPI en Vivo")
                st.caption("Verifica si un código de los que no hicieron match realmente existe en la base de datos de SERPI o si nunca fue creado en el ERP.")
                
                c_diag1, c_diag2 = st.columns([3, 1])
                with c_diag1:
                    sku_a_probar = st.text_input("Ingresa o pega el SKU / Código de barras a consultar en SERPI:", value="", placeholder="Ej: 9789585531642", key="sku_diag_input")
                with c_diag2:
                    st.write("")
                    btn_probar_serpi = st.button("🔍 Probar en SERPI", type="primary", use_container_width=True, key="btn_probar_serpi")
                    
                if btn_probar_serpi and sku_a_probar.strip():
                    with st.spinner(f"Consultando '{sku_a_probar.strip()}' en /api/v1/Articulo de SERPI..."):
                        res_serpi_diag = consultar_serpi_api("/api/v1/Articulo", params={"codigo": sku_a_probar.strip()})
                        if res_serpi_diag and isinstance(res_serpi_diag, list) and len(res_serpi_diag) > 0:
                            art_d = res_serpi_diag[0]
                            st.success(f"✅ **¡El código SÍ existe en SERPI!**")
                            st.markdown(
                                f"- **Código SERPI:** `{art_d.get('codigo')}`\n"
                                f"- **Título / Descripción en SERPI:** **{art_d.get('descripcion')}**\n"
                                f"- **Grupo Contable:** {resolver_grupo_contable_articulo(art_d)} (ID: {art_d.get('idgrupocontable')})\n"
                                f"- **Activo en SERPI:** {'Sí' if art_d.get('activo') else 'No'}\n\n"
                                f"💡 **¿Por qué no hizo match antes?** Este producto está registrado en el catálogo maestro de artículos de SERPI, pero **no estaba en el archivo de control local** porque tenía saldo de inventario en 0 cuando se generó el snapshot."
                            )
                            if st.button("➕ Incorporar este producto al Archivo de Control Local", key="btn_add_snap_single"):
                                actualizar_sku_en_snapshot(art_d.get('codigo'), stock=0, precio=0)
                                st.success("¡Producto incorporado al archivo de control! En la próxima auditoría ya hará match.")
                                st.rerun()
                        else:
                            st.error(f"❌ **El código '{sku_a_probar.strip()}' NO existe en SERPI.**")
                            st.markdown(
                                f"💡 **Diagnóstico:** La API de SERPI no devolvió ningún artículo con este código. "
                                f"Causas posibles: el SKU fue inventado en Shopify, es un producto temporal, o tiene un error de digitación en Shopify frente al código de barras real."
                            )
            
        # --- FASE 2: SINCRONIZACIÓN CONTROLADA ---
        st.write("")
        with st.container(border=True):
            st.markdown("#### 🚀 Fase 2: Sincronización Controlada en Shopify")
            col_sy1, col_sy2, col_sy3 = st.columns([3, 2, 2])
            
            pendientes_rec = [d for d in desfasados if not esta_procesado(d["SKU"])]
            with col_sy1:
                tam_lote_sel = st.selectbox(
                    "Lote a sincronizar:",
                    ["Todo el lote de desfasados", "Bloque de 100 productos", "Bloque de 250 productos", "Bloque de 500 productos"],
                    key="tam_lote_rec_sel"
                )
            with col_sy2:
                st.write("")
                st.caption(f"Pendientes por sincronizar: **{len(pendientes_rec)}** de {len(desfasados)}")
            with col_sy3:
                st.write("")
                btn_sync_desfasados = st.button(
                    "🚀 Sincronizar Diferencias en Shopify",
                    type="primary",
                    use_container_width=True,
                    key="btn_sync_desfasados"
                )
                
            if btn_sync_desfasados:
                if not pendientes_rec:
                    st.info("Todos los productos desfasados ya han sido procesados y sincronizados.")
                else:
                    limite_lote = len(pendientes_rec)
                    if "100" in tam_lote_sel: limite_lote = min(100, len(pendientes_rec))
                    elif "250" in tam_lote_sel: limite_lote = min(250, len(pendientes_rec))
                    elif "500" in tam_lote_sel: limite_lote = min(500, len(pendientes_rec))
                    
                    lote_a_procesar = pendientes_rec[:limite_lote]
                    total_lote = len(lote_a_procesar)
                    
                    prog_sync = st.progress(0)
                    status_sync = st.empty()
                    
                    exitos, errores = 0, 0
                    for idx, item in enumerate(lote_a_procesar):
                        sku = item["SKU"]
                        p_id = item["_product_id"]
                        serpi_info = item["_serpi_item"]
                        tit = item["Título"]
                        
                        status_sync.text(f"[{idx+1}/{total_lote}] Sincronizando: {tit[:32]}... ({sku})")
                        
                        try:
                            # 1. Si difiere el stock, actualizar inventario con protección de existencias
                            stk_a_enviar = item["_erp_stock"]
                            if item["_diff_stock"]:
                                if stk_a_enviar == 0:
                                    stk_vivo = obtener_stock_puntual_serpi(sku, forzar_en_vivo=True)
                                    if stk_vivo > 0:
                                        stk_a_enviar = stk_vivo
                                actualizar_stock_shopify(p_id, stk_a_enviar)
                                
                            # 2. Actualizar precio, sku, taxable, canales y ficha
                            p_erp = float(item.get("_erp_price") or serpi_info.get("precio") or 0)
                            precio_a_enviar = p_erp if p_erp > 0 else None
                            fila_update = pd.Series({
                                "serpi": sku,
                                "descripcion": serpi_info.get("descripcion", tit),
                                "price": precio_a_enviar,
                                "idgrupocontable": serpi_info.get("idgrupocontable"),
                                "grupocontable": serpi_info.get("grupocontable"),
                                "autor": serpi_info.get("autor", ""),
                                "editorial": serpi_info.get("editorial", ""),
                                "presentacion": serpi_info.get("presentacion", ""),
                                "estado": serpi_info.get("estado", ""),
                                **(serpi_info.get("camposPersonalizados") or {})
                            })
                            actualizar_producto_con_esquema(p_id, fila_update)
                            
                            # 3. Registrar procesado
                            registrar_producto_procesado(sku)
                            actualizar_sku_en_snapshot(sku, stock=stk_a_enviar, precio=item["_erp_price"])
                            exitos += 1
                        except Exception as e:
                            errores += 1
                            
                        time.sleep(0.05)
                        prog_sync.progress((idx + 1) / total_lote)
                        
                    st.balloons()
                    st.success(f"🎉 Sincronización finalizada: **{exitos}** productos actualizados exitosamente en Shopify. ({errores} errores)")
                    st.rerun()

# =============================================================
# PESTAÑA 3: CARGA MANUAL VÍA EXCEL/CSV
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