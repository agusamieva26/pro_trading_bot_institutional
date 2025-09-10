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
    """DESHABILITADO: Ahora usamos Alpaca como fuente de verdad para daily change"""
    # Ya no necesitamos reset de medianoche - Alpaca maneja esto
    return False

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

            # DESHABILITADO: Reset automático - ahora usamos Alpaca
            # El daily change viene directamente de Alpaca (equity - last_equity)
            pass

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
    
    def get_daily_pnl_absolute(self, current_equity: float) -> float:
        """Calcula el P&L diario en valor absoluto"""
        start = self.state.get("daily_start_equity", INITIAL_EQUITY)
        return current_equity - start
    
    def update_daily_pnl(self, current_equity: float):
        """Actualiza el daily_pnl en estado"""
        daily_pnl = self.get_daily_pnl_absolute(current_equity)
        self.state["daily_pnl"] = daily_pnl

    def reset_daily_pnl(self, current_equity: float):
        """
        Reinicia manualmente el P&L diario.
        """
        logger.info(f"🔄 Punto de partida diario reiniciado a ${current_equity:,.2f}")
        self.state["daily_start_equity"] = current_equity
        self.state["last_reset_date"] = _now_cet().isoformat()
        self.save()