import os
import json
import requests
from pathlib import Path
from datetime import date
from dotenv import load_dotenv

# 1. Cargar variables de entorno
base_dir = Path(__file__).parent
load_dotenv(dotenv_path=base_dir / '.env')

SERPI_BASE_URL = os.getenv("SERPI_BASE_URL", "https://apis.serpi.com.co").rstrip("/")
HEADERS = {
    "secretkey": os.getenv("SERPI_SECRETKEY", "").strip(),
    "Authorization": f"Bearer {os.getenv('SERPI_TOKEN', '').strip()}",
    "Accept": "application/json"
}

# Diccionario base con reglas de mapeo conocidas hacia Shopify
MAPEOS_SUGERIDOS = {
    "codigo": "SKU / metafield: custom.serpi",
    "barras": "barcode",
    "descripcion": "title",
    "descripcionalterna": "descriptionHtml",
    "idgrupocontable": "productType",
    "idlinea": "vendor",
    "idcategoria": "tags",
    "peso": "weight",
    "costo": "cost_per_item",
    "activo": "status",
    "saldo": "inventory_quantity",
    "precio": "price",
    "precioAnterior": "compare_at_price",
    "codigoBodega": "location_id"
}

def obtener_muestra_api(endpoint, params=None, timeout=30):
    url = f"{SERPI_BASE_URL}{endpoint}"
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
        if res.status_code == 200:
            data = res.json().get("result", [])
            if data and len(data) > 0:
                return data[0]
        else:
            print(f"⚠️ Error {res.status_code} al consultar {endpoint}: {res.text[:100]}")
    except Exception as e:
        print(f"💥 Excepción al consultar {endpoint}: {e}")
    return None

def generar_o_actualizar_esquema():
    print("==================================================")
    print("🔄 Obteniendo campos en vivo y actualizando serpi_schema.json...")
    print("==================================================")

    # Objeto base para construir/actualizar el JSON
    esquema_final = {
        "api_articulos": {
            "endpoint": "/api/v1/Articulo",
            "metodo": "GET",
            "campo_clave": "codigo",
            "campos": {}
        },
        "api_inventario": {
            "endpoint": "/api/v1/SaldoInventarioSinCosto",
            "metodo": "GET",
            "campo_clave": "codigo",
            "campos": {}
        },
        "api_precios": {
            "endpoint": "/api/v1/ListaPrecioDetalle",
            "metodo": "GET",
            "campo_clave": "codigo",
            "campos": {}
        }
    }

    # 1. Muestra API Artículos
    print("📡 Consultando /api/v1/Articulo...")
    sample_art = obtener_muestra_api("/api/v1/Articulo", params={"limite": 1, "pagina": 1})
    if sample_art:
        for k, v in sample_art.items():
            esquema_final["api_articulos"]["campos"][k] = {
                "tipo": type(v).__name__ if v is not None else "desconocido",
                "ejemplo": v,
                "mapeo_shopify": MAPEOS_SUGERIDOS.get(k, "Sin mapear")
            }
        print(f"  ✅ {len(sample_art.keys())} campos detectados.")

    # 2. Muestra API Inventario (Saldos)
    hoy = date.today().strftime("%Y-%m-%d")
    print("\n📡 Consultando /api/v1/SaldoInventarioSinCosto...")
    sample_inv = obtener_muestra_api("/api/v1/SaldoInventarioSinCosto", params={"fechaCorte": hoy, "limite": 1, "pagina": 1}, timeout=60)
    if sample_inv:
        for k, v in sample_inv.items():
            esquema_final["api_inventario"]["campos"][k] = {
                "tipo": type(v).__name__ if v is not None else "desconocido",
                "ejemplo": v,
                "mapeo_shopify": MAPEOS_SUGERIDOS.get(k, "Sin mapear")
            }
        print(f"  ✅ {len(sample_inv.keys())} campos detectados.")

    # 3. Muestra API Precios
    print("\n📡 Consultando /api/v1/ListaPrecioDetalle...")
    sample_prc = obtener_muestra_api("/api/v1/ListaPrecioDetalle", params={"limite": 1, "pagina": 1})
    if sample_prc:
        for k, v in sample_prc.items():
            esquema_final["api_precios"]["campos"][k] = {
                "tipo": type(v).__name__ if v is not None else "desconocido",
                "ejemplo": v,
                "mapeo_shopify": MAPEOS_SUGERIDOS.get(k, "Sin mapear")
            }
        print(f"  ✅ {len(sample_prc.keys())} campos detectados.")

    # Guardar o sobreescribir el archivo serpi_schema.json
    schema_path = base_dir / "serpi_schema.json"
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(esquema_final, f, indent=2, ensure_ascii=False)

    print("\n==================================================")
    print(f"🎉 ARCHIVO ACTUALIZADO ÉXITOSAMENTE: {schema_path}")
    print("==================================================")

if __name__ == "__main__":
    generar_o_actualizar_esquema()