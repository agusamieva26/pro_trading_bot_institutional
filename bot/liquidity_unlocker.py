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
from alpaca.data.enums import DataFeed

from .config import settings
from .util import logger, should_skip_realtime_pricing, get_cache_ttl_for_symbol
from .symbol_manager import symbol_manager
from .execution import get_available_cash, close_position
from .telegram import send_telegram


# Configuration
CASH_THRESHOLD = 200.0  # Trigger liquidity unlock when cash < $200
TARGET_UNLOCK_AMOUNT = 600.0  # Target to free up ~$600 per unlock event
MAX_UNLOCKS_PER_HOUR = 6  # Maximum positions to close per hour (increased for emergencies)
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

# Caché de precios mejorado con TTL dinámico
_price_cache = {}
_LAST_KNOWN_PRICES = {}  # Fallback cache for when real-time data fails

# 🔇 SPAM PREVENTION: Track which symbols have already shown warnings
_WARNED_SYMBOLS = set()  # Symbols that already showed "no cached price" warning
_MARKET_CLOSED_SYMBOLS = set()  # Track symbols outside market hours for grouped message


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
    """
    Obtiene el precio actual con manejo robusto de errores SIP y market hours.
    - Crypto: Obtiene precio 24/7
    - Stocks: Obtiene precio solo durante horario de mercado, usa cache fuera de horas
    - Añade feed='iex' para evitar errores SIP
    - Implementa fallback a último precio conocido
    """
    now = time.time()
    cache_key = f"{symbol}_price"
    cache_ttl = get_cache_ttl_for_symbol(symbol)
    
    # 1. Verificar cache con TTL dinámico
    if cache_key in _price_cache:
        price, timestamp = _price_cache[cache_key]
        if now - timestamp < cache_ttl:
            return price
    
    # 2. Skip real-time pricing para stocks fuera de horario
    if should_skip_realtime_pricing(symbol):
        # Usar último precio conocido para stocks después de horas
        if symbol in _LAST_KNOWN_PRICES:
            logger.debug(f"📊 {symbol}: Usando precio cached después de horas ${_LAST_KNOWN_PRICES[symbol]:.4f}")
            return _LAST_KNOWN_PRICES[symbol]
        else:
            # 🔇 RATE-LIMITED WARNING: Only warn once per symbol per session
            if symbol not in _WARNED_SYMBOLS:
                _WARNED_SYMBOLS.add(symbol)
                _MARKET_CLOSED_SYMBOLS.add(symbol)
                # Only log individual warnings for the first few symbols
                if len(_WARNED_SYMBOLS) <= 3:
                    logger.warning(f"⚠️ {symbol}: No hay precio cached disponible fuera de horario")
                elif len(_WARNED_SYMBOLS) == 4:
                    # Show consolidated message when we have 4+ symbols
                    symbols_list = ', '.join(sorted(_MARKET_CLOSED_SYMBOLS))
                    logger.warning(f"⚠️ Mercado cerrado - {len(_MARKET_CLOSED_SYMBOLS)} stocks sin precio en tiempo real: {symbols_list}")
            return None
    
    # 3. Obtener precio en tiempo real
    try:
        if symbol_manager.is_crypto(symbol):  # Cripto - 24/7
            request = CryptoBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=getattr(TimeFrame, 'Minute'),
                limit=1
            )
            bars = crypto_client.get_crypto_bars(request)
            
            bars_df = getattr(bars, 'df', None)
            if bars_df is None or bars_df.empty:
                logger.warning(f"⚠️ No hay datos de precio para {symbol} (cripto)")
                return _LAST_KNOWN_PRICES.get(symbol)  # Fallback
            price = float(bars_df.iloc[-1]["close"])
            
        else:  # Stocks - CON FEED IEX para evitar SIP errors
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=getattr(TimeFrame, 'Minute'),
                limit=1,
                feed=DataFeed.IEX  # 🔧 FIX: Añadir feed IEX para evitar errores SIP
            )
            bars = stock_client.get_stock_bars(request)
            
            bars_df = getattr(bars, 'df', None)
            if bars_df is None or bars_df.empty:
                logger.warning(f"⚠️ No hay datos IEX para {symbol} (posible mercado cerrado)")
                return _LAST_KNOWN_PRICES.get(symbol)  # Fallback
            
            df = bars_df
            if hasattr(df.index, 'levels'):  # MultiIndex
                df = df.reset_index()
            price = float(df.iloc[-1]["close"])
        
        # 4. Guardar en ambos caches
        _price_cache[cache_key] = (price, now)
        _LAST_KNOWN_PRICES[symbol] = price  # Fallback cache
        return price
        
    except Exception as e:
        error_msg = str(e)
        if "subscription does not permit querying recent SIP data" in error_msg:
            # SIP error específico - usar fallback sin spam de logs
            logger.warning(f"⚠️ SIP access denied para {symbol}, usando precio cached")
        else:
            # Otros errores
            logger.warning(f"⚠️ Error obteniendo precio de {symbol}: {e}")
        
        # Intentar fallback a último precio conocido
        if symbol in _LAST_KNOWN_PRICES:
            logger.debug(f"🔄 Fallback: {symbol} = ${_LAST_KNOWN_PRICES[symbol]:.4f}")
            return _LAST_KNOWN_PRICES[symbol]
        
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
        Uses market_value directly to avoid SIP data restrictions.
        """
        symbol = normalize_symbol(getattr(position, 'symbol', ''))
        qty = float(getattr(position, 'qty', 0))
        entry_price = float(getattr(position, 'avg_entry_price', 0))
        
        # 🔧 FIX: Use market_value directly instead of price lookup (avoids SIP restrictions)
        market_value = float(getattr(position, 'market_value', 0))
        unrealized_pl = float(getattr(position, 'unrealized_pl', 0))
        unrealized_plpc = float(getattr(position, 'unrealized_plpc', 0))
        
        # Calculate notional value (capital that would be freed) - use market_value directly
        notional_value = abs(market_value)
        
        # Use unrealized P&L data directly from position
        pnl = unrealized_pl
        pnl_pct = unrealized_plpc
        
        # Get position age
        age_minutes = _get_position_age_minutes(symbol, position_times)
        
        # 🚨 CAPITAL-FIRST SCORING ALGORITHM - PRIORITIZE LARGE POSITIONS
        # Skip micro-positions that won't free meaningful capital
        MIN_CAPITAL_THRESHOLD = 50.0  # Don't close positions < $50
        if notional_value < MIN_CAPITAL_THRESHOLD:
            logger.debug(f"⚠️ Omitiendo micro-posición {symbol}: ${notional_value:.2f} < ${MIN_CAPITAL_THRESHOLD}")
            return None
        
        weakness_score = 0.0
        reasons = []
        
        # 1. CAPITAL SIZE (70% of score) - MOST IMPORTANT
        # Heavily prioritize larger positions that free more capital
        if notional_value >= 500:
            capital_score = min(notional_value / 50, 100)  # Up to 100 points for large positions
            weakness_score += capital_score * 0.7
            reasons.append(f"CAPITAL ALTO ${notional_value:.0f}")
        elif notional_value >= 200:
            capital_score = notional_value / 100  # Medium positions
            weakness_score += capital_score * 0.7
            reasons.append(f"capital medio ${notional_value:.0f}")
        elif notional_value >= 100:
            capital_score = notional_value / 200  # Small but acceptable
            weakness_score += capital_score * 0.7
            reasons.append(f"capital pequeño ${notional_value:.0f}")
        else:
            # Still above threshold but small
            capital_score = 1  # Minimal score for small positions
            weakness_score += capital_score
            reasons.append(f"capital mínimo ${notional_value:.0f}")
        
        # 2. P&L Performance (20% of score) - Secondary consideration
        if pnl_pct < -0.01:  # Losing > 1%
            pnl_penalty = abs(pnl_pct) * 50  # Moderate penalty for losses
            weakness_score += pnl_penalty * 0.2
            reasons.append(f"pérdida {pnl_pct:.2%}")
        elif pnl_pct < 0.005:  # Small gains < 0.5%
            stagnant_penalty = 5  # Small penalty for stagnation
            weakness_score += stagnant_penalty * 0.2
            reasons.append("ganancias mínimas")
        
        # 3. Time Factor (10% of score) - Minor consideration
        if age_minutes > 60:  # Very old positions
            time_penalty = (age_minutes - 60) / 120  # Scale by hours over 1 hour
            weakness_score += time_penalty * 10
            reasons.append(f"muy antigua {age_minutes:.0f}min")
        elif age_minutes > 30:
            time_penalty = (age_minutes - 30) / 180
            weakness_score += time_penalty * 5
            reasons.append(f"antigua {age_minutes:.0f}min")
        
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
        Select 2-3 largest positions to close, targeting $600+ capital unlock.
        Priority: CAPITAL SIZE first, then weakness score.
        """
        # Score all positions (excludes micro-positions automatically)
        scored_positions = []
        for pos in positions:
            weakness = self._calculate_position_weakness(pos, position_times)
            if weakness:  # Will be None for micro-positions < $50
                scored_positions.append(weakness)
        
        if not scored_positions:
            logger.warning("⚠️ No se encontraron posiciones válidas (todas < $50) para liquidity unlock")
            return []
        
        # Log all candidates with their capital amounts
        logger.info(f"💰 EVALUANDO {len(scored_positions)} posiciones para liquidity unlock:")
        for pos in scored_positions:
            logger.info(f"  📊 {pos.symbol}: ${pos.notional_value:.0f} capital, {pos.pnl_pct:+.2%} P&L, score={pos.weakness_score:.1f}")
        
        # PRIORITY 1: Sort by CAPITAL SIZE first (largest positions first)
        scored_positions.sort(key=lambda x: x.notional_value, reverse=True)
        
        # PRIORITY 2: Among large positions, prefer those with poor performance
        large_positions = [p for p in scored_positions if p.notional_value >= 200]
        medium_positions = [p for p in scored_positions if 100 <= p.notional_value < 200]
        small_positions = [p for p in scored_positions if p.notional_value < 100]
        
        # Sort each group by weakness score
        large_positions.sort(key=lambda x: x.weakness_score, reverse=True)
        medium_positions.sort(key=lambda x: x.weakness_score, reverse=True)
        small_positions.sort(key=lambda x: x.weakness_score, reverse=True)
        
        # Rebuild list: large positions first, then medium, then small
        prioritized_positions = large_positions + medium_positions + small_positions
        
        # Select positions to close
        selected = []
        total_capital = 0.0
        
        for weak_pos in prioritized_positions:
            if len(selected) >= 3:  # Max 3 positions per unlock (increased from 2)
                break
                
            if total_capital >= TARGET_UNLOCK_AMOUNT and len(selected) >= 2:  # Target reached with at least 2
                break
                
            selected.append(weak_pos)
            total_capital += weak_pos.notional_value
            
            logger.critical(f"🎯 SELECCIONADO PARA CIERRE: {weak_pos.symbol} liberará ${weak_pos.notional_value:.0f} capital "
                          f"(P&L actual: ${weak_pos.pnl:+.2f} / {weak_pos.pnl_pct:+.2%}, score: {weak_pos.weakness_score:.1f})")
        
        logger.critical(f"💰 TOTAL CAPITAL A LIBERAR: ${total_capital:.0f} de {len(selected)} posiciones (objetivo: ${TARGET_UNLOCK_AMOUNT:.0f})")
        
        # Show what will be closed
        if selected:
            logger.critical("📋 RESUMEN DE POSICIONES A CERRAR:")
            for i, pos in enumerate(selected, 1):
                logger.critical(f"  {i}. {pos.symbol}: ${pos.notional_value:.0f} capital, P&L ${pos.pnl:+.2f} ({pos.pnl_pct:+.2%})")
        return selected
    
    def _execute_liquidity_unlock(self, positions_to_close: List[PositionWeakness], current_cash: float):
        """Execute the liquidity unlock by closing selected positions."""
        total_freed_capital = 0.0
        closed_positions = []
        failed_positions = []
        
        logger.critical(f"💰 LIQUIDITY UNLOCK INICIADO: Cash crítico ${current_cash:.2f} < ${CASH_THRESHOLD}")
        
        for weak_pos in positions_to_close:
            try:
                logger.critical(f"🚨 CERRANDO POSICIÓN: {weak_pos.symbol} "
                               f"Capital=${weak_pos.notional_value:.0f} P&L=${weak_pos.pnl:+.2f} ({weak_pos.pnl_pct:+.2%}) "
                               f"Score={weak_pos.weakness_score:.1f} ({weak_pos.reason})")
                
                success = close_position(weak_pos.symbol, force_close=False)
                
                if success:
                    total_freed_capital += weak_pos.notional_value
                    closed_positions.append(weak_pos)
                    logger.critical(f"✅ CAPITAL LIBERADO: {weak_pos.symbol} cerrado exitosamente - "
                                  f"${weak_pos.notional_value:.0f} capital liberado (P&L final: ${weak_pos.pnl:+.2f})")
                else:
                    failed_positions.append(weak_pos)
                    logger.warning(f"⚠️ FALLO AL CERRAR: {weak_pos.symbol} - ${weak_pos.notional_value:.0f} NO liberados (PDT/balance/error)")
                    
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