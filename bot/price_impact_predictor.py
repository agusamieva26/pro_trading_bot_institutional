"""
🎯 ML PRICE IMPACT PREDICTOR
Modelo de Machine Learning para predecir impacto de noticias en precios
Correlaciona sentiment de noticias con movimientos históricos de precios
"""

import asyncio
import pandas as pd
import numpy as np
import joblib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
from collections import defaultdict

# ML Libraries
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import warnings
warnings.filterwarnings('ignore')

from .util import logger
from .config import settings
from .data import fetch_bars
from .ai_sentiment_analyzer import SentimentResult, MarketSentimentSummary

@dataclass
class PriceImpactPrediction:
    """Predicción de impacto en precio"""
    symbol: str
    current_price: float
    predicted_impact: float        # Cambio porcentual esperado
    confidence: float             # 0.0 - 1.0
    timeframe: str               # "15min", "1h", "4h", "24h"
    direction: str               # "up", "down", "neutral"
    sentiment_score: float
    critical_events: List[str]
    model_used: str
    timestamp: datetime
    
    # Detalles de predicción
    probability_up: float = 0.0
    probability_down: float = 0.0
    volatility_adjusted: bool = False
    risk_level: str = "medium"  # "low", "medium", "high"

@dataclass
class PriceMovementRecord:
    """Registro de movimiento de precio histórico"""
    symbol: str
    timestamp: datetime
    price_before: float
    price_after_15m: float
    price_after_1h: float
    price_after_4h: float
    price_after_24h: float
    sentiment_score: float
    news_count: int
    critical_keywords: List[str]
    volatility: float
    volume: float

