# bot/auto_tuner.py
import json
import os
import pandas as pd
from datetime import datetime, timedelta, timezone
from .config import settings
from .util import logger


AUTO_CONFIG_FILE = "bot/auto_config.json"
DEFAULT_CONFIG = {
    "risk_per_trade": 0.02,
    "max_gross_exposure": 0.5,
    "tp_multiplier": 2.0,
    "sl_multiplier": 1.5,
    "last_tune_time": None
}


def _load_auto_config():
    """Carga la configuración de auto-ajuste."""
    if not os.path.exists(AUTO_CONFIG_FILE):
        with open(AUTO_CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG.copy()

    try:
        with open(AUTO_CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"❌ Error al cargar auto_config.json: {e}")
        return DEFAULT_CONFIG.copy()


def _save_auto_config(config):
    """Guarda la configuración de auto-ajuste."""
    try:
        with open(AUTO_CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"❌ Error al guardar auto_config.json: {e}")


def _calculate_daily_pnl():
    """Calcula el P&L de las últimas 24 horas."""
    if not os.path.exists("trades_log.csv"):
        logger.warning("⚠️ No existe trades_log.csv")
        return 0.0, 0

    try:
        df = pd.read_csv("trades_log.csv")

        # ✅ Asegurar que sea una copia
        df = df.copy()

        if "exit_date" not in df.columns:
            logger.warning("⚠️ Columna 'exit_date' no encontrada en trades_log.csv")
            return 0.0, 0

        # ✅ Convertir a datetime con UTC
        df["exit_date"] = pd.to_datetime(df["exit_date"], errors="coerce", utc=True)

        # ✅ Eliminar filas con fechas inválidas
        df = df.dropna(subset=["exit_date"])

        # ✅ Cutoff con zona horaria
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)

        # ✅ Filtrar
        df_today = df[df["exit_date"] >= cutoff].copy()

        if df_today.empty:
            return 0.0, 0

        # ✅ Calcular P&L
        df_today["realized_pnl"] = pd.to_numeric(df_today["realized_pnl"], errors="coerce")
        total_pnl = df_today["realized_pnl"].sum()
        num_trades = len(df_today)

        return total_pnl, num_trades

    except Exception as e:
        logger.error(f"❌ Error al calcular P&L diario: {e}")
        return 0.0, 0


def tune_risk_parameters():
    """
    Ajusta automáticamente los parámetros de riesgo.
    """
    config = _load_auto_config()
    last_tune = config.get("last_tune_time")

    # ✅ Verificar si ya ha pasado el tiempo mínimo
    if last_tune:
        try:
            last_tune = datetime.fromisoformat(last_tune)
            now = datetime.now(timezone.utc)
            if now - last_tune < timedelta(minutes=30):
                logger.info("⏳ Auto-tune: aún no es hora de ajustar (cada 30 min)")
                return config
        except Exception as e:
            logger.error(f"❌ Error al parsear last_tune_time: {e}")

    # ✅ Calcular P&L
    pnl, num_trades = _calculate_daily_pnl()
    logger.info(f"📊 Auto-tuner: P&L últimas 24h = ${pnl:.2f} ({num_trades} trades)")

    # ✅ Ajustar risk_per_trade
    current_risk = config["risk_per_trade"]
    if pnl > 0:
        new_risk = min(current_risk * 1.1, 0.05)  # Hasta 5%
    elif pnl < 0:
        new_risk = max(current_risk * 0.9, 0.005)  # Mínimo 0.5%
    else:
        new_risk = current_risk

    # ✅ Ajustar exposición
    new_exp = new_risk * 10
    new_exp = max(0.2, min(new_exp, 2.0))

    # ✅ Actualizar config
    config["risk_per_trade"] = round(new_risk, 4)
    config["max_gross_exposure"] = round(new_exp, 2)
    config["last_tune_time"] = datetime.now(timezone.utc).isoformat()

    _save_auto_config(config)
    logger.info(
        f"✅ Auto-ajuste aplicado: risk_per_trade={new_risk:.2%}, "
        f"max_exposure={new_exp:.1f}x"
    )

    return config