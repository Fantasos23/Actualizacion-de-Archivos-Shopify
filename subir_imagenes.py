import os
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

base_dir = Path(__file__).parent
load_dotenv(dotenv_path=base_dir / '.env')
load_dotenv(dotenv_path=base_dir / 'Shopify.env')

try:
    import streamlit as st
except ImportError:
    st = None

base_dir = Path(__file__).parent
load_dotenv(dotenv_path=base_dir / '.env')
load_dotenv(dotenv_path=base_dir / 'Shopify.env')

def get_secret(key, default=""):
    try:
        if st and hasattr(st, "secrets") and st.secrets:
            if key in st.secrets:
                return str(st.secrets[key]).strip().strip('"').strip("'")
            for k, v in st.secrets.items():
                if isinstance(k, str) and k.lower() == key.lower() and not isinstance(v, dict):
                    return str(v).strip().strip('"').strip("'")
            for sec_k, sec_v in st.secrets.items():
                if isinstance(sec_v, dict):
                    for sub_k, sub_v in sec_v.items():
                        if isinstance(sub_k, str) and (sub_k.lower() == key.lower() or f"{sec_k}_{sub_k}".lower() == key.lower()):
                            return str(sub_v).strip().strip('"').strip("'")
    except Exception:
        pass
    val = os.getenv(key, default)
    return str(val).strip().strip('"').strip("'") if val is not None else str(default).strip()

def obtener_shopify_config():
    raw_url = get_secret("SHOPIFY_SHOP_URL", "").replace("https://", "").replace("http://", "").strip("/")
    token = get_secret("SHOPIFY_API_TOKEN", "")
    version = get_secret("SHOPIFY_API_VERSION", "2024-04")
    gql_url = f"https://{raw_url}/admin/api/{version}/graphql.json" if raw_url else ""
    rest_url = f"https://{raw_url}/admin/api/{version}" if raw_url else ""
    headers = {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json"
    }
    return raw_url, token, version, gql_url, rest_url, headers

def ejecutar_graphql(query, variables=None):
    raw_url, token, version, gql_url, rest_url, headers = obtener_shopify_config()
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    res = requests.post(gql_url, json=payload, headers=headers, timeout=45)
    if res.status_code == 200:
        return res.json()
    raise Exception(f"HTTP {res.status_code}: {res.text}")

def buscar_producto_por_nombre_y_serpi(nombre_libro, codigo_serpi):
    """
    Busca productos en Shopify filtrando por Nombre y valida de forma estricta 
    que el metafield custom.serpi o el título coincida con la búsqueda.
    """
    query = """
    query buscarProducto($query: String!) {
      products(first: 10, query: $query) {
        edges {
          node {
            id
            title
            handle
            metafield(namespace: "custom", key: "serpi") {
              value
            }
          }
        }
      }
    }
    """
    # Construir búsqueda combinada
    terminos = []
    if nombre_libro.strip():
        terminos.append(f"title:*'{nombre_libro.strip()}'*")
    if codigo_serpi.strip():
        terminos.append(f"metafields.custom.serpi:'{codigo_serpi.strip()}'")
        
    search_query = " AND ".join(terminos) if terminos else "status:active"
    
    res = ejecutar_graphql(query, {"query": search_query})
    products_edges = res.get("data", {}).get("products", {}).get("edges", [])
    
    resultados = []
    serpi_clean = codigo_serpi.strip()

    for edge in products_edges:
        node = edge["node"]
        meta_val = node.get("metafield", {}).get("value") if node.get("metafield") else "Sin código SERPI"
        
        # Guardar resultados candidatos con su información explicita
        resultados.append({
            "id": node["id"],
            "title": node["title"],
            "serpi": meta_val,
            "handle": node["handle"]
        })
        
    return resultados

def cargar_imagen_a_shopify(product_id, file_bytes, file_name):
    """
    Sube la imagen directamente al producto en Shopify enviando Base64 (Método probado sin errores CDN).
    """
    try:
        raw_url, token, version, gql_url, rest_url, headers = obtener_shopify_config()
        product_numeric_id = product_id.split("/")[-1]
        base64_image = base64.b64encode(file_bytes).decode('utf-8')
        
        url_endpoint = f"{rest_url}/products/{product_numeric_id}/images.json"
        
        payload = {
            "image": {
                "attachment": base64_image,
                "filename": file_name,
                "position": 1,
                "alt": f"Portada SERPI {file_name}"
            }
        }
        
        res = requests.post(url_endpoint, json=payload, headers=headers, timeout=30)
        
        if res.status_code in [200, 201]:
            return True, "Exitosa"
        else:
            return False, f"HTTP {res.status_code}: {res.text[:150]}"
            
    except Exception as e:
        return False, str(e)