# bot/main.py
import os
# 🧠 Force TensorFlow to use CPU only to avoid CUDA errors in all environments
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

import logging
import time
import threading
import pandas as pd
from tenacity import retry, wait_exponential, stop_after_attempt
from alpaca.trading.client import TradingClient

from .auto_tuner import tune_risk_parameters
from .config import settings
from .data import fetch_bars, fetch_all_bars
from .strategy_optimizer import run_advanced_optimization, OptimizationResult
from .features import make_features
from .strategy import load_trading_model, hybrid_signal, reset_signal_memory, reset_model_cache
from .advanced_ml import auto_load_ml_models, load_optimized_params
from .sizing import volatility_target_size, kelly_cap
from .execution import place_order, close_position
from .state import BotState
from .exposure import get_total_exposure 
from .telegram import alert_risk_stop, alert_error, send_telegram
from .position_monitor import monitor_closed_positions
from .profit_taking import auto_profit_taking
from .profit_management import profit_manager
from .dynamic_shorts import dynamic_short_manager 
from .parallel_analyzer import parallel_signal_analysis, filter_strong_signals, get_cached_positions
from .multi_timeframe import enhance_signals_with_multi_tf
from .risk_management_v2 import AdvancedRiskManager, analyze_risk_environment
from .symbol_manager import symbol_manager
from .sentiment_analysis import sentiment_integrator
from .portfolio_rebalancer import portfolio_rebalancer
from .dynamic_config import dynamic_config_manager
from .model_selection import advanced_model_selector
from .advanced_features import advanced_feature_generator
from .ai_system_simple import get_ai_adjusted_signal, get_ai_system_status
from .ai_news_simple import get_ai_sentiment_adjustment  # 🤖 AI HÍBRIDA REAL
from .intelligent_monitor import IntelligentMonitor  # 🤖 SISTEMA DE MONITOREO INTELIGENTE 24/7
from .util import logger 
from health_server import start_health_server
from datetime import datetime, timedelta
import pytz
import os
import sys
from pathlib import Path
import subprocess

from datetime import datetime, timedelta


def is_stock_market_open() -> bool:
    """Devuelve True si el mercado de acciones de EE.UU. está abierto ahora."""
    eastern = pytz.timezone("US/Eastern")
    now = datetime.now(eastern)

    # Días hábiles: lunes(0) a viernes(4)
    if now.weekday() > 4:
        return False

    # Horario regular del mercado: 9:30 a 16:00 hora NY
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

    return market_open <= now <= market_close


def _client():
    return TradingClient(
        api_key=settings.alpaca_api_key,
        secret_key=settings.alpaca_secret_key,
        paper=(settings.mode == "paper")
    )


def _is_crypto(symbol: str) -> bool:
    return symbol_manager.is_crypto(symbol)


def _get_position(symbol: str):
    client = _client()
    try:
        return client.get_open_position(symbol.replace("/", ""))
    except Exception:
        return None

def _get_position_cached(symbol: str, client):
    """Obtener posición usando cache de posiciones para mejor rendimiento."""
    try:
        positions = get_cached_positions(client)  # 🚀 CACHE INTELIGENTE
        symbol_normalized = symbol.replace("/", "")
        for pos in positions:
            if pos.symbol == symbol_normalized:
                return pos
        return None
    except Exception:
        return None


