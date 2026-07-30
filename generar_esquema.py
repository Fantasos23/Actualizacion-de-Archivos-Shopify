import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables
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

# Consulta para obtener las definiciones de Metafields
query_definitions = """
query {
  metafieldDefinitions(first: 100, ownerType: PRODUCT) {
    edges {
      node {
        name
        namespace
        key
        type {
          name
        }
      }
    }
  }
}
"""

def generar_esquema_completo():
    print("🔄 Generando esquema completo (Atributos Estándar + Metafields)...")
    
    # 1. Definición de Atributos Estándar de Shopify y mapeo con columnas de exportación
    esquema = {
        "campos_estandar": {
            "descriptionHtml": {
                "nombre": "Descripción HTML",
                "tipo_dato": "string",
                "nivel": "product",
                "posibles_columnas_excel": ["Body (HTML)", "Body HTML", "Descripción", "Descripcion", "Body"]
            },
            "vendor": {
                "nombre": "Proveedor / Marca",
                "tipo_dato": "string",
                "nivel": "product",
                "posibles_columnas_excel": ["Vendor", "Proveedor", "Marca"]
            },
            "productType": {
                "nombre": "Tipo de Producto",
                "tipo_dato": "string",
                "nivel": "product",
                "posibles_columnas_excel": ["Type", "Tipo", "Product Type"]
            },
            "tags": {
                "nombre": "Etiquetas",
                "tipo_dato": "list_string",
                "nivel": "product",
                "posibles_columnas_excel": ["Tags", "Etiquetas"]
            },
            "price": {
                "nombre": "Precio de Venta",
                "tipo_dato": "money",
                "nivel": "variant",
                "posibles_columnas_excel": ["Variant Price", "Price", "Precio"]
            },
            "sku": {
                "nombre": "SKU",
                "tipo_dato": "string",
                "nivel": "variant",
                "posibles_columnas_excel": ["Variant SKU", "SKU", "Codigo SKU"]
            },
            "taxable": {
                "nombre": "Cobra Impuestos (IVA)",
                "tipo_dato": "boolean",
                "nivel": "variant",
                "posibles_columnas_excel": ["Variant Taxable", "Taxable", "Impuestos", "Impuesto", "Aplica Impuesto"]
            },
            "inventoryQuantity": {
                "nombre": "Cantidad en Inventario",
                "tipo_dato": "integer",
                "nivel": "inventory",
                "posibles_columnas_excel": ["Variant Inventory Qty", "Inventory Qty", "Inventario", "Cantidad", "Stock"]
            }
        },
        "metafields": {}
    }

    # 2. Obtener Metafields dinámicamente desde Shopify
    try:
        response = requests.post(GRAPHQL_URL, json={"query": query_definitions}, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            definitions = data.get("data", {}).get("metafieldDefinitions", {}).get("edges", [])
            
            for item in definitions:
                node = item["node"]
                key = node["key"]
                esquema["metafields"][key] = {
                    "name": node["name"],
                    "namespace": node["namespace"],
                    "key": key,
                    "type": node["type"]["name"],
                    "posibles_columnas_excel": [
                        f"{node['name']} (product.metafields.{node['namespace']}.{key})",
                        node["name"],
                        key,
                        f"{node['namespace']}.{key}"
                    ]
                }
            print(f"✅ Se agregaron {len(esquema['metafields'])} Metafields detectados desde la API.")
        else:
            print(f"⚠️ No se pudieron obtener los metafields dinámicos: HTTP {response.status_code}")
    except Exception as e:
        print(f"⚠️ Error al conectar con la API de Metafields: {e}")

    # 3. Guardar archivo JSON
    ruta_json = base_dir / "shopify_schema.json"
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(esquema, f, indent=4, ensure_ascii=False)

    print(f"🎉 ¡Esquema completo guardado exitosamente en: {ruta_json}!")

if __name__ == "__main__":
    generar_esquema_completo()