class NewsDataCollector:
    """
    📊 Recolector de datos de noticias y precios para entrenamiento
    Almacena correlaciones históricas sentiment-precio
    """
    
    def __init__(self, db_path: str = "data_cache/news_price_data.db"):
        self.db_path = db_path
        self.ensure_database()
        
        # Cache para optimizar consultas
        self.price_cache = {}
        self.cache_ttl = 300  # 5 minutos
        
        logger.info(f"📊 News Data Collector inicializado: {db_path}")
    
    def ensure_database(self):
        """Crea la base de datos si no existe"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabla de movimientos de precio con sentiment
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    price_before REAL NOT NULL,
                    price_after_15m REAL,
                    price_after_1h REAL,
                    price_after_4h REAL,
                    price_after_24h REAL,
                    sentiment_score REAL NOT NULL,
                    news_count INTEGER DEFAULT 1,
                    critical_keywords TEXT,
                    volatility REAL,
                    volume REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Índices para optimizar consultas
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_timestamp ON price_movements(symbol, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentiment ON price_movements(sentiment_score)")
            
            conn.commit()
    
    async def record_sentiment_price_event(self, symbol: str, sentiment_score: float, 
                                         critical_keywords: List[str], 
                                         news_count: int = 1) -> bool:
        """
        📝 Registra evento de sentiment y programa seguimiento de precio
        """
        try:
            # Obtener precio actual
            current_price = await self._get_current_price(symbol)
            if not current_price:
                return False
            
            # Obtener métricas de mercado
            volatility, volume = await self._get_market_metrics(symbol)
            
            # Registrar en base de datos
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO price_movements 
                    (symbol, timestamp, price_before, sentiment_score, news_count, 
                     critical_keywords, volatility, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol,
                    datetime.now(),
                    current_price,
                    sentiment_score,
                    news_count,
                    json.dumps(critical_keywords),
                    volatility,
                    volume
                ))
                
                record_id = cursor.lastrowid
                conn.commit()
            
            # Programar actualización de precios futuros
            asyncio.create_task(self._schedule_price_updates(record_id, symbol))
            
            logger.debug(f"📝 Registrado evento: {symbol} @ ${current_price:.4f}, sentiment={sentiment_score:.3f}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error registrando evento: {e}")
            return False
    
    async def _update_price_after_delay(self, record_id: int, symbol: str, delay_seconds: int, column_name: str):
        """Espera un delay y actualiza un campo de precio en la BD."""
        try:
            await asyncio.sleep(delay_seconds)
            
            # Obtener precio actualizado
            updated_price = await self._get_current_price(symbol)
            if updated_price:
                # Actualizar base de datos
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(f"""
                        UPDATE price_movements 
                        SET {column_name} = ? 
                        WHERE id = ?
                    """, (updated_price, record_id))
                    conn.commit()
                
                logger.debug(f"🔄 {symbol} {column_name}: ${updated_price:.4f} (record: {record_id})")
        except Exception as e:
            logger.debug(f"Error actualizando precio {column_name} para record {record_id}: {e}")

    async def _schedule_price_updates(self, record_id: int, symbol: str):
        """Programa actualizaciones de precio en intervalos específicos de forma concurrente."""
        update_intervals = [
            (900, "price_after_15m"),   # 15 minutos
            (3600, "price_after_1h"),   # 1 hora
            (14400, "price_after_4h"),  # 4 horas
            (86400, "price_after_24h")  # 24 horas
        ]
        for delay_seconds, column_name in update_intervals:
            asyncio.create_task(self._update_price_after_delay(record_id, symbol, delay_seconds, column_name))
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Obtiene precio actual del símbolo"""
        try:
            # Verificar cache
            cache_key = f"price_{symbol}"
            current_time = time.time()
            
            if (cache_key in self.price_cache and 
                current_time - self.price_cache[cache_key]["timestamp"] < self.cache_ttl):
                return self.price_cache[cache_key]["price"]
            
            # Obtener datos recientes
            df = fetch_bars(symbol, "1Min", limit=1)
            if df is not None and not df.empty:
                price = float(df["close"].iloc[-1])
                
                # Actualizar cache
                self.price_cache[cache_key] = {
                    "price": price,
                    "timestamp": current_time
                }
                
                return price
                
        except Exception as e:
            logger.debug(f"Error obteniendo precio {symbol}: {e}")
        
        return None
    
    async def _get_market_metrics(self, symbol: str) -> Tuple[float, float]:
        """Obtiene volatilidad y volumen del símbolo"""
        try:
            # Obtener datos de las últimas 24 horas
            df = fetch_bars(symbol, "1Min", limit=1440)  # 24 horas de datos
            
            if df is not None and not df.empty:
                # Calcular volatilidad (desviación estándar de retornos)
                returns = df["close"].pct_change().dropna()
                volatility = float(returns.std() * np.sqrt(1440))  # Anualizada
                
                # Volumen promedio
                volume = float(df["volume"].mean())
                
                return volatility, volume
                
        except Exception as e:
            logger.debug(f"Error obteniendo métricas {symbol}: {e}")
        
        return 0.0, 0.0
    
    def get_training_data(self, min_records: int = 100, 
                         days_back: int = 30) -> pd.DataFrame:
        """
        📚 Obtiene datos para entrenamiento del modelo
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT * FROM price_movements 
                WHERE timestamp >= ? 
                AND price_after_1h IS NOT NULL
                ORDER BY timestamp DESC
            """
            
            df = pd.read_sql_query(query, conn, params=(cutoff_date,))
        
        if len(df) < min_records:
            logger.warning(f"⚠️ Pocos datos para entrenamiento: {len(df)} < {min_records}")
            return pd.DataFrame()
        
        logger.info(f"📚 Datos de entrenamiento: {len(df)} registros")
        return df
    
    def get_data_statistics(self) -> Dict:
        """Estadísticas de la base de datos"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Contar registros por símbolo
            cursor.execute("""
                SELECT symbol, COUNT(*) as count 
                FROM price_movements 
                GROUP BY symbol 
                ORDER BY count DESC
            """)
            symbol_counts = dict(cursor.fetchall())
            
            # Estadísticas generales
            cursor.execute("SELECT COUNT(*) FROM price_movements")
            total_records = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM price_movements 
                WHERE price_after_24h IS NOT NULL
            """)
            complete_records = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT AVG(sentiment_score), MIN(sentiment_score), MAX(sentiment_score)
                FROM price_movements
            """)
            avg_sentiment, min_sentiment, max_sentiment = cursor.fetchone()
        
        return {
            "total_records": total_records,
            "complete_records": complete_records,
            "symbol_counts": symbol_counts,
            "avg_sentiment": avg_sentiment or 0.0,
            "sentiment_range": [min_sentiment or 0.0, max_sentiment or 0.0]
        }

class PriceImpactModel:
    """
    🤖 Modelo ML para predicción de impacto en precios
    Entrena y predice basado en correlaciones sentiment-precio
    """
    
    def __init__(self, model_path: str = "models/price_impact_model.joblib"):
        self.model_path = model_path
        self.models = {}  # Modelos por timeframe
        self.scalers = {}  # Scalers por timeframe
        self.is_trained = False
        
        # Parámetros del modelo
        self.timeframes = ["15min", "1h", "4h", "24h"]
        self.feature_columns = [
            "sentiment_score", "news_count", "volatility", "volume",
            "sentiment_abs", "sentiment_squared", "volatility_sentiment_interaction"
        ]
        
        # Métricas de rendimiento
        self.model_metrics = {}
        
        # Cargar modelo si existe
        self.load_models()
        
        logger.info("🤖 Price Impact Model inicializado")
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepara features para entrenamiento"""
        
        # Features básicas
        features_df = df[["sentiment_score", "news_count", "volatility", "volume"]].copy()
        
        # Features derivadas
        features_df["sentiment_abs"] = np.abs(features_df["sentiment_score"])
        features_df["sentiment_squared"] = features_df["sentiment_score"] ** 2
        features_df["volatility_sentiment_interaction"] = (
            features_df["volatility"] * features_df["sentiment_abs"]
        )
        
        # Normalizar volumen (log transform para manejar valores extremos)
        features_df["volume"] = np.log1p(features_df["volume"])
        
        # Llenar valores faltantes
        features_df = features_df.fillna(0)
        
        return features_df
    
    def prepare_targets(self, df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Prepara targets (cambios porcentuales) para cada timeframe"""
        targets = {}
        
        price_columns = {
            "15min": "price_after_15m",
            "1h": "price_after_1h",
            "4h": "price_after_4h",
            "24h": "price_after_24h"
        }
        
        for timeframe, column in price_columns.items():
            if column in df.columns:
                # Calcular cambio porcentual
                price_change = (df[column] - df["price_before"]) / df["price_before"]
                
                # Filtrar valores extremos (outliers)
                price_change = np.clip(price_change, -0.5, 0.5)  # ±50% máximo
                
                targets[timeframe] = price_change.values
        
        return targets
    
    def train_models(self, training_data: pd.DataFrame) -> bool:
        """
        🎓 Entrena modelos para cada timeframe
        """
        if training_data.empty:
            logger.error("❌ No hay datos para entrenamiento")
            return False
        
        logger.info(f"🎓 Entrenando modelos con {len(training_data)} registros...")
        
        # Preparar features
        X = self.prepare_features(training_data)
        y_dict = self.prepare_targets(training_data)
        
        if not y_dict:
            logger.error("❌ No se pudieron preparar targets")
            return False
        
        # Entrenar modelo para cada timeframe
        for timeframe in self.timeframes:
            if timeframe not in y_dict:
                continue
            
            try:
                y = y_dict[timeframe]
                
                # Filtrar filas con targets válidos
                valid_mask = ~np.isnan(y)
                X_valid = X[valid_mask]
                y_valid = y[valid_mask]
                
                if len(X_valid) < 50:  # Mínimo de datos
                    logger.warning(f"⚠️ Pocos datos para {timeframe}: {len(X_valid)}")
                    continue
                
                # Split datos
                X_train, X_test, y_train, y_test = train_test_split(
                    X_valid, y_valid, test_size=0.2, random_state=42
                )
                
                # Escalar features
                scaler = StandardScaler()
                X_train_scaled = scaler.fit_transform(X_train)
                X_test_scaled = scaler.transform(X_test)
                
                # Entrenar modelo ensemble
                rf_model = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=-1
                )
                
                gb_model = GradientBoostingRegressor(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42
                )
                
                # Entrenar ambos modelos
                rf_model.fit(X_train_scaled, y_train)
                gb_model.fit(X_train_scaled, y_train)
                
                # Crear ensemble
                ensemble_model = {
                    "rf": rf_model,
                    "gb": gb_model,
                    "weights": [0.6, 0.4]  # Más peso a Random Forest
                }
                
                # Evaluar rendimiento
                rf_pred = rf_model.predict(X_test_scaled)
                gb_pred = gb_model.predict(X_test_scaled)
                ensemble_pred = (ensemble_model["weights"][0] * rf_pred + 
                               ensemble_model["weights"][1] * gb_pred)
                
                # Métricas
                mse = mean_squared_error(y_test, ensemble_pred)
                mae = mean_absolute_error(y_test, ensemble_pred)
                r2 = r2_score(y_test, ensemble_pred)
                
                # Guardar modelo y scaler
                self.models[timeframe] = ensemble_model
                self.scalers[timeframe] = scaler
                self.model_metrics[timeframe] = {
                    "mse": mse,
                    "mae": mae,
                    "r2": r2,
                    "train_samples": len(X_train),
                    "test_samples": len(X_test)
                }
                
                logger.info(f"✅ {timeframe}: R²={r2:.3f}, MAE={mae:.4f}, MSE={mse:.6f}")
                
            except Exception as e:
                logger.error(f"❌ Error entrenando {timeframe}: {e}")
                continue
        
        # Marcar como entrenado si al menos un modelo fue exitoso
        self.is_trained = len(self.models) > 0
        
        if self.is_trained:
            self.save_models()
            logger.info(f"🎓 Entrenamiento completado: {len(self.models)} modelos")
        
        return self.is_trained
    
    def predict_price_impact(self, sentiment_score: float, news_count: int = 1,
                           volatility: float = 0.02, volume: float = 1000000,
                           symbol: str = "UNKNOWN") -> Dict[str, PriceImpactPrediction]:
        """
        🎯 Predice impacto en precio para todos los timeframes
        """
        if not self.is_trained:
            logger.warning("⚠️ Modelo no entrenado, usando predicción básica")
            return self._basic_prediction(sentiment_score, symbol)
        
        predictions = {}
        
        # Preparar input
        input_data = pd.DataFrame([{
            "sentiment_score": sentiment_score,
            "news_count": news_count,
            "volatility": volatility,
            "volume": np.log1p(volume),
            "sentiment_abs": abs(sentiment_score),
            "sentiment_squared": sentiment_score ** 2,
            "volatility_sentiment_interaction": volatility * abs(sentiment_score)
        }])
        
        # Predecir para cada timeframe
        for timeframe in self.timeframes:
            if timeframe not in self.models:
                continue
            
            try:
                # Escalar input
                scaler = self.scalers[timeframe]
                input_scaled = scaler.transform(input_data)
                
                # Predicción ensemble
                ensemble = self.models[timeframe]
                rf_pred = ensemble["rf"].predict(input_scaled)[0]
                gb_pred = ensemble["gb"].predict(input_scaled)[0]
                
                predicted_change = (ensemble["weights"][0] * rf_pred + 
                                  ensemble["weights"][1] * gb_pred)
                
                # Calcular confianza basada en métricas del modelo
                model_r2 = self.model_metrics[timeframe]["r2"]
                confidence = max(0.1, min(0.95, model_r2))
                
                # Determinar dirección
                if predicted_change > 0.005:  # >0.5%
                    direction = "up"
                elif predicted_change < -0.005:  # <-0.5%
                    direction = "down"
                else:
                    direction = "neutral"
                
                # Calcular probabilidades
                abs_change = abs(predicted_change)
                prob_up = max(0.1, min(0.9, 0.5 + predicted_change * 2))
                prob_down = 1.0 - prob_up
                
                # Nivel de riesgo
                if abs_change > 0.03:  # >3%
                    risk_level = "high"
                elif abs_change > 0.01:  # >1%
                    risk_level = "medium"
                else:
                    risk_level = "low"
                
                # Crear predicción
                prediction = PriceImpactPrediction(
                    symbol=symbol,
                    current_price=0.0,  # Se actualiza externamente
                    predicted_impact=predicted_change,
                    confidence=confidence,
                    timeframe=timeframe,
                    direction=direction,
                    sentiment_score=sentiment_score,
                    critical_events=[],  # Se actualiza externamente
                    model_used="ensemble_ml",
                    timestamp=datetime.now(),
                    probability_up=prob_up,
                    probability_down=prob_down,
                    volatility_adjusted=True,
                    risk_level=risk_level
                )
                
                predictions[timeframe] = prediction
                
            except Exception as e:
                logger.debug(f"Error prediciendo {timeframe}: {e}")
        
        return predictions
    
    def _basic_prediction(self, sentiment_score: float, symbol: str) -> Dict[str, PriceImpactPrediction]:
        """Predicción básica cuando no hay modelo entrenado"""
        
        # Predicción simple basada en sentiment
        base_impact = sentiment_score * 0.02  # ±2% máximo
        
        predictions = {}
        
        for timeframe in self.timeframes:
            # Ajustar impacto por timeframe
            if timeframe == "15min":
                impact = base_impact * 0.3
            elif timeframe == "1h":
                impact = base_impact * 0.6
            elif timeframe == "4h":
                impact = base_impact * 0.8
            else:  # 24h
                impact = base_impact
            
            direction = "up" if impact > 0 else "down" if impact < 0 else "neutral"
            
            prediction = PriceImpactPrediction(
                symbol=symbol,
                current_price=0.0,
                predicted_impact=impact,
                confidence=0.3,  # Baja confianza
                timeframe=timeframe,
                direction=direction,
                sentiment_score=sentiment_score,
                critical_events=[],
                model_used="basic_sentiment",
                timestamp=datetime.now(),
                probability_up=0.5 + sentiment_score * 0.3,
                probability_down=0.5 - sentiment_score * 0.3,
                volatility_adjusted=False,
                risk_level="medium"
            )
            
            predictions[timeframe] = prediction
        
        return predictions
    
    def save_models(self):
        """Guarda modelos entrenados"""
        try:
            Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
            
            model_data = {
                "models": self.models,
                "scalers": self.scalers,
                "metrics": self.model_metrics,
                "feature_columns": self.feature_columns,
                "trained_at": datetime.now().isoformat()
            }
            
            joblib.dump(model_data, self.model_path)
            logger.info(f"💾 Modelos guardados: {self.model_path}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando modelos: {e}")
    
    def load_models(self):
        """Carga modelos desde disco"""
        try:
            if Path(self.model_path).exists():
                model_data = joblib.load(self.model_path)
                
                self.models = model_data.get("models", {})
                self.scalers = model_data.get("scalers", {})
                self.model_metrics = model_data.get("metrics", {})
                
                self.is_trained = len(self.models) > 0
                
                if self.is_trained:
                    trained_at = model_data.get("trained_at", "unknown")
                    logger.info(f"📂 Modelos cargados: {len(self.models)} timeframes (entrenado: {trained_at})")
                    
                    # Mostrar métricas
                    for timeframe, metrics in self.model_metrics.items():
                        logger.debug(f"  {timeframe}: R²={metrics.get('r2', 0):.3f}")
            
        except Exception as e:
            logger.error(f"❌ Error cargando modelos: {e}")
    
    def get_model_info(self) -> Dict:
        """Información sobre los modelos"""
        return {
            "is_trained": self.is_trained,
            "timeframes": list(self.models.keys()),
            "metrics": self.model_metrics,
            "model_path": self.model_path,
            "feature_count": len(self.feature_columns)
        }

class PriceImpactPredictor:
    """
    🚀 Predictor principal de impacto en precios
    Combina recolección de datos, entrenamiento y predicción
    """
    
    def __init__(self):
        self.data_collector = NewsDataCollector()
        self.ml_model = PriceImpactModel()
        
        # Configuración de auto-entrenamiento
        self.auto_retrain_interval = 86400  # 24 horas
        self.last_training = 0
        self.min_data_for_training = 100
        
        logger.info("🚀 Price Impact Predictor inicializado")
    
    async def record_news_event(self, sentiment_result: SentimentResult) -> bool:
        """
        📝 Registra evento de noticias para aprendizaje futuro
        """
        return await self.data_collector.record_sentiment_price_event(
            symbol=sentiment_result.symbol,
            sentiment_score=sentiment_result.sentiment_score,
            critical_keywords=sentiment_result.critical_keywords,
            news_count=1
        )
    
    async def predict_impact(self, sentiment_result: SentimentResult, 
                           current_price: float, 
                           market_volatility: float = 0.02) -> Dict[str, PriceImpactPrediction]:
        """
        🎯 Predice impacto en precio basado en sentiment
        """
        # Obtener métricas de mercado
        volume = 1000000  # Default, se puede mejorar con datos reales
        
        # Hacer predicción
        predictions = self.ml_model.predict_price_impact(
            sentiment_score=sentiment_result.sentiment_score,
            news_count=1,
            volatility=market_volatility,
            volume=volume,
            symbol=sentiment_result.symbol
        )
        
        # Actualizar con datos reales
        for timeframe, prediction in predictions.items():
            prediction.current_price = current_price
            prediction.critical_events = sentiment_result.critical_keywords
        
        # Registrar evento para aprendizaje futuro
        await self.record_news_event(sentiment_result)
        
        return predictions
    
    async def auto_retrain_if_needed(self) -> bool:
        """
        🔄 Re-entrena automáticamente si es necesario
        """
        current_time = time.time()
        
        if (current_time - self.last_training) < self.auto_retrain_interval:
            return False
        
        # Verificar si hay suficientes datos nuevos
        stats = self.data_collector.get_data_statistics()
        
        if stats["total_records"] < self.min_data_for_training:
            logger.info(f"📊 Pocos datos para re-entrenamiento: {stats['total_records']}")
            return False
        
        logger.info("🔄 Iniciando re-entrenamiento automático...")
        
        # Obtener datos de entrenamiento
        training_data = self.data_collector.get_training_data()
        
        if training_data.empty:
            return False
        
        # Re-entrenar modelos
        success = self.ml_model.train_models(training_data)
        
        if success:
            self.last_training = current_time
            logger.info("✅ Re-entrenamiento completado")
        
        return success
    
    def get_system_status(self) -> Dict:
        """Estado del sistema predictor"""
        data_stats = self.data_collector.get_data_statistics()
        model_info = self.ml_model.get_model_info()
        
        return {
            "model_trained": model_info["is_trained"],
            "available_timeframes": model_info["timeframes"],
            "data_records": data_stats["total_records"],
            "complete_records": data_stats["complete_records"],
            "last_training": datetime.fromtimestamp(self.last_training) if self.last_training > 0 else None,
            "next_training": datetime.fromtimestamp(self.last_training + self.auto_retrain_interval) if self.last_training > 0 else None
        }

# Instancia global
price_impact_predictor = PriceImpactPredictor()

# Funciones de conveniencia
async def predict_news_price_impact(sentiment_result: SentimentResult, 
                                  current_price: float,
                                  market_volatility: float = 0.02) -> Dict[str, PriceImpactPrediction]:
    """
    🎯 Función principal para predecir impacto de noticias en precios
    """
    return await price_impact_predictor.predict_impact(
        sentiment_result, current_price, market_volatility
    )

async def train_price_impact_model() -> bool:
    """
    🎓 Entrena el modelo de impacto en precios
    """
    training_data = price_impact_predictor.data_collector.get_training_data()
    
    if training_data.empty:
        logger.warning("⚠️ No hay datos suficientes para entrenar")
        return False
    
    return price_impact_predictor.ml_model.train_models(training_data)

def get_price_predictor_status() -> Dict:
    """Estado del predictor de precios"""
    return price_impact_predictor.get_system_status()

if __name__ == "__main__":
    # Test del sistema
    async def test_price_predictor():
        logger.info("🧪 Testing Price Impact Predictor...")
        
        # Definir una clase de prueba localmente para que el script sea ejecutable
        @dataclass
        class MockSentimentResult:
            article_id: str
            symbol: str
            sentiment_score: float
            confidence: float
            sentiment_label: str
            critical_keywords: List[str]
            price_impact_prediction: Dict
            reasoning: str
            timestamp: datetime
            emotional_intensity: float
            market_relevance: float
            urgency_level: int
            event_type: str
        
        # Crear sentiment de prueba
        test_sentiment = MockSentimentResult(
            article_id="test_123",
            symbol="BTC/USD",
            sentiment_score=0.7,
            confidence=0.8,
            sentiment_label="bullish",
            critical_keywords=["bullish", "positive"],
            price_impact_prediction={},
            reasoning="Test sentiment for BTC",
            timestamp=datetime.now(),
            emotional_intensity=0.6,
            market_relevance=0.8,
            urgency_level=2,
            event_type="general"
        )
        
        # Predecir impacto
        predictions = await predict_news_price_impact(
            test_sentiment, 
            current_price=45000.0,
            market_volatility=0.03
        )
        
        print(f"\n✅ Predicciones generadas:")
        for timeframe, prediction in predictions.items():
            print(f"{timeframe}: {prediction.predicted_impact:+.2%} ({prediction.direction}) - Confianza: {prediction.confidence:.2f}")
        
        # Estado del sistema
        status = get_price_predictor_status()
        print(f"\nEstado del sistema:")
        print(f"Modelo entrenado: {status['model_trained']}")
        print(f"Registros de datos: {status['data_records']}")
        print(f"Timeframes disponibles: {status['available_timeframes']}")
    
    asyncio.run(test_price_predictor())