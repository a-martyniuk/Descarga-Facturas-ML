import os
import requests
import json
import time
from datetime import datetime

# CONFIGURACIÓN
APP_ID = "8297816339344135"
CLIENT_SECRET = "oOPHDGv6uzRbtXGunlY8heigzOeejXv8"
REDIRECT_URI = "https://www.google.com/"
ACCESS_TOKEN = "APP_USR-7178598796886263-010923-5772699097d67e9c31817ac9aeb6f586-51746963" 
REFRESH_TOKEN = "" # Si tienes un refresh token, ponlo aquí

BASE_URL = "https://api.mercadolibre.com"
DOWNLOAD_FOLDER = "d:/Google Antigravity/Facturas_Compras"
TOKEN_FILE = "d:/Google Antigravity/Descarga-Facturas-ML/meli_tokens.json"

# Variables globales para los tokens activos
CURRENT_ACCESS_TOKEN = ACCESS_TOKEN
CURRENT_REFRESH_TOKEN = REFRESH_TOKEN

def load_tokens():
    """Carga tokens desde el archivo JSON si existe"""
    global CURRENT_ACCESS_TOKEN, CURRENT_REFRESH_TOKEN
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                data = json.load(f)
                CURRENT_ACCESS_TOKEN = data.get('access_token', ACCESS_TOKEN)
                CURRENT_REFRESH_TOKEN = data.get('refresh_token', REFRESH_TOKEN)
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
            CURRENT_REFRESH_TOKEN = res_data.get('refresh_token')
            save_tokens(CURRENT_ACCESS_TOKEN, CURRENT_REFRESH_TOKEN)
            print("Token renovado exitosamente.")
            return True
        else:
            print(f"Error renovando token: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Excepción al renovar token: {e}")
        return False

