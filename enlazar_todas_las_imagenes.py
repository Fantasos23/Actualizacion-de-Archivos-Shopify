import os
import json
import csv
import time
import urllib.request
import urllib.parse
import re
from dotenv import load_dotenv

load_dotenv()
SHOP_URL = os.getenv("SHOPIFY_SHOP_URL", "libreriatroya-com.myshopify.com")
API_TOKEN = os.getenv("SHOPIFY_API_TOKEN")
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-04")
GRAPHQL_URL = f"https://{SHOP_URL}/admin/api/{API_VERSION}/graphql.json"
STORE_FRONTEND_URL = "https://libreriatroya.com"
HEADERS = {
    "X-Shopify-Access-Token": API_TOKEN,
    "Content-Type": "application/json"
}

def query_shopify(graphql_query, variables=None):
    payload = {"query": graphql_query}
    if variables:
        payload["variables"] = variables
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=HEADERS
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        cost = res.get("extensions", {}).get("cost", {})
        throttle = cost.get("throttleStatus", {})
        available = throttle.get("currentlyAvailable", 1000)
        restore_rate = throttle.get("restoreRate", 100)
        if available < 400:
            time.sleep(max((500 - available) / restore_rate, 0.5))
        return res

QUERY_FILES = """
query getFiles($first: Int!, $after: String) {
  files(first: $first, after: $after) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        createdAt
        ... on MediaImage {
          id
          image {
            url
            originalSrc
          }
        }
        ... on GenericFile {
          id
          url
        }
      }
    }
  }
}
"""

MUTATION_CREATE_MEDIA = """
mutation addMedia($productId: ID!, $media: [CreateMediaInput!]!) {
  productCreateMedia(productId: $productId, media: $media) {
    media {
      id
      status
    }
    mediaUserErrors {
      field
      message
    }
  }
}
"""

def clean_filename(url):
    if not url:
        return ""
    path = urllib.parse.urlparse(url).path
    filename = path.split("/")[-1]
    return filename.lower()

