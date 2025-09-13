# bot/main.py
import logging
import time
import threading
import pandas as pd
from tenacity import retry, wait_exponential, stop_after_attempt
from alpaca.trading.client import TradingClient

from .auto_tuner import tune_risk_parameters
from .config import settings
from .data import fetch_bars, fetch_all_bars
from .features import make_features
from .strategy import load_trading_model, hybrid_signal, reset_signal_memory
from .advanced_ml import auto_load_ml_models, load_optimized_params
from .sizing import volatility_target_size, kelly_cap
from .execution import place_order, close_position
from .state import BotState
from .exposure import get_total_exposure
from .telegram import alert_risk_stop, alert_error
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
from .util import logger
import datetime as dt
import pytz


logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))


def is_stock_market_open() -> bool:
    """Devuelve True si el mercado de acciones de EE.UU. está abierto ahora."""
    eastern = pytz.timezone("US/Eastern")
    now = dt.datetime.now(eastern)

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
    
    if daily_change <= daily_loss_limit or daily_change_pct <= daily_loss_pct_limit:
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

    # 🧠 INTEGRACIÓN IA PERSONAL - Análisis cada 30min
    ai_analysis = {}
    try:
        from bot.news_integration import get_ai_market_analysis
        ai_analysis = await get_ai_market_analysis(settings.symbols[:10])  # Analizar top 10 símbolos
        
        if ai_analysis.get("ai_available") and ai_analysis.get("analysis"):
            analysis = ai_analysis["analysis"]
            logger.info(f"🧠 IA Personal activa - {len(analysis.get('signals', []))} señales generadas")
            
            # Log del sentiment general
            sentiment = analysis.get("sentiment", {})
            sentiment_score = sentiment.get("overall_sentiment", 0.0)
            logger.info(f"📰 Sentiment noticias: {sentiment_score:+.2f} ({sentiment.get('confidence', 0):.1%} confianza)")
            
    except Exception as e:
        logger.debug(f"IA Personal no disponible: {e}")

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
    
    # 📊 INTEGRACIÓN DE SENTIMENT: Ajustar por Fear & Greed Index
    sentiment_enhanced_signals = sentiment_integrator.enhance_signals_with_sentiment(mtf_enhanced_signals)
    
    # 🔄 REBALANCEO DE PORTFOLIO: Ajustar por diversificación
    portfolio_analysis = portfolio_rebalancer.analyze_current_portfolio(
        [{'symbol': getattr(pos, 'symbol', ''), 'market_value': getattr(pos, 'market_value', 0)} for pos in get_cached_positions(client)]
    )
    signals = portfolio_rebalancer.apply_rebalancing_to_signals(sentiment_enhanced_signals, portfolio_analysis)
    
    # 🛡️ CONFIGURACIÓN DINÁMICA: Adaptar a condiciones de mercado
    sentiment_level = sentiment_enhanced_signals[0].get('sentiment_level', 'neutral') if sentiment_enhanced_signals else 'neutral'
    dynamic_config_manager.adapt_to_market_conditions(market_condition, sentiment_level)

    logger.info(f"📈 Total señales detectadas: {len(signals)} de {len(other_symbols)} activos")

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
        
        # 🛡️ RISK MANAGEMENT 2.0: Cálculo avanzado con regímenes de mercado
        risk_manager = AdvancedRiskManager()
        symbol_regime = risk_environment["symbol_regimes"].get(symbol, {"regime": "neutral", "confidence": 0.5})
        symbol_vol = risk_environment["symbol_vol_conditions"].get(symbol, {"vol_regime": "normal", "vol_ratio": 1.0})
        
        # Calcular position size optimizado
        advanced_sizing = risk_manager.calculate_position_size_v2(
            equity=position_equity, price=price, atr=atr, signal_strength=sig,
            market_regime=symbol_regime, vol_clustering=symbol_vol
        )
        
        # Calcular stops dinámicos
        dynamic_stops = risk_manager.calculate_dynamic_stops(
            symbol=symbol, price=price, atr=atr, signal_strength=sig,
            market_regime=symbol_regime, vol_clustering=symbol_vol
        )
        
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
        
        # Usar sizing avanzado
        shares = advanced_sizing["shares"]
        leverage = max(min(abs(sig) * 0.8 + advanced_sizing["adjusted_risk_pct"] * 10, 1.0), 0.05)
        qty = shares * leverage
        
        # Actualizar stops dinámicos
        settings.stop_loss_pct = dynamic_stops["stop_loss_pct"]
        settings.take_profit_pct = dynamic_stops["take_profit_pct"]
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


def main():
    logger.info("🚀 Bot de trading institucional iniciado (modo paper). Ctrl+C para detener.")
    state = BotState()

    try:
        clf = load_trading_model()
        if clf is None:
            logger.critical("❌ No se pudo cargar el modelo. Deteniendo bot.")
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


if __name__ == "__main__":
    main()