from dotenv import load_dotenv
load_dotenv()
import os
import json
import csv
import time
import urllib.request
import re

SHOP_URL = "libreriatroya-com.myshopify.com"
API_TOKEN = os.getenv("SHOPIFY_API_TOKEN")
API_VERSION = "2024-04"
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
        # Check throttle
        cost = res.get("extensions", {}).get("cost", {})
        throttle = cost.get("throttleStatus", {})
        available = throttle.get("currentlyAvailable", 1000)
        restore_rate = throttle.get("restoreRate", 100)
        if available < 400:
            sleep_time = (500 - available) / restore_rate
            time.sleep(max(sleep_time, 0.5))
        return res

# GraphQL Mutations
DELETE_MUTATION = """
mutation delProd($input: ProductDeleteInput!) {
  productDelete(input: $input) {
    deletedProductId
    userErrors {
      field
      message
    }
  }
}
"""

CREATE_MUTATION = """
mutation createProd($input: ProductInput!, $media: [CreateMediaInput!]) {
  productCreate(input: $input, media: $media) {
    product {
      id
      title
      handle
      media(first: 10) {
        edges {
          node {
            id
            status
          }
        }
      }
      variants(first: 1) {
        edges {
          node {
            id
          }
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

BULK_VARIANT_MUTATION = """
mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    productVariants {
      id
      price
      barcode
      taxable
      sku
    }
    userErrors {
      field
      message
    }
  }
}
"""

def main():
    print("=" * 60)
    print("🚀 INICIANDO PROCESO DE BORRADO Y RECREACIÓN EN SHOPIFY")
    print("=" * 60)

    # 1. Load backup data
    with open("backup_completo_productos_shopify.json", "r", encoding="utf-8") as f:
        backup_data = json.load(f)

    # 2. Load base_datos_productos_shopify.json
    with open("base_datos_productos_shopify.json", "r", encoding="utf-8") as f:
        db_data = json.load(f)

    prods_to_delete = backup_data["productos"]
    print(f"📦 Total productos respaldados a eliminar de Shopify: {len(prods_to_delete)}")

    # ========================================================
    # PASO 1: ELIMINACIÓN DE PRODUCTOS EXISTENTES
    # ========================================================
    print("\n--- PASO 1: ELIMINANDO PRODUCTOS EXISTENTES EN SHOPIFY ---")
    deleted_count = 0
    delete_errors = []

    for idx, p in enumerate(prods_to_delete, 1):
        prod_id = p["id"]
        title = p["title"]
        print(f"[{idx}/{len(prods_to_delete)}] Eliminando '{title}' ({prod_id})...", end=" ")
        try:
            res = query_shopify(DELETE_MUTATION, {"input": {"id": prod_id}})
            errors = res.get("data", {}).get("productDelete", {}).get("userErrors", [])
            if not errors:
                deleted_count += 1
                print("✅ ELIMINADO")
            else:
                print(f"❌ Error: {errors}")
                delete_errors.append((prod_id, title, errors))
        except Exception as ex:
            print(f"❌ Excepción: {ex}")
            delete_errors.append((prod_id, title, str(ex)))
        time.sleep(0.1)

    print(f"\nResumen eliminación: {deleted_count} eliminados con éxito. Errores: {len(delete_errors)}")

    # Wait a few seconds to let Shopify settle indices
    print("Esperando 5 segundos antes de recrear...")
    time.sleep(5)

    # ========================================================
    # PASO 2: RECREACIÓN DE PRODUCTOS DESDE LA BASE DE DATOS
    # ========================================================
    print("\n--- PASO 2: RECREANDO PRODUCTOS EN SHOPIFY ---")

    # Map backup products by barcode / sku / title
    backup_by_code = {}
    for bp in prods_to_delete:
        bc = None
        if bp.get("variants", {}).get("edges"):
            bc = bp["variants"]["edges"][0]["node"].get("barcode")
        if bc:
            backup_by_code[bc] = bp
        # Also store by code in _info_origen
        if bp.get("_info_origen", {}).get("codigo_buscado"):
            backup_by_code[bp["_info_origen"]["codigo_buscado"]] = bp

    all_db_products = db_data["productos"]
    print(f"Total productos a crear en base de datos: {len(all_db_products)}")

    recreated_products = []
    created_count = 0
    create_errors = []

    for idx, p in enumerate(all_db_products, 1):
        code = p["codigo_buscado"]
        orig_desc = p["descripcion_archivo"]
        bp = backup_by_code.get(code)

        print(f"[{idx}/{len(all_db_products)}] Creando '{orig_desc}' (Código: {code})...", end=" ")

        # Determine fields to use
        title = p.get("shopify_titulo") or orig_desc
        handle = p.get("shopify_handle") or re.sub(r"[^\w\s-]", "", title.lower()).strip().replace(" ", "-")
        desc_html = bp.get("descriptionHtml") if bp else f"<p>{title}</p>"
        vendor = bp.get("vendor") if bp and bp.get("vendor") else (p.get("meta_editorial") or "Librería Troya")
        product_type = bp.get("productType") if bp and bp.get("productType") else (p.get("meta_categoria") or "Libros")
        tags = bp.get("tags") if bp and bp.get("tags") else [p.get("meta_categoria")] if p.get("meta_categoria") else []

        # Build clean metafields
        metafields_input = []
        # Standard custom metafields
        if p.get("meta_autor"):
            metafields_input.append({"namespace": "custom", "key": "autor", "value": p["meta_autor"], "type": "single_line_text_field"})
        if p.get("meta_editorial"):
            metafields_input.append({"namespace": "custom", "key": "editorial", "value": p["meta_editorial"], "type": "single_line_text_field"})
        if p.get("meta_categoria"):
            metafields_input.append({"namespace": "custom", "key": "categoria", "value": p["meta_categoria"], "type": "single_line_text_field"})
        if p.get("meta_paginas"):
            metafields_input.append({"namespace": "custom", "key": "paginas", "value": str(p["meta_paginas"]), "type": "single_line_text_field"})
        if p.get("meta_presentacion"):
            metafields_input.append({"namespace": "custom", "key": "presentacion", "value": p["meta_presentacion"], "type": "single_line_text_field"})
        if p.get("meta_estado"):
            metafields_input.append({"namespace": "custom", "key": "estado", "value": p["meta_estado"], "type": "single_line_text_field"})
        
        # serpi metafield
        serpi_val = p.get("meta_serpi") or code
        metafields_input.append({"namespace": "custom", "key": "serpi", "value": str(serpi_val), "type": "single_line_text_field"})

        # If backup had SEO tags, preserve them
        if bp and bp.get("seo"):
            seo = bp["seo"]
            if seo.get("title"):
                metafields_input.append({"namespace": "global", "key": "title_tag", "value": seo["title"], "type": "single_line_text_field"})
            if seo.get("description"):
                metafields_input.append({"namespace": "global", "key": "description_tag", "value": seo["description"], "type": "single_line_text_field"})

        # Build media list
        media_input = []
        all_imgs_str = p.get("shopify_todas_imagenes") or p.get("shopify_imagen_principal") or ""
        if all_imgs_str:
            img_list = [u.strip() for u in all_imgs_str.split("|") if u.strip().startswith("http")]
            for img_url in img_list:
                media_input.append({
                    "originalSource": img_url,
                    "mediaContentType": "IMAGE"
                })

        # Price and barcode
        price = p.get("shopify_precio")
        if not price or float(price or 0) == 0:
            price_str = p.get("precio_unitario_archivo", "0").replace("$", "").replace(",", "").strip()
            price = f"{float(price_str):.2f}" if price_str else "39000.00"

        prod_input = {
            "title": title,
            "handle": handle,
            "descriptionHtml": desc_html,
            "status": "ACTIVE",
            "vendor": vendor,
            "productType": product_type,
            "tags": tags,
            "metafields": metafields_input
        }

        # Step 2.1: Create product
        try:
            res_c = query_shopify(CREATE_MUTATION, {"input": prod_input, "media": media_input if media_input else None})
            prod_res = res_c.get("data", {}).get("productCreate", {})
            user_errors = prod_res.get("userErrors", [])
            new_prod = prod_res.get("product")

            if user_errors or not new_prod:
                print(f"❌ Error al crear producto: {user_errors}")
                create_errors.append((code, title, user_errors))
                recreated_products.append(p)
                continue

            new_prod_id = new_prod["id"]
            new_handle = new_prod["handle"]
            new_var_id = new_prod["variants"]["edges"][0]["node"]["id"]

            # Step 2.2: Update default variant with price, barcode, sku, taxable=False
            v_input = {
                "productId": new_prod_id,
                "variants": [{
                    "id": new_var_id,
                    "price": str(price),
                    "barcode": str(code),
                    "taxable": False,
                    "inventoryItem": {
                        "sku": str(code),
                        "tracked": True
                    }
                }]
            }

            res_v = query_shopify(BULK_VARIANT_MUTATION, v_input)
            v_errors = res_v.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])
            if v_errors:
                print(f"⚠️ Alerta en variante: {v_errors}", end=" ")

            created_count += 1
            print(f"✅ CREADO -> {new_prod_id} (Handle: {new_handle}, Precio: {price}, IVA: NO)")

            # Update product object for database
            updated_p = dict(p)
            updated_p["encontrado_shopify"] = "SÍ"
            updated_p["tipo_coincidencia"] = "Recreado exitosamente en Shopify"
            updated_p["shopify_id"] = new_prod_id
            updated_p["shopify_titulo"] = title
            updated_p["shopify_handle"] = new_handle
            updated_p["shopify_estado"] = "ACTIVE"
            updated_p["shopify_url"] = f"{STORE_FRONTEND_URL}/products/{new_handle}"
            updated_p["shopify_sku"] = str(code)
            updated_p["shopify_barcode"] = str(code)
            updated_p["shopify_precio"] = str(price)
            updated_p["shopify_tiene_iva"] = "NO"

            recreated_products.append(updated_p)

        except Exception as ex:
            print(f"❌ Excepción creando: {ex}")
            create_errors.append((code, title, str(ex)))
            recreated_products.append(p)

        time.sleep(0.15)

    print("\n" + "=" * 60)
    print(f"RESUMEN FINAL DE RECREACIÓN:")
    print(f"  • Total procesados: {len(all_db_products)}")
    print(f"  • Creados con éxito: {created_count}")
    print(f"  • Errores: {len(create_errors)}")
    print("=" * 60)

    # ========================================================
    # PASO 3: GUARDAR BASE DE DATOS ACTUALIZADA (CSV Y JSON)
    # ========================================================
    headers = [
        "Archivo Origen",
        "Ítem #",
        "Código Buscado",
        "Descripción en Archivo / Factura",
        "Encontrado en Shopify",
        "Tipo de Coincidencia",
        "Título / Nombre en Shopify",
        "SKU en Shopify",
        "Código de Barras en Shopify",
        "Precio Shopify",
        "¿Tiene IVA?",
        "Enlace Página Web (URL)",
        "Enlace Imagen Principal",
        "Todas las Imágenes (URLs)",
        "Cantidad de Imágenes",
        "Metafield: Autor",
        "Metafield: Editorial",
        "Metafield: Categoría",
        "Metafield: Páginas",
        "Metafield: Presentación",
        "Metafield: Estado",
        "Metafield: Serpi",
        "Cantidad Facturada",
        "Precio Unitario Facturado",
        "Total Facturado",
        "Estado en Shopify",
        "Shopify Product ID",
        "Handle Shopify"
    ]

    output_csv = "base_datos_productos_shopify.csv"
    with open(output_csv, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in recreated_products:
            writer.writerow([
                r.get("archivo_origen", ""),
                r.get("item_num", ""),
                r.get("codigo_buscado", ""),
                r.get("descripcion_archivo", ""),
                r.get("encontrado_shopify", ""),
                r.get("tipo_coincidencia", ""),
                r.get("shopify_titulo", ""),
                r.get("shopify_sku", ""),
                r.get("shopify_barcode", ""),
                r.get("shopify_precio", ""),
                r.get("shopify_tiene_iva", ""),
                r.get("shopify_url", ""),
                r.get("shopify_imagen_principal", ""),
                r.get("shopify_todas_imagenes", ""),
                r.get("shopify_cantidad_imagenes", 0),
                r.get("meta_autor", ""),
                r.get("meta_editorial", ""),
                r.get("meta_categoria", ""),
                r.get("meta_paginas", ""),
                r.get("meta_presentacion", ""),
                r.get("meta_estado", ""),
                r.get("meta_serpi", ""),
                r.get("cantidad_archivo", ""),
                r.get("precio_unitario_archivo", ""),
                r.get("total_archivo", ""),
                r.get("shopify_estado", ""),
                r.get("shopify_id", ""),
                r.get("shopify_handle", "")
            ])

    output_json = "base_datos_productos_shopify.json"
    with open(output_json, mode="w", encoding="utf-8") as f:
        json.dump({
            "total_items": len(recreated_products),
            "creados_exitosamente": created_count,
            "errores": len(create_errors),
            "productos": recreated_products
        }, f, indent=2, ensure_ascii=False)

    print(f"✅ Archivo CSV actualizado en: {output_csv}")
    print(f"✅ Archivo JSON actualizado en: {output_json}")

if __name__ == "__main__":
    main()