def main():
    print("=" * 60)
    print("🚀 INICIANDO VINCULACIÓN MASIVA DE IMÁGENES DESDE SHOPIFY FILES")
    print("=" * 60)

    # 1. Load backup to build filename-to-code mapping
    with open("backup_completo_productos_shopify.json", "r", encoding="utf-8") as f:
        backup_data = json.load(f)

    filename_to_code = {}
    for p in backup_data["productos"]:
        code = p.get("_info_origen", {}).get("codigo_buscado", "")
        # Also check variants for barcode
        if not code and p.get("variants", {}).get("edges"):
            code = p["variants"]["edges"][0]["node"].get("barcode")
        for edge in p["images"]["edges"]:
            fn = clean_filename(edge["node"]["url"])
            if fn and code:
                filename_to_code[fn] = code

    # 2. Load current recreated database (code -> product)
    with open("base_datos_productos_shopify.json", "r", encoding="utf-8") as f:
        db_data = json.load(f)

    code_to_product = {p["codigo_buscado"]: p for p in db_data["productos"]}
    
    print(f"📖 Mapeo de nombres de archivo respaldados: {len(filename_to_code)}")
    print(f"📦 Total productos en base de datos: {len(code_to_product)}")

    # 3. Retrieve all files from Shopify storage
    all_shopify_files = []
    has_next = True
    cursor = None
    page = 1

    print("\n--- PASO 1: ESCANEANDO EL ALMACENAMIENTO DE ARCHIVOS EN SHOPIFY ---")
    while has_next:
        print(f"  • Consultando página {page} de archivos...", end=" ")
        res = query_shopify(QUERY_FILES, {"first": 150, "after": cursor})
        files_data = res.get("data", {}).get("files", {})
        edges = files_data.get("edges", [])
        
        for e in edges:
            node = e["node"]
            url = None
            if "image" in node and node["image"]:
                url = node["image"].get("url") or node["image"].get("originalSrc")
            elif "url" in node:
                url = node.get("url")
            
            if url:
                fn = clean_filename(url)
                all_shopify_files.append({
                    "id": node["id"],
                    "filename": fn,
                    "url": url
                })

        page_info = files_data.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")
        print(f"Obtenidos {len(edges)} archivos (Total acumulado: {len(all_shopify_files)})")
        page += 1
        time.sleep(0.1)

    print(f"\n✅ Total de archivos escaneados en Shopify: {len(all_shopify_files)}")

    # 4. Group matching files by product code
    print("\n--- PASO 2: EMPAREJANDO ARCHIVOS CON PRODUCTOS ---")
    product_images_to_link = {code: [] for code in code_to_product.keys()}

    for f in all_shopify_files:
        fn = f["filename"]
        matched_code = None

        # Check 1: Exact filename in backup mapping
        if fn in filename_to_code:
            matched_code = filename_to_code[fn]
        else:
            # Check 2: Barcode / ISBN contained in filename (e.g. 9789974894181.jpg)
            for code in code_to_product.keys():
                if code and len(code) >= 6 and code in fn:
                    matched_code = code
                    break

        if matched_code and matched_code in product_images_to_link:
            # Avoid duplicate URLs
            existing_urls = [x["url"] for x in product_images_to_link[matched_code]]
            if f["url"] not in existing_urls:
                product_images_to_link[matched_code].append(f)

    # Sort each product's images so that the ISBN/cover image is first
    for code, imgs in product_images_to_link.items():
        if len(imgs) > 1:
            imgs.sort(key=lambda x: 0 if (code in x["filename"]) else 1)

    matched_products = sum(1 for c, imgs in product_images_to_link.items() if len(imgs) > 0)
    total_imgs_matched = sum(len(imgs) for imgs in product_images_to_link.values())
    print(f"✅ Se encontraron imágenes para {matched_products} de {len(code_to_product)} productos (Total fotos: {total_imgs_matched})")

    # 5. Link images to recreated products in Shopify
    print("\n--- PASO 3: VINCULANDO IMÁGENES A LOS PRODUCTOS EN SHOPIFY ---")
    linked_count = 0
    errors_count = 0

    for idx, (code, imgs) in enumerate(product_images_to_link.items(), 1):
        if not imgs:
            continue

        prod_info = code_to_product[code]
        prod_id = prod_info.get("shopify_id")
        title = prod_info.get("shopify_titulo")

        if not prod_id:
            continue

        print(f"[{idx}/{len(code_to_product)}] Vinculando {len(imgs)} imagen(es) a '{title}' ({code})...", end=" ")

        media_input = []
        for img in imgs:
            media_input.append({
                "originalSource": img["url"],
                "mediaContentType": "IMAGE",
                "alt": f"Portada {title}"
            })

        try:
            res_m = query_shopify(MUTATION_CREATE_MEDIA, {"productId": prod_id, "media": media_input})
            user_errors = res_m.get("data", {}).get("productCreateMedia", {}).get("mediaUserErrors", [])
            if not user_errors:
                linked_count += 1
                print("✅ VINCULADO")
                # update db object with live URLs
                prod_info["shopify_imagen_principal"] = imgs[0]["url"]
                prod_info["shopify_todas_imagenes"] = " | ".join([im["url"] for im in imgs])
                prod_info["shopify_cantidad_imagenes"] = len(imgs)
            else:
                errors_count += 1
                print(f"❌ Error: {user_errors}")
        except Exception as ex:
            errors_count += 1
            print(f"❌ Excepción: {ex}")

        time.sleep(0.1)

    print("\n" + "=" * 60)
    print(f"RESUMEN FINAL DE VINCULACIÓN:")
    print(f"  • Productos vinculados con éxito: {linked_count}")
    print(f"  • Errores: {errors_count}")
    print("=" * 60)

    # 6. Save updated CSV and JSON database
    headers = [
        "Archivo Origen", "Ítem #", "Código Buscado", "Descripción en Archivo / Factura",
        "Encontrado en Shopify", "Tipo de Coincidencia", "Título / Nombre en Shopify",
        "SKU en Shopify", "Código de Barras en Shopify", "Precio Shopify", "¿Tiene IVA?",
        "Enlace Página Web (URL)", "Enlace Imagen Principal", "Todas las Imágenes (URLs)",
        "Cantidad de Imágenes", "Metafield: Autor", "Metafield: Editorial", "Metafield: Categoría",
        "Metafield: Páginas", "Metafield: Presentación", "Metafield: Estado", "Metafield: Serpi",
        "Cantidad Facturada", "Precio Unitario Facturado", "Total Facturado", "Estado en Shopify",
        "Shopify Product ID", "Handle Shopify"
    ]

    output_csv = "base_datos_productos_shopify.csv"
    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in db_data["productos"]:
            writer.writerow([
                r.get("archivo_origen", ""), r.get("item_num", ""), r.get("codigo_buscado", ""),
                r.get("descripcion_archivo", ""), r.get("encontrado_shopify", ""), r.get("tipo_coincidencia", ""),
                r.get("shopify_titulo", ""), r.get("shopify_sku", ""), r.get("shopify_barcode", ""),
                r.get("shopify_precio", ""), r.get("shopify_tiene_iva", ""), r.get("shopify_url", ""),
                r.get("shopify_imagen_principal", ""), r.get("shopify_todas_imagenes", ""),
                r.get("shopify_cantidad_imagenes", 0), r.get("meta_autor", ""), r.get("meta_editorial", ""),
                r.get("meta_categoria", ""), r.get("meta_paginas", ""), r.get("meta_presentacion", ""),
                r.get("meta_estado", ""), r.get("meta_serpi", ""), r.get("cantidad_archivo", ""),
                r.get("precio_unitario_archivo", ""), r.get("total_archivo", ""), r.get("shopify_estado", ""),
                r.get("shopify_id", ""), r.get("shopify_handle", "")
            ])

    output_json = "base_datos_productos_shopify.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(db_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Archivo CSV consolidado actualizado en: {output_csv}")
    print(f"✅ Archivo JSON consolidado actualizado en: {output_json}")

if __name__ == "__main__":
    main()
