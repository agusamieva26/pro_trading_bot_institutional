# bot/strategy.py
import numpy as np
import pandas as pd
import os
import joblib
from bot.util import logger
from sklearn.ensemble import RandomForestClassifier
from joblib import dump
from .features import make_features
from .config import settings
_trading_model_instance = None

# =========================
# 📊 Análisis de Fibonacci
# =========================

def calculate_fibonacci_levels(df, period=50):
    """
    Calcula niveles de retracción de Fibonacci basados en los últimos 'period' períodos.
    Retorna dict con niveles de soporte y resistencia.
    """
    if len(df) < period:
        return {'support': 0, 'resistance': 0, 'trend': 0}
    
    # Obtener high y low del período
    recent_data = df.tail(period)
    high_price = recent_data['high'].max()
    low_price = recent_data['low'].min()
    current_price = df['close'].iloc[-1]
    
    # Niveles de Fibonacci clásicos
    price_range = high_price - low_price
    if price_range == 0:
        return {'support': 0, 'resistance': 0, 'trend': 0}
    
    # Niveles de retracimiento más importantes
    fib_levels = {
        'level_236': high_price - (price_range * 0.236),
        'level_382': high_price - (price_range * 0.382), 
        'level_500': high_price - (price_range * 0.500),
        'level_618': high_price - (price_range * 0.618),
        'level_786': high_price - (price_range * 0.786)
    }
    
    # Determinar soporte y resistencia más cercanos
    levels_array = list(fib_levels.values())
    levels_array.extend([high_price, low_price])
    levels_array.sort()
    
    # Encontrar el nivel de soporte (por debajo del precio actual)
    support_level = low_price
    for level in levels_array:
        if level < current_price:
            support_level = level
        else:
            break
    
    # Encontrar el nivel de resistencia (por encima del precio actual) 
    resistance_level = high_price
    for level in reversed(levels_array):
        if level > current_price:
            resistance_level = level
        else:
            break
    
    # Calcular señales normalizadas
    # Distancia al soporte (positivo si está cerca del soporte)
    support_signal = max(0, 1 - (current_price - support_level) / price_range) if price_range > 0 else 0
    
    # Distancia a la resistencia (negativo si está cerca de la resistencia)
    resistance_signal = max(0, 1 - (resistance_level - current_price) / price_range) if price_range > 0 else 0
    
    # Tendencia general basada en posición en el rango Fibonacci
    position_in_range = (current_price - low_price) / price_range if price_range > 0 else 0.5
    
    # Señal de tendencia: +1 si está en zona alta (>0.618), -1 si está en zona baja (<0.382)
    if position_in_range > 0.618:
        trend_signal = (position_in_range - 0.618) / 0.382  # Normalizado 0-1
    elif position_in_range < 0.382:
        trend_signal = -(0.382 - position_in_range) / 0.382  # Normalizado 0 a -1
    else:
        trend_signal = 0  # Zona neutral
    
    return {
        'support': float(np.clip(support_signal, 0, 1)),
        'resistance': float(np.clip(-resistance_signal, -1, 0)),  # Negativo para resistencia
        'trend': float(np.clip(trend_signal, -1, 1))
    }

def add_fibonacci_features(df):
    """
    Añade features de Fibonacci al DataFrame.
    """
    if len(df) < 50:
        df['fib_support'] = 0.0
        df['fib_resistance'] = 0.0  
        df['fib_trend'] = 0.0
        return df
    
    # Calcular niveles para cada fila (usando ventana móvil)
    fib_support = []
    fib_resistance = []
    fib_trend = []
    
    for i in range(len(df)):
        if i < 49:  # No hay suficientes datos
            fib_support.append(0.0)
            fib_resistance.append(0.0)
            fib_trend.append(0.0)
        else:
            # Usar los últimos 50 períodos hasta la fila actual
            subset = df.iloc[max(0, i-49):i+1]
            fib_data = calculate_fibonacci_levels(subset)
            fib_support.append(fib_data['support'])
            fib_resistance.append(fib_data['resistance']) 
            fib_trend.append(fib_data['trend'])
    
    df['fib_support'] = fib_support
    df['fib_resistance'] = fib_resistance
    df['fib_trend'] = fib_trend
    
    return df

