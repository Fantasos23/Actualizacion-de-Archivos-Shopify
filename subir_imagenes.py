import os
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
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

def buscar_product_id_por_serpi(serpi_code):
    """
    Busca el ID único de un producto en Shopify filtrando por el Metafield custom.serpi
    """
    query = """
    query buscarPorSerpi($query: String!) {
      products(first: 1, query: $query) {
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
    search_query = f"metafields.custom.serpi:'{serpi_code}'"
    res = ejecutar_graphql(query, {"query": search_query})
    products = res.get("data", {}).get("products", {}).get("edges", [])
    
    if products:
        return products[0]["node"]["id"], products[0]["node"]["title"]
    return None, None

def cargar_imagen_a_shopify(product_id, file_bytes, file_name):
    """
    Sube la imagen directamente a Shopify enviándola en formato Base64.
    ¡Esto omite el CDN de GCS/S3 y evita errores de firma por completo!
    """
    try:
        # Extraer el ID numérico de Shopify del formato GraphQL (gid://shopify/Product/123456)
        product_numeric_id = product_id.split("/")[-1]
        
        # Convertir la imagen a Base64
        base64_image = base64.b64encode(file_bytes).decode('utf-8')
        
        # Endpoint de imágenes del producto
        url_endpoint = f"{REST_URL}/products/{product_numeric_id}/images.json"
        
        payload = {
            "image": {
                "attachment": base64_image,
                "filename": file_name,
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