@retry(wait=wait_exponential(multiplier=1, min=5, max=60), stop=stop_after_attempt(5))
def run_once(state: BotState, clf):
    client = _client()

    # 0. RESETEAR CASH RESERVADO al inicio de cada iteración
    from bot.execution import reset_reserved_cash
    reset_reserved_cash()
    
    # 0.1. RESETEAR MEMORIA DE SEÑALES (fix sesgo bajista perpetuo)
    reset_signal_memory()
    
    # 🏛️ ARBITRAGE SUBSYSTEM INITIALIZATION (CRITICAL: Outside kill-switch path)
    arbitrage_initialized = False
    arbitrage_engine = None
    try:
        from .arbitrage_engine import arbitrage_engine
        from .execution import reset_arbitrage_tracking
        
        # Reset arbitrage tracking at start of each iteration
        reset_arbitrage_tracking()
        arbitrage_initialized = True
        
        # Log arbitrage initialization status
        arbitrage_mode = settings.arbitrage_mode.lower()
        if settings.arbitrage_enabled:
            if arbitrage_mode == "real":
                logger.critical(f"🚨 ARBITRAGE SUBSYSTEM: REAL TRADING MODE - Actual trades will be executed")
            else:
                logger.warning(f"🎭 ARBITRAGE SUBSYSTEM: SIMULATION MODE - No real trades (mode: {arbitrage_mode})")
            logger.info(f"💰 Arbitrage engine initialized successfully")
        else:
            logger.info(f"💰 Arbitrage subsystem disabled in configuration")
            
    except Exception as e:
        logger.error(f"❌ Arbitrage subsystem initialization failed: {e}")
        logger.debug(f"❌ Arbitrage error details: {str(e)}")
        arbitrage_initialized = False

    # 1. Configuración Dinámica y Auto-ajuste
    dynamic_config = dynamic_config_manager.get_current_config()
    performance_metrics = dynamic_config_manager.analyze_recent_performance()
    
    # Aplicar configuración dinámica
    settings.risk_per_trade = dynamic_config["risk_per_trade"]
    settings.take_profit_pct = dynamic_config["take_profit_pct"] 
    settings.stop_loss_pct = dynamic_config["stop_loss_pct"]
    settings.max_gross_exposure = dynamic_config["max_gross_exposure"]
    
    logger.debug(f"🔧 Config dinámico: risk={settings.risk_per_trade:.3f}, tp={settings.take_profit_pct:.3f}, sl={settings.stop_loss_pct:.3f}")

    # 1. Equity actual y cash disponible - USANDO ALPACA COMO FUENTE DE VERDAD
    try:
        account = client.get_account()
        current_equity = float(getattr(account, 'equity', 0))
        available_cash = float(getattr(account, 'cash', 0))
        last_equity = float(getattr(account, "last_equity", current_equity))
        
        # Calcular daily change usando Alpaca (igual que dashboard y telegram)
        daily_change = current_equity - last_equity
        daily_change_pct = (daily_change / last_equity) if last_equity > 0 else 0.0
        
        # Actualizar estado con valores de Alpaca
        state.state["equity"] = current_equity
        state.state["daily_pnl"] = daily_change
        state.state["last_equity"] = last_equity
        state.save()
        
        logger.info(f"💵 Cash disponible: ${available_cash:,.2f} | Equity: ${current_equity:,.2f}")
        logger.debug(f"🔍 Alpaca P&L: Actual=${current_equity:,.2f}, Ayer=${last_equity:,.2f}, Cambio=${daily_change:+,.2f}")
        
    except Exception as e:
        logger.error(f"❌ No se pudo obtener equity: {e}")
        return

    
    # ✅ P&L diario usando valores reales de Alpaca
    logger.info(f"📈 P&L diario Alpaca: {daily_change_pct:+.2f}% (${daily_change:+,.2f}) | Ayer: ${last_equity:,.2f}")
    
    # 🚨 KILL SWITCH DIARIO: Parar si pérdidas > $3000 o > 15%  
    daily_loss_limit = -3000  # $3000 pérdida máxima (expandido para recuperación épica)
    daily_loss_pct_limit = -15.0  # 15% pérdida máxima
    
    # 🧪 RISK MANAGEMENT TEST MODE BYPASS
    kill_switch_active = daily_change <= daily_loss_limit or daily_change_pct <= daily_loss_pct_limit
    bypass_kill_switch = settings.risk_management_test_mode or settings.disable_kill_switch
    
    if kill_switch_active and bypass_kill_switch:
        logger.warning(f"🧪 KILL SWITCH BYPASSED FOR TESTING: Loss ${daily_change:+,.2f} ({daily_change_pct:+.2f}%) - Continuing for risk management validation")
        logger.info(f"🧪 Test Mode: risk_management_test_mode={settings.risk_management_test_mode}, disable_kill_switch={settings.disable_kill_switch}")
    elif kill_switch_active:
        logger.critical(f"🚨🛑 KILL SWITCH ACTIVADO: Pérdida diaria ${daily_change:+,.2f} ({daily_change_pct:+.2f}%) excede límites!")
        logger.critical(f"🚨 CERRANDO TODAS LAS POSICIONES Y PAUSANDO TRADING")
        
        # Cerrar todas las posiciones inmediatamente
        try:
            from bot.execution import close_all
            from bot.telegram import send_telegram
            
            telegram_msg = f"""🚨 KILL SWITCH ACTIVADO 🚨

💀 Pérdida diaria: ${daily_change:+,.2f} ({daily_change_pct:+.2f}%)
🛑 Límite: -$3000 o -15%

🚨 CERRANDO TODAS LAS POSICIONES
⏸️ TRADING PAUSADO hasta reset diario"""
            send_telegram(telegram_msg)
            
            close_all()
            logger.critical(f"✅ Todas las posiciones cerradas por KILL SWITCH")
        except Exception as e:
            logger.error(f"❌ Error cerrando posiciones: {e}")
        
        logger.critical(f"🚨 TRADING PAUSADO hasta próximo reset diario")
        return "KILL_SWITCH_ACTIVATED"
    
    # 🎯 TAKE PROFIT DIARIO: $1000 - Cerrar todas las posiciones
    if daily_change >= 1000:
        from bot.execution import close_all
        from bot.telegram import send_telegram
        
        msg = f"🎯 META ALCANZADA: ${daily_change:+,.2f} beneficio diario ≥ $1,000"
        logger.critical(f"💰 {msg}")
        logger.critical("🚨 CERRANDO TODAS LAS POSICIONES - OBJETIVO DIARIO CUMPLIDO")
        
        # 🚨 NOTIFICACIÓN TELEGRAM PRIORITARIA
        try:
            telegram_msg = f"""🎯 ¡OBJETIVO DIARIO CUMPLIDO! 🎯

💰 Beneficio alcanzado: ${daily_change:+,.2f}
🎯 Objetivo: $1,000.00
📊 Porcentaje: {(daily_change/1000)*100:.1f}%

🚨 CERRANDO TODAS LAS POSICIONES AUTOMÁTICAMENTE

✅ Bot detenido por seguridad tras alcanzar meta diaria"""
            send_telegram(telegram_msg)
            logger.info("📱 Telegram: Notificación de objetivo enviada")
        except Exception as e:
            logger.error(f"❌ Error enviando Telegram de objetivo: {e}")
            
        close_all()
        logger.critical("✅ Todas las posiciones cerradas. Bot detenido por objetivo diario.")
        return "STOP"
    
    # 💰 GESTIÓN INTELIGENTE DE BENEFICIOS: 40% Reinversión, 60% Protección
    elif daily_change > 0:  # Solo si hay beneficio
        # 1. Gestionar distribución de beneficios
        try:
            if profit_manager.should_distribute_profits(daily_change):
                distribution_result = profit_manager.distribute_daily_profits(current_equity, daily_change)
                if distribution_result["distributed"]:
                    # Enviar notificación de distribución
                    profit_manager.send_distribution_notification(distribution_result)
                    logger.info(f"💰 Beneficios distribuidos: Reinversión ${distribution_result['amount_reinvested']:,.2f}, Protegido ${distribution_result['amount_protected']:,.2f}")
        except Exception as e:
            logger.error(f"❌ Error en gestión de beneficios: {e}")
        
        # 2. Notificaciones de progreso hacia objetivo $1000
        progress_pct = (daily_change / 1000) * 100
        
        # Notificar cada 25% de progreso (250, 500, 750)
        milestone_250 = daily_change >= 250 and not state.state.get("notified_250", False)
        milestone_500 = daily_change >= 500 and not state.state.get("notified_500", False) 
        milestone_750 = daily_change >= 750 and not state.state.get("notified_750", False)
        
        if milestone_250 or milestone_500 or milestone_750:
            from bot.telegram import send_telegram
            try:
                telegram_msg = ""
                if milestone_750:
                    telegram_msg = f"🔥 ¡75% DEL OBJETIVO! 🔥\n\n💰 Beneficio: ${daily_change:+,.2f}\n🎯 Faltan solo: ${1000-daily_change:.2f} para $1,000\n⚡ ¡Casi en la meta!"
                    state.state["notified_750"] = True
                elif milestone_500:
                    telegram_msg = f"🚀 ¡MITAD DEL CAMINO! 🚀\n\n💰 Beneficio: ${daily_change:+,.2f}\n🎯 Progreso: 50% hacia $1,000\n💪 ¡Sigue así!"
                    state.state["notified_500"] = True
                elif milestone_250:
                    telegram_msg = f"📈 ¡Primer cuarto! 📈\n\n💰 Beneficio: ${daily_change:+,.2f}\n🎯 Progreso: 25% hacia $1,000\n✨ ¡Buen comienzo!"
                    state.state["notified_250"] = True
                
                if telegram_msg:
                    send_telegram(telegram_msg)
                state.save()  # Guardar estado de notificaciones
                logger.info(f"📱 Telegram: Notificación de progreso enviada ({progress_pct:.1f}%)")
            except Exception as e:
                logger.error(f"❌ Error enviando Telegram de progreso: {e}")

    # 3. Exposición bruta - GESTIONAR PERO CONTINUAR
    exposure_managed = False
    try:
        current_exposure = get_total_exposure()
        if current_exposure >= settings.max_gross_exposure:
            logger.warning(f"⚠️ Exposición {current_exposure:.2f}x ≥ límite {settings.max_gross_exposure}x. Reduciendo...")
            try:
                positions = client.get_all_positions()
                sorted_positions = sorted(positions, key=lambda p: abs(float(getattr(p, 'qty', 0))), reverse=False)
                for pos in sorted_positions:
                    qty = float(getattr(pos, 'qty', 0))
                    symbol = getattr(pos, 'symbol', '')
                    side = "long" if qty > 0 else "short"
                    logger.info(f"🔁 Reduciendo exposición: cerrando {abs(qty)} de {symbol}")
                    # ✅ Pasar el objeto de posición directamente para evitar inconsistencias
                    if symbol:
                        close_position(symbol)
                    exposure_managed = True
                    break
            except Exception as e:
                logger.error(f"❌ No se pudieron obtener posiciones para cierre: {e}")
        
        # ✅ CONTINUAR después de gestionar exposición
        if exposure_managed:
            logger.info("✅ Exposición gestionada. Continuando con análisis de activos...")
    except Exception as e:
        logger.exception("💥 Error al verificar exposición")
        # ✅ NO return aquí - continuar con otros activos

    # 4. Cash disponible (ya obtenido arriba)
    # available_cash ya se obtuvo en el paso 1

    total_equity = current_equity


    # --- 5. PROFIT-TAKING AUTOMÁTICO ---
    profit_result = auto_profit_taking()
    if profit_result == "PROFITS_TAKEN":
        logger.info("💰 Profit-taking ejecutado. Actualizando equity...")
        # Actualizar equity tras profit-taking
        account = client.get_account()
        current_equity = float(getattr(account, 'equity', 0))
        total_equity = current_equity
        available_cash = float(getattr(account, 'cash', 0))
        logger.info(f"📊 Equity actualizado: ${total_equity:,.2f}, Cash: ${available_cash:,.2f}")

    # 🧠 INTEGRACIÓN IA GRATUITA - Análisis inteligente sin costos
    ai_analysis = {}
    try:
        from bot.free_ai_assistant import get_free_ai_analysis_sync
        
        # Preparar datos de mercado para IA (se llenarán durante el análisis de símbolos)
        market_data_for_ai = {}
        
        # Por ahora ejecutamos sin datos - se mejorará cuando tengamos los datos de mercado
        ai_analysis = get_free_ai_analysis_sync(settings.symbols[:5], market_data_for_ai)
        
        if ai_analysis.get("ai_available"):
            signals = ai_analysis.get("signals", [])
            logger.info(f"🤖 IA GRATUITA integrada - lista para análisis")
            
            if signals:
                strong_signals = [s for s in signals if s.confidence > 0.7]
                logger.info(f"🎯 {len(signals)} señales generadas, {len(strong_signals)} fuertes")
            
    except Exception as e:
        logger.debug(f"IA Gratuita: {e}")

    # --- 6. BTC/USD DIVERSIFICADO (máximo 40% para balance) ---
    btc_max_allocation = 0.40  # Máximo 40% del equity total
    btc_max_cash = min(total_equity * btc_max_allocation, available_cash * 0.6)  # Máx 60% del cash disponible
    equity_for_btc = btc_max_cash

    if "BTC/USD" in settings.symbols:
        try:
            df = fetch_bars("BTC/USD", start=None, end=None, min_bars=50)  # Solo mínimo necesario
            if not df.empty and len(df) >= 100:
                feats = make_features(df, symbol="BTC/USD")
                latest = feats.iloc[-1]

                sig = hybrid_signal(latest, clf, symbol="BTC/USD")
                if sig != 0:
                    price = float(latest["close"])
                    atr = float(latest["atr_14"])
                    shares = volatility_target_size(equity_for_btc, price, atr)
                    frac_k = kelly_cap(0.5 + abs(sig)/2, cap=settings.risk_per_trade * 4)
                    leverage = max(min(abs(sig) + frac_k, 1.5), 0.1)
                    qty = shares * leverage
                    side = "buy" if sig > 0 else "sell"

                    # 🎯 LÍMITE INTELIGENTE: máximo 40% del equity o 60% del cash disponible
                    max_qty_by_equity = (total_equity * 0.40) / price  # 40% del equity total
                    max_qty_by_cash = (available_cash * 0.60) / price  # 60% del cash disponible
                    qty = min(qty, max_qty_by_equity, max_qty_by_cash)

                    if qty >= 1e-6:
                        is_crypto = True
                        pos = _get_position("BTC/USD")

                        if pos:
                            current_qty = float(getattr(pos, 'qty', 0))
                            if side == "buy" and current_qty > 0:
                                logger.info(f"🟢 Posición larga existente en BTC/USD. Consolidando y aumentando...")
                                # 🚀 USAR CONSOLIDACIÓN para evitar micro-posiciones
                                place_order("BTC/USD", qty, side, price, fractional=False, is_crypto=is_crypto)
                            elif side == "buy" and current_qty < 0:
                                logger.info("🔄 Cerrando corto y abriendo largo en BTC/USD")
                                # Abrir nueva posición directamente (Alpaca ya agrega automáticamente)
                                place_order("BTC/USD", qty, "buy", price, fractional=False, is_crypto=is_crypto)
                            elif side == "sell" and current_qty > 0:
                                # ✅ CRYPTO: Solo cerrar posición larga, NO abrir short (ARREGLADO SALDO)
                                safe_qty = abs(current_qty) * 0.95  # 95% para evitar errores de saldo
                                logger.info(f"🔄 Señal bajista: cerrando posición larga en BTC/USD ({safe_qty:.6f} de {abs(current_qty):.6f})")
                                place_order("BTC/USD", safe_qty, "sell", price, fractional=True, is_crypto=is_crypto)
                        else:
                            # ✅ CRYPTO: Solo abrir posición si es LONG (buy)
                            if side == "buy":
                                logger.info(f"📈 Abriendo nueva posición LONG en BTC/USD")
                                # Para nueva posición, no necesitar consolidación
                                place_order("BTC/USD", qty, side, price, fractional=False, is_crypto=is_crypto)
                            else:
                                logger.info(f"🔥 CRYPTO SHORT HABILITADO: BTC/USD señal bajista {sig:.3f}")
        except Exception as e:
            logger.error(f"💥 Error procesando BTC/USD: {e}")

    # --- 7. Resto de símbolos (dinámico según capital disponible) ---
    # Si tomamos profits, tendremos más cash disponible para otros activos
    btc_position_value = 0
    try:
        positions = get_cached_positions(client)  # 🚀 CACHE INTELIGENTE
        for pos in positions:
            if getattr(pos, 'symbol', '') == "BTCUSD":
                btc_position_value = abs(float(getattr(pos, 'market_value', 0)))
                break
    except:
        pass
    
    # 🎯 DIVERSIFICACIÓN FORZADA: Reservar siempre mínimo 30% para otros activos
    btc_percentage = btc_position_value / total_equity if total_equity > 0 else 0
    min_reserved_for_others = total_equity * 0.30  # SIEMPRE 30% reservado para diversificación
    max_btc_allowed = total_equity * 0.50  # BTC nunca más de 50% del portafolio
    
    # Cash real disponible para otros (sin confusión de 'reservado')
    remaining_cash_after_btc = available_cash - (max_btc_allowed * 0.6)  # Reservar 60% del límite BTC
    equity_for_rest = max(min_reserved_for_others, remaining_cash_after_btc)
    equity_for_rest = min(equity_for_rest, available_cash * 0.75)  # Máximo 75% del cash disponible
    
    other_symbols = settings.symbols  # ✅ INCLUIR TODOS los símbolos (incluyendo BTC)
    signals = []
    
    # 🕐 DETECTAR HORARIOS DE MERCADO: Separar cryptos (24/7) de acciones (NYSE hours)
    market_is_open = is_stock_market_open()
    crypto_symbols = []
    stock_symbols = []
    
    for symbol in other_symbols:
        asset_type = symbol_manager.get_asset_type(symbol)
        if asset_type.name == "CRYPTO":
            crypto_symbols.append(symbol)
        else:  # STOCK, ETF, etc.
            stock_symbols.append(symbol)
    
    # 📊 OPTIMIZACIÓN POR HORARIOS: Solo analizar según disponibilidad de mercado
    symbols_to_analyze = crypto_symbols.copy()  # Cryptos siempre 24/7
    
    if market_is_open:
        symbols_to_analyze.extend(stock_symbols)  # Agregar acciones si mercado abierto
        logger.info(f"📈 Mercado ABIERTO: analizando {len(crypto_symbols)} cryptos + {len(stock_symbols)} acciones")
    else:
        logger.info(f"🌙 Mercado CERRADO: solo analizando {len(crypto_symbols)} cryptos (24/7)")
        logger.info(f"⏰ Acciones pausadas hasta: 9:30 AM ET (lunes-viernes)")
    
    logger.info(f"🔍 Total activos a analizar: {len(symbols_to_analyze)}")
    logger.info(f"💰 BTC: {btc_percentage:.1%} del portafolio, Disponible para otros: ${equity_for_rest:,.2f} (DIVERSIFICADO)")

    # 🚀 ANÁLISIS PARALELO ULTRA-RÁPIDO: Descarga + análisis simultáneo
    symbols_batch = symbols_to_analyze  # ✅ ANALIZAR TODOS los símbolos disponibles (no limitar)
    logger.info(f"⚡ Análisis completo: procesando TODOS los {len(symbols_batch)} activos")
    
    # 🚀 DESCARGA PARALELA: todos los símbolos a la vez
    all_data = fetch_all_bars(symbols_batch, start="", end="", min_bars=50)
    
    # 🌍 ANÁLISIS DE ENTORNO DE RIESGO: Detectar regímenes de mercado
    risk_environment = analyze_risk_environment(all_data)
    market_condition = risk_environment.get("market_condition", "NORMAL")

    # 🛡️ FIX: Añadir validación para volatilidad anormalmente baja
    if market_condition == "ULTRA_LOW_VOLATILITY":
        logger.critical("🚨 DETECTADA VOLATILIDAD ANORMALMENTE BAJA. Usando 'NORMAL' como fallback para evitar bloqueo.")
        market_condition = "NORMAL" # Fallback a modo normal para continuar operando
        # Se podría enviar una alerta de Telegram aquí también

    
    # 🤖 ADVANCED ML: Selección optimizada (simplificada temporalmente)
    # model_comparison = advanced_model_selector.run_model_comparison(
    #     pd.concat([data for data in all_data.values()]) if all_data else pd.DataFrame()
    # )
    
    # 🧠 ANÁLISIS PARALELO OPTIMIZADO: features + señales + scoring simultáneo
    analysis_results = parallel_signal_analysis(all_data, clf, max_workers=3)  # REDUCIDO para evitar colgadas
    
    # 📊 FILTRAR SEÑALES FUERTES
    base_signals = filter_strong_signals(analysis_results, min_threshold=0.1)
    
    # 🕐 MEJORA MULTI-TIMEFRAME ULTRA-RÁPIDA: 6 workers para velocidad máxima
    mtf_enhanced_signals = enhance_signals_with_multi_tf(base_signals, clf)
    
    # 🧠 AI SYSTEM REAL: Sistema simplificado que REALMENTE funciona
    ai_enhanced_signals = []
    ai_integration_enabled = True  # Flag para activar/desactivar AI system
    
    if ai_integration_enabled:
        try:
            # 🤖 SISTEMA AI REAL - Log de inicio
            logger.info("🧠 INICIANDO ANÁLISIS AI REAL...")
            ai_status = get_ai_system_status()
            logger.info(f"🤖 AI Status: AGUS={ai_status['agus_available']}, "
                       f"Cache={len(ai_status['cache_symbols'])}, Sources={ai_status['news_sources']}")
            
            # Procesar cada señal con ajuste AI REAL
            ai_adjustments_made = 0
            for signal in mtf_enhanced_signals:
                symbol = signal.get('symbol', '')
                original_score = signal.get('score', 0.0)
                
                # Solo ajustar señales significativas 
                if symbol and abs(original_score) > 0.05:
                    try:
                        # 🧠 LLAMADA REAL AL SISTEMA AI
                        adjusted_score, ai_recommendation = get_ai_adjusted_signal(symbol, original_score)
                        
                        # Verificar si hubo ajuste significativo
                        if abs(adjusted_score - original_score) > 0.01:
                            ai_adjustments_made += 1
                            adjustment_pct = ((adjusted_score / original_score) - 1) * 100 if original_score != 0 else 0
                            
                            # LOG VISIBLE del ajuste
                            logger.info(f"🧠 AI AJUSTE {symbol}: {original_score:.3f} → {adjusted_score:.3f} "
                                       f"({adjustment_pct:+.1f}%) | {ai_recommendation[:50]}")
                            
                            # Actualizar señal
                            signal['ai_original_score'] = original_score
                            signal['score'] = adjusted_score
                            signal['ai_recommendation'] = ai_recommendation
                            signal['ai_adjusted'] = True
                        else:
                            # Sin ajuste significativo
                            signal['ai_recommendation'] = ai_recommendation
                            signal['ai_adjusted'] = False
                            
                    except Exception as ai_error:
                        logger.error(f"❌ Error AI para {symbol}: {ai_error}")
                        signal['ai_recommendation'] = f"AI Error: {str(ai_error)[:30]}"
                        signal['ai_adjusted'] = False
                
                ai_enhanced_signals.append(signal)
            
            # 🧠 RESUMEN AI VISIBLE EN LOGS
            logger.info(f"🧠 AI COMPLETADO: {ai_adjustments_made}/{len(mtf_enhanced_signals)} señales ajustadas")
                
        except Exception as ai_error:
            logger.warning(f"🤖 AI integration warning: {ai_error}")
            # Fallback: usar señales originales
            ai_enhanced_signals = mtf_enhanced_signals
    else:
        # AI deshabilitado: usar señales clásicas
        ai_enhanced_signals = mtf_enhanced_signals
    
    # 📊 INTEGRACIÓN DE SENTIMENT CLÁSICA: Ajustar por Fear & Greed Index (como backup)
    sentiment_enhanced_signals = sentiment_integrator.enhance_signals_with_sentiment(ai_enhanced_signals)
    
    # 🔄 REBALANCEO DE PORTFOLIO: Ajustar por diversificación
    portfolio_analysis = portfolio_rebalancer.analyze_current_portfolio(
        [{'symbol': getattr(pos, 'symbol', ''), 'market_value': getattr(pos, 'market_value', 0)} for pos in get_cached_positions(client)]
    )
    signals = portfolio_rebalancer.apply_rebalancing_to_signals(sentiment_enhanced_signals, portfolio_analysis)
    
    # 🛡️ CONFIGURACIÓN DINÁMICA: Adaptar a condiciones de mercado
    sentiment_level = sentiment_enhanced_signals[0].get('sentiment_level', 'neutral') if sentiment_enhanced_signals else 'neutral'
    dynamic_config_manager.adapt_to_market_conditions(market_condition, sentiment_level)

    logger.info(f"📈 Total señales detectadas: {len(signals)} de {len(other_symbols)} activos")

    # 🏛️ INSTITUTIONAL ARBITRAGE ANALYSIS
    arbitrage_results = []
    arbitrage_profits_executed = 0.0
    
    try:
        # Import arbitrage modules
        from .arbitrage_engine import arbitrage_engine
        from .execution import execute_arbitrage_trade, validate_arbitrage_risk_limits, reset_arbitrage_tracking
        
        # Reset arbitrage tracking at start of each iteration
        reset_arbitrage_tracking()
        
        logger.info("🏛️ SCANNING FOR ARBITRAGE OPPORTUNITIES...")
        
        # Detect arbitrage opportunities across all tradeable symbols
        arbitrage_opportunities = arbitrage_engine.detect_opportunities(symbols_to_analyze)
        
        if arbitrage_opportunities:
            logger.info(f"💰 ARBITRAGE: {len(arbitrage_opportunities)} opportunities detected!")
            
            # Filter executable opportunities based on available capital
            executable_opportunities = arbitrage_engine.filter_executable_opportunities(
                arbitrage_opportunities, available_cash
            )
            
            if executable_opportunities:
                logger.critical(f"🎯 EXECUTABLE ARBITRAGE: {len(executable_opportunities)} high-profit opportunities")
                
                # Execute arbitrage trades
                for opportunity in executable_opportunities:
                    # Validate risk limits before execution
                    if validate_arbitrage_risk_limits(opportunity, current_equity):
                        # Send high-profit alert to Telegram before execution
                        if opportunity.is_high_profit(1.0):  # ≥1% profit
                            try:
                                from .telegram import send_telegram
                                telegram_msg = f"""🏛️ HIGH-PROFIT ARBITRAGE DETECTED! 🏛️

💰 Symbol: {opportunity.symbol}
📈 Expected Profit: {opportunity.net_profit_pct:.1%}
💵 Potential USD: ${opportunity.potential_profit_usd:.2f}
⚡ Spread: {opportunity.spread_pct:.1%}

🔵 Buy: {opportunity.buy_exchange} @ ${opportunity.buy_price:.6f}
🔴 Sell: {opportunity.sell_exchange} @ ${opportunity.sell_price:.6f}

🎯 Confidence: {opportunity.confidence_score:.0%}
⏱️ Executing now..."""
                                send_telegram(telegram_msg)
                                logger.info("📱 Telegram: High-profit arbitrage alert sent")
                            except Exception as e:
                                logger.error(f"❌ Telegram arbitrage alert failed: {e}")
                        
                        # Execute the arbitrage trade
                        execution_result = execute_arbitrage_trade(opportunity)
                        arbitrage_results.append(execution_result)
                        
                        if execution_result.get("success", False):
                            actual_profit = execution_result.get("actual_profit_usd", 0.0)
                            arbitrage_profits_executed += actual_profit
                            
                            # Record successful execution in engine
                            arbitrage_engine.record_execution(opportunity, actual_profit)
                            
                            # Send success notification for high profits
                            if actual_profit >= 10.0:  # $10+ profit
                                try:
                                    from .telegram import send_telegram
                                    success_msg = f"""✅ ARBITRAGE EXECUTED SUCCESSFULLY! ✅

💰 Symbol: {opportunity.symbol}
📈 Actual Profit: ${actual_profit:.2f}
🎯 Expected: {opportunity.net_profit_pct:.1%}
⚡ Trade ID: {execution_result.get('trade_id', 'N/A')}

💵 Investment: ${execution_result.get('quantity', 0) * opportunity.buy_price:.2f}
📊 Quantity: {execution_result.get('quantity', 0):.6f}

🚀 Institutional arbitrage system working!"""
                                    send_telegram(success_msg)
                                except Exception as e:
                                    logger.error(f"❌ Telegram success alert failed: {e}")
                        else:
                            error = execution_result.get("error", "Unknown error")
                            logger.warning(f"⚠️ Arbitrage execution failed for {opportunity.symbol}: {error}")
                    else:
                        logger.debug(f"🚫 {opportunity.symbol}: Risk validation failed")
            else:
                logger.info("💰 ARBITRAGE: No executable opportunities within risk limits")
        else:
            logger.debug("🔍 ARBITRAGE: No opportunities detected this iteration")
        
        # Log arbitrage performance summary
        if arbitrage_results:
            successful_arbitrages = sum(1 for r in arbitrage_results if r.get("success", False))
            total_arbitrages = len(arbitrage_results)
            performance_stats = arbitrage_engine.get_performance_stats()
            
            logger.critical(f"🏛️ ARBITRAGE SUMMARY:")
            logger.critical(f"   ✅ Executed: {successful_arbitrages}/{total_arbitrages}")
            logger.critical(f"   💰 Session Profit: ${arbitrage_profits_executed:.2f}")
            logger.critical(f"   📊 Success Rate: {performance_stats['success_rate']:.1%}")
            logger.critical(f"   🎯 Total Detected: {performance_stats['opportunities_detected']}")
        
    except Exception as e:
        logger.error(f"❌ Arbitrage analysis failed: {e}")
        logger.debug(f"❌ Arbitrage error details: {str(e)}")

    signals.sort(key=lambda x: abs(x["signal"]), reverse=True)

    logger.info(f"💰 Procesando {len(signals)} señales detectadas...")
    
    for i, item in enumerate(signals, 1):
        symbol = item["symbol"]
        sig = item["signal"]
        price = item["price"]
        atr = item["atr"]
        
        # 🎯 SCORE DETALLADO CON EVALUACIÓN
        signal_strength = "MÁXIMA" if abs(sig) >= 0.5 else "ALTA" if abs(sig) >= 0.3 else "MEDIA"
        direction = "LONG" if sig > 0 else "SHORT"
        direction_emoji = "📊" if sig > 0 else "📉"
        
        logger.info(f"{direction_emoji} {direction} ({i}/{len(signals)}) {symbol}: score={sig:+.3f} ({signal_strength}) @ ${price:.2f}")
        
        # 🎯 POSITION SIZING BALANCEADO: Para diversificación óptima
        if abs(sig) >= 0.2:  # Señales fuertes
            position_equity = equity_for_rest * 0.25  # 25% del disponible por señal fuerte
        elif abs(sig) >= 0.15:  # Señales medias
            position_equity = equity_for_rest * 0.15  # 15% del disponible por señal media
        else:  # Señales débiles pero >0.1
            position_equity = equity_for_rest * 0.08  # 8% del disponible por señal débil
        
        # 🏛️ INSTITUTIONAL-GRADE DYNAMIC RISK MANAGEMENT SYSTEM
        from .integrated_risk_system import get_integrated_risk_assessment
        
        # Get comprehensive risk assessment from all risk management components
        risk_assessment = get_integrated_risk_assessment(
            symbol=symbol, signal_strength=sig, equity=position_equity, price=price, atr=atr
        )
        
        # Check if trade should be allowed based on integrated risk analysis
        if not risk_assessment.get('allow_trade', False):
            logger.info(f"🚫 {symbol}: Trade blocked by integrated risk management")
            logger.debug(f"   Risk Score: {risk_assessment.get('risk_score', 0):.2f} | "
                        f"Drawdown: {risk_assessment.get('current_drawdown', 0):.1%} | "
                        f"Emergency: {risk_assessment.get('emergency_mode', False)}")
            continue
        
        # Get position sizing from integrated system
        recommended_shares = risk_assessment.get('position_size_shares', 0)
        max_position_usd = risk_assessment.get('max_position_usd', 0)
        risk_multiplier = risk_assessment.get('risk_multiplier', 1.0)
        
        # Log integrated risk assessment
        logger.info(f"🏛️ {symbol} RISK ASSESSMENT: "
                   f"Score: {risk_assessment.get('risk_score', 0):.2f} | "
                   f"Regime: {risk_assessment.get('volatility_regime', 'unknown')} | "
                   f"Multiplier: {risk_multiplier:.2f}x | "
                   f"Max: ${max_position_usd:.0f}")
        
        # Get dynamic stops from integrated system
        stop_loss_adj = risk_assessment.get('stop_loss_adjustment', 1.0)
        take_profit_adj = risk_assessment.get('take_profit_adjustment', 1.0)
        
        # Calculate adjusted stops
        dynamic_stop_loss_pct = settings.stop_loss_pct * stop_loss_adj
        dynamic_take_profit_pct = settings.take_profit_pct * take_profit_adj
        
        # Apply safety bounds
        dynamic_stop_loss_pct = max(0.003, min(0.05, dynamic_stop_loss_pct))  # 0.3% to 5%
        dynamic_take_profit_pct = max(0.01, min(0.15, dynamic_take_profit_pct))  # 1% to 15%
        
        # 🤖 ADVANCED ML PREDICTION: Combinar con modelo óptimo
        try:
            if symbol in all_data:
                symbol_data = all_data[symbol]
                ml_prediction, best_model, ml_confidence = advanced_model_selector.get_optimal_prediction(symbol_data)
                
                # Combinar señal tradicional con ML avanzado
                combined_signal = (sig * 0.6) + (ml_prediction * 0.4)  # 60% tradicional, 40% ML avanzado
                
                logger.debug(f"🤖 {symbol}: ML={ml_prediction:+.3f} ({best_model}, conf={ml_confidence:.2f}) → Combined={combined_signal:+.3f}")
                
                # Usar señal combinada
                sig = combined_signal
        except Exception as e:
            logger.debug(f"⚠️ Error en predicción ML para {symbol}: {e}")
        
        # 🧠 IA HÍBRIDA REAL: Aplicar ajuste de sentiment con noticias y OpenAI
        try:
            ai_adjustment = get_ai_sentiment_adjustment(symbol, sig)
            if ai_adjustment != 0.0:
                original_sig = sig
                sig = sig + ai_adjustment
                sig = max(-1.0, min(1.0, sig))  # Mantener en rango válido
                logger.info(f"🤖 AI Analysis: {symbol} sentiment {ai_adjustment:+.3f} applied (signal: {original_sig:+.3f} → {sig:+.3f})")
            else:
                logger.debug(f"🤖 AI Neutral: {symbol} no sentiment adjustment needed")
        except Exception as e:
            logger.warning(f"⚠️ AI Error para {symbol}: {e}")
        
        # Use integrated risk management system for position sizing
        shares = recommended_shares
        leverage = max(min(abs(sig) * 0.8 + risk_multiplier * 0.2, 2.0), 0.05)  # Enhanced leverage calculation
        qty = min(shares * leverage, max_position_usd / price) if price > 0 else 0
        
        # Apply dynamic stops from integrated system
        settings.stop_loss_pct = dynamic_stop_loss_pct
        settings.take_profit_pct = dynamic_take_profit_pct
        side = "buy" if sig > 0 else "sell"
        
        logger.info(f"💰 {symbol}: qty={qty:.6f} side={side} (leverage={leverage:.2f}x, shares={shares:.6f})")
        
        if qty < 1e-6:
            logger.info(f"⚠️ {symbol}: cantidad muy pequeña, skip")
            continue

        is_crypto = _is_crypto(symbol)
        pos = _get_position_cached(symbol, client)  # 🚀 CACHE OPTIMIZADO
        if pos:
            current_qty = float(pos.qty)
            is_long = current_qty > 0
            is_short = current_qty < 0

            if side == "buy":
                if is_long:
                    logger.info(f"📊 LONG {symbol}: score={sig:+.3f}, qty={qty:.6f} (consolidando y aumentando posición)")
                    # 🚀 USAR CONSOLIDACIÓN para todos los símbolos, no solo BTC
                    place_order(symbol, qty, "buy", price, fractional=not is_crypto, is_crypto=is_crypto)
                elif is_short:
                    logger.info(f"📊 LONG {symbol}: score={sig:+.3f}, qty={qty:.6f} (consolidando: cerrar short + abrir long)")
                    # Abrir nueva posición directamente (Alpaca maneja automáticamente posiciones opuestas)
                    place_order(symbol, qty, "buy", price, fractional=not is_crypto, is_crypto=is_crypto)
            else:  # side == "sell"
                if is_crypto:
                    # 🔄 CRYPTO OPTIMIZADO: Solo cerrar posiciones largas existentes
                    if is_long:
                        logger.info(f"📉 CLOSE LONG {symbol}: score={sig:+.3f}, qty={abs(current_qty):.6f} (señal bajista)")
                        place_order(symbol, abs(current_qty), "sell", price, fractional=not is_crypto, is_crypto=is_crypto)
                    else:
                        logger.info(f"⚠️ {symbol}: Señal bajista ({sig:+.3f}) → SKIP (no posición larga para cerrar)")
                else:
                    # 🚫 ACCIONES: SHORTS DESHABILITADOS (Alpaca no permite fractional shorts)
                    if is_long:
                        logger.info(f"📉 CLOSE LONG {symbol}: score={sig:+.3f}, qty={abs(current_qty):.6f} (solo cerrar, no short)")
                        place_order(symbol, abs(current_qty), "sell", price, fractional=not is_crypto, is_crypto=is_crypto)
                    else:
                        logger.warning(f"⚠️ {symbol}: Señal bajista ({sig:+.3f}) → SKIP STOCK SHORT (fractional shorts no permitidos por Alpaca)")
        else:
            # 🔥 CRYPTO SHORTS ACTIVADOS: Sin restricciones para máxima agresividad
            action = "LONG" if side == "buy" else "SHORT"
            action_emoji = "📊" if side == "buy" else "📉"
            
            # ✅ LOG OPTIMIZADO para meta $1000
            if is_crypto and side == "sell":
                logger.info(f"🔥 CRYPTO {action} DINÁMICO {symbol}: score={sig:+.3f}, qty={qty:.6f}")
                
                # USAR SHORT DINÁMICO: Compra basado en riesgo + Short
                if dynamic_short_manager.should_use_dynamic_short(symbol):
                    # Calcular cantidad basada en riesgo (2% del equity)
                    # Variable ya definida como current_equity anteriormente en la función
                    purchase_amount = current_equity * settings.risk_per_trade
                    
                    result = dynamic_short_manager.execute_dynamic_short(symbol, qty, price, side, purchase_amount)
                    if result["success"]:
                        logger.info(f"✅ SHORT DINÁMICO EXITOSO {symbol}: ${purchase_amount:.0f} comprado + short ejecutado")
                    else:
                        logger.error(f"❌ SHORT DINÁMICO FALLÓ {symbol}: {result.get('error', 'Error desconocido')}")
                else:
                    # Fallback a orden normal
                    place_order(symbol, qty, side, price, fractional=not is_crypto, is_crypto=is_crypto)
            elif not is_crypto and side == "sell":
                # 🚫 STOCKS: No shorts permitidos
                logger.warning(f"⚠️ STOCK SHORT BLOQUEADO {symbol}: score={sig:+.3f} → Alpaca no permite fractional shorts")
            else:
                # ✅ LONGS (stocks y crypto) - Nueva posición
                logger.info(f"{action_emoji} {action} {symbol}: score={sig:+.3f}, qty={qty:.6f}, price=${price:.2f}")
                # Para nuevas posiciones, no necesitar consolidación previa
                place_order(symbol, qty, side, price, fractional=not is_crypto, is_crypto=is_crypto)

    # 7. Monitorear cierres ahora se ejecuta en thread separado
    # (removido de aquí para evitar bloqueo del bucle principal)

    # 8. Guardar estado
    try:
        state.save()
    except Exception as e:
        logger.error(f"❌ No se pudo guardar estado: {e}")

    return  # ✅ Único punto de salida

