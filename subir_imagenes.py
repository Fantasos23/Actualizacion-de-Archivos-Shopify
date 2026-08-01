import os
import json
import requests
import urllib.request
import urllib.parse
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
    Sube la imagen al CDN respetando de forma estricta el multipart de S3/GCS
    """
    file_size = str(len(file_bytes))
    ext = file_name.split('.')[-1].lower()
    
    mime = "image/jpeg"
    if ext == "png":
        mime = "image/png"
    elif ext == "webp":
        mime = "image/webp"

    # 1. Solicitar la URL de carga (Staged Upload)
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
            "resource": "PRODUCT_IMAGE",
            "fileSize": file_size
        }]
    }
    
    res_stage = ejecutar_graphql(mutation_stage, payload_stage)
    targets = res_stage.get("data", {}).get("stagedUploadsCreate", {}).get("stagedTargets", [])
    
    if not targets:
        return False, "Shopify no devolvió URL de carga."
        
    target = targets[0]
    upload_url = target["url"]
    resource_url = target["resourceUrl"]
    
    # 2. Construir multipart/form-data nativo para evitar corrupción de firma
    boundary = "----WebKitFormBoundaryShopifyPythonSync"
    body = bytearray()

    # Agregar cada parámetro entregado por Shopify
    for param in target["parameters"]:
        body.extend(f"--{boundary}\r\n".encode('utf-8'))
        body.extend(f'Content-Disposition: form-data; name="{param["name"]}"\r\n\r\n'.encode('utf-8'))
        body.extend(f'{param["value"]}\r\n'.encode('utf-8'))

    # Agregar el archivo físico 'file' como último elemento
    body.extend(f"--{boundary}\r\n".encode('utf-8'))
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'.encode('utf-8'))
    body.extend(f'Content-Type: {mime}\r\n\r\n'.encode('utf-8'))
    body.extend(file_bytes)
    body.extend(f"\r\n--{boundary}--\r\n".encode('utf-8'))

    req = urllib.request.Request(
        upload_url,
        data=bytes(body),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            if response.status not in [200, 201]:
                return False, f"Error CDN HTTP {response.status}"
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode('utf-8', errors='ignore')
        return False, f"Error CDN HTTP {e.code}: {err_msg[:120]}"

    # 3. Vincular la imagen al Producto
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