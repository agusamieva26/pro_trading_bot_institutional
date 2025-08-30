import argparse, pandas as pd, numpy as np
from .data import fetch_bars
from .features import make_features
from .strategy import load_model, hybrid_signal
from .config import settings
from .util import logger

def _concat_symbols(symbols, start, end):
    frames = {}
    for s in symbols:
        df = fetch_bars(s, start, end)
        if df.empty: logger.warning(f"No data {s}"); continue
        f = make_features(df); f["symbol"] = s; frames[s] = f
    return frames

def backtest_vectorbt(frames: dict[str, pd.DataFrame]):
    try:
        import vectorbt as vbt  # heavy, optional
    except Exception:
        logger.warning("vectorbt no disponible; usando backtester simple.")
        return backtest_simple(frames)

    # Build wide price and signals
    closes = pd.concat({s: f["close"] for s,f in frames.items()}, axis=1).dropna()
    clf = load_model()
    sigs = {}
    for s,f in frames.items():
        sig = f.apply(lambda r: hybrid_signal(r, clf), axis=1)
        sigs[s] = sig.reindex(closes.index).fillna(0)
    sigs = pd.concat(sigs, axis=1).reindex(closes.index).fillna(0)

    entries = sigs > 0.4
    exits = sigs < -0.4

    pf = vbt.Portfolio.from_signals(
        close=closes,
        entries=entries,
        exits=exits,
        fees=0.0005,
        slippage=0.0005,
        freq="D"
    )
    stats = pf.stats()
    print(stats)
    return stats

def backtest_simple(frames: dict[str, pd.DataFrame]):
    equity = 100000.0
    pos = {s:0 for s in frames}
    entry = {s:0.0 for s in frames}
    all_idx = sorted(set().union(*[f.index for f in frames.values()]))
    clf = load_model()

    for ts in all_idx:
        for s,f in frames.items():
            if ts not in f.index: continue
            row = f.loc[ts]
            sig = hybrid_signal(row, clf)
            px = float(row["close"])
            # Exit on opposite signal
            if pos[s]!=0 and sig*pos[s] < -0.5:
                equity += pos[s]*(px - entry[s]); pos[s]=0
            if pos[s]==0 and abs(sig)>0.4:
                # naive equal risk: 1 unit each
                pos[s] = 100 * (1 if sig>0 else -1); entry[s]=px
    # MTM
    for s,f in frames.items():
        if pos[s]!=0:
            equity += pos[s]*(f.iloc[-1]["close"] - entry[s])
    print(f"Equity MTM: {equity:.2f}")
    return {"final_equity": equity}

def run(symbols, start, end):
    frames = _concat_symbols(symbols, start, end)
    if not frames: 
        print("Sin datos."); return
    return backtest_vectorbt(frames)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="+", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", default=None)
    args = ap.parse_args()
    run(args.symbols, args.start, args.end)
