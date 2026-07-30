import os
import requests
from dotenv import load_dotenv

# Cargar variables
load_dotenv()
load_dotenv(dotenv_path="Shopify.env")

RAW_SHOP_URL = os.getenv("SHOPIFY_SHOP_URL", "").replace("https://", "").replace("http://", "").strip("/")
API_TOKEN = os.getenv("SHOPIFY_API_TOKEN", "").strip()
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-04").strip()

print("="*50)
print("🔍 INICIANDO DIAGNÓSTICO DE CONEXIÓN A SHOPIFY")
print(f"• Tienda: {RAW_SHOP_URL}")
print(f"• Versión API: {API_VERSION}")
print(f"• Token cargado: {API_TOKEN[:8]}... (Longitud: {len(API_TOKEN)})")
print("="*50)

# Endpoint de GraphQL
url = f"https://{RAW_SHOP_URL}/admin/api/{API_VERSION}/graphql.json"

# Header de autorización
headers = {
    "X-Shopify-Access-Token": API_TOKEN,
    "Content-Type": "application/json"
}

# Consulta ultra simple para validar la tienda
query = """
{
  shop {
    name
    email
    myshopifyDomain
  }
}
"""

try:
    response = requests.post(url, json={"query": query}, headers=headers)
    print(f"\n📡 Código de respuesta HTTP: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if "data" in data and data["data"].get("shop"):
            shop_info = data["data"]["shop"]
            print("\n✅ ¡CONEXIÓN EXITOSA CON SHOPIFY!")
            print(f"• Nombre de la Tienda: {shop_info.get('name')}")
            print(f"• Email de la Tienda: {shop_info.get('email')}")
            print(f"• Dominio Interno: {shop_info.get('myshopifyDomain')}")
        else:
            print("\n❌ La petición respondió 200 pero devolvió errores de GraphQL:")
            print(data)
    else:
        print(f"\n❌ Error de Autenticación (HTTP {response.status_code}):")
        print(response.text)

except Exception as e:
        print(f"\n❌ Error grave de red/conexión: {e}")