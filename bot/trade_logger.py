import csv
import os
from datetime import datetime, timezone
from .util import logger
from .telegram import alert_trade_entry, alert_trade_exit
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]  # carpeta raíz del proyecto
TRADES_FILE = str(ROOT / "trades_log.csv")

HEADERS = [
    "symbol", "entry_date", "exit_date", "side", "qty", "entry_price",
    "exit_price", "realized_pnl", "realized_pnl_pct", "status"
]


def init_trades_file():
    """Crea el archivo CSV si no existe."""
    if not os.path.exists(TRADES_FILE):
        with open(TRADES_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS)
            writer.writeheader()
        logger.info(f"✅ Archivo de trades creado: {TRADES_FILE}")


def log_trade_entry(symbol: str, qty: float, side: str, entry_price: float):
    """Registra la apertura de una posición."""
    init_trades_file()
    row = {
        "symbol": symbol,
        "entry_date": datetime.now(timezone.utc).isoformat(),
        "exit_date": "",
        "side": side.lower(),
        "qty": f"{qty:.6f}",
        "entry_price": f"{entry_price:.2f}",
        "exit_price": "",
        "realized_pnl": "",
        "realized_pnl_pct": "",
        "status": "open"
    }
    _append_row(row)
    logger.info(f"🟢 Entrada registrada: {side.upper()} {qty} {symbol} @ ${entry_price:.2f}")
    alert_trade_entry(symbol, side, qty, entry_price)


def log_trade_exit(symbol: str, qty: float, exit_price: float, pnl: float, pnl_pct: float):
    """
    Cierra la posición abierta más antigua para el símbolo.
    Maneja cierres totales y parciales.
    """
    trades = _read_all_trades()
    updated = False

    for trade in trades:
        if trade["symbol"] == symbol and trade["status"] == "open":
            entry_qty = float(trade["qty"])
            side = trade["side"]

            if qty >= entry_qty:
                # Cierre total
                trade["exit_date"] = datetime.now(timezone.utc).isoformat()
                trade["exit_price"] = f"{exit_price:.2f}"
                trade["realized_pnl"] = f"{pnl:.2f}"
                trade["realized_pnl_pct"] = f"{pnl_pct:+.2%}"
                trade["status"] = "closed"
                updated = True
                logger.info(f"✅ Cerrado: {side.upper()} {entry_qty} {symbol} @ ${exit_price:.2f} → P&L: ${pnl:.2f} ({pnl_pct:+.2%})")
                alert_trade_exit(symbol, side, entry_qty, exit_price, pnl, pnl_pct)
            else:
                # Cierre parcial
                partial_pnl = pnl * (qty / entry_qty)
                _create_partial_replacement(trade, entry_qty - qty)
                trade["exit_date"] = datetime.now(timezone.utc).isoformat()
                trade["exit_price"] = f"{exit_price:.2f}"
                trade["realized_pnl"] = f"{partial_pnl:.2f}"
                trade["realized_pnl_pct"] = f"{pnl_pct:+.2%}"
                trade["status"] = "partially_closed"
                updated = True
                logger.info(f"🟡 Cierre parcial: {side.upper()} {qty} {symbol} @ ${exit_price:.2f} → P&L: ${partial_pnl:.2f}")
                alert_trade_exit(symbol, side, qty, exit_price, partial_pnl, pnl_pct)
                qty = 0

            if qty <= 0:
                break

    _write_all_trades(trades)
    return updated


def log_closed_trades(closed_trades: list):
    """
    NUEVA FUNCIÓN: Registra automáticamente todas las operaciones cerradas.
    Espera una lista de dicts como devuelve Alpaca:
    [{
        "symbol": "BTC/USD",
        "qty": "0.01",
        "side": "buy",
        "avg_entry_price": "29250.0",
        "avg_exit_price": "29500.0",
        "realized_pl": "2.5"
    }, ...]
    """
    init_trades_file()

    for t in closed_trades:
        try:
            symbol = t.get("symbol", "N/A")
            qty = float(t.get("qty", 0))
            side = t.get("side", "buy").lower()
            entry_price = float(t.get("avg_entry_price", 0))
            exit_price = float(t.get("avg_exit_price", 0))
            pnl = float(t.get("realized_pl", 0))
            pnl_pct = (pnl / (entry_price * qty)) if entry_price > 0 else 0.0

            row = {
                "symbol": symbol,
                "entry_date": "",  # No siempre viene del broker → opcional
                "exit_date": datetime.now(timezone.utc).isoformat(),
                "side": side,
                "qty": f"{qty:.6f}",
                "entry_price": f"{entry_price:.2f}",
                "exit_price": f"{exit_price:.2f}",
                "realized_pnl": f"{pnl:.2f}",
                "realized_pnl_pct": f"{pnl_pct:+.2%}",
                "status": "closed"
            }
            _append_row(row)
            logger.info(f"📕 Trade cerrado registrado: {side.upper()} {qty} {symbol} @ {exit_price:.2f} → P&L: ${pnl:.2f} ({pnl_pct:+.2%})")
            alert_trade_exit(symbol, side, qty, exit_price, pnl, pnl_pct)

        except Exception as e:
            logger.error(f"❌ Error registrando trade cerrado {t}: {e}")


def _create_partial_replacement(trade, remaining_qty):
    """Genera una nueva fila 'open' para la parte no cerrada de la posición."""
    new_trade = trade.copy()
    new_trade["qty"] = f"{remaining_qty:.6f}"
    new_trade["entry_date"] = datetime.now(timezone.utc).isoformat()
    new_trade["exit_date"] = ""
    new_trade["exit_price"] = ""
    new_trade["realized_pnl"] = ""
    new_trade["realized_pnl_pct"] = ""
    new_trade["status"] = "open"
    _append_row(new_trade)


def _read_all_trades():
    if not os.path.exists(TRADES_FILE):
        return []
    with open(TRADES_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _write_all_trades(trades):
    with open(TRADES_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(trades)


def _append_row(row):
    with open(TRADES_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writerow(row)
