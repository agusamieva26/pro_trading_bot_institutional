# bot/reporter.py
import pandas as pd
import os
from datetime import datetime, timezone
from .util import logger
from .config import settings

REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

def generate_daily_report():
    """
    Genera un reporte diario en Excel con P&L, métricas y detalle de trades.
    """
    trades_file = "trades_log.csv"
    
    if not os.path.exists(trades_file):
        logger.warning("⚠️ No hay trades_log.csv para generar reporte.")
        return

    # 1. Leer trades
    df = pd.read_csv(trades_file)
    if df.empty:
        logger.warning("⚠️ trades_log.csv está vacío.")
        return

    # 2. Convertir fechas
    df["entry_date"] = pd.to_datetime(df["entry_date"], errors="coerce", utc=True)
    df["exit_date"] = pd.to_datetime(df["exit_date"], errors="coerce", utc=True)

    # 3. Filtrar trades cerrados de hoy
    today = datetime.now(timezone.utc).date()
    df_closed = df[df["status"] == "closed"].copy()
    df_closed["exit_day"] = df_closed["exit_date"].dt.date
    df_today = df_closed[df_closed["exit_day"] == today].copy()  # ✅ .copy() aquí

    if df_today.empty:
        logger.info("🟡 No hay trades cerrados hoy. Reporte no generado.")
        return

    # 4. Convertir P&L a número
    df_today.loc[:, "realized_pnl"] = pd.to_numeric(df_today["realized_pnl"], errors="coerce")
    df_today.loc[:, "realized_pnl_pct"] = df_today["realized_pnl_pct"].str.replace("%", "").astype(float) / 100

    # 5. Calcular métricas
    total_pnl = df_today["realized_pnl"].sum()
    total_pnl_pct = (df_today["realized_pnl_pct"] + 1).prod() - 1  # Retorno compuesto
    num_trades = len(df_today)
    win_rate = (df_today["realized_pnl"] > 0).mean() if num_trades > 0 else 0.0
    avg_pnl = df_today["realized_pnl"].mean()
    largest_win = df_today["realized_pnl"].max()
    largest_loss = df_today["realized_pnl"].min()

    # 6. Crear resumen
    summary = pd.DataFrame({
        "Métrica": [
            "Fecha",
            "Trades Cerrados",
            "P&L Total (USD)",
            "P&L Total (%)",
            "Win Rate",
            "P&L Promedio",
            "Mayor Ganancia",
            "Mayor Pérdida"
        ],
        "Valor": [
            today.strftime("%Y-%m-%d"),
            num_trades,
            f"${total_pnl:.2f}",
            f"{total_pnl_pct:.2%}",
            f"{win_rate:.2%}",
            f"${avg_pnl:.2f}",
            f"${largest_win:.2f}",
            f"${largest_loss:.2f}"
        ]
    })

    # 7. Ordenar por fecha de cierre
    df_export = df_today[[
        "symbol", "side", "qty", "entry_price", "exit_price",
        "realized_pnl", "realized_pnl_pct", "exit_date"
    ]].copy()
    df_export = df_export.sort_values("exit_date", ascending=False)
    df_export["exit_date"] = df_export["exit_date"].dt.strftime("%H:%M:%S")

    # 8. Guardar en Excel
    filename = f"{REPORTS_DIR}/reporte_{today}.xlsx"
    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Resumen", index=False)
        df_export.to_excel(writer, sheet_name="Trades", index=False)

    logger.info(f"✅ Reporte diario generado: {filename}")

    # 9. Enviar por Telegram (opcional)
    try:
        from .telegram import send_telegram
        msg = (
            f"📊 *Reporte Diario*\n"
            f"──────────────────\n"
            f"• *Fecha:* `{today}`\n"
            f"• *Trades:* `{num_trades}`\n"
            f"• *P&L:* `${total_pnl:.2f}` ({total_pnl_pct:+.2%})\n"
            f"• *Win Rate:* `{win_rate:.1%}`"
        )
        send_telegram(msg)
    except Exception as e:
        logger.warning(f"❌ No se pudo enviar reporte por Telegram: {e}")