def get_headers():
    return {
        "Authorization": f"Bearer {CURRENT_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

def meli_request(method, url, **kwargs):
    """Wrapper para requests de MeLi que maneja refresh automático si el token expira (401)"""
    global CURRENT_ACCESS_TOKEN
    
    if 'headers' not in kwargs:
        kwargs['headers'] = get_headers()
    
    response = requests.request(method, url, **kwargs)
    
    if response.status_code == 401:
        print("Token detectado como expirado durante la ejecución. Refrescando...")
        if refresh_access_token():
            # Reintentar con el nuevo token
            kwargs['headers'] = get_headers()
            return requests.request(method, url, **kwargs)
        else:
            print("No se pudo refrescar el token periódicamente.")
    
    return response

def get_my_user_id():
    """Obtiene el ID del usuario actual"""
    url = f"{BASE_URL}/users/me"
    response = meli_request("GET", url, timeout=10)
    if response.status_code == 200:
        return response.json().get('id')
    else:
        print(f"Error obteniendo usuario: {response.status_code} - {response.text}")
        return None

def get_orders_page(user_id, offset=0, limit=50):
    """Obtiene una página de órdenes de compra"""
    url = f"{BASE_URL}/orders/search"
    params = {
        "buyer": user_id,
        "limit": limit,
        "offset": offset,
        "sort": "date_desc" 
    }
    print(f"Buscando compras (Offset: {offset})...")
    response = meli_request("GET", url, params=params, timeout=10)
    
    if response.status_code == 200:
        return response.json().get('results', [])
    else:
        print(f"Error buscando órdenes: {response.status_code} - {response.text}")
        return []

def get_fiscal_documents_info(pack_id):
    """Busca información de documentos fiscales de un paquete"""
    if not pack_id:
        return []
        
    url = f"{BASE_URL}/packs/{pack_id}/fiscal_documents"
    try:
        response = meli_request("GET", url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # La API de packs devuelve un dict con la clave 'fiscal_documents'
            if isinstance(data, dict):
                return data.get('fiscal_documents', [])
            return data if isinstance(data, list) else []
        elif response.status_code == 404:
            return []
        else:
            return []
    except Exception:
        return []


def download_document(pack_id, file_id, filename, relative_path="Otros"):
    """
    Descarga el documento en la ruta relativa especificada.
    """
    # Construir ruta completa: DownloadFolder / Año / Mes / Tipo
    final_folder = os.path.join(DOWNLOAD_FOLDER, relative_path)
    if not os.path.exists(final_folder):
        os.makedirs(final_folder, exist_ok=True)
    
    filepath = os.path.join(final_folder, filename)
    
    if os.path.exists(filepath):
        return 'SKIPPED'

    url = f"{BASE_URL}/packs/{pack_id}/fiscal_documents/{file_id}"
    
    try:
        response = meli_request("GET", url, stream=True, timeout=15)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"    [OK] Guardado: {filename}")
            return 'DOWNLOADED'
        else:
            print(f"    [ERROR] Falló descarga {filename}: {response.status_code}")
            return 'ERROR'
    except Exception as e:
        print(f"    [ERROR] Excepción descarga {filename}: {e}")
        return 'ERROR'

def process_orders():
    load_tokens() # Intentar cargar tokens guardados
    
    user_id = get_my_user_id()
    
    # Si falla el user_id inicial (token expirado), intentar refrescar una vez
    if not user_id:
        if refresh_access_token():
            user_id = get_my_user_id()
            
    if not user_id:
        print("Error crítico: No se pudo autenticar con Mercado Libre. Verifica tus credenciales.")
        return

    offset = 0
    limit = 50
    processed_targets = set()
    newly_downloaded = [] # Lista para el reporte por email
    
    stats_meli = {
        'processed_orders': 0,
        'docs_found': 0,
        'downloaded': 0,
        'skipped': 0,
        'errors': 0
    }
    
    print("Iniciando escaneo de historial de compras (Organización por Año/Mes)...")
    
    while True:
        orders = get_orders_page(user_id, offset, limit)
        if not orders:
            break
            
        print(f"Procesando lote (Offset: {offset})...")
        stats_meli['processed_orders'] += len(orders)
        
        for order in orders:
            order_id = order.get('id')
            pack_id = order.get('pack_id')
            target_id = pack_id if pack_id else order_id
            
            # Evitar reprocesar el mismo pack (varias órdenes en un solo envío)
            if target_id in processed_targets:
                continue
            processed_targets.add(target_id)
            
            # Fecha formato: 2023-10-25T10:00:00.000-04:00
            date_str = order.get('date_created', '')
            try:
                dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                year = str(dt.year)
                month = f"{dt.month:02d}"
            except Exception:
                year = "SinFecha"
                month = "General"

            fiscal_docs = get_fiscal_documents_info(target_id)
            
            if fiscal_docs:
                print(f"  > Pack/Orden {target_id}: {len(fiscal_docs)} docs encontrados.")
                stats_meli['docs_found'] += len(fiscal_docs)
                for doc in fiscal_docs:
                    doc_id = doc.get('id')
                    filename = doc.get('filename', f"factura_{order_id}.pdf")
                    # relative_path ahora es solo Año / Mes
                    relative_path = os.path.join(year, month)
                    
                    status = download_document(target_id, doc_id, filename, relative_path)
                    
                    if status == 'DOWNLOADED':
                        stats_meli['downloaded'] += 1
                        newly_downloaded.append(f"{year}/{month}: {filename}")
                    elif status == 'SKIPPED':
                        stats_meli['skipped'] += 1
                    else:
                        stats_meli['errors'] += 1
            
        offset += limit
        time.sleep(0.3)


    print("\n--- Iniciando sincronización con Google Drive ---")
    stats_drive = {}
    try:
        import drive_uploader
        stats_drive = drive_uploader.main()
        
        # ENVIAR EMAIL SI HAY NUEVAS FACTURAS
        if stats_meli['downloaded'] > 0:
            print("Preparando notificación por email...")
            subject = f"Nuevas Facturas Mercado Libre ({stats_meli['downloaded']})"
            body = "Se han detectado y descargado nuevas facturas:\n\n"
            body += "\n".join(newly_downloaded)
            body += "\n\nLos archivos ya están organizados localmente y sincronizados en Google Drive."
            drive_uploader.send_email(subject, body)
            
    except ImportError:
        print("No se encontró el módulo 'drive_uploader.py'.")
    except Exception as e:
        print(f"Error durante la sincronización/notificación: {e}")

    # REPORTE FINAL
    print("\n" + "="*40)
    print("       REPORTE DE EJECUCIÓN FINAL       ")
    print("="*40)
    print("MERCADOLIBRE (Descarga Local):")
    print(f"  - Órdenes procesadas:   {stats_meli['processed_orders']}")
    print(f"  - Documentos detectados:{stats_meli['docs_found']}")
    print(f"  - Descargados nuevos:   {stats_meli['downloaded']}")
    print(f"  - Omitidos (Existían):  {stats_meli['skipped']}")
    print(f"  - Errores de descarga:   {stats_meli['errors']}")
    print("-" * 40)
    if stats_drive:
        print("GOOGLE DRIVE (Nube):")
        print(f"  - Archivos subidos:     {stats_drive.get('uploaded', 0)}")
        print(f"  - Omitidos (Existían):  {stats_drive.get('skipped', 0)}")
        print(f"  - Errores de subida:    {stats_drive.get('errors', 0)}")
    else:
        print("GOOGLE DRIVE: No ejecutado o sin datos.")
    print("="*40 + "\n")


if __name__ == "__main__":
    process_orders()

