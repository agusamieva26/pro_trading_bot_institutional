# bot/google_drive_uploader.py
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from .util import logger

# Si modificas estos SCOPES, borra el archivo token.json
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Construir rutas absolutas a la raíz del proyecto para los archivos de credenciales
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = os.path.join(PROJECT_ROOT, 'credentials.json')
TOKEN_FILE = os.path.join(PROJECT_ROOT, 'token.json')

def get_drive_service():
    """Crea y retorna un servicio de Google Drive autenticado."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"❌ Error refrescando token de Google: {e}")
                creds = None # Forzar re-autenticación
        
        if not creds:
            if not os.path.exists(CREDENTIALS_FILE):
                logger.error(f"❌ {CREDENTIALS_FILE} no encontrado. Por favor, sigue las instrucciones para crearlo.")
                return None
            
            # MODIFICADO: No intentar autorización interactiva en el bot principal
            logger.error(f"❌ {TOKEN_FILE} no encontrado o inválido.")
            logger.error("   Ejecuta 'python authorize_gdrive.py' para generar el token de autorización.")
            return None
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
    return build('drive', 'v3', credentials=creds)

def find_or_create_folder(service, folder_name: str):
    """Encuentra una carpeta por nombre o la crea si no existe."""
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = response.get('files', [])
    
    if files:
        return files[0].get('id')
    else:
        file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        folder = service.files().create(body=file_metadata, fields='id').execute()
        logger.info(f"📁 Carpeta de Google Drive '{folder_name}' creada.")
        return folder.get('id')

def upload_report_to_drive(file_path: str, folder_name: str = "TradingBot_Reports"):
    """Sube un archivo de reporte a una carpeta específica en Google Drive."""
    try:
        service = get_drive_service()
        if not service:
            logger.error("❌ No se pudo obtener el servicio de Google Drive. Subida cancelada.")
            return

        folder_id = find_or_create_folder(service, folder_name)
        
        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [folder_id]
        }
        media = MediaFileUpload(file_path, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        logger.info(f"☁️ Reporte subido a Google Drive con éxito. File ID: {file.get('id')}")

    except Exception as e:
        logger.error(f"❌ Error al subir reporte a Google Drive: {e}")
        logger.warning("   Asegúrate de que 'credentials.json' está configurado correctamente.")