# Lista de features que el modelo espera (deben coincidir con make_features)
FEATURES = [
    "ret_1", "ema_12", "ema_26", "rsi_14",
    "macd", "macd_sig", "macd_hist", "atr_14", "vol_roll",
    "fib_support", "fib_resistance", "fib_trend"
]


def rule_signal(row):
    """
    Señal basada en cruce de EMA + RSI + volatilidad + Fibonacci.
    Devuelve una señal entre -1.0 y +1.0 (no binaria).
    """
    # Tendencia
    ema_trend = 1.0 if row["ema_12"] > row["ema_26"] else -1.0
    
    # Momento
    if row["rsi_14"] > 70:
        rsi_signal = -1.0
    elif row["rsi_14"] < 30:
        rsi_signal = +1.0
    else:
        rsi_signal = 0.0
    
    # Confirmación de precio
    price_momentum = 1.0 if row["close"] > row["ema_26"] else -1.0
    
    # Señales de Fibonacci (si están disponibles)
    fib_signal = 0.0
    if 'fib_support' in row and 'fib_resistance' in row and 'fib_trend' in row:
        # Cerca del soporte = señal alcista
        # Cerca de resistencia = señal bajista  
        # Tendencia Fibonacci refuerza la dirección
        fib_signal = (row['fib_support'] * 1.5 +  # Soporte es bullish
                     row['fib_resistance'] * -1.5 +  # Resistencia es bearish (invertir signo)
                     row['fib_trend'] * 0.8)  # Tendencia general
        fib_signal = np.clip(fib_signal, -1.0, 1.0)
    
    # Combinar señales con pesos (reducir peso tradicional para dar espacio a Fibonacci)
    signal = (0.35 * ema_trend + 
              0.25 * rsi_signal + 
              0.15 * price_momentum +
              0.25 * fib_signal)  # 25% peso para Fibonacci
    
    # Ajustar por volatilidad: menos confianza si ATR es alto
    atr_ratio = row["atr_14"] / row["close"]
    if atr_ratio > 0.03:  # >3% de volatilidad diaria
        signal *= 0.5  # Reducir confianza
    
    return np.clip(signal, -1.0, 1.0)  # Normalizar


def prepare_xy(df: pd.DataFrame):
    """
    Prepara X e y para entrenamiento.
    y = 0 (SELL), 1 (HOLD), 2 (BUY) basado en retorno futuro
    """
    # For training, use default symbol since this is combined data from multiple symbols
    feats = make_features(df, symbol="TRAINING_DATA")
    feats = feats.dropna(subset=FEATURES + ["close"])
    
    # Usar retorno futuro con 3 clases
    future_ret = feats["close"].shift(-1) / feats["close"] - 1
    
    # ✅ ARREGLO: 3 clases para ensemble model
    y = np.where(future_ret < -0.01, 0,      # SELL si baja >1%
          np.where(future_ret > 0.01, 2, 1)) # BUY si sube >1%, sino HOLD
    
    X = feats[FEATURES]
    return X, y


def train_model(df: pd.DataFrame):
    """Entrena el modelo y lo guarda."""
    X, y = prepare_xy(df)
    if X.empty or len(X) < 100:
        logger.error("❌ No hay suficientes datos para entrenar.")
        return None

    # 🎯 REPRODUCIBILIDAD: Seed fijo para entrenamientos determinísticos
    import hashlib
    # Seed basado en contenido de datos, no en tiempo
    data_hash = hashlib.md5(str(sorted(X.columns.tolist())).encode()).hexdigest()[:8]
    fixed_seed = int(data_hash, 16) % 2**31
    
    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        random_state=fixed_seed,  # 🔥 SEED DETERMINÍSTICO basado en datos
        n_jobs=-1,
        class_weight="balanced"
    )
    clf.fit(X, y)
    
    # Guardar modelo
    os.makedirs(os.path.dirname(settings.model_path), exist_ok=True)
    dump(clf, settings.model_path)
    logger.info(f"✅ Modelo entrenado y guardado en {settings.model_path}")
    return clf