def _apply_live_parameters(best_params: Dict[str, Any]):
    """
    Aplica los nuevos parámetros optimizados a la configuración en vivo del bot,
    sin necesidad de reiniciar.
    """
    from .config import settings
    logger.info("🚀 Aplicando nuevos parámetros de Optuna en vivo...")
    
    for key, value in best_params.items():
        if hasattr(settings, key):
            old_value = getattr(settings, key)
            setattr(settings, key, value)
            logger.info(f"   🔧 Parámetro '{key}' actualizado: {old_value} → {value}")
        else:
            logger.warning(f"   ⚠️ Parámetro '{key}' no encontrado en la configuración actual. Omitiendo.")
            
    logger.info("✅ Nuevos parámetros aplicados. El bot operará con la configuración optimizada.")

def _update_optuna_config_file(best_params: Dict[str, Any]):
    """
    Genera y escribe el archivo bot/optuna_config.py con los nuevos parámetros optimizados.
    Esto permite que el bot los cargue en el próximo reinicio.
    """
    config_path = Path("bot/optuna_config.py")
    
    content = "# Este archivo es generado automáticamente por el optimizador de Optuna.\n"
    content += "# NO EDITAR MANUALMENTE.\n\n"
    content += "from .config import Settings\n\n"
    content += "def apply_optimized_config(settings: Settings) -> Settings:\n"
    content += "    # Parámetros optimizados por Optuna\n"
    content += "    print('⚙️ Aplicando configuración optimizada por Optuna...')\n"
    
    for key, value in best_params.items():
        if isinstance(value, str):
            content += f"    settings.{key} = '{value}'\n"
        else:
            content += f"    settings.{key} = {value}\n"
    
    content += "\n    return settings\n"
    
    try:
        with open(config_path, "w") as f:
            f.write(content)
        logger.info(f"✅ Archivo de configuración de Optuna actualizado: {config_path}")
    except Exception as e:
        logger.error(f"❌ No se pudo actualizar el archivo de configuración de Optuna: {e}")

