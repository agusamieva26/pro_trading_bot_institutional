import argparse, optuna, pandas as pd, numpy as np
from .data import fetch_bars
from .features import make_features, ema, rsi, macd, atr
from .strategy import load_trading_model, hybrid_signal, FEATURES
from .config import settings
from .util import logger, should_skip_realtime_pricing
from .symbol_configs import get_symbol_config, symbol_config_manager

def objective(trial: optuna.Trial, symbols, start, end):
    # --- 1. OPTIMIZACIÓN DE PARÁMETROS DE INDICADORES (EXISTENTE) ---
    macd_fast = trial.suggest_int("macd_fast", 8, 18)
    macd_slow = trial.suggest_int("macd_slow", 20, 30)
    macd_sig  = trial.suggest_int("macd_sig", 5, 12)
    rsi_len   = trial.suggest_int("rsi_len", 8, 21)
    thr_entry = trial.suggest_float("thr_entry", 0.3, 0.7)
    thr_exit  = trial.suggest_float("thr_exit", -0.7, -0.3)
    
    # --- 2. 💎 NUEVO: OPTIMIZACIÓN DE TP/SL POR NIVEL DE VOLATILIDAD ---
    tier_params = {}
    tier_ranges = {
        "low":        {"tp_range": (0.01, 0.04), "sl_range": (0.005, 0.02)},
        "medium":     {"tp_range": (0.02, 0.08), "sl_range": (0.01, 0.04)},
        "high":       {"tp_range": (0.04, 0.15), "sl_range": (0.02, 0.08)},
        "ultra_high": {"tp_range": (0.08, 0.25), "sl_range": (0.04, 0.12)},
    }
    
    for tier, ranges in tier_ranges.items():
        # Sugerir un TP y SL para cada nivel de volatilidad
        tp = trial.suggest_float(f"tp_{tier}", ranges["tp_range"][0], ranges["tp_range"][1])
        sl = trial.suggest_float(f"sl_{tier}", ranges["sl_range"][0], ranges["sl_range"][1])
        tier_params[tier] = {'tp': tp, 'sl': sl}

    total_pnl = 0.0
    clf = load_trading_model()

    for s in symbols:
        df = fetch_bars(s, start, end)
        if df.empty: continue
        
        f = df.copy()
        f["ret_1"] = f["close"].pct_change()
        f["ema_12"] = ema(pd.Series(f["close"]), 12)
        f["ema_26"] = ema(pd.Series(f["close"]), 26)
        f["rsi_14"] = rsi(pd.Series(f["close"]), rsi_len)
        m, sig, h = macd(pd.Series(f["close"]), macd_fast, macd_slow, macd_sig)
        f["macd"], f["macd_sig"], f["macd_hist"] = m, sig, h
        f["atr_14"] = atr(f, 14)
        f["vol_roll"] = f["ret_1"].rolling(24).std() * (24**0.5)
        f = f.dropna()
        clf = load_trading_model()
        pos = 0; entry=0; equity=0
        for _, row in f.iterrows():
            hs = hybrid_signal(row, clf, symbol=s)  # usa features modificadas
            if pos!=0 and hs*pos < thr_exit: equity += pos*(row["close"]-entry); pos=0
            if pos==0 and abs(hs) > thr_entry:
                pos = 1 if hs>0 else -1; entry = row["close"]
        if pos!=0: equity += pos*(f.iloc[-1]["close"]-entry)
        pnl += equity
    return float(pnl)

def run(symbols, start, end, n_trials):
    study = optuna.create_study(direction="maximize")
    study.optimize(lambda t: objective(t, symbols, start, end), n_trials=n_trials)
    print("Best params:", study.best_trial.params)
    return study.best_trial.params

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="+", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", default=None)
    ap.add_argument("--trials", type=int, default=30)
    args = ap.parse_args()
    run(args.symbols, args.start, args.end, args.trials)