def load_trading_model():
    """Carga el modelo desde disco."""
    global _trading_model_instance
    if _trading_model_instance is not None:
        return _trading_model_instance
    if not os.path.exists(settings.model_path):
        logger.warning(f"⚠️ No se encontró el modelo en {settings.model_path}")
        return None

    try:
        model = joblib.load(settings.model_path)
        if hasattr(model, 'feature_names_in_'):
            missing = set(FEATURES) - set(model.feature_names_in_)
            if missing:
                logger.error(f"❌ Modelo espera features que faltan: {missing}")
                return None
        else:
            logger.warning("⚠️ Modelo no tiene 'feature_names_in_'. Podría causar errores.")
        
        _trading_model_instance = model
        logger.info(f"✅ Modelo cargado correctamente. Usa {len(FEATURES)} features.")
        return model
    except Exception as e:
        logger.error(f"❌ No se pudo cargar el modelo: {e}")
        return None


_last_signals = {}

def reset_signal_memory():
    """Resetea la memoria de señales para permitir recálculo limpio"""
    global _last_signals
    _last_signals.clear()
    logger.info("🔄 Memoria de señales reseteada - permitiendo recálculo limpio")

def hybrid_signal(features, model=None, timeframe=None):
    """
    Genera señal híbrida:
    - Si el modelo está disponible: combina predicción + reglas
    - Si no: usa solo reglas
    Retorna: float entre -1.0 (fuerte venta) y +1.0 (fuerte compra)
    """
    model = model or _trading_model_instance
    if model is None:
        logger.warning("⚠️ No hay modelo cargado. Usando solo reglas.")
        return rule_signal(features)

    try:
        # Preparar input
        try:
            if isinstance(features, pd.Series):
                data_row = {col: features[col] for col in FEATURES}
                X = pd.DataFrame([data_row])
            elif isinstance(features, dict):
                data_row = {col: features[col] for col in FEATURES}
                X = pd.DataFrame([data_row])
            elif isinstance(features, pd.DataFrame):
                X = features[FEATURES].copy()
            else:
                logger.error(f"❌ Tipo no soportado: {type(features)}")
                return 0.0
        except KeyError as e:
            logger.error(f"❌ Feature faltante: {e}")
            return rule_signal(features)

        if pd.isna(X).any().any():
            logger.warning("⚠️ Input contiene NaN. Usando solo reglas.")
            return rule_signal(features)

        # Predicción del modelo
        proba = model.predict_proba(X)[0]  # [P(0), P(1), P(2)] para SELL/HOLD/BUY
        if len(proba) == 3:  # 3 clases: SELL(0), HOLD(1), BUY(2)
            model_signal = float(proba[2] - proba[0])  # BUY - SELL probabilidad
        else:  # Fallback por si hay modelo binario
            model_signal = float(proba[1] - proba[0])

        # Señal de reglas
        rule_sig = rule_signal(features)

        # 🔎 DEBUG: ver valores sin redondeo
        logger.debug(f"🔧 [hybrid_signal] proba={proba.tolist()} | model_signal={model_signal:.6f} | rule_signal={rule_sig:.6f}")

        # Combinar con pesos (modelo 70%, reglas 30%)
        combined_signal = 0.7 * model_signal + 0.3 * rule_sig

        # Ajustar por volatilidad
        if "atr_14" in features and "close" in features:
            atr_ratio = features["atr_14"] / features["close"]
            if atr_ratio > 0.08:
                combined_signal *= 0.7

        current_signal = float(np.clip(combined_signal, -1.0, 1.0))

        # 🎯 FILTRO DE ESTABILIDAD: Sin sesgo artificial - mantener integridad de señal
        symbol = features.get("symbol", f"UNK_{hash(str(features))%10000}")
        
        # Aplicar solo clipping sin ruido artificial 
        current_signal = float(np.clip(current_signal, -1.0, 1.0))
        
        # Filtro de estabilidad con clave por (symbol, timeframe) para evitar cross-talk
        tf_key = f"{symbol}:{timeframe or 'default'}"
        last_signal = _last_signals.get(tf_key)
        if last_signal is not None:
            if abs(current_signal - last_signal) < 0.03:  # 🔥 REDUCIDO: 0.15 → 0.03 (5x más restrictivo)
                logger.debug(f"🔧 [hybrid_signal] {tf_key}: Señal estable → mantener {last_signal:.6f}")
                current_signal = last_signal
            else:
                logger.debug(f"🆕 [hybrid_signal] {tf_key}: Nueva señal {current_signal:.6f} (cambio: {abs(current_signal - last_signal):.6f})")

        _last_signals[tf_key] = current_signal
        return current_signal

    except Exception as e:
        logger.error(f"❌ Error en señal híbrida: {e}")
        sig = rule_signal(features)
        logger.debug(f"🔧 [hybrid_signal] Fallback a reglas: {sig:.6f}")
        return sig