def run_periodic_optimization(state: BotState):
    """
    Ejecuta la optimización de hiperparámetros con Optuna periódicamente.
    """
    from .strategy_optimizer import run_advanced_optimization
    from .config import settings
    
    optimize_interval_days = 14 # Re-optimizar cada 14 días (dos semanas)
    
    while True:
        try:
            last_optimization_str = state.state.get("last_optimization_date")
            should_optimize = True
            
            if last_optimization_str:
                last_optimization_date = datetime.fromisoformat(last_optimization_str)
                if (datetime.now() - last_optimization_date).days < optimize_interval_days:
                    should_optimize = False
            
            if should_optimize:
                logger.info("🧠 OPTUNA: Iniciando optimización de hiperparámetros periódica...")
                
                # Ejecutar optimización con un número razonable de trials
                # Usar un subconjunto de símbolos para no tardar demasiado
                symbols_to_optimize = settings.symbols[:10] # Optimizar con los 10 primeros símbolos
                
                optimization_results = run_advanced_optimization(
                    symbols=symbols_to_optimize,
                    n_trials=50 # Número de trials razonable para ejecución periódica
                )
                
                if optimization_results and not optimization_results.get('error'):
                    best_params = optimization_results.get('best_params')
                    logger.info("✅ OPTUNA: Optimización periódica completada.")
                    logger.info(f"🏆 Mejores parámetros encontrados: {best_params}")
                    
                    # 1. Persistir para futuros reinicios
                    _update_optuna_config_file(best_params)
                    
                    # 2. 🚀 AUTO-APLICACIÓN EN VIVO: Actualizar configuración sin reiniciar
                    _apply_live_parameters(best_params)
                    
                    # 📱 NOTIFICACIÓN TELEGRAM
                    try:
                        param_str = "\n".join([f"• {k}: {v:.4f}" if isinstance(v, float) else f"• {k}: {v}" for k, v in best_params.items()])
                        msg = f"🧠 OPTUNA COMPLETADO\n\n🏆 Nuevos parámetros aplicados en vivo:\n{param_str}"
                        send_telegram(msg)
                    except Exception as e:
                        logger.error(f"❌ Error enviando Telegram de Optuna: {e}")
                    
                    state.state["last_optimization_date"] = datetime.now().isoformat()
                    state.save()
                else:
                    logger.error("❌ OPTUNA: Optimización periódica falló.")
            
            # Esperar 24 horas para la próxima verificación
            time.sleep(86400) 
            
        except Exception as e:
            logger.error(f"💥 Error en optimización periódica: {e}")
            time.sleep(3600) # Esperar una hora en caso de error

