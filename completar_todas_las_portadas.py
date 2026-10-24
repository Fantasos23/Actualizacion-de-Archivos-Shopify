import os
import json
import csv
import time
import base64
import urllib.request
import urllib.parse
import re
from dotenv import load_dotenv

load_dotenv()
SHOP_URL = os.getenv("SHOPIFY_SHOP_URL", "libreriatroya-com.myshopify.com")
API_TOKEN = os.getenv("SHOPIFY_API_TOKEN")
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-04")
GRAPHQL_URL = f"https://{SHOP_URL}/admin/api/{API_VERSION}/graphql.json"
REST_URL = f"https://{SHOP_URL}/admin/api/{API_VERSION}"
STORE_FRONTEND_URL = "https://libreriatroya.com"

HEADERS_GQL = {
    "X-Shopify-Access-Token": API_TOKEN,
    "Content-Type": "application/json"
}

HEADERS_REST = {
    "X-Shopify-Access-Token": API_TOKEN,
    "Content-Type": "application/json"
}

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def query_shopify_gql(query, variables=None):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=HEADERS_GQL
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def upload_image_base64_to_shopify(product_id, img_bytes, filename, alt_text=""):
    numeric_id = product_id.split("/")[-1]
    url_endpoint = f"{REST_URL}/products/{numeric_id}/images.json"
    b64_str = base64.b64encode(img_bytes).decode("utf-8")
    payload = {
        "image": {
            "attachment": b64_str,
            "filename": filename,
            "position": 1,
            "alt": alt_text or f"Portada {filename}"
        }
    }
    req = urllib.request.Request(
        url_endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=HEADERS_REST
    )
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status in [200, 201]:
                res = json.loads(resp.read().decode("utf-8"))
                return True, res["image"]["src"]
    except Exception as e:
        return False, str(e)
    return False, "Error desconocido"

def find_cover_image(isbn, title=""):
    # 1. Buscalibre Search by ISBN
    try:
        bl_url = f"https://www.buscalibre.com.co/libros/search?q={isbn}"
        req = urllib.request.Request(bl_url, headers=BROWSER_HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            # Look for product image in cdn
            imgs = re.findall(r"https://images\.cdn\d+\.buscalibre\.com/[^\s\"\']+\.jpg", html)
            if imgs:
                # get original or high quality if available
                img_url = imgs[0].replace("fit-in/180x180/", "fit-in/360x360/")
                req_img = urllib.request.Request(img_url, headers=BROWSER_HEADERS)
                with urllib.request.urlopen(req_img, timeout=8) as r_img:
                    return r_img.read(), f"Buscalibre ({img_url})"
    except Exception:
        pass

    # 2. Google Books by ISBN
    try:
        gb_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
        req = urllib.request.Request(gb_url, headers=BROWSER_HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            gb_data = json.loads(resp.read().decode("utf-8"))
            items = gb_data.get("items", [])
            if items:
                img_links = items[0].get("volumeInfo", {}).get("imageLinks", {})
                thumb = img_links.get("thumbnail") or img_links.get("smallThumbnail")
                if thumb:
                    thumb = thumb.replace("http://", "https://")
                    req_img = urllib.request.Request(thumb, headers=BROWSER_HEADERS)
                    with urllib.request.urlopen(req_img, timeout=8) as r_img:
                        return r_img.read(), f"Google Books ({thumb})"
    except Exception:
        pass

    # 3. OpenLibrary
    try:
        ol_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
        req = urllib.request.Request(ol_url, headers=BROWSER_HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status == 200:
                img_bytes = resp.read()
                if len(img_bytes) > 2000:
                    return img_bytes, f"OpenLibrary ({ol_url})"
    except Exception:
        pass

    # 4. Buscalibre Search by Title (fallback)
    if title:
        try:
            clean_t = urllib.parse.quote(title.split(".")[0].strip())
            bl_url = f"https://www.buscalibre.com.co/libros/search?q={clean_t}"
            req = urllib.request.Request(bl_url, headers=BROWSER_HEADERS)
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                imgs = re.findall(r"https://images\.cdn\d+\.buscalibre\.com/[^\s\"\']+\.jpg", html)
                if imgs:
                    img_url = imgs[0].replace("fit-in/180x180/", "fit-in/360x360/")
                    req_img = urllib.request.Request(img_url, headers=BROWSER_HEADERS)
                    with urllib.request.urlopen(req_img, timeout=8) as r_img:
                        return r_img.read(), f"Buscalibre por título ({img_url})"
        except Exception:
            pass

    return None, None

def main():
    print("=" * 60)
    print("🚀 INICIANDO BÚSQUEDA Y ASIGNACIÓN AUTOMÁTICA DE PORTADAS")
    print("=" * 60)

    with open("base_datos_productos_shopify.json", "r", encoding="utf-8") as f:
        db = json.load(f)

    products = db["productos"]
    print(f"Total productos en base de datos: {len(products)}")

    # Check current status of each product in Shopify
    QUERY_CHECK = """
    query checkProd($id: ID!) {
      product(id: $id) {
        id
        title
        featuredImage { url }
        images(first: 10) {
          edges {
            node { url }
          }
        }
      }
    }
    """

    updated_count = 0
    already_had_img = 0
    not_found_covers = []

    for idx, p in enumerate(products, 1):
        prod_id = p.get("shopify_id")
        code = p.get("codigo_buscado")
        title = p.get("shopify_titulo") or p.get("descripcion_archivo")

        if not prod_id:
            continue

        print(f"[{idx}/{len(products)}] {title[:35]} ({code})...", end=" ")

        # Check if product already has image in Shopify
        res_chk = query_shopify_gql(QUERY_CHECK, {"id": prod_id})
        prod_data = res_chk.get("data", {}).get("product")
        
        featured = prod_data.get("featuredImage") if prod_data else None
        if featured and featured.get("url"):
            already_had_img += 1
            print(f"✅ Ya tiene portada en Shopify")
            # Update db info
            p["shopify_imagen_principal"] = featured["url"]
            p["shopify_cantidad_imagenes"] = len(prod_data.get("images", {}).get("edges", []))
            continue

        # Look for cover image
        img_bytes, source_info = find_cover_image(code, title)
        if img_bytes:
            filename = f"{code}.jpg"
            ok, new_cdn_url = upload_image_base64_to_shopify(prod_id, img_bytes, filename, f"Portada {title}")
            if ok:
                updated_count += 1
                p["shopify_imagen_principal"] = new_cdn_url
                p["shopify_todas_imagenes"] = new_cdn_url
                p["shopify_cantidad_imagenes"] = 1
                print(f"🎉 ASIGNADA con éxito desde {source_info[:30]}")
            else:
                print(f"❌ Error al subir a Shopify: {new_cdn_url}")
        else:
            not_found_covers.append((code, title))
            print("⚠️ Portada no encontrada online")

        time.sleep(0.3)

    print("\n" + "=" * 60)
    print(f"RESUMEN FINAL DE PORTADAS:")
    print(f"  • Productos que ya tenían imagen: {already_had_img}")
    print(f"  • Productos a los que se les asignó portada nueva: {updated_count}")
    print(f"  • Total productos con imagen ahora: {already_had_img + updated_count} de {len(products)}")
    print(f"  • Sin portada encontrada: {len(not_found_covers)}")
    print("=" * 60)

    # Save updated CSV and JSON
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

    with open("base_datos_productos_shopify.csv", "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in products:
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

    with open("base_datos_productos_shopify.json", "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

    print("✅ Base de datos actualizada con éxito en CSV y JSON.")

if __name__ == "__main__":
    main()
