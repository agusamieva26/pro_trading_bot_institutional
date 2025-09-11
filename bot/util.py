from loguru import logger
import sys, os, json, datetime as dt
import pytz
from .config import settings

logger.remove()
logger.add(sys.stderr, level=settings.log_level)

def jdump(obj, path:str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)

def jload(path:str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default

def now_utc():
    return dt.datetime.now(dt.timezone.utc)

# ========= MARKET HOURS UTILITIES =========

def is_market_open() -> bool:
    """
    Check if US stock market is currently open.
    Market hours: Monday-Friday 9:30 AM - 4:00 PM ET
    """
    try:
        et_tz = pytz.timezone('US/Eastern')
        now_et = dt.datetime.now(et_tz)
        
        # Check if it's a weekday (0=Monday, 6=Sunday)
        if now_et.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
        
        # Check market hours (9:30 AM - 4:00 PM ET)
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= now_et <= market_close
    except Exception as e:
        logger.warning(f"⚠️ Error checking market hours: {e}, defaulting to CLOSED")
        return False

def is_crypto_symbol(symbol: str) -> bool:
    """Check if symbol is a cryptocurrency (contains / or ends with USD)."""
    return "/" in symbol or symbol.endswith("USD")

def should_skip_realtime_pricing(symbol: str) -> bool:
    """
    Determine if we should skip real-time pricing for this symbol.
    Returns True for stocks when market is closed.
    Always returns False for crypto (24/7 markets).
    """
    if is_crypto_symbol(symbol):
        return False  # Crypto markets are 24/7
    
    return not is_market_open()  # Skip stocks when market is closed

def get_cache_ttl_for_symbol(symbol: str) -> int:
    """
    Get appropriate cache TTL based on symbol type and market hours.
    - Crypto: 5 seconds (fast-moving 24/7)
    - Stocks during market hours: 10 seconds
    - Stocks after hours: 300 seconds (5 minutes)
    """
    if is_crypto_symbol(symbol):
        return 5  # Crypto: short TTL for fast updates
    
    if is_market_open():
        return 10  # Stocks during market: moderate TTL
    else:
        return 300  # Stocks after hours: long TTL (stale data is fine)
