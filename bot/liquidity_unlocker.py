# bot/liquidity_unlocker.py
import json
import os
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from alpaca.trading.client import TradingClient
from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from .config import settings
from .util import logger
from .execution import get_available_cash, close_position
from .telegram import send_telegram


# Configuration
CASH_THRESHOLD = 200.0  # Trigger liquidity unlock when cash < $200
TARGET_UNLOCK_AMOUNT = 600.0  # Target to free up ~$600 per unlock event
MAX_UNLOCKS_PER_HOUR = 2  # Maximum positions to close per hour
UNLOCK_HISTORY_FILE = "bot/liquidity_unlock_history.json"
POSITION_TIMES_FILE = "bot/position_entry_times.json"


# Clientes para datos históricos
crypto_client = CryptoHistoricalDataClient(
    api_key=settings.alpaca_api_key,
    secret_key=settings.alpaca_secret_key
)

stock_client = StockHistoricalDataClient(
    api_key=settings.alpaca_api_key,
    secret_key=settings.alpaca_secret_key
)

# Caché de precios
_price_cache = {}
_CACHE_TTL = 5  # segundos


# ========= UTILITY FUNCTIONS (avoiding circular import) =========

def normalize_symbol(symbol: str) -> str:
    """Normalize symbol to consistent format."""
    if "/" in symbol:
        return symbol
    if symbol.endswith("USD"):
        base = symbol.replace("USD", "")
        return f"{base}/USD"
    return symbol


def _get_current_price(symbol: str) -> Optional[float]:
    """Get current price using 1-minute bars."""
    now = time.time()
    cache_key = f"{symbol}_price"
    if cache_key in _price_cache:
        price, timestamp = _price_cache[cache_key]
        if now - timestamp < _CACHE_TTL:
            return price

    try:
        if "/" in symbol:  # Crypto
            request = CryptoBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=getattr(TimeFrame, 'Minute'),
                limit=1
            )
            bars = crypto_client.get_crypto_bars(request)
            
            bars_df = getattr(bars, 'df', None)
            if bars_df is None or bars_df.empty:
                logger.warning(f"⚠️ No hay datos de precio para {symbol} (cripto)")
                return None
            price = float(bars_df.iloc[-1]["close"])
        else:  # Stocks
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=getattr(TimeFrame, 'Minute'),
                limit=1
            )
            bars = stock_client.get_stock_bars(request)
            
            bars_df = getattr(bars, 'df', None)
            if bars_df is None or bars_df.empty:
                logger.warning(f"⚠️ No hay datos de precio para {symbol} (probablemente mercado cerrado)")
                return None
            df = bars_df
            if hasattr(df.index, 'levels'):  # MultiIndex
                df = df.reset_index()
            price = float(df.iloc[-1]["close"])

        _price_cache[cache_key] = (price, now)
        return price
    except Exception as e:
        logger.error(f"❌ No se pudo obtener precio de {symbol}: {e}")
        return None


def _load_position_times() -> Dict:
    """Load position entry timestamps from file."""
    try:
        if os.path.exists(POSITION_TIMES_FILE):
            with open(POSITION_TIMES_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"⚠️ Error cargando position times: {e}")
    return {}


def _get_position_age_minutes(symbol: str, position_times: dict) -> float:
    """Return position age in minutes."""
    if symbol not in position_times:
        return 0.0
    age_seconds = time.time() - position_times[symbol]
    return age_seconds / 60.0


# ========= END UTILITY FUNCTIONS =========


@dataclass
class PositionWeakness:
    """Data class to score position weakness for liquidity unlock decisions."""
    symbol: str
    notional_value: float
    pnl: float
    pnl_pct: float
    age_minutes: float
    weakness_score: float
    reason: str


