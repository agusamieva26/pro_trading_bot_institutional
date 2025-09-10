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

    # Programar el reporte a las 08:35 (5 minutos después del BOD sync de Alpaca)
    schedule.every().day.at("08:35").do(
        lambda: logger.info("📅 Generando reporte diario tras actualización Alpaca (08:35)...") or generate_daily_report()
    )

    # Mostrar la hora actual en España
    now = datetime.now(madrid_tz)
    logger.info(f"⏰ Reporter programado: generará reporte diario a las 08:35 CET/CEST (tras sync Alpaca). Hora actual: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    while True:
        schedule.run_pending()
        time.sleep(30)  # Revisa cada 30 segundos