import os
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
    Busca el ID de producto en Shopify filtrando por el Metafield custom.serpi
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
    Sube el archivo al CDN de Shopify usando FILE_UPLOAD para evitar errores SignatureDoesNotMatch
    """
    file_size = str(len(file_bytes))
    ext = file_name.split('.')[-1].lower()
    
    mime = "image/png" if ext == "png" else "image/webp" if ext == "webp" else "image/jpeg"
    
    # 1. Solicitar la URL de subida para recursos tipo FILE_UPLOAD
    mutation_stage = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
      stagedUploadsCreate(input: $input) {
        stagedTargets {
          url
          resourceUrl
          parameters {
            name
            value
          }
        }
        userErrors { field message }
      }
    }
    """
    
    payload_stage = {
        "input": [{
            "filename": file_name,
            "mimeType": mime,
            "resource": "FILE_UPLOAD",
            "fileSize": file_size
        }]
    }
    
    res_stage = ejecutar_graphql(mutation_stage, payload_stage)
    targets = res_stage.get("data", {}).get("stagedUploadsCreate", {}).get("stagedTargets", [])
    
    if not targets:
        return False, "Error al solicitar espacio de carga en Shopify"
        
    target = targets[0]
    upload_url = target["url"]
    resource_url = target["resourceUrl"]
    
    # 2. Reconstruir los parámetros respetando la firma estricta
    params_list = [(p["name"], p["value"]) for p in target["parameters"]]
    
    # Subir usando multipart/form-data puro con tuple para no alterar la firma
    res_upload = requests.post(
        upload_url,
        data=params_list,
        files={'file': (file_name, file_bytes, mime)}
    )
    
    if res_upload.status_code not in [200, 201]:
        return False, f"Error en CDN HTTP {res_upload.status_code}"

    # 3. Asociar la imagen cargada al Producto
    mutation_media = """
    mutation productCreateMedia($media: [CreateMediaInput!]!, $productId: ID!) {
      productCreateMedia(media: $media, productId: $productId) {
        media { id }
        userErrors { field message }
      }
    }
    """
    
    payload_media = {
        "productId": product_id,
        "media": [{
            "originalSource": resource_url,
            "mediaContentType": "IMAGE",
            "alt": f"Portada SERPI {file_name}"
        }]
    }
    
    res_media = ejecutar_graphql(mutation_media, payload_media)
    errors = res_media.get("data", {}).get("productCreateMedia", {}).get("userErrors", [])
    
    if not errors:
        return True, "Exitosa"
    return False, ", ".join([e["message"] for e in errors])