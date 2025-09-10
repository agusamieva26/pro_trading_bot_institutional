# daily_reporter.py
import time
from datetime import datetime
import pytz
from bot.reporter import generate_daily_report
from bot.util import logger

def run_reporter():
    """
    Genera reporte diario cuando Alpaca resetea el daily change (8:15-8:30 AM Madrid).
    Detecta automáticamente el reset en lugar de usar horarios fijos.
    """
    madrid_tz = pytz.timezone("Europe/Madrid")
    last_known_equity = None
    reset_detected = False
    
    logger.info("⏰ Reporter en modo DETECTAR RESET: generará reporte cuando Alpaca resetee daily change")
    
    while True:
        try:
            # Obtener datos actuales de Alpaca
            from alpaca.trading.client import TradingClient
            from bot.config import settings
            
            client = TradingClient(
                api_key=settings.alpaca_api_key,
                secret_key=settings.alpaca_secret_key,
                paper=(settings.mode == "paper")
            )
            
            account = client.get_account()
            current_equity = float(account.equity)
            last_equity = float(getattr(account, "last_equity", current_equity))
            
            # DETECTAR RESET: Si last_equity cambió significativamente vs equity conocido
            if last_known_equity is not None:
                # Reset detectado si last_equity se acerca al equity anterior
                if abs(last_equity - last_known_equity) < abs(current_equity - last_known_equity):
                    if not reset_detected:
                        now = datetime.now(madrid_tz)
                        logger.info(f"🔄 RESET DETECTADO a las {now.strftime('%H:%M:%S')} - last_equity: ${last_equity:,.2f}")
                        logger.info("📅 Generando reporte diario tras reset automático de Alpaca...")
                        
                        # Generar reporte del día anterior
                        generate_daily_report()
                        reset_detected = True
                        
                        logger.info("✅ Reporte generado tras detectar reset del daily change")
            
            # Actualizar equity conocido
            last_known_equity = current_equity
            
            # Reset flag al mediodía para detectar el próximo reset
            now = datetime.now(madrid_tz)
            if now.hour >= 12 and reset_detected:
                reset_detected = False
                logger.debug("🔄 Flag de reset reiniciado para próximo día")
            
        except Exception as e:
            logger.warning(f"⚠️ Error en detector de reset: {e}")
            
        time.sleep(60)  # Revisar cada minuto durante la ventana de reset