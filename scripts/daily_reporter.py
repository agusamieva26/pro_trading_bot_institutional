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
                        
                        # 💰 DISTRIBUCIÓN DE BENEFICIOS 40-60% AL FINAL DEL DÍA
                        try:
                            from bot.profit_management import profit_manager
                            
                            # Calcular beneficio del día que acaba de terminar
                            previous_daily_profit = last_known_equity - last_equity
                            
                            logger.info(f"💰 Evaluando distribución de beneficios del día anterior: ${previous_daily_profit:+,.2f}")
                            
                            if previous_daily_profit > 0:
                                # Verificar si ya se distribuyó (para evitar duplicados)
                                if profit_manager.should_distribute_profits(previous_daily_profit):
                                    logger.info("🔄 Ejecutando distribución 40-60% tras reset diario...")
                                    distribution_result = profit_manager.distribute_daily_profits(last_known_equity, previous_daily_profit)
                                    
                                    if distribution_result["distributed"]:
                                        # Enviar notificación de distribución
                                        profit_manager.send_distribution_notification(distribution_result)
                                        logger.info(f"✅ DISTRIBUCIÓN COMPLETADA: Reinversión ${distribution_result['amount_reinvested']:,.2f}, Protegido ${distribution_result['amount_protected']:,.2f}")
                                    else:
                                        logger.info(f"⚠️ Distribución omitida: {distribution_result.get('reason', 'Ya distribuido hoy')}")
                                else:
                                    logger.info("ℹ️ Beneficios ya distribuidos anteriormente durante el día")
                            else:
                                logger.info(f"ℹ️ Sin beneficios para distribuir (${previous_daily_profit:+,.2f})")
                                
                        except Exception as e:
                            logger.error(f"❌ Error en distribución de beneficios durante reset: {e}")
                        
                        reset_detected = True
                        logger.info("✅ Reporte generado y beneficios procesados tras detectar reset del daily change")
            
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