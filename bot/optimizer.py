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
        
        # --- 3. 💎 USAR TP/SL OPTIMIZADOS EN EL BACKTEST ---
        try:
            symbol_config = get_symbol_config(s)
            volatility_tier = symbol_config.volatility_tier
        except Exception:
            volatility_tier = "medium" # Fallback por si el símbolo no está configurado

        # Obtener TP/SL del trial actual para el tier de este símbolo
        tp_pct = tier_params.get(volatility_tier, tier_params["medium"])['tp']
        sl_pct = tier_params.get(volatility_tier, tier_params["medium"])['sl']

        pos = 0; entry=0; equity=0
        for _, row in f.iterrows():
            hs = hybrid_signal(row, clf, symbol=s)
            px = float(row["close"])
            
            # Lógica de salida mejorada con TP/SL
            should_exit = False
            if pos > 0: # Posición larga
                if px <= entry * (1 - sl_pct): should_exit = True # Stop Loss
                elif px >= entry * (1 + tp_pct): should_exit = True # Take Profit
                elif hs < thr_exit: should_exit = True # Reversión de señal
            elif pos < 0: # Posición corta
                if px >= entry * (1 + sl_pct): should_exit = True # Stop Loss
                elif px <= entry * (1 - tp_pct): should_exit = True # Take Profit
                elif hs > -thr_exit: should_exit = True # Reversión de señal

            if pos != 0 and should_exit:
                equity += pos*(px - entry)
                pos=0
            
            # Lógica de entrada
            if pos==0 and abs(hs) > thr_entry:
                pos = 1 if hs > 0 else -1
                entry = px
        
        # Mark-to-market para posiciones abiertas al final del backtest
        if pos != 0: 
            equity += pos * (f.iloc[-1]["close"] - entry)
        
        total_pnl += equity
        
    return float(total_pnl)

def update_configs_with_optuna_results(best_params: dict):
    """
    Actualiza el archivo configs/symbol_configs.json con los resultados de Optuna.
    """
    logger.info("🔄 Actualizando configuraciones de símbolos con resultados de Optuna...")

    # Cargar todas las configuraciones existentes
    all_configs = symbol_config_manager.list_all_configs()

    # Iterar sobre los parámetros optimizados
    for param_name, value in best_params.items():
        if param_name.startswith('tp_') or param_name.startswith('sl_'):
            parts = param_name.split('_')
            param_type = parts[0] # 'tp' o 'sl'
            tier = "_".join(parts[1:]) # 'low', 'medium', 'high', 'ultra_high'

            # Actualizar todos los símbolos que pertenecen a este tier
            for symbol, config in all_configs.items():
                if config.volatility_tier == tier:
                    # Actualizar la configuración en el manager
                    symbol_config_manager.update_config(symbol, **{f"{param_type}_pct": value})

    # Guardar todos los cambios en el archivo JSON (esto sobreescribe el archivo)
    symbol_config_manager.save_configs()
    logger.info("✅ Archivo configs/symbol_configs.json actualizado con parámetros optimizados.")

def run(symbols, start, end, n_trials):
    study = optuna.create_study(direction="maximize")
    study.optimize(lambda t: objective(t, symbols, start, end), n_trials=n_trials)
    
    best_params = study.best_trial.params
    logger.info(f"🏆 Mejores parámetros encontrados: {best_params}")
    
    # 💎 NUEVO: Actualizar automáticamente el archivo de configuración
    update_configs_with_optuna_results(best_params)
    
    return best_params

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="+", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", default=None)
    ap.add_argument("--trials", type=int, default=30)
    args = ap.parse_args()
    run(args.symbols, args.start, args.end, args.trials)
