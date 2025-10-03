<<<<<<< HEAD
#!/usr/bin/env python3
"""
🔑 SCRIPT DE AUTORIZACIÓN PARA GOOGLE DRIVE

Ejecuta este script UNA SOLA VEZ de forma interactiva para generar el archivo `token.json`.
Este archivo es necesario para que el bot pueda subir reportes a tu Google Drive.

Pasos:
1. Asegúrate de tener tu archivo `credentials.json` en la misma carpeta.
2. Ejecuta este script: `python authorize_gdrive.py`
3. Se abrirá una ventana en tu navegador. Inicia sesión con tu cuenta de Google y concede los permisos.
4. Una vez autorizado, se creará un archivo `token.json` en esta carpeta.

¡Listo! Ahora el bot podrá usar este token para subir archivos sin necesidad de volver a autorizar.
"""
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Si modificas estos SCOPES, borra el archivo token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

def authorize_gdrive():
    """
    Realiza el flujo de autorización de OAuth2 para Google Drive.
    """
    creds = None
    
    if os.path.exists(TOKEN_FILE):
        logger.info(f"✅ El archivo '{TOKEN_FILE}' ya existe. La autorización parece estar completa.")
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            if creds and creds.valid:
                 logger.info("Las credenciales son válidas. No se necesita re-autorización.")
                 return
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refrescando token de acceso...")
                creds.refresh(Request())
                logger.info("Token refrescado exitosamente.")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo cargar '{TOKEN_FILE}'. Se procederá a re-autorizar. Error: {e}")

    if not creds or not creds.valid:
        if not os.path.exists(CREDENTIALS_FILE):
            logger.error(f"❌ {CREDENTIALS_FILE} no encontrado. Por favor, sigue las instrucciones para crearlo.")
            return
        
        logger.info("🔑 Iniciando flujo de autorización. Se abrirá una ventana en tu navegador.")
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        logger.info(f"✅ ¡Autorización completada! Se ha guardado el token en '{TOKEN_FILE}'.")

if __name__ == '__main__':
=======
#!/usr/bin/env python
"""
🔑 SCRIPT DE AUTORIZACIÓN PARA GOOGLE DRIVE

Ejecuta este script UNA SOLA VEZ de forma interactiva para generar el archivo `token.json`.
Este archivo es necesario para que el bot pueda subir reportes a tu Google Drive.

Pasos:
1. Asegúrate de tener tu archivo `credentials.json` en la misma carpeta.
2. Ejecuta este script: `python authorize_gdrive.py`
3. Se abrirá una ventana en tu navegador. Inicia sesión con tu cuenta de Google y concede los permisos.
4. Una vez autorizado, se creará un archivo `token.json` en esta carpeta.

¡Listo! Ahora el bot podrá usar este token para subir archivos sin necesidad de volver a autorizar.
"""
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Si modificas estos SCOPES, borra el archivo token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Construir rutas absolutas a la raíz del proyecto para los archivos de credenciales
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = os.path.join(PROJECT_ROOT, 'credentials.json')
TOKEN_FILE = os.path.join(PROJECT_ROOT, 'token.json')

def authorize_gdrive():
    """
    Realiza el flujo de autorización de OAuth2 para Google Drive.
    """
    creds = None
    
    # Forzar re-autorización eliminando el token existente si lo hay.
    if os.path.exists(TOKEN_FILE):
        logger.info(f"Se encontró un '{TOKEN_FILE}' existente. Eliminándolo para forzar una nueva autorización.")
        os.remove(TOKEN_FILE)

    if not os.path.exists(CREDENTIALS_FILE):
        logger.error(f"❌ {CREDENTIALS_FILE} no encontrado. Por favor, sigue las instrucciones para crearlo.")
        return
    
    logger.info("🔑 Iniciando flujo de autorización para Google Drive.")
    try:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        # run_console() muestra una URL para copiar y pegar manualmente en el navegador.
        creds = flow.run_console()
    except Exception as e:
        logger.error(f"❌ Error durante el flujo de autorización: {e}")
        logger.error("   Asegúrate de que 'credentials.json' es para una 'Aplicación de escritorio'.")
        return
    
    # Guardar las credenciales para el próximo uso
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())
    logger.info(f"✅ ¡Autorización completada! Se ha guardado el token en '{TOKEN_FILE}'.")

if __name__ == '__main__':
>>>>>>> 5467461205daa4de03832788163f55c1d92bf1e5
    authorize_gdrive()