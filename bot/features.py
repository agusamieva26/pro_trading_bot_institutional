import pandas as pd
import numpy as np

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

def make_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ret_1"] = out["close"].pct_change()
    out["ema_12"] = ema(out["close"], 12)
    out["ema_26"] = ema(out["close"], 26)
    out["rsi_14"] = rsi(out["close"], 14)
    m, s, h = macd(out["close"])
    out["macd"], out["macd_sig"], out["macd_hist"] = m, s, h
    out["atr_14"] = atr(out, 14)
    out["vol_roll"] = out["ret_1"].rolling(24).std() * (24**0.5)
    return out.dropna()
