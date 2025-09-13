import pandas as pd
import numpy as np
from typing import Optional

def ema(x: pd.Series, span:int): return x.ewm(span=span, adjust=False).mean()

def rsi(close: pd.Series, period:int=14):
    d = close.diff()
    up = d.clip(lower=0).rolling(period).mean()
    dn = -d.clip(upper=0).rolling(period).mean()
    rs = up / (dn + 1e-9)
    return 100 - (100/(1+rs))

def macd(close: pd.Series, fast:int=12, slow:int=26, signal:int=9):
    m = ema(close, fast) - ema(close, slow)
    s = ema(m, signal)
    return m, s, m - s

def atr(df: pd.DataFrame, period:int=14):
    h,l,c = df['high'], df['low'], df['close']
    tr = pd.concat([(h-l),(h-c.shift()).abs(),(l-c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def make_features(df: pd.DataFrame, symbol: Optional[str] = None) -> pd.DataFrame:
    out = df.copy()
    out["ret_1"] = out["close"].pct_change()
    
    # 🎯 DIVERSIFICACIÓN: EMAs variables por símbolo para reducir correlación
    # Priority: parameter > DataFrame attribute > default
    if symbol is None:
        symbol = getattr(df, 'symbol', 'BTC/USD')
    if symbol and isinstance(symbol, str):
        crypto_base = symbol.split('/')[0] if '/' in symbol else symbol.replace('USD', '')
    else:
        crypto_base = 'BTC'  # Default fallback
    
    # Períodos específicos por crypto para diversificar señales
    ema_periods = {
        'BTC': (12, 26), 'ETH': (10, 24), 'SOL': (14, 28), 'AVAX': (11, 25),
        'LINK': (13, 27), 'DOT': (12, 25), 'LTC': (10, 22), 'SHIB': (15, 30),
        'DOGE': (14, 29), 'XRP': (11, 23), 'UNI': (13, 26), 'AAVE': (15, 31),
        'PEPE': (16, 32), 'BCH': (10, 24), 'MKR': (14, 29), 'CRV': (13, 28), 'GRT': (12, 27)
    }
    
    fast, slow = ema_periods.get(crypto_base, (12, 26))
    # Ensure close_series is always a pandas Series
    close_col = out["close"]
    if isinstance(close_col, pd.Series):
        close_series: pd.Series = close_col
    else:
        close_series = pd.Series(close_col)
    
    out["ema_12"] = ema(close_series, fast)
    out["ema_26"] = ema(close_series, slow)
    
    # RSI con períodos diversificados
    rsi_periods = {'BTC': 14, 'ETH': 13, 'SOL': 15, 'AVAX': 14, 'LINK': 13, 
                   'DOT': 14, 'LTC': 12, 'SHIB': 16, 'DOGE': 15, 'XRP': 13,
                   'UNI': 15, 'AAVE': 16, 'PEPE': 18, 'BCH': 12, 'MKR': 15, 'CRV': 14, 'GRT': 13}
    rsi_period = rsi_periods.get(crypto_base, 14)
    out["rsi_14"] = rsi(close_series, rsi_period)
    
    m, s, h = macd(close_series, fast, slow)
    out["macd"], out["macd_sig"], out["macd_hist"] = m, s, h
    out["atr_14"] = atr(out, 14)
    out["vol_roll"] = out["ret_1"].rolling(24).std() * (24**0.5)
    
    # Añadir features de Fibonacci
    from .strategy import add_fibonacci_features
    out = add_fibonacci_features(out)
    
    return out.dropna()
