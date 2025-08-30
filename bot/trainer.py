import argparse
import pandas as pd
import joblib
from typing import List, Optional

from bot.data import fetch_bars
from bot.strategy import train_model
from bot.util import logger


def train(symbols: List[str], start: str, end: Optional[str] = None, model_path: str = "model.pkl"):
    dfs = []
    for s in symbols:
        df = fetch_bars(s, start, end)
        if df.empty:
            logger.warning(f"⚠️ Skip {s}, no data.")
            continue
        df["symbol"] = s
        dfs.append(df)

    if not dfs:
        logger.error("❌ No data to train.")
        return None

    data = pd.concat(dfs).sort_index()
    logger.info(f"📊 Datos combinados: {len(data)} filas de {len(symbols)} símbolos.")
    logger.info("🤖 Entrenando modelo...")

    clf = train_model(data)
    joblib.dump(clf, model_path)

    logger.info(f"✅ Modelo entrenado y guardado en {model_path}.")
    return clf


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Entrena un modelo con datos de trading")
    ap.add_argument("--symbols", nargs="+", required=True, help="Lista de símbolos (ej. BTC/USD ETH/USD)")
    ap.add_argument("--start", required=True, help="Fecha de inicio (YYYY-MM-DD)")
    ap.add_argument("--end", default=None, help="Fecha de fin (YYYY-MM-DD opcional)")
    ap.add_argument("--model", default="models.pkl", help="Ruta para guardar el modelo entrenado")
    args = ap.parse_args()

    train(args.symbols, args.start, args.end, args.model)
