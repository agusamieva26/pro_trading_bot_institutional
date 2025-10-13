#!/usr/bin/env python
"""
?? SCRIPT DE AUTORIZACI車N PARA GOOGLE DRIVE

Ejecuta este script UNA SOLA VEZ de forma interactiva para generar el archivo `token.json`.
Este archivo es necesario para que el bot pueda subir reportes a tu Google Drive.

Pasos:
1. Aseg迆rate de tener tu archivo `credentials.json` en la misma carpeta.
2. Ejecuta este script: `python authorize_gdrive.py`
3. Se abrir芍 una ventana en tu navegador. Inicia sesi車n con tu cuenta de Google y concede los permisos.
4. Una vez autorizado, se crear芍 un archivo `token.json` en esta carpeta.

?Listo! Ahora el bot podr芍 usar este token para subir archivos sin necesidad de volver a autorizar.
"""
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import base64
from google_auth_oauthlib.flow import InstalledAppFlow
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Si modificas estos SCOPES, borra el archivo token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Construir rutas absolutas a la ra赤z del proyecto para los archivos de credenciales
PROJECT_ROOT = Path(__file__).resolve().parent.parent # Navega dos niveles arriba desde el script actual
CREDENTIALS_FILE = PROJECT_ROOT / 'credentials.json'
TOKEN_FILE = PROJECT_ROOT / 'token.json'

def authorize_gdrive():
    """
    Realiza el flujo de autorizaci車n de OAuth2 para Google Drive.
    """
    # ?? NUEVO: L車gica para leer credenciales desde secrets de Fly.io
    gcreds_b64 = os.environ.get('GCREDS_JSON_B64')
    gtoken_b64 = os.environ.get('GTOKEN_JSON_B64')

    if gcreds_b64 and gtoken_b64:
        logger.info("?? Usando credenciales de Google Drive desde secrets de entorno.")
        try:
            # Decodificar y cargar las credenciales desde las variables de entorno
            creds_json_str = base64.b64decode(gcreds_b64).decode('utf-8')
            token_json_str = base64.b64decode(gtoken_b64).decode('utf-8')
            
            # Guardar en archivos temporales para que el flujo de Google los pueda usar
            with open(CREDENTIALS_FILE, 'w') as f:
                f.write(creds_json_str)
            with open(TOKEN_FILE, 'w') as f:
                f.write(token_json_str)
            
            logger.info(f"? Credenciales y token guardados temporalmente para autorizaci車n.")
            # El flujo continuar芍 usando los archivos creados.
        except Exception as e:
            logger.error(f"? Error cargando credenciales desde secrets: {e}. Se intentar芍 el flujo interactivo.")

    creds = None
    
    # Forzar re-autorizaci車n eliminando el token existente si lo hay.
    if os.path.exists(TOKEN_FILE):
        logger.info(f"Se encontr車 un '{TOKEN_FILE}' existente. Elimin芍ndolo para forzar una nueva autorizaci車n.")
        os.remove(TOKEN_FILE)
    
    if not Path(CREDENTIALS_FILE).exists():
        logger.error(f"? {CREDENTIALS_FILE} no encontrado. Por favor, sigue las instrucciones para crearlo.")
        return

    logger.info("?? Iniciando flujo de autorizaci車n para Google Drive.")
    try:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        # run_local_server() abre el navegador y gestiona la autenticaci車n autom芍ticamente.
        creds = flow.run_local_server(port=0)
    except Exception as e:
        logger.error(f"? Error durante el flujo de autorizaci車n interactivo: {e}")
        logger.error("   Aseg迆rate de que 'credentials.json' es para una 'Aplicaci車n de escritorio' y que puedes abrir un navegador.")
        return

    # Guardar las credenciales para el pr車ximo uso
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())
    logger.info(f"? ?Autorizaci車n completada! Se ha guardado el token en '{TOKEN_FILE}'.")

if __name__ == '__main__':
    authorize_gdrive()