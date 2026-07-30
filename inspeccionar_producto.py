import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# 1. Cargar credenciales del .env
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

# 2. Reemplaza este handle por uno que exista en tu tienda
HANDLE_A_PROBAR = "mision-lectora-4-la-aventura-comienza" 

# 3. Query para traer la estructura EXACTA del producto y sus metafields
query_inspeccion = """
query inspeccionarProducto($query: String!) {
  products(first: 1, query: $query) {
    edges {
      node {
        id
        handle
        title
        productType
        vendor
        tags
        descriptionHtml
        
        # Variantes (Precio, Impuestos, SKU)
        variants(first: 5) {
          edges {
            node {
              id
              title
              sku
              price
              taxable
            }
          }
        }
        
        # Metafields definidos en el producto
        metafields(first: 20) {
          edges {
            node {
              id
              namespace
              key
              type
              value
            }
          }
        }
      }
    }
  }
}
"""

def ejecutar_inspeccion():
    print("=" * 60)
    print(f"🔍 INSPECCIONANDO ESTRUCTURA API PARA EL HANDLE: {HANDLE_A_PROBAR}")
    print("=" * 60)
    
    response = requests.post(
        GRAPHQL_URL, 
        json={"query": query_inspeccion, "variables": {"query": f"handle:{HANDLE_A_PROBAR}"}}, 
        headers=HEADERS
    )
    
    if response.status_code == 200:
        data = response.json()
        products = data.get("data", {}).get("products", {}).get("edges", [])
        
        if not products:
            print(f"❌ No se encontró ningún producto con el handle '{HANDLE_A_PROBAR}'.")
            return
            
        prod = products[0]["node"]
        
        print("\n📦 1. CAMPOS ESTÁNDAR DEL PRODUCTO (API):")
        print(f"  • ID API:           {prod.get('id')}")
        print(f"  • Handle:           {prod.get('handle')}")
        print(f"  • Title:            {prod.get('title')}")
        print(f"  • Vendor:           {prod.get('vendor')}")
        print(f"  • Product Type:     {prod.get('productType')}")
        print(f"  • Tags:             {prod.get('tags')}")

        print("\n🏷️ 2. VARIANTE (IMPUESTOS Y PRECIOS EN API):")
        variantes = prod.get("variants", {}).get("edges", [])
        for v in variantes:
            v_node = v["node"]
            print(f"  • Variant ID:      {v_node.get('id')}")
            print(f"  • SKU:             {v_node.get('sku')}")
            print(f"  • Price:           {v_node.get('price')}")
            print(f"  • Taxable (IVA):   {v_node.get('taxable')}  <-- (Este es el campo exacto de impuestos)")

        print("\n📂 3. METAFIELDS CONFIGURADOS EN ESTE PRODUCTO:")
        metafields = prod.get("metafields", {}).get("edges", [])
        if not metafields:
            print("  ⚠️ El producto no tiene metafields asignados o poblados actualmente.")
        else:
            for m in metafields:
                m_node = m["node"]
                ns = m_node.get('namespace')
                key = m_node.get('key')
                m_type = m_node.get('type')
                val = m_node.get('value')
                print(f"  • [{ns}.{key}] | Tipo API: '{m_type}' | Valor actual: '{val}'")
                print(f"    👉 Para actualizar usas -> namespace: '{ns}', key: '{key}', type: '{m_type}'")

        print("\n" + "=" * 60)
        print("📄 JSON COMPLETO DEVUELTO POR LA API:")
        print("=" * 60)
        print(json.dumps(prod, indent=2, ensure_ascii=False))

    else:
        print(f"❌ Error HTTP {response.status_code}: {response.text}")

if __name__ == "__main__":
    ejecutar_inspeccion()