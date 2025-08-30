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
    """
    Carga el modelo de trading desde disco. Se asegura de que solo
    se cargue una vez (singleton).
    """
    global _trading_model_instance

    # ✅ Reutilizar el modelo si ya está en memoria
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
            logger.info(f"✅ Modelo cargado correctamente. Usa {len(model.feature_names_in_)} features.")
        else:
            logger.warning("⚠️ Modelo no tiene 'feature_names_in_'. Podría causar errores.")

        # 🔒 Guardamos en cache y devolvemos
        _trading_model_instance = model
        return _trading_model_instance

    except Exception as e:
        logger.error(f"❌ No se pudo cargar el modelo: {e}")
        return None



def hybrid_signal(features, model=None):
    """
    Genera señal híbrida:
    - Si el modelo está disponible: combina predicción + reglas
    - Si no: usa solo reglas
    Retorna: float entre -1.0 (fuerte venta) y +1.0 (fuerte compra)
    """
    from .strategy import load_trading_model  # asegura carga del modelo singleton

    # 🔹 Cargar modelo si no se pasa como argumento
    if model is None:
        model = load_trading_model()

    if model is None:
        logger.warning("⚠️ No hay modelo cargado. Usando solo reglas.")
        return rule_signal(features)

    try:
        # Preparar input para el modelo
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

        # Predicción del modelo (probabilidad)
        proba = model.predict_proba(X)[0]  # [P(0), P(1)]
        model_signal = proba[1] - proba[0]  # -1 a +1

        # Señal de reglas
        rule_sig = rule_signal(features)

        # Combinar con peso (modelo 70%, reglas 30%)
        combined_signal = 0.7 * model_signal + 0.3 * rule_sig

        # Ajustar por volatilidad
        if "atr_14" in features and "close" in features:
            atr_ratio = features["atr_14"] / features["close"]
            if atr_ratio > 0.05:  # alta volatilidad
                combined_signal *= 0.5

        # Normalizar
        current_signal = np.clip(combined_signal, -1.0, 1.0)

        # 🔹 Mantener estabilidad de la señal por símbolo
        symbol = features.get("symbol", "UNKNOWN")
        if "_last_signals" not in globals():
            global _last_signals
            _last_signals = {}

        if symbol in _last_signals:
            last_signal = _last_signals[symbol]
            # Solo cambia si la diferencia es significativa
            if (current_signal > 0.3 and last_signal > 0.1) or \
               (current_signal < -0.3 and last_signal < -0.1):
                _last_signals[symbol] = current_signal
                return current_signal
            elif abs(current_signal - last_signal) < 0.2:
                logger.debug(f"🔧 [hybrid_signal] Señal estable. Manteniendo {last_signal:.2f}")
                return last_signal

        _last_signals[symbol] = current_signal
        return current_signal

    except Exception as e:
        logger.error(f"❌ Error en señal híbrida: {e}")
        sig = rule_signal(features)
        logger.debug(f"🔧 [hybrid_signal] Fallback a reglas: {sig:.2f}")
        return sig

def precompute_model_signals(df: pd.DataFrame, model=None) -> pd.DataFrame:
    """
    Precalcula señales del modelo + híbridas para todo un DataFrame.
    Muchísimo más rápido que llamar hybrid_signal() en cada fila.
    """
    if model is None:
        model = load_trading_model()
    if model is None:
        logger.warning("⚠️ No hay modelo. Se usarán solo reglas.")
        df["rule_signal"] = df.apply(rule_signal, axis=1)
        df["model_signal"] = 0.0
        df["combined_signal"] = df["rule_signal"]
        return df

    feats = make_features(df).dropna(subset=FEATURES + ["close"])
    X = feats[FEATURES]

    # 🔹 Predicciones en batch
    probas = model.predict_proba(X)
    feats["model_signal"] = probas[:, 1] - probas[:, 0]

    # Señal basada en reglas
    feats["rule_signal"] = feats.apply(rule_signal, axis=1)

    # Combinar con peso 70/30
    feats["combined_signal"] = 0.7 * feats["model_signal"] + 0.3 * feats["rule_signal"]

    # Ajustar por volatilidad
    atr_ratio = feats["atr_14"] / feats["close"]
    feats.loc[atr_ratio > 0.05, "combined_signal"] *= 0.5

    # Normalizar
    feats["combined_signal"] = feats["combined_signal"].clip(-1.0, 1.0)

    return feats

