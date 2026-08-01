import os
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

base_dir = Path(__file__).parent
load_dotenv(dotenv_path=base_dir / '.env')
load_dotenv(dotenv_path=base_dir / 'Shopify.env')

RAW_SHOP_URL = os.getenv("SHOPIFY_SHOP_URL", "").replace("https://", "").replace("http://", "").strip("/")
API_TOKEN = os.getenv("SHOPIFY_API_TOKEN", "").strip()
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-04").strip()

GRAPHQL_URL = f"https://{RAW_SHOP_URL}/admin/api/{API_VERSION}/graphql.json"
REST_URL = f"https://{RAW_SHOP_URL}/admin/api/{API_VERSION}"

HEADERS = {
    "X-Shopify-Access-Token": API_TOKEN,
    "Content-Type": "application/json"
}

def ejecutar_graphql(query, variables=None):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    res = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS)
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
        product_numeric_id = product_id.split("/")[-1]
        base64_image = base64.b64encode(file_bytes).decode('utf-8')
        
        url_endpoint = f"{REST_URL}/products/{product_numeric_id}/images.json"
        
        payload = {
            "image": {
                "attachment": base64_image,
                "filename": file_name,
                "position": 1,
                "alt": f"Portada SERPI {file_name}"
            }
        }
        
        res = requests.post(url_endpoint, json=payload, headers=HEADERS)
        
        if res.status_code in [200, 201]:
            return True, "Exitosa"
        else:
            return False, f"HTTP {res.status_code}: {res.text[:150]}"
            
    except Exception as e:
        return False, str(e)