import os
import pickle
import os
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload

# Alcances: Acceso a Drive y envío de Gmail
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/gmail.send'
]

CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'
LOCAL_BASE_FOLDER = r'D:\Projects\Descarga-Facturas-ML\Facturas_Compras'
DRIVE_ROOT_FOLDER_NAME = 'Facturas_MercadoLibre'
DEFAULT_RECIPIENT = "alexis.martyniuk@gmail.com" # Actualizado por el usuario

def authenticate_google():
    """Autentica con Google y retorna las credenciales."""
    creds = None
    # El archivo token.pickle almacena los tokens de acceso y refresh del usuario.
    # Se crea automáticamente tras la primera autenticación exitosa.
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
            
    # Si no hay credenciales (o son inválidas)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(f"No se encontró {CREDENTIALS_FILE}. Por favor colócalo en la misma carpeta.")
                
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Guardar credenciales para la próxima
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    return creds

def get_drive_service():
    creds = authenticate_google()
    return build('drive', 'v3', credentials=creds)

def get_gmail_service():
    creds = authenticate_google()
    return build('gmail', 'v1', credentials=creds)

def send_email(subject, body, to=DEFAULT_RECIPIENT):
    """Envía un correo electrónico usando la Gmail API."""
    try:
        service = get_gmail_service()
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        
        # Codificar mensaje en base64
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        msg_body = {'raw': raw}
        
        service.users().messages().send(userId='me', body=msg_body).execute()
        print(f"Correo de notificación enviado a {to}.")
    except Exception as e:
        print(f"Error enviando correo: {e}")


def find_or_create_folder(service, folder_name, parent_id=None):
    """Busca una carpeta por nombre y parent_id; si no existe, la crea."""
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    
    if not items:
        # Crear
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
            
        folder = service.files().create(body=file_metadata, fields='id').execute()
        print(f"Creada carpeta Drive: {folder_name} ({folder.get('id')})")
        return folder.get('id')
    else:
        # Retornar existente
        return items[0].get('id')

def upload_recursive(service, local_path, parent_drive_id, stats):
    """Recorre local_path y replica la estructura en Drive bajo parent_drive_id."""
    for item in os.listdir(local_path):
        item_path = os.path.join(local_path, item)
        
        try:
            if os.path.isdir(item_path):
                # Es carpeta: buscar/crear en Drive y recursión
                folder_id = find_or_create_folder(service, item, parent_drive_id)
                upload_recursive(service, item_path, folder_id, stats)
                
            else:
                # Es archivo: verificar si existe y subir
                query = f"name='{item}' and '{parent_drive_id}' in parents and trashed=false"
                results = service.files().list(q=query, fields='files(id)').execute()
                
                if not results.get('files'):
                    print(f"Subiendo archivo: {item}...")
                    media = MediaFileUpload(item_path, resumable=True)
                    file_metadata = {'name': item, 'parents': [parent_drive_id]}
                    
                    service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                    stats['uploaded'] += 1
                else:
                    # print(f"Saltando archivo existente: {item}")
                    stats['skipped'] += 1
        except Exception as e:
            print(f"Error procesando {item}: {e}")
            stats['errors'] += 1

def main():
    stats = {'uploaded': 0, 'skipped': 0, 'errors': 0}
    
    if not os.path.exists(LOCAL_BASE_FOLDER):
        print(f"Carpeta local no encontrada: {LOCAL_BASE_FOLDER}")
        return stats

    try:
        service = get_drive_service()
        print("Autenticación Google exitosa.")
        
        # Carpeta raíz en Drive
        root_id = find_or_create_folder(service, DRIVE_ROOT_FOLDER_NAME)
        
        print(f"Iniciando sincronización desde {LOCAL_BASE_FOLDER}...")
        upload_recursive(service, LOCAL_BASE_FOLDER, root_id, stats)
        
        print("Sincronización completada.")
        
    except Exception as e:
        print(f"Error general Drive: {e}")
        stats['errors'] += 1
        
    return stats

if __name__ == '__main__':
    final_stats = main()
    print(f"Resumen Drive: {final_stats}")
