import numpy as np, pandas as pd, os

# ===== PARÁMETROS DEL BOT =====
capital_inicial = 10000  # USD
win_rate = 0.545
tp = 0.015      # take profit 1.5%
sl = 0.007      # stop loss 0.7%
risk_per_trade = 0.013  # 1.3% del capital
cost_per_trade = 0.002  # 0.2% por trade
years = 20
n_sims = 2000

scenarios = {
    "Conservador (200 trades/año)": 200,
    "Base (500 trades/año)": 500,
    "Agresivo (2000 trades/año)": 2000
}

def simulate(trades_per_year):
    n_trades_total = trades_per_year * years
    finales = []
    cagrs = []
    drawdowns = []
    for _ in range(n_sims):
        capital = capital_inicial
        equity_curve = [capital]
        for _ in range(n_trades_total):
            riesgo_usd = capital * risk_per_trade
            if np.random.rand() < win_rate:
                ganancia = riesgo_usd * (tp / sl)
                capital += ganancia - (capital * cost_per_trade)
            else:
                perdida = riesgo_usd
                capital -= perdida + (capital * cost_per_trade)
            equity_curve.append(capital)
        finales.append(capital)
        cagr = (capital / capital_inicial) ** (1 / years) - 1
        cagrs.append(cagr)
        peak = np.maximum.accumulate(equity_curve)
        dd = (np.array(equity_curve) - peak) / peak
        drawdowns.append(dd.min())
    return np.array(finales), np.array(cagrs), np.array(drawdowns)

summary = []
raw = []

for nombre, trades in scenarios.items():
    finales, cagrs, dds = simulate(trades)
    summary.append({
        "Escenario": nombre,
        "Trades/año": trades,
        "Capital Final Mediano (USD)": round(np.median(finales), 2),
        "P10 Capital (USD)": round(np.percentile(finales, 10), 2),
        "P90 Capital (USD)": round(np.percentile(finales, 90), 2),
        "CAGR Mediano (%)": round(np.median(cagrs) * 100, 2),
        "CAGR P10 (%)": round(np.percentile(cagrs, 10) * 100, 2),
        "CAGR P90 (%)": round(np.percentile(cagrs, 90) * 100, 2),
        "Prob > Capital Inicial (%)": round(np.mean(finales > capital_inicial) * 100, 2),
        "Max Drawdown Mediano (%)": round(np.median(dds) * 100, 2)
    })
    for i in range(n_sims):
        raw.append({
            "Escenario": nombre,
            "Sim": i + 1,
            "Capital_Final_USD": round(finales[i], 2),
            "CAGR_%": round(cagrs[i] * 100, 2),
            "MaxDD_%": round(dds[i] * 100, 2)
        })

df_summary = pd.DataFrame(summary)
df_raw = pd.DataFrame(raw)

out_path = os.path.join(os.getcwd(), "simulacion_20y_realista_10000USD.xlsx")
with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
    df_summary.to_excel(writer, sheet_name="Resumen", index=False)
    df_raw.to_excel(writer, sheet_name="Datos brutos", index=False)

print(f"\n✅ Archivo guardado en: {out_path}")
print(df_summary)
