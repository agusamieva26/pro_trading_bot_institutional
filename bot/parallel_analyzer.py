"""
Sistema de análisis paralelo ultra-rápido para maximizar rendimiento del bot.
Paraleliza análisis de features + señales + scoring para 300%+ velocidad.
"""

import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple
from .features import make_features
from .strategy import hybrid_signal
from .util import logger


def analyze_symbol(symbol_data: Tuple[str, pd.DataFrame, object]) -> Dict:
    """
    Analiza un símbolo completo: features + señal + score.
    Diseñado para ejecución paralela.
    """
    symbol, df, clf = symbol_data
    
    try:
        # Verificar datos mínimos
        if df.empty or len(df) < 50:
            return {"symbol": symbol, "error": "Sin datos suficientes"}
        
        # 1. Calcular features
        feats = make_features(df)
        latest = feats.iloc[-1]
        
        # 2. Calcular señal híbrida
        sig = hybrid_signal(latest, clf)
        
        # 3. Evaluación de score
        score_status = "🟢 FUERTE" if abs(sig) >= 0.2 else "🟡 MODERADA" if abs(sig) >= 0.1 else "🔴 DÉBIL"
        signal_direction = "🔺 ALCISTA" if sig > 0 else "🔻 BAJISTA" if sig < 0 else "➡️ NEUTRAL"
        
        return {
            "symbol": symbol,
            "signal": sig,
            "features": latest,
            "price": float(latest["close"]),
            "atr": float(latest["atr_14"]),
            "score_status": score_status,
            "signal_direction": signal_direction,
            "error": None
        }
        
    except Exception as e:
        logger.warning(f"⚠️ Error analizando {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


def parallel_signal_analysis(symbols_data: Dict[str, pd.DataFrame], clf, max_workers: int = 6) -> List[Dict]:
    """
    Análisis paralelo ultra-rápido de múltiples símbolos.
    
    Args:
        symbols_data: Dict {symbol: DataFrame} con datos de mercado
        clf: Modelo de ML entrenado
        max_workers: Número de hilos paralelos (default: 6)
    
    Returns:
        Lista de análisis de señales para cada símbolo
    """
    
    # Preparar datos para análisis paralelo
    analysis_tasks = []
    for symbol, df in symbols_data.items():
        if not df.empty:
            analysis_tasks.append((symbol, df, clf))
    
    if not analysis_tasks:
        logger.warning("⚠️ No hay datos para analizar")
        return []
    
    logger.info(f"🚀 Iniciando análisis paralelo de {len(analysis_tasks)} símbolos ({max_workers} hilos)")
    
    results = []
    
    # Ejecución paralela del análisis completo
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submeter todas las tareas
        futures = {executor.submit(analyze_symbol, task): task[0] for task in analysis_tasks}
        
        # Recopilar resultados conforme completan
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                result = future.result()
                results.append(result)
                
                # Log del resultado
                if result.get("error"):
                    logger.warning(f"⚠️ {symbol}: {result['error']}")
                else:
                    sig = result["signal"]
                    score_status = result["score_status"]
                    signal_direction = result["signal_direction"]
                    price = result["price"]
                    
                    logger.info(f"📊 {symbol}: SCORE={sig:+.3f} ({score_status} {signal_direction}) @ ${price:.2f}")
                    
            except Exception as e:
                logger.error(f"💥 Error procesando resultado de {symbol}: {e}")
                results.append({"symbol": symbol, "error": str(e)})
    
    # Filtrar solo resultados válidos
    valid_results = [r for r in results if not r.get("error")]
    error_count = len(results) - len(valid_results)
    
    logger.info(f"✅ Análisis paralelo completado: {len(valid_results)} éxitos, {error_count} errores")
    
    return valid_results


def filter_strong_signals(analysis_results: List[Dict], min_threshold: float = 0.05) -> List[Dict]:  # ⚡ SCALPING: Más agresivo
    """
    Filtra y ordena señales por fuerza, excluyendo señales débiles.
    """
    # Filtrar señales fuertes
    strong_signals = []
    for result in analysis_results:
        if not result.get("error") and abs(result["signal"]) >= min_threshold:
            strong_signals.append({
                "symbol": result["symbol"],
                "signal": result["signal"],
                "features": result["features"],
                "price": result["price"],
                "atr": result["atr"]
            })
            logger.info(f"✅ {result['symbol']}: INCLUIDO para trading")
        elif not result.get("error"):
            logger.info(f"⚠️ {result['symbol']}: Score débil, no se opera")
    
    # Ordenar por fuerza de señal (descendente)
    strong_signals.sort(key=lambda x: abs(x["signal"]), reverse=True)
    
    logger.info(f"⚡ Análisis rápido: {len(strong_signals)}/{len(analysis_results)} señales fuertes")
    
    return strong_signals


# Cache para posiciones (evitar múltiples API calls)
_positions_cache = {"data": None, "timestamp": 0, "ttl": 10}  # 10 segundos TTL

def get_cached_positions(client):
    """
    Cache inteligente para posiciones, evita llamadas redundantes a la API.
    """
    import time
    
    current_time = time.time()
    
    # Verificar si cache está válido
    if (_positions_cache["data"] is not None and 
        current_time - _positions_cache["timestamp"] < _positions_cache["ttl"]):
        logger.debug("📋 Usando posiciones desde cache")
        return _positions_cache["data"]
    
    # Cache expirado, obtener datos frescos
    try:
        positions = client.get_all_positions()
        _positions_cache["data"] = positions
        _positions_cache["timestamp"] = current_time
        logger.debug(f"🔄 Cache de posiciones actualizado ({len(positions)} posiciones)")
        return positions
    except Exception as e:
        logger.error(f"❌ Error obteniendo posiciones: {e}")
        # Retornar cache anterior si está disponible
        return _positions_cache["data"] or []