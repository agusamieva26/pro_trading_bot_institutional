# daily_reporter.py
import schedule
import time
from datetime import datetime
import pytz  # ✅ Usar pytz
from bot.reporter import generate_daily_report
from bot.util import logger

def run_reporter():
    """
    Ejecuta el generador de reportes diarios a las 00:00 hora de España.
    """
    # Zona horaria de España
    madrid_tz = pytz.timezone("Europe/Madrid")  # ✅ pytz.timezone

    # Programar el reporte a las 00:00 (medianoche) en hora local de España
    schedule.every().day.at("00:00", madrid_tz).do(
        lambda: logger.info("📅 Generando reporte diario a medianoche (España)...") or generate_daily_report()
    )

    # Mostrar la hora actual en España
    now = datetime.now(madrid_tz)
    logger.info(f"⏰ Reporter programado: generará reporte diario a las 00:00 CET/CEST (España). Hora actual: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    while True:
        schedule.run_pending()
        time.sleep(30)  # Revisa cada 30 segundos