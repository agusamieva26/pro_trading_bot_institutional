# bot/state.py
import json
import os
from datetime import datetime, timezone
from .config import settings
from .util import logger

STATE_FILE = "bot/state.json"
INITIAL_EQUITY = settings.initial_equity

def _now_cet():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Madrid"))
    except ImportError:
        return datetime.now()  # Fallback

def _is_new_day(last_reset: str) -> bool:
    """Verifica si ha pasado a un nuevo día (CET/CEST)"""
    try:
        if not last_reset or last_reset.strip() == "":
            return True  # Si no hay fecha, asumimos nuevo día
        last = datetime.fromisoformat(last_reset)
        now = _now_cet()
        return now.date() > last.date()
    except Exception as e:
        logger.error(f"❌ Error al comparar fechas: {e}")
        return True  # Por seguridad, reinicia si hay error

class BotState:
    def __init__(self):
        self.state = self.load()

    def load(self):
        if not os.path.exists(STATE_FILE):
            logger.info("🆕 No se encontró estado. Usando valores iniciales.")
            now = _now_cet().isoformat()
            return {
                "equity": INITIAL_EQUITY,
                "daily_start_equity": INITIAL_EQUITY,
                "last_reset_date": now
            }

        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)

            # Validar y resetear si es nuevo día
            if _is_new_day(state.get("last_reset_date", "")):
                logger.info(f"🌅 Nuevo día detectado. Reiniciando P&L diario.")
                current_equity = state.get("equity", INITIAL_EQUITY)
                state["daily_start_equity"] = current_equity
                state["last_reset_date"] = _now_cet().isoformat()

            return state
        except Exception as e:
            logger.error(f"❌ No se pudo cargar estado: {e}")
            now = _now_cet().isoformat()
            return {
                "equity": INITIAL_EQUITY,
                "daily_start_equity": INITIAL_EQUITY,
                "last_reset_date": now
            }

    def save(self):
        try:
            with open(STATE_FILE, "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"❌ No se pudo guardar estado: {e}")

    def get_daily_pnl_pct(self, current_equity: float) -> float:
        start = self.state.get("daily_start_equity", INITIAL_EQUITY)
        if start <= 0:
            return 0.0
        return (current_equity / start) - 1

    def reset_daily_pnl(self, current_equity: float):
        """
        Reinicia manualmente el P&L diario.
        """
        logger.info(f"🔄 Punto de partida diario reiniciado a ${current_equity:,.2f}")
        self.state["daily_start_equity"] = current_equity
        self.state["last_reset_date"] = _now_cet().isoformat()
        self.save()