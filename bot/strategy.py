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

# Lista de features que el modelo espera (deben coincidir con make_features)
FEATURES = [
    "ret_1", "ema_12", "ema_26", "rsi_14",
    "macd", "macd_sig", "macd_hist", "atr_14", "vol_roll"
]


def rule_signal(row):
    """
    Señal basada en cruce de EMA + RSI + volatilidad.
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
    
    # Combinar señales con pesos
    signal = 0.5 * ema_trend + 0.3 * rsi_signal + 0.2 * price_momentum
    
    # Ajustar por volatilidad: menos confianza si ATR es alto
    atr_ratio = row["atr_14"] / row["close"]
    if atr_ratio > 0.03:  # >3% de volatilidad diaria
        signal *= 0.5  # Reducir confianza
    
    return np.clip(signal, -1.0, 1.0)  # Normalizar


def prepare_xy(df: pd.DataFrame):
    """
    Prepara X e y para entrenamiento.
    y = 1 si el precio sube en la siguiente vela (1h)
    """
    feats = make_features(df)
    feats = feats.dropna(subset=FEATURES + ["close"])
    
    # Usar retorno futuro en lugar de binario simple
    future_ret = feats["close"].shift(-1) / feats["close"] - 1
    y = (future_ret > 0).astype(int)  # 1 si sube, 0 si baja
    
    X = feats[FEATURES]
    return X, y


def train_model(df: pd.DataFrame):
    """Entrena el modelo y lo guarda."""
    X, y = prepare_xy(df)
    if X.empty or len(X) < 100:
        logger.error("❌ No hay suficientes datos para entrenar.")
        return None

    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        random_state=42,
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
    global _trading_model_instance
    if _trading_model_instance is not None:
        return _trading_model_instance
    """Carga el modelo desde disco."""
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

def hybrid_signal(features, model=None):
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
        if isinstance(features, pd.Series):
            X = pd.DataFrame([features[FEATURES].values], columns=FEATURES)
        elif isinstance(features, dict):
            X = pd.DataFrame([features], columns=FEATURES)
        elif isinstance(features, pd.DataFrame):
            X = features[FEATURES]
        else:
            logger.error(f"❌ Tipo no soportado: {type(features)}")
            return 0.0

        if X.isna().any().any():
            logger.warning("⚠️ Input contiene NaN. Usando solo reglas.")
            return rule_signal(features)

        # Predicción del modelo
        proba = model.predict_proba(X)[0]  # [P(0), P(1)]
        model_signal = float(proba[1] - proba[0])  # rango -1 a +1

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

        # Filtro de estabilidad (simétrico)
        symbol = features.get("symbol", "UNKNOWN")
        last_signal = _last_signals.get(symbol)
        if last_signal is not None:
            if abs(current_signal - last_signal) < 0.15:
                logger.debug(f"🔧 [hybrid_signal] Señal estable → mantener {last_signal:.4f}")
                current_signal = last_signal

        _last_signals[symbol] = current_signal
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

            # 🔍 DEBUG: Ver features en detalle (por si alguna viene igual entre símbolos)
            try:
                features_dict = {f: float(last_row[f]) for f in FEATURES}
                logger.debug(f"🧪 [{symbol}] features: {features_dict}")
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