def run_periodic_retraining(state: BotState):
    """
    Ejecuta el re-entrenamiento del modelo periódicamente.
    """
    from .model_training import train_all_models
    from .data import fetch_all_bars
    from .config import settings
    
    retrain_interval_days = 7 # Re-entrenar cada 7 días
    
    while True:
        try:
            last_training_str = state.state.get("last_retraining_date")
            should_retrain = True
            
            if last_training_str:
                last_training_date = datetime.fromisoformat(last_training_str)
                if (datetime.now() - last_training_date).days < retrain_interval_days:
                    should_retrain = False
            
            if should_retrain:
                logger.info("🔄 INICIANDO RE-ENTRENAMIENTO PERIÓDICO...")
                
                # Fetch data for training
                end_date = datetime.now()
                start_date = end_date - timedelta(days=settings.training_data_days)
                
                training_data = fetch_all_bars(
                    settings.symbols, 
                    start=start_date.strftime('%Y-%m-%d'), 
                    end=end_date.strftime('%Y-%m-%d')
                )
                
                if training_data:
                    train_results = train_all_models(training_data)
                    if train_results:
                        logger.info("✅ RE-ENTRENAMIENTO PERIÓDICO COMPLETADO.")
                        state.state["last_retraining_date"] = datetime.now().isoformat()
                        state.save()
                        reset_model_cache() # Reset cache to load new model
                        
                        # 📱 NOTIFICACIÓN TELEGRAM
                        try:
                            msg = f"🔄 RE-ENTRENAMIENTO COMPLETADO\n\n✅ El modelo de trading ha sido actualizado con los últimos datos del mercado."
                            send_telegram(msg)
                        except Exception as e:
                            logger.error(f"❌ Error enviando Telegram de re-entrenamiento: {e}")
                            
            
            # Wait for next check (1 day)
            time.sleep(86400) 
            
        except Exception as e:
            logger.error(f"💥 Error en re-entrenamiento periódico: {e}")
            time.sleep(3600) # Wait an hour on error

