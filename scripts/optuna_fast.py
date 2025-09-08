#!/usr/bin/env python3
"""
Optimización RÁPIDA de hiperparámetros con Optuna + Fibonacci.
Versión optimizada para velocidad sin perder precisión.
"""

import sys
import os
sys.path.insert(0, '.')

import optuna
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

from bot.data import fetch_bars
from bot.features import make_features
from bot.strategy import hybrid_signal, load_trading_model
from bot.util import logger

# Configuración OPTIMIZADA para velocidad
SYMBOLS = ["BTC/USD"]  # Solo 1 símbolo para máxima velocidad
START_DATE = "2025-08-15"  # Solo últimas 3 semanas
INITIAL_CAPITAL = 100000.0
SAMPLE_EVERY_N = 20  # Procesar cada 20va vela (1 de cada 20 horas)

optuna.logging.set_verbosity(optuna.logging.ERROR)

def simulate_trade(entry_price, exit_price, qty, side):
    """Simula P&L de una operación."""
    if side == "long":
        return (exit_price - entry_price) * qty
    else:
        return (entry_price - exit_price) * qty

def run_ultra_fast_backtest(params, symbol_data, model=None):
    """Backtest ultrarrápido con muestreo optimizado."""
    
    cash = INITIAL_CAPITAL
    total_pnl = 0.0
    num_trades = 0
    win_count = 0
    max_drawdown = 0.0
    peak_equity = INITIAL_CAPITAL
    
    RISK_PER_TRADE = params["risk_per_trade"]
    TAKE_PROFIT_PCT = params["take_profit_pct"]
    STOP_LOSS_PCT = params["stop_loss_pct"]
    
    for symbol, feats in symbol_data.items():
        if feats.empty or len(feats) < 100:
            continue
        
        # PRE-CALCULAR todas las señales de una vez (más eficiente)
        logger.debug(f"🔮 Pre-calculando señales para {symbol}...")
        signals = []
        
        # Muestrear cada N velas para velocidad
        sampled_indices = list(range(50, len(feats), SAMPLE_EVERY_N))
        
        for i in sampled_indices:
            row = feats.iloc[i]
            sig = hybrid_signal(row, model)
            signals.append((i, sig, float(row["close"]), float(row.get("atr_14", 0))))
        
        logger.debug(f"✅ {len(signals)} señales calculadas para {symbol}")
        
        # Procesar trades con señales pre-calculadas
        for i, (idx, sig, price, atr) in enumerate(signals):
            if abs(sig) < 0.25:  # Solo señales fuertes
                continue
                
            # Position sizing simplificado
            risk_amount = cash * RISK_PER_TRADE
            if atr > 0:
                qty = risk_amount / (atr * 2)  # Risk-based sizing
            else:
                qty = risk_amount / (price * 0.02)  # 2% como ATR fallback
                
            qty = max(qty, cash * 0.001)  # Mínimo 0.1% del cash
            
            side = "long" if sig > 0 else "short"
            
            # Calcular niveles TP/SL
            if side == "long":
                tp_price = price * (1 + TAKE_PROFIT_PCT)
                sl_price = price * (1 - STOP_LOSS_PCT)
            else:
                tp_price = price * (1 - TAKE_PROFIT_PCT)
                sl_price = price * (1 + STOP_LOSS_PCT)
            
            # Buscar salida en próximas velas (máx 10 velas futuras)
            future_start = idx + 1
            future_end = min(idx + 10, len(feats))
            
            if future_end <= future_start:
                continue
                
            future_prices = feats.iloc[future_start:future_end]["close"].values
            
            exit_price = None
            for f_price in future_prices:
                if side == "long":
                    if f_price >= tp_price:
                        exit_price = tp_price
                        break
                    elif f_price <= sl_price:
                        exit_price = sl_price
                        break
                else:  # short
                    if f_price <= tp_price:
                        exit_price = tp_price
                        break
                    elif f_price >= sl_price:
                        exit_price = sl_price
                        break
            
            # Si no se disparó TP/SL, usar último precio
            if exit_price is None and len(future_prices) > 0:
                exit_price = future_prices[-1]
            
            if exit_price is not None:
                # Calcular P&L
                trade_qty = qty / price  # Cantidad en unidades del activo
                pnl = simulate_trade(price, exit_price, trade_qty, side)
                
                total_pnl += pnl
                num_trades += 1
                
                if pnl > 0:
                    win_count += 1
                
                # Actualizar cash (simplificado)
                cash += pnl
                
                # Tracking de drawdown
                current_equity = INITIAL_CAPITAL + total_pnl
                peak_equity = max(peak_equity, current_equity)
                current_dd = peak_equity - current_equity
                max_drawdown = max(max_drawdown, current_dd)
    
    # Métricas finales
    win_rate = win_count / num_trades if num_trades > 0 else 0.0
    
    # Objective function (maximizar)
    if num_trades < 5:  # Penalizar muy pocos trades
        objective_val = -1e6
    else:
        # Balancear P&L, win rate y minimizar drawdown
        objective_val = (total_pnl + 
                        win_rate * 5000 + 
                        num_trades * 10 - 
                        max_drawdown * 2)
    
    return {
        "pnl": total_pnl,
        "num_trades": num_trades,
        "win_rate": win_rate,
        "max_drawdown": max_drawdown,
        "objective": objective_val
    }

