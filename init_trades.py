# init_trades.py
import csv

HEADERS = [
    "symbol", "entry_date", "exit_date", "side", "qty", "entry_price",
    "exit_price", "realized_pnl", "realized_pnl_pct", "status"
]

with open("trades_log.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(HEADERS)

print("✅ trades_log.csv creado con éxito")