class LiquidityUnlocker:
    """
    Intelligent liquidity management system that automatically frees up capital
    by closing weak positions when cash falls below threshold.
    """
    
    def __init__(self):
        self.client = TradingClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            paper=(settings.mode == "paper")
        )
        self.unlock_history = self._load_unlock_history()
    
    def _load_unlock_history(self) -> List[Dict]:
        """Load unlock event history from file."""
        try:
            if os.path.exists(UNLOCK_HISTORY_FILE):
                with open(UNLOCK_HISTORY_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ Error cargando historial de unlocks: {e}")
        return []
    
    def _save_unlock_history(self):
        """Save unlock event history to file."""
        try:
            os.makedirs(os.path.dirname(UNLOCK_HISTORY_FILE), exist_ok=True)
            with open(UNLOCK_HISTORY_FILE, 'w') as f:
                json.dump(self.unlock_history, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Error guardando historial de unlocks: {e}")
    
    def _is_rate_limited(self) -> bool:
        """Check if we've exceeded max unlocks per hour."""
        current_time = time.time()
        one_hour_ago = current_time - 3600  # 1 hour in seconds
        
        # Count recent unlocks in the last hour
        recent_unlocks = [
            event for event in self.unlock_history
            if event.get('timestamp', 0) > one_hour_ago
        ]
        
        if len(recent_unlocks) >= MAX_UNLOCKS_PER_HOUR:
            logger.warning(f"⏰ Rate limit: {len(recent_unlocks)} unlocks en última hora ≥ {MAX_UNLOCKS_PER_HOUR}")
            return True
        return False
    
    def _calculate_position_weakness(self, position, position_times: Dict) -> Optional[PositionWeakness]:
        """
        Calculate weakness score for a position based on multiple factors.
        Higher score = weaker position = better candidate for closing.
        """
        symbol = normalize_symbol(getattr(position, 'symbol', ''))
        qty = float(getattr(position, 'qty', 0))
        entry_price = float(getattr(position, 'avg_entry_price', 0))
        current_price = _get_current_price(symbol)
        
        if not current_price:
            return None
        
        # Calculate P&L
        if qty > 0:  # LONG
            pnl = (current_price - entry_price) * qty
            pnl_pct = (current_price - entry_price) / entry_price
        else:  # SHORT
            pnl = (entry_price - current_price) * abs(qty)
            pnl_pct = (entry_price - current_price) / entry_price
        
        # Get position age
        age_minutes = _get_position_age_minutes(symbol, position_times)
        
        # Calculate notional value (capital that would be freed)
        notional_value = abs(qty) * current_price
        
        # 🎯 WEAKNESS SCORING ALGORITHM
        weakness_score = 0.0
        reasons = []
        
        # 1. P&L Performance (40% of score)
        if pnl_pct < -0.005:  # Losing > 0.5%
            pnl_penalty = abs(pnl_pct) * 100  # Convert to positive score
            weakness_score += pnl_penalty * 0.4
            reasons.append(f"pérdida {pnl_pct:.2%}")
        elif pnl_pct < 0.002:  # Small gains < 0.2%
            stagnant_penalty = 10  # Base penalty for stagnation
            weakness_score += stagnant_penalty * 0.4
            reasons.append("ganancias mínimas")
        
        # 2. Time Factor (30% of score)
        if age_minutes > 45:  # Position older than 45 minutes
            time_penalty = (age_minutes - 45) / 60  # Scale by hours over 45 min
            weakness_score += time_penalty * 30
            reasons.append(f"edad {age_minutes:.0f}min")
        elif age_minutes > 30:  # Moderately old
            time_penalty = (age_minutes - 30) / 60
            weakness_score += time_penalty * 15
            reasons.append(f"algo antigua {age_minutes:.0f}min")
        
        # 3. Capital Recovery Potential (20% of score)
        # Larger positions score higher as they free more capital
        if notional_value > 500:
            capital_bonus = min(notional_value / 100, 20)  # Cap at 20 points
            weakness_score += capital_bonus * 0.2
            reasons.append(f"capital alto ${notional_value:.0f}")
        
        # 4. Asset Type Preference (10% of score)
        # Slightly prefer closing stocks over crypto (PDT considerations)
        is_crypto = "/" in symbol
        if not is_crypto:  # Stocks
            weakness_score += 2  # Small bonus for stocks
            reasons.append("stock")
        
        reason = " + ".join(reasons) if reasons else "evaluación estándar"
        
        return PositionWeakness(
            symbol=symbol,
            notional_value=notional_value,
            pnl=pnl,
            pnl_pct=pnl_pct,
            age_minutes=age_minutes,
            weakness_score=weakness_score,
            reason=reason
        )
    
    def _select_positions_to_close(self, positions, position_times: Dict) -> List[PositionWeakness]:
        """
        Select 1-2 weakest positions to close, targeting ~$600 capital unlock.
        """
        # Score all positions
        scored_positions = []
        for pos in positions:
            weakness = self._calculate_position_weakness(pos, position_times)
            if weakness:
                scored_positions.append(weakness)
        
        if not scored_positions:
            logger.warning("⚠️ No se pudieron evaluar posiciones para liquidity unlock")
            return []
        
        # Sort by weakness score (highest = weakest = best to close)
        scored_positions.sort(key=lambda x: x.weakness_score, reverse=True)
        
        # Select positions to close
        selected = []
        total_capital = 0.0
        
        for weak_pos in scored_positions:
            if len(selected) >= 2:  # Max 2 positions per unlock
                break
                
            if total_capital >= TARGET_UNLOCK_AMOUNT:  # Target reached
                break
                
            selected.append(weak_pos)
            total_capital += weak_pos.notional_value
            
            logger.debug(f"📊 Candidato: {weak_pos.symbol} score={weak_pos.weakness_score:.1f} "
                        f"capital=${weak_pos.notional_value:.0f} P&L={weak_pos.pnl_pct:+.2%} "
                        f"({weak_pos.reason})")
        
        return selected
    
    def _execute_liquidity_unlock(self, positions_to_close: List[PositionWeakness], current_cash: float):
        """Execute the liquidity unlock by closing selected positions."""
        total_freed_capital = 0.0
        closed_positions = []
        failed_positions = []
        
        logger.critical(f"💰 LIQUIDITY UNLOCK INICIADO: Cash crítico ${current_cash:.2f} < ${CASH_THRESHOLD}")
        
        for weak_pos in positions_to_close:
            try:
                logger.info(f"🎯 Cerrando {weak_pos.symbol}: Score={weak_pos.weakness_score:.1f}, "
                           f"Capital=${weak_pos.notional_value:.0f}, P&L={weak_pos.pnl_pct:+.2%} ({weak_pos.reason})")
                
                success = close_position(weak_pos.symbol, force_close=False)
                
                if success:
                    total_freed_capital += weak_pos.notional_value
                    closed_positions.append(weak_pos)
                    logger.critical(f"✅ LIQUIDITY UNLOCK: {weak_pos.symbol} cerrado - "
                                  f"${weak_pos.notional_value:.0f} liberados (P&L: {weak_pos.pnl:+.2f})")
                else:
                    failed_positions.append(weak_pos)
                    logger.warning(f"⚠️ LIQUIDITY UNLOCK: {weak_pos.symbol} falló cierre (PDT/balance)")
                    
            except Exception as e:
                failed_positions.append(weak_pos)
                logger.error(f"❌ LIQUIDITY UNLOCK: Error cerrando {weak_pos.symbol}: {e}")
        
        # Log unlock event
        unlock_event = {
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat(),
            'trigger_cash': current_cash,
            'target_amount': TARGET_UNLOCK_AMOUNT,
            'positions_closed': len(closed_positions),
            'positions_failed': len(failed_positions),
            'capital_freed': total_freed_capital,
            'closed_symbols': [pos.symbol for pos in closed_positions],
            'failed_symbols': [pos.symbol for pos in failed_positions]
        }
        
        self.unlock_history.append(unlock_event)
        self._save_unlock_history()
        
        # Send Telegram notification
        if closed_positions:
            self._send_unlock_notification(unlock_event, closed_positions)
        
        # Final status
        if closed_positions:
            logger.critical(f"💰 LIQUIDITY UNLOCK COMPLETADO: {len(closed_positions)} posiciones cerradas, "
                          f"${total_freed_capital:.0f} capital liberado")
        else:
            logger.warning("⚠️ LIQUIDITY UNLOCK: Sin posiciones cerradas exitosamente")
        
        return len(closed_positions) > 0
    
    def _send_unlock_notification(self, unlock_event: Dict, closed_positions: List[PositionWeakness]):
        """Send Telegram notification about liquidity unlock event."""
        try:
            closed_symbols = [pos.symbol for pos in closed_positions]
            total_pnl = sum(pos.pnl for pos in closed_positions)
            
            message = f"""💰 LIQUIDITY UNLOCK EJECUTADO
            
🚨 Cash crítico: ${unlock_event['trigger_cash']:.2f} < ${CASH_THRESHOLD}

✅ Posiciones cerradas: {len(closed_positions)}
📊 Símbolos: {', '.join(closed_symbols)}
💵 Capital liberado: ${unlock_event['capital_freed']:.0f}
📈 P&L total: ${total_pnl:+.2f}

🎯 Objetivo: Mantener liquidez mínima para nuevas oportunidades"""
            
            send_telegram(message)
            logger.info("📱 Telegram: Notificación de liquidity unlock enviada")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación Telegram: {e}")
    
    def check_and_unlock_liquidity(self) -> bool:
        """
        Main entry point: Check cash levels and unlock liquidity if needed.
        Returns True if unlock was executed, False otherwise.
        """
        try:
            # 1. Check current cash
            available_cash, total_cash = get_available_cash()
            
            # 2. Check if unlock is needed
            if available_cash >= CASH_THRESHOLD:
                return False  # No unlock needed
            
            # 3. Check rate limiting
            if self._is_rate_limited():
                logger.warning(f"⏰ Liquidity unlock omitido: Rate limit alcanzado ({MAX_UNLOCKS_PER_HOUR}/hora)")
                return False
            
            # 4. Get positions and position times
            positions = self.client.get_all_positions()
            if not positions:
                logger.warning(f"⚠️ Cash crítico ${available_cash:.2f} pero sin posiciones para cerrar")
                return False
            
            position_times = _load_position_times()
            
            # 5. Select positions to close
            positions_to_close = self._select_positions_to_close(positions, position_times)
            if not positions_to_close:
                logger.warning(f"⚠️ Cash crítico ${available_cash:.2f} pero no se encontraron posiciones débiles")
                return False
            
            # 6. Execute unlock
            return self._execute_liquidity_unlock(positions_to_close, available_cash)
            
        except Exception as e:
            logger.error(f"❌ Error en liquidity unlock: {e}")
            return False
    
    def get_unlock_stats(self) -> Dict:
        """Get statistics about recent unlock events."""
        current_time = time.time()
        one_hour_ago = current_time - 3600
        
        recent_unlocks = [
            event for event in self.unlock_history
            if event.get('timestamp', 0) > one_hour_ago
        ]
        
        total_events = len(self.unlock_history)
        total_capital_freed = sum(event.get('capital_freed', 0) for event in self.unlock_history)
        
        return {
            'total_events': total_events,
            'recent_events_1h': len(recent_unlocks),
            'total_capital_freed': total_capital_freed,
            'rate_limit_remaining': max(0, MAX_UNLOCKS_PER_HOUR - len(recent_unlocks)),
            'last_unlock': self.unlock_history[-1] if self.unlock_history else None
        }


# Global instance
liquidity_unlocker = LiquidityUnlocker()