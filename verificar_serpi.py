import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# 1. Cargar variables desde .env
base_dir = Path(__file__).parent
load_dotenv(dotenv_path=base_dir / '.env')

SERPI_BASE_URL = os.getenv("SERPI_BASE_URL", "https://apis.serpi.com.co").rstrip("/")
SERPI_SECRETKEY = os.getenv("SERPI_SECRETKEY", "").strip()
SERPI_TOKEN = os.getenv("SERPI_TOKEN", "").strip()

# Encabezados HTTP requeridos de forma simultánea según la especificación OpenAPI de Serpi
HEADERS = {
    "secretkey": SERPI_SECRETKEY,
    "Authorization": f"Bearer {SERPI_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def consultar_serpi(nombre_servicio, endpoint, params=None):
    url = f"{SERPI_BASE_URL}{endpoint}"
    print(f"\n==================================================")
    print(f"📡 Consultando: {nombre_servicio}")
    print(f"URL: {url}")
    print(f"Params: {params}")
    print(f"==================================================")
    
    try:
        # Aumentamos el timeout a 60 segundos para permitir consultas pesadas
        response = requests.get(url, headers=HEADERS, params=params, timeout=60)
        print(f"Estado HTTP: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ ¡CONEXIÓN EXITOSA!")
            data = response.json()
            if isinstance(data, list):
                print(f"Registros obtenidos: {len(data)}")
                if len(data) > 0:
                    print("Muestra del primer registro:")
                    print(json.dumps(data[0], indent=2, ensure_ascii=False)[:400] + "...\n")
            elif isinstance(data, dict):
                print("Resultado obtenido:")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:400] + "...\n")
            return True
        elif response.status_code == 204:
            print("⚠️ 204 No Content: Petición correcta pero no hay registros en ese rango.")
            return True
        elif response.status_code == 401:
            print("❌ 401 Unauthorized: El Token JWT falta, está desincronizado o expiró.")
        elif response.status_code == 403:
            print("❌ 403 Forbidden: La secretkey enviada no corresponde al NIT/Empresa del token.")
        else:
            print(f"❌ Error HTTP {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"💥 Excepción de red: {e}")
        
    return False

if __name__ == "__main__":
    from datetime import date

    print("🚀 Verificando Autenticación Core de SERPI Apis...")
    
    if not SERPI_SECRETKEY or not SERPI_TOKEN:
        print("❌ Error: Verifica que SERPI_SECRETKEY y SERPI_TOKEN estén configurados en el archivo .env")
        exit()

    # Fecha de corte de hoy en formato YYYY-MM-DD
    hoy = date.today().strftime("%Y-%m-%d")

    # 1. Probar catálogo de artículos/productos
    consultar_serpi("Catálogo de Artículos", "/api/v1/Articulo", params={"limite": 5, "pagina": 1})

    # 2. Probar inventarios sin costo (Enviando fechaCorte obligatoria)
    consultar_serpi("Saldos de Inventario", "/api/v1/SaldoInventarioSinCosto", params={"fechaCorte": hoy, "limite": 5, "pagina": 1})

    # 3. Probar listas de precios
    consultar_serpi("Listas de Precios", "/api/v1/ListaPrecios", params={"limite": 5, "pagina": 1})