import os
import requests
import json
import time
from datetime import datetime

# CONFIGURACION
CONFIG_FILE = r"D:\Projects\Descarga-Facturas-ML\config_meli.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    print("WARNING: config_meli.json no encontrado, por favor creelo.")
    return {}

config = load_config()
APP_ID = config.get("app_id", "")
CLIENT_SECRET = config.get("client_secret", "")
REDIRECT_URI = config.get("redirect_uri", "https://www.google.com/")
# Variables globales para los tokens activos
CURRENT_ACCESS_TOKEN = None
CURRENT_REFRESH_TOKEN = None

BASE_URL = "https://api.mercadolibre.com"
DOWNLOAD_FOLDER = r"D:\Projects\Descarga-Facturas-ML\Facturas_Compras"
TOKEN_FILE = r"D:\Projects\Descarga-Facturas-ML\meli_tokens.json"
LOG_FILE = r"D:\Projects\Descarga-Facturas-ML\execution.log"

def log_execution(status, message=""):
    """Guarda un registro de la ejecucion en el archivo de log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} - {status} - {message}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Error escribiendo en log: {e}")

def has_executed_today():
    """Verifica si ya hubo una ejecucion exitosa hoy"""
    if not os.path.exists(LOG_FILE):
        return False
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in reversed(lines):
                if today_str in line and "EXITO" in line:
                    return True
    except Exception as e:
        print(f"Error leyendo log: {e}")
    return False

def load_tokens():
    """Carga tokens desde el archivo JSON si existe"""
    global CURRENT_ACCESS_TOKEN, CURRENT_REFRESH_TOKEN
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                data = json.load(f)
                CURRENT_ACCESS_TOKEN = data.get('access_token')
                CURRENT_REFRESH_TOKEN = data.get('refresh_token')
        except:
            pass

def save_tokens(access_token, refresh_token):
    """Guarda los nuevos tokens en el archivo JSON"""
    with open(TOKEN_FILE, 'w') as f:
        json.dump({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'updated_at': datetime.now().isoformat()
        }, f)

def refresh_access_token():
    """Usa el refresh_token para obtener un nuevo access_token"""
    global CURRENT_ACCESS_TOKEN, CURRENT_REFRESH_TOKEN
    print("Tentando renovar token de Mercado Libre...")
    
    if not CURRENT_REFRESH_TOKEN:
        print("Error: No hay REFRESH_TOKEN disponible para renovar.")
        return False

    url = f"{BASE_URL}/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": APP_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": CURRENT_REFRESH_TOKEN
    }
    
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            res_data = response.json()
            CURRENT_ACCESS_TOKEN = res_data.get('access_token')
            CURRENT_REFRESH_TOKEN = res_data.get('refresh_token', CURRENT_REFRESH_TOKEN)
            save_tokens(CURRENT_ACCESS_TOKEN, CURRENT_REFRESH_TOKEN)
            print("Token renovado exitosamente.")
            return True
        else:
            print(f"Error renovando token: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Excepcion al renovar token: {e}")
        return False

def get_headers():
    return {
        "Authorization": f"Bearer {CURRENT_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

def meli_request(method, url, **kwargs):
    """Envia una peticion y maneja automaticamente el refresco de token si expira"""
    if 'headers' not in kwargs:
        kwargs['headers'] = get_headers()
    
    response = requests.request(method, url, **kwargs)
    
    if response.status_code == 401:
        print("Token detectado como expirado durante la ejecucion. Refrescando...")
        if refresh_access_token():
            kwargs['headers'] = get_headers()
            return requests.request(method, url, **kwargs)
        else:
            print("No se pudo refrescar el token periodicamente.")
    
    return response

def get_my_user_id():
    url = f"{BASE_URL}/users/me"
    response = meli_request("GET", url, timeout=10)
    if response.status_code == 200:
        return response.json().get('id')
    return None

def get_orders_page(user_id, offset=0, limit=50):
    url = f"{BASE_URL}/orders/search"
    params = {"buyer": user_id, "limit": limit, "offset": offset, "sort": "date_desc"}
    print(f"Buscando compras (Offset: {offset})...")
    response = meli_request("GET", url, params=params, timeout=10)
    return response.json().get('results', []) if response.status_code == 200 else []

def get_fiscal_documents_info(pack_id):
    if not pack_id: return []
    url = f"{BASE_URL}/packs/{pack_id}/fiscal_documents"
    try:
        response = meli_request("GET", url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('fiscal_documents', []) if isinstance(data, dict) else data
        return []
    except: return []

def download_document(pack_id, file_id, filename, relative_path="Otros"):
    final_folder = os.path.join(DOWNLOAD_FOLDER, relative_path)
    if not os.path.exists(final_folder): os.makedirs(final_folder, exist_ok=True)
    filepath = os.path.join(final_folder, filename)
    if os.path.exists(filepath): return 'SKIPPED'
    url = f"{BASE_URL}/packs/{pack_id}/fiscal_documents/{file_id}"
    try:
        response = meli_request("GET", url, stream=True, timeout=15)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
            print(f"    [OK] Guardado: {filename}")
            return 'DOWNLOADED'
        return 'ERROR'
    except: return 'ERROR'

def process_orders():
    log_execution("INICIO")
    load_tokens()
    user_id = get_my_user_id()
    if not user_id:
        if refresh_access_token(): user_id = get_my_user_id()
    if not user_id:
        log_execution("ERROR", "No se pudo autenticar")
        return

    offset, limit = 0, 50
    processed_targets, newly_downloaded = set(), []
    stats_meli = {'processed_orders': 0, 'docs_found': 0, 'downloaded': 0, 'skipped': 0, 'errors': 0}
    
    while True:
        orders = get_orders_page(user_id, offset, limit)
        if not orders: break
        stats_meli['processed_orders'] += len(orders)
        for order in orders:
            target_id = order.get('pack_id') or order.get('id')
            if target_id in processed_targets: continue
            processed_targets.add(target_id)
            date_str = order.get('date_created', '')
            try:
                dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                year, month = str(dt.year), f"{dt.month:02d}"
            except: year, month = "SinFecha", "General"
            fiscal_docs = get_fiscal_documents_info(target_id)
            if fiscal_docs:
                stats_meli['docs_found'] += len(fiscal_docs)
                for doc in fiscal_docs:
                    filename = doc.get('filename', f"factura_{order.get('id')}.pdf")
                    status = download_document(target_id, doc.get('id'), filename, os.path.join(year, month))
                    if status == 'DOWNLOADED':
                        stats_meli['downloaded'] += 1
                        newly_downloaded.append(f"{year}/{month}: {filename}")
                    elif status == 'SKIPPED': stats_meli['skipped'] += 1
                    else: stats_meli['errors'] += 1
        offset += limit
        time.sleep(0.3)

    stats_drive = {}
    try:
        import drive_uploader
        stats_drive = drive_uploader.main()
        if newly_downloaded:
            subject = f"Nuevas Facturas Mercado Libre ({len(newly_downloaded)})"
            body = "Se han detectado y descargado nuevas facturas:\n\n" + "\n".join(newly_downloaded)
            drive_uploader.send_email(subject, body)
    except Exception as e:
        print(f"Error sync: {e}")

    log_execution("EXITO", f"{stats_meli['downloaded']} descargas, {stats_drive.get('uploaded', 0)} subidas")

if __name__ == "__main__":
    if has_executed_today():
        print("Ya se ejecuto exitosamente hoy. Saltando...")
    else:
        process_orders()