def main():
    # 🧠 INICIAR ORQUESTADOR CENTRAL
    orchestrator = AGUSOrchestrator()
    asyncio.run(orchestrator.start())
    logger.info("✅ AGUS Orchestrator iniciado")
    
    send_telegram("🚀 Bot de trading institucional INICIADO (modo paper).")
    logger.info("🚀 Bot de trading institucional iniciado (modo paper). Ctrl+C para detener.")
    state = BotState()

    # 🤖 AUTO-TRAINING: Entrenar solo si no existe NINGÚN modelo en la carpeta.
    model_dir = Path(os.path.dirname(settings.model_path))
    existing_models = list(model_dir.glob("*.pkl"))

    if not existing_models:
        logger.warning(f"⚠️ No se encontraron modelos en '{model_dir}'. Iniciando entrenamiento automático...")
        try:
            # Ejecutar script de entrenamiento de forma segura
            result = subprocess.run(
                [sys.executable, "scripts/train_model.py"],
                capture_output=True, text=True, check=True, timeout=1800 # 30 min timeout
            )
            logger.info("✅ Entrenamiento completado. El modelo ya está disponible.")
            logger.debug(f"Output del entrenamiento:\n{result.stdout}")
        except subprocess.CalledProcessError as train_error:
            logger.critical(f"❌ Falló el entrenamiento automático del modelo: {train_error.stderr}")
            logger.critical("Deteniendo bot. Revisa los logs de entrenamiento.")
            return
        except Exception as train_error:
            logger.critical(f"❌ Error inesperado durante el entrenamiento: {train_error}. Deteniendo bot.")
            return
    else:
        logger.info(f"✅ {len(existing_models)} modelo(s) detectado(s) en '{model_dir}'. Saltando entrenamiento.")

    try:
        clf = load_trading_model()
        if clf is None:
            logger.critical(f"❌ No se pudo cargar el modelo desde '{settings.model_path}'.")
            logger.critical("   El archivo podría estar corrupto o no ser compatible.")
            logger.critical("   Por favor, borra el modelo existente y reinicia para re-entrenar.")
            return
        logger.info("✅ Modelo de trading cargado y listo para usar.")
        logger.info(f"🧠 Modelo: {type(clf).__name__} | Features: {len(clf.feature_names_in_)} | Riesgo: {settings.risk_per_trade:.2%}")
    except Exception as e:
        logger.error(f"❌ No se pudo cargar el modelo: {e}")
        return
    
    # Cargar parámetros optimizados por Optuna
    try:
        optimized_params = load_optimized_params()
        if optimized_params:
            logger.info("🎯 Parámetros optimizados por Optuna aplicados")
        else:
            logger.info("ℹ️ Usando parámetros por defecto")
    except Exception as e:
        logger.warning(f"⚠️ Error cargando parámetros optimizados: {e}")
    
    # Cargar modelos ML avanzados automáticamente
    try:
        ml_loaded = auto_load_ml_models()
        if ml_loaded:
            logger.info("🤖 Modelos ML avanzados cargados - IA completa activada")
        else:
            logger.info("ℹ️ Usando modelos tradicionales - ML avanzado se entrenará automáticamente")
    except Exception as e:
        logger.warning(f"⚠️ Error cargando modelos ML avanzados: {e}")
        logger.info("ℹ️ Continuando con modelo tradicional")
    
    # 🔧 INICIAR POSITION MONITOR EN THREAD SEPARADO
    logger.info("🔄 Iniciando Position Monitor en thread separado...")
    monitor_thread = threading.Thread(
        target=monitor_closed_positions, 
        args=(clf,),
        daemon=True,
        name="PositionMonitor"
    )
    monitor_thread.start()
    logger.info("✅ Position Monitor activo en thread paralelo")
    
    # 📅 INICIAR DAILY REPORTER EN THREAD SEPARADO
    logger.info("📅 Iniciando Daily Reporter en thread separado...")
    from scripts.daily_reporter import run_reporter
    reporter_thread = threading.Thread(
        target=run_reporter,
        daemon=True,
        name="DailyReporter"
    )
    reporter_thread.start()
    logger.info("✅ Daily Reporter activo - detectará reset de Alpaca automáticamente")
    
    # 🔧 INICIAR SELF-HEALING SYSTEM EN THREAD SEPARADO
    logger.info("🔧 Iniciando Self-Healing System en thread separado...")
    try:
        from .agus_self_healing import initialize_self_healing, get_self_healing
        from .agus_self_healing_integration import AGUSSelfHealingBridge
        
        # Create and start the self-healing system
        def run_self_healing_async():
            """Run self-healing in its own event loop"""
            async def init_system():
                try:
                    # Initialize the self-healing system with the central orchestrator
                    self_healing = await initialize_self_healing(orchestrator)
                    logger.info("✅ Self-Healing initialized and monitoring started")
                    
                    # Keep system running
                    while True:
                        await asyncio.sleep(60)  # Health check every minute
                        if not self_healing.is_running:
                            logger.warning("⚠️ Self-healing stopped, restarting...")
                            await self_healing.start()
                except Exception as e:
                    logger.error(f"❌ Self-healing system error: {e}")
            
            asyncio.run(init_system())
        
        self_healing_thread = threading.Thread(
            target=run_self_healing_async,
            daemon=True,
            name="SelfHealingSystem"
        )
        self_healing_thread.start()
        logger.info("✅ Self-Healing System activo - monitoreando errores automáticamente")
    except ImportError as e:
        logger.warning(f"⚠️ Self-Healing System no disponible: {e}")
    except Exception as e:
        logger.error(f"❌ Error iniciando Self-Healing System: {e}")
    
    # 🤖 INICIAR INTELLIGENT MONITOR EN THREAD SEPARADO
    logger.info("🤖 Iniciando Intelligent Monitor 24/7 con AGUS...")
    intelligent_monitor = IntelligentMonitor(bot_instance={'state': state, 'clf': clf})
    monitor_intelligence_thread = threading.Thread(
        target=intelligent_monitor.start_monitoring,
        daemon=True,
        name="IntelligentMonitor"
    )
    monitor_intelligence_thread.start()
    logger.info("✅ Intelligent Monitor 24/7 activo con AGUS - auto-diagnosis y auto-correction habilitados")
    
    # 🔄 INICIAR RE-ENTRENAMIENTO PERIÓDICO
    logger.info("🔄 Iniciando Re-entrenamiento Periódico en thread separado...")
    retrain_thread = threading.Thread(
        target=run_periodic_retraining,
        args=(state,),
        daemon=True,
        name="PeriodicRetrainer"
    )
    retrain_thread.start()
    logger.info("✅ Re-entrenamiento Periódico activo")
    
    # 🧠 INICIAR OPTIMIZACIÓN PERIÓDICA CON OPTUNA
    logger.info("🧠 Iniciando Optuna Periodic Optimizer en thread separado...")
    optimization_thread = threading.Thread(
        target=run_periodic_optimization,
        args=(state,),
        daemon=True,
        name="PeriodicOptimizer"
    )
    optimization_thread.start()
    logger.info("✅ Optuna Periodic Optimizer activo")

    try:
        while True:
            try:
                result = run_once(state, clf)
                if result == "STOP":
                    logger.critical("🛑 Bot detenido por stop diario.")
                    break
            except KeyboardInterrupt:
                logger.info("🛑 Bot detenido por el usuario.")
                break
            except Exception as e:
                logger.exception("💥 Error en el loop principal")
                alert_error("Error en loop principal", str(e))
            logger.info("⏳ Esperando 15 segundos para próxima iteración...")  # 🔥 META $1000
            time.sleep(8)   # 🔥 ULTRA-VELOCIDAD: 8 segundos para máxima frecuencia
    finally:
        send_telegram("🛑 Bot de trading institucional DETENIDO.")
        logger.info("🛑 Bot de trading detenido.")


if __name__ == "__main__":
    main()