def load_optimized_data():
    """Carga datos una sola vez para reutilizar."""
    print("📊 Cargando datos optimizados...")
    
    data = {}
    for symbol in SYMBOLS:
        df = fetch_bars(symbol, start=START_DATE)
        if df.empty:
            logger.warning(f"⚠️ No hay datos para {symbol}")
            continue
            
        feats = make_features(df)
        if feats.empty:
            continue
            
        data[symbol] = feats
        print(f"✅ {symbol}: {len(feats)} velas cargadas")
    
    return data

# Datos y modelo globales (cargados una vez)
PRELOADED_DATA = load_optimized_data()
MODEL = load_trading_model()

def objective(trial):
    """Función objetivo optimizada."""
    if not PRELOADED_DATA:
        return -1e6
    
    # Parámetros a optimizar
    params = {
        "risk_per_trade": trial.suggest_float("risk_per_trade", 0.005, 0.025, step=0.005),
        "take_profit_pct": trial.suggest_float("take_profit_pct", 0.01, 0.06, step=0.01),
        "stop_loss_pct": trial.suggest_float("stop_loss_pct", 0.01, 0.04, step=0.01),
    }
    
    # Ejecutar backtest
    results = run_ultra_fast_backtest(params, PRELOADED_DATA, model=MODEL)
    
    # Guardar métricas adicionales
    trial.set_user_attr("num_trades", results["num_trades"])
    trial.set_user_attr("win_rate", results["win_rate"])
    trial.set_user_attr("pnl", results["pnl"])
    trial.set_user_attr("max_drawdown", results["max_drawdown"])
    
    return results["objective"]

def main():
    """Ejecuta optimización ultrarrápida."""
    print("🚀 OPTUNA ULTRARRÁPIDO con Fibonacci iniciando...")
    print(f"📊 Símbolos: {SYMBOLS}")
    print(f"📅 Período: {START_DATE} - presente")
    print(f"⚡ Muestreo: cada {SAMPLE_EVERY_N} velas")
    print(f"🧠 Modelo ML: {'✅ Cargado' if MODEL else '❌ No disponible'}")
    
    # Crear estudio Optuna
    study = optuna.create_study(direction="maximize")
    
    # Optimización con progress bar
    study.optimize(objective, n_trials=15, show_progress_bar=True)
    
    # Resultados
    best_params = study.best_params
    best_value = study.best_value
    best_trial = study.best_trial
    
    print("\n" + "="*50)
    print("🏆 OPTIMIZACIÓN COMPLETADA")
    print("="*50)
    
    print(f"📈 Mejor puntuación: {best_value:.2f}")
    print(f"📊 Trades realizados: {best_trial.user_attrs.get('num_trades', 'N/A')}")
    print(f"🎯 Win rate: {best_trial.user_attrs.get('win_rate', 0)*100:.1f}%")
    print(f"💰 P&L total: ${best_trial.user_attrs.get('pnl', 0):,.2f}")
    print(f"📉 Max drawdown: ${best_trial.user_attrs.get('max_drawdown', 0):,.2f}")
    
    print("\n🔧 MEJORES PARÁMETROS:")
    for param, value in best_params.items():
        print(f"   {param}: {value}")
    
    print("\n✅ ¡Optimización con Fibonacci completada!")
    return best_params

if __name__ == "__main__":
    main()