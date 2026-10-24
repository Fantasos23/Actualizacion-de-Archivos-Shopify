from dotenv import load_dotenv
load_dotenv()
import os
import json
import urllib.request
import time

SHOP_URL = "libreriatroya-com.myshopify.com"
API_TOKEN = os.getenv("SHOPIFY_API_TOKEN")
API_VERSION = "2024-04"
GRAPHQL_URL = f"https://{SHOP_URL}/admin/api/{API_VERSION}/graphql.json"

# Load the base database we created to get the list of products
with open("base_datos_productos_shopify.json", "r", encoding="utf-8") as f:
    base_data = json.load(f)

products_to_backup = [p for p in base_data["productos"] if p["encontrado_shopify"] == "SÍ" and p["shopify_id"]]

print(f"Total productos a respaldar desde Shopify: {len(products_to_backup)}")

QUERY_FULL_PRODUCT = """
query getFullProduct($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    descriptionHtml
    status
    vendor
    productType
    tags
    seo {
      title
      description
    }
    collections(first: 10) {
      edges {
        node {
          id
          title
          handle
        }
      }
    }
    images(first: 20) {
      edges {
        node {
          id
          url
          altText
        }
      }
    }
    variants(first: 10) {
      edges {
        node {
          id
          title
          sku
          barcode
          price
          compareAtPrice
          taxable
          inventoryQuantity
          inventoryItem {
            id
            tracked
          }
        }
      }
    }
    metafields(first: 50) {
      edges {
        node {
          id
          namespace
          key
          value
          type
        }
      }
    }
  }
}
"""

def query_shopify(graphql_query, variables=None):
    payload = {"query": graphql_query}
    if variables:
        payload["variables"] = variables
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "X-Shopify-Access-Token": API_TOKEN,
            "Content-Type": "application/json"
        }
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

full_backups = []

for idx, p in enumerate(products_to_backup, 1):
    prod_id = p["shopify_id"]
    code = p["codigo_buscado"]
    title = p["shopify_titulo"]
    print(f"[{idx}/{len(products_to_backup)}] Respaldando '{title}' ({prod_id})...", end=" ")
    
    try:
        res = query_shopify(QUERY_FULL_PRODUCT, {"id": prod_id})
        prod_data = res.get("data", {}).get("product")
        if prod_data:
            # Attach source invoice info as well
            prod_data["_info_origen"] = {
                "archivo_origen": p["archivo_origen"],
                "item_num": p["item_num"],
                "codigo_buscado": code,
                "descripcion_archivo": p["descripcion_archivo"],
                "cantidad_archivo": p["cantidad_archivo"],
                "precio_unitario_archivo": p["precio_unitario_archivo"],
                "total_archivo": p["total_archivo"]
            }
            full_backups.append(prod_data)
            print("OK")
        else:
            print("ERROR: Producto no devuelto")
    except Exception as e:
        print(f"ERROR: {e}")
    time.sleep(0.05)

backup_file = "backup_completo_productos_shopify.json"
with open(backup_file, "w", encoding="utf-8") as f:
    json.dump({
        "fecha_backup": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_respaldados": len(full_backups),
        "productos": full_backups
    }, f, indent=2, ensure_ascii=False)

print("\n" + "="*50)
print(f"✅ RESPALDO COMPLETADO: {len(full_backups)} productos guardados en {backup_file}")
print("="*50)
