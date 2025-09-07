# backtest_optuna.py
import optuna
import pandas as pd
import numpy as np
from datetime import datetime
from bot.data import fetch_bars
from bot.features import make_features
from bot.strategy import hybrid_signal, load_trading_model
from bot.sizing import volatility_target_size
from bot.risk import compute_brackets
from bot.util import logger


# Configuración
SYMBOLS = ["BTC/USD", "ETH/USD"]  # Añade más si quieres
START_DATE = "2024-01-01"
INITIAL_CAPITAL = 100000.0

optuna.logging.set_verbosity(optuna.logging.WARNING)

# --------------------- Funciones --------------------- #
def simulate_trade(entry_price, exit_price, qty, side):
    return (exit_price - entry_price) * qty if side == "long" else (entry_price - exit_price) * qty

def run_backtest(params, symbol_data, model=None):
    """Ejecuta un backtest y devuelve métricas."""
    cash = INITIAL_CAPITAL
    positions = []
    equity_curve = []

    total_pnl = 0.0
    num_trades = 0
    win_count = 0
    loss_count = 0
    max_drawdown = 0.0
    peak = INITIAL_CAPITAL

    RISK_PER_TRADE = params["risk_per_trade"]
    TAKE_PROFIT_PCT = params["take_profit_pct"]
    STOP_LOSS_PCT = params["stop_loss_pct"]
    MAX_GROSS_EXPOSURE = params["max_gross_exposure"]

    for symbol, feats in symbol_data.items():
        if feats.empty or len(feats) < 100:
            continue

        # 🔹 Precalcular señales para todas las velas de este símbolo
        feats["signal"] = feats.apply(lambda row: hybrid_signal(row, model), axis=1)

        logger.info(f"📊 {symbol}: empezando backtest con {len(feats)} velas")
        for i in range(100, len(feats)):
            latest = feats.iloc[i]
            price = float(latest["close"])

            # Equity
            equity = cash + sum(simulate_trade(pos["entry_price"], price, pos["qty"], pos["side"]) for pos in positions)
            equity_curve.append(equity)
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)

            gross_exposure = sum(abs(pos["qty"] * pos["entry_price"]) for pos in positions) / (equity + 1e-8)
            if gross_exposure >= MAX_GROSS_EXPOSURE:
                continue

            # 🔹 Usar señal ya precalculada
            sig = latest["signal"]
            if sig == 0:
                continue

            shares = volatility_target_size(equity, price, float(latest["atr_14"]))
            qty = shares * max(min(abs(sig) + 0.5, 1.5), 0.1)
            if qty < 1e-6:
                continue

            side = "long" if sig > 0 else "short"

            tp, sl, _ = compute_brackets(
                price, side,
                type('RiskParams', (), {
                    'take_profit_pct': TAKE_PROFIT_PCT,
                    'stop_loss_pct': STOP_LOSS_PCT
                })()
            )

            cost = qty * price
            if cost > cash * 0.95:
                continue

            positions.append({"qty": qty, "entry_price": price, "tp": tp, "sl": sl, "side": side, "open_idx": i})
            cash -= cost

            # TP/SL en futuras velas
            future_prices = feats.iloc[i+1:]["close"].values
            exit_idx = None
            exit_price = None
            for j, f_price in enumerate(future_prices):
                closed = False
                if side == "long":
                    if f_price >= tp:
                        exit_price = tp
                        closed = True
                    elif f_price <= sl:
                        exit_price = sl
                        closed = True
                else:
                    if f_price <= tp:
                        exit_price = tp
                        closed = True
                    elif f_price >= sl:
                        exit_price = sl
                        closed = True
                if closed:
                    pnl = simulate_trade(price, exit_price, qty, side)
                    cash += qty * exit_price
                    total_pnl += pnl
                    num_trades += 1
                    if pnl > 0:
                        win_count += 1
                    else:
                        loss_count += 1
                    exit_idx = i + 1 + j
                    break
            if exit_idx is not None:
                positions = [p for p in positions if p["open_idx"] != i]

            if i % 5000 == 0:
                logger.info(f"  Procesadas {i} velas de {symbol}")

    equity_curve = np.array(equity_curve)
    daily_returns = np.diff(equity_curve) / (equity_curve[:-1] + 1e-8)
    sharpe = (np.mean(daily_returns) / (np.std(daily_returns) + 1e-8)) * np.sqrt(252) if len(daily_returns) > 1 else 0.0
    win_rate = win_count / num_trades if num_trades > 0 else 0.0
    profit_factor = (win_count * (total_pnl / num_trades)) / (loss_count * abs(total_pnl / num_trades) + 1e-8) if loss_count > 0 else float('inf')
    final_equity = cash + sum(simulate_trade(pos["entry_price"], pos["entry_price"], pos["qty"], pos["side"]) for pos in positions)
    objective_val = total_pnl + sharpe * 1000 + win_rate * 10000 - max_drawdown

    return {
        "pnl": total_pnl, "num_trades": num_trades, "win_rate": win_rate,
        "profit_factor": profit_factor, "sharpe": sharpe, "max_drawdown": max_drawdown,
        "final_equity": final_equity, "objective": objective_val
    }


# --------------------- Cargar datos --------------------- #
def load_symbol_data(symbols, start_date):
    data = {}
    for symbol in symbols:
        df = fetch_bars(symbol, start=start_date)
        if df.empty:
            logger.warning(f"⚠️ No hay datos para {symbol}")
            continue
        feats = make_features(df)
        if feats.empty:
            continue
        data[symbol] = feats
    logger.info(f"📊 Datos cargados para {len(data)} símbolos")
    return data

PRELOADED_DATA = load_symbol_data(SYMBOLS, START_DATE)
MODEL = load_trading_model()

# --------------------- Función objetivo --------------------- #
def objective(trial):
    if not PRELOADED_DATA:
        return -1e6

    params = {
        "risk_per_trade": trial.suggest_float("risk_per_trade", 0.001, 0.02, step=0.001),
        "take_profit_pct": trial.suggest_float("take_profit_pct", 0.005, 0.05, step=0.005),
        "stop_loss_pct": trial.suggest_float("stop_loss_pct", 0.005, 0.03, step=0.005),
        "max_gross_exposure": trial.suggest_float("max_gross_exposure", 1.0, 3.0, step=0.1),
    }

    results = run_backtest(params, PRELOADED_DATA, model=MODEL)

    trial.set_user_attr("num_trades", results["num_trades"])
    trial.set_user_attr("win_rate", results["win_rate"])
    trial.set_user_attr("max_drawdown", results["max_drawdown"])
    trial.set_user_attr("final_equity", results["final_equity"])

    return results["objective"]

# --------------------- Main --------------------- #
if __name__ == "__main__":
    logger.info("🚀 Iniciando optimización de hiperparámetros con Optuna...")
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=50, show_progress_bar=True)

    best_params = study.best_params
    best_result = study.best_value

    logger.info("🏆 Mejores parámetros encontrados:")
    for k, v in best_params.items():
        logger.info(f"  {k}: {v}")
    logger.info(f"📈 Puntuación objetivo: {best_result:.2f}")