def generate_signals(market_data, model=None):
    """
    Genera señales de trading para cada símbolo en market_data.
    """
    signals = []
    logger.info(f"📊 Generando señales para {len(market_data)} símbolos")
    for symbol, df in market_data.items():
        logger.info(f"🔎 {symbol}: {len(df)} filas de datos")
        if df.empty:
            logger.warning(f"⚠️ Sin datos para {symbol}")
            continue
        try:
            last_row = df.iloc[-1].copy()
            last_row["symbol"] = symbol

            # 🔍 DEBUG: Ver features en detalle + verificar unicidad
            try:
                features_dict = {f: float(last_row[f]) for f in FEATURES}
                features_hash = hash(str(sorted(features_dict.items())))
                logger.debug(f"🧪 [{symbol}] features_hash: {features_hash}, unique_features: {len(set(features_dict.values()))}")
                if len(set(features_dict.values())) < len(FEATURES) / 2:
                    logger.warning(f"⚠️ [{symbol}] Demasiadas features duplicadas - posible problema de datos")
            except Exception as e:
                logger.error(f"❌ No se pudieron loggear las features de {symbol}: {e}")

            score = hybrid_signal(last_row, model)

            # Determinar BUY / SELL / HOLD
            if score > 0.2:
                action = "BUY"
            elif score < -0.2:
                action = "SELL"
            else:
                action = "HOLD"

            signals.append({
                "symbol": symbol,
                "score": float(score),
                "signal": action
            })
            logger.info(f"📈 Señal {symbol}: {action} ({score:+.2f})")
        except Exception as e:
            logger.error(f"❌ Error generando señal para {symbol}: {e}")
    return signals
    
# =========================
# 📊 Asignación de capital
# =========================

def allocate_positions(signals, equity, max_exposure=0.3, max_allocation_per_asset=0.5):
    """
    Distribuye capital entre activos según la fuerza de la señal.

    :param signals: Lista de señales [{'symbol': 'BTCUSD', 'signal': 'BUY', 'score': 0.75}, ...]
    :param equity: Capital total de la cuenta
    :param max_exposure: Porcentaje máximo de equity a usar (0.3 = 30%)
    :param max_allocation_per_asset: Límite por activo (0.5 = máx. 50% del equity en uno solo)
    :return: Lista de asignaciones [{'symbol': 'BTCUSD', 'allocation': 1234.56, 'signal': 'BUY', 'score': 0.75}, ...]
    """
    if not signals:
        return []

    # Filtra señales válidas (con score y signal coherentes)
    ranked = sorted(
        [s for s in signals if "score" in s and s["signal"] in ("BUY", "SELL")],
        key=lambda x: x["score"],
        reverse=True
    )

    total_score = sum(s["score"] for s in ranked) or 1.0
    total_capital = equity * max_exposure

    allocations = []
    for s in ranked:
        weight = s["score"] / total_score
        alloc = min(weight * total_capital, equity * max_allocation_per_asset)
        allocations.append({
            "symbol": s["symbol"],
            "allocation": alloc,
            "signal": s["signal"],
            "score": s["score"],  # 👈 ***ESTO ES LO QUE TE FALTABA***
        })

    return allocations