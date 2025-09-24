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
    authorize_gdrive()