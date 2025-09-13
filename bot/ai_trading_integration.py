"""
🚀 AI TRADING INTEGRATION - SISTEMA DE INTEGRACIÓN AVANZADA
Integra análisis de IA con decisiones de trading en tiempo real
Sistema de boost/penalty, emergency stops y ajuste dinámico de señales
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from enum import Enum
import threading
from collections import defaultdict, deque

from .util import logger
from .config import settings
from .advanced_news_engine import get_latest_news, NewsArticle
from .ai_sentiment_analyzer import analyze_news_sentiment, MarketSentimentSummary, SentimentResult
from .price_impact_predictor import predict_news_price_impact, PriceImpactPrediction

class AlertLevel(Enum):
    """Niveles de alerta para eventos críticos"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5

@dataclass
class TradingSignalAdjustment:
    """Ajuste de señal de trading basado en IA"""
    symbol: str
    original_signal: float
    ai_adjusted_signal: float
    sentiment_score: float
    confidence: float
    boost_factor: float
    penalty_factor: float
    emergency_stop: bool
    price_predictions: Dict[str, PriceImpactPrediction]
    critical_events: List[str]
    recommendation: str
    timestamp: datetime

@dataclass 
class EmergencyAlert:
    """Alerta de emergencia del sistema"""
    symbol: str
    alert_level: AlertLevel
    trigger_reason: str
    sentiment_score: float
    critical_keywords: List[str]
    recommended_action: str
    impact_prediction: Dict
    timestamp: datetime
    auto_resolved: bool = False

class NewsBasedEmergencyManager:
    """
    🚨 Gestor de emergencias basado en noticias
    Detecta eventos críticos que requieren acción inmediata
    """
    
    def __init__(self):
        # Configuración de emergencias
        self.emergency_thresholds = {
            "critical_sentiment": -0.8,      # Sentiment extremadamente negativo
            "critical_keywords_count": 3,    # Múltiples keywords críticas
            "high_impact_prediction": 0.15,  # Predicción de >15% movimiento
            "news_volume_spike": 10          # Spike de volumen de noticias
        }
        
        # Keywords que disparan emergencias
        self.emergency_keywords = {
            "immediate_stop": [
                "bankruptcy", "fraud", "scandal", "investigation", "lawsuit",
                "hack", "security breach", "delisted", "suspended", "halted"
            ],
            "high_risk": [
                "regulation", "ban", "crackdown", "violation", "fine",
                "recall", "shutdown", "emergency", "crisis"
            ],
            "market_crash": [
                "crash", "collapse", "plunge", "panic", "selloff",
                "liquidation", "margin call", "bubble burst"
            ]
        }
        
        # Estado de emergencias activas
        self.active_emergencies = {}
        self.emergency_history = deque(maxlen=100)
        
        # Lock para thread safety
        self.lock = threading.Lock()
        
        logger.info("🚨 Emergency Manager inicializado")
    
    def evaluate_emergency_conditions(self, sentiment_summary: MarketSentimentSummary,
                                    news_articles: List[NewsArticle]) -> Dict[str, EmergencyAlert]:
        """
        🔍 Evalúa condiciones de emergencia basadas en análisis
        """
        emergencies = {}
        
        # Evaluar por símbolo
        for symbol, sentiment in sentiment_summary.symbol_sentiments.items():
            alert = self._check_symbol_emergency(
                symbol, sentiment, sentiment_summary, news_articles
            )
            
            if alert:
                emergencies[symbol] = alert
                
                # Registrar en histórico
                self.emergency_history.append(alert)
                
                # Notificar
                logger.critical(f"🚨 EMERGENCIA {alert.alert_level.name}: {symbol} - {alert.trigger_reason}")
        
        # Emergencias de mercado general
        market_alert = self._check_market_emergency(sentiment_summary, news_articles)
        if market_alert:
            emergencies["MARKET"] = market_alert
            self.emergency_history.append(market_alert)
            logger.critical(f"🚨 EMERGENCIA DE MERCADO: {market_alert.trigger_reason}")
        
        # Actualizar emergencias activas
        with self.lock:
            self.active_emergencies.update(emergencies)
        
        return emergencies
    
    def _check_symbol_emergency(self, symbol: str, sentiment: float,
                              summary: MarketSentimentSummary,
                              articles: List[NewsArticle]) -> Optional[EmergencyAlert]:
        """Verifica emergencias específicas de un símbolo"""
        
        # Filtrar artículos relevantes para el símbolo
        symbol_articles = [
            a for a in articles 
            if symbol in a.symbols or 
            symbol.replace("/USD", "").replace("/", "").lower() in a.title.lower()
        ]
        
        if not symbol_articles:
            return None
        
        # Análisis de keywords críticas
        all_text = " ".join([f"{a.title} {a.content}" for a in symbol_articles]).lower()
        critical_keywords = []
        alert_level = AlertLevel.LOW
        
        # Verificar keywords de emergencia inmediata
        for keyword in self.emergency_keywords["immediate_stop"]:
            if keyword in all_text:
                critical_keywords.append(keyword)
                alert_level = AlertLevel.EMERGENCY
        
        # Verificar keywords de alto riesgo
        if alert_level < AlertLevel.EMERGENCY:
            for keyword in self.emergency_keywords["high_risk"]:
                if keyword in all_text:
                    critical_keywords.append(keyword)
                    alert_level = max(alert_level, AlertLevel.HIGH)
        
        # Verificar crash de mercado
        for keyword in self.emergency_keywords["market_crash"]:
            if keyword in all_text:
                critical_keywords.append(keyword)
                alert_level = max(alert_level, AlertLevel.CRITICAL)
        
        # Evaluación de sentiment extremo
        if sentiment <= self.emergency_thresholds["critical_sentiment"]:
            alert_level = max(alert_level, AlertLevel.CRITICAL)
            critical_keywords.append("extreme_negative_sentiment")
        
        # Múltiples keywords críticas
        if len(critical_keywords) >= self.emergency_thresholds["critical_keywords_count"]:
            alert_level = max(alert_level, AlertLevel.CRITICAL)
        
        # Solo crear alerta si es significativa
        if alert_level <= AlertLevel.MEDIUM and not critical_keywords:
            return None
        
        # Determinar acción recomendada
        if alert_level >= AlertLevel.EMERGENCY:
            action = "CLOSE_ALL_POSITIONS_IMMEDIATELY"
        elif alert_level >= AlertLevel.CRITICAL:
            action = "CLOSE_POSITIONS_AND_AVOID_NEW_ENTRIES"
        elif alert_level >= AlertLevel.HIGH:
            action = "REDUCE_POSITION_SIZE_BY_50%"
        else:
            action = "MONITOR_CLOSELY"
        
        return EmergencyAlert(
            symbol=symbol,
            alert_level=alert_level,
            trigger_reason=f"Critical events detected: {', '.join(critical_keywords[:3])}",
            sentiment_score=sentiment,
            critical_keywords=critical_keywords,
            recommended_action=action,
            impact_prediction={},
            timestamp=datetime.now()
        )
    
    def _check_market_emergency(self, summary: MarketSentimentSummary,
                              articles: List[NewsArticle]) -> Optional[EmergencyAlert]:
        """Verifica emergencias de mercado general"""
        
        # Crash de mercado general
        if (summary.market_condition in ["panic", "extreme_fear"] and
            summary.overall_sentiment <= -0.7 and
            len(summary.critical_events) >= 3):
            
            return EmergencyAlert(
                symbol="MARKET",
                alert_level=AlertLevel.EMERGENCY,
                trigger_reason=f"Market panic detected: {summary.market_condition}",
                sentiment_score=summary.overall_sentiment,
                critical_keywords=[e["keywords"][0] if e["keywords"] else "critical" for e in summary.critical_events[:3]],
                recommended_action="CLOSE_ALL_POSITIONS_MARKET_WIDE",
                impact_prediction={},
                timestamp=datetime.now()
            )
        
        return None
    
    def get_active_emergencies(self) -> Dict[str, EmergencyAlert]:
        """Obtiene emergencias activas"""
        with self.lock:
            return self.active_emergencies.copy()
    
    def resolve_emergency(self, symbol: str, reason: str = "Manual resolution"):
        """Resuelve una emergencia activa"""
        with self.lock:
            if symbol in self.active_emergencies:
                self.active_emergencies[symbol].auto_resolved = True
                logger.info(f"✅ Emergencia resuelta: {symbol} - {reason}")
                del self.active_emergencies[symbol]

class AISignalBooster:
    """
    ⚡ Sistema de boost/penalty para señales basado en IA
    Ajusta señales de trading según análisis de sentiment y predicciones
    """
    
    def __init__(self):
        # Configuración de boost/penalty
        self.boost_config = {
            "max_boost": 2.5,          # Máximo 250% boost
            "max_penalty": 0.2,        # Máximo 80% penalty
            "sentiment_weight": 0.4,   # Peso del sentiment
            "confidence_weight": 0.3,  # Peso de la confianza
            "prediction_weight": 0.3   # Peso de predicción de impacto
        }
        
        # Configuración de timeframes para boost
        self.timeframe_weights = {
            "15min": 0.3,
            "1h": 0.5,
            "4h": 0.3,
            "24h": 0.1
        }
        
        # Histórico de ajustes
        self.adjustment_history = deque(maxlen=1000)
        
        logger.info("⚡ AI Signal Booster inicializado")
    
    def calculate_signal_adjustment(self, original_signal: float,
                                  sentiment_result: SentimentResult,
                                  price_predictions: Dict[str, PriceImpactPrediction],
                                  emergency_status: Optional[EmergencyAlert] = None) -> TradingSignalAdjustment:
        """
        🎯 Calcula ajuste de señal basado en análisis de IA
        """
        
        # Inicializar factores
        boost_factor = 1.0
        penalty_factor = 1.0
        emergency_stop = False
        
        # 1. EMERGENCY STOP - Tiene prioridad máxima
        if emergency_status and emergency_status.alert_level >= AlertLevel.HIGH:
            if emergency_status.alert_level >= AlertLevel.EMERGENCY:
                # Emergencia crítica: detener completamente
                emergency_stop = True
                boost_factor = 0.0
                penalty_factor = 1.0
            elif emergency_status.alert_level >= AlertLevel.CRITICAL:
                # Crítico: penalizar fuertemente
                penalty_factor = 0.1
                boost_factor = 0.1
            else:
                # Alto riesgo: penalizar moderadamente
                penalty_factor = 0.5
                boost_factor = 0.5
        
        # 2. SENTIMENT BOOST/PENALTY (solo si no hay emergencia)
        if not emergency_stop:
            sentiment_factor = self._calculate_sentiment_factor(sentiment_result)
            
            # 3. PREDICCIÓN DE IMPACTO
            prediction_factor = self._calculate_prediction_factor(price_predictions, original_signal)
            
            # 4. FACTOR DE CONFIANZA
            confidence_factor = sentiment_result.confidence
            
            # Combinar factores
            if original_signal > 0:  # Señal alcista
                if sentiment_result.sentiment_score > 0:
                    # Sentiment positivo refuerza señal alcista
                    boost_factor = 1.0 + (
                        self.boost_config["sentiment_weight"] * sentiment_factor +
                        self.boost_config["prediction_weight"] * prediction_factor +
                        self.boost_config["confidence_weight"] * confidence_factor
                    )
                    boost_factor = min(boost_factor, self.boost_config["max_boost"])
                else:
                    # Sentiment negativo penaliza señal alcista
                    penalty_factor = max(
                        self.boost_config["max_penalty"],
                        1.0 + sentiment_factor * 0.8  # sentiment_factor será negativo
                    )
            
            else:  # Señal bajista
                if sentiment_result.sentiment_score < 0:
                    # Sentiment negativo refuerza señal bajista
                    boost_factor = 1.0 + abs(sentiment_factor) * 0.8
                    boost_factor = min(boost_factor, self.boost_config["max_boost"])
                else:
                    # Sentiment positivo penaliza señal bajista
                    penalty_factor = max(
                        self.boost_config["max_penalty"],
                        1.0 - sentiment_factor * 0.8
                    )
        
        # Calcular señal ajustada
        if emergency_stop:
            ai_adjusted_signal = 0.0
        else:
            ai_adjusted_signal = original_signal * boost_factor * penalty_factor
            ai_adjusted_signal = np.clip(ai_adjusted_signal, -1.0, 1.0)
        
        # Generar recomendación
        recommendation = self._generate_recommendation(
            original_signal, ai_adjusted_signal, sentiment_result, emergency_status
        )
        
        # Crear resultado
        adjustment = TradingSignalAdjustment(
            symbol=sentiment_result.symbol,
            original_signal=original_signal,
            ai_adjusted_signal=ai_adjusted_signal,
            sentiment_score=sentiment_result.sentiment_score,
            confidence=sentiment_result.confidence,
            boost_factor=boost_factor,
            penalty_factor=penalty_factor,
            emergency_stop=emergency_stop,
            price_predictions=price_predictions,
            critical_events=sentiment_result.critical_keywords,
            recommendation=recommendation,
            timestamp=datetime.now()
        )
        
        # Guardar en histórico
        self.adjustment_history.append(adjustment)
        
        return adjustment
    
    def _calculate_sentiment_factor(self, sentiment_result: SentimentResult) -> float:
        """Calcula factor de ajuste basado en sentiment"""
        
        # Factor base del sentiment
        sentiment_factor = sentiment_result.sentiment_score
        
        # Ajustar por intensidad emocional
        intensity_multiplier = 1.0 + (sentiment_result.emotional_intensity - 0.5)
        sentiment_factor *= intensity_multiplier
        
        # Ajustar por relevancia de mercado
        relevance_multiplier = 0.5 + sentiment_result.market_relevance * 0.5
        sentiment_factor *= relevance_multiplier
        
        # Ajustar por nivel de urgencia
        urgency_multiplier = 1.0 + (sentiment_result.urgency_level - 3) * 0.2
        sentiment_factor *= urgency_multiplier
        
        return np.clip(sentiment_factor, -1.0, 1.0)
    
    def _calculate_prediction_factor(self, predictions: Dict[str, PriceImpactPrediction],
                                   original_signal: float) -> float:
        """Calcula factor basado en predicciones de precio"""
        
        if not predictions:
            return 0.0
        
        # Promedio ponderado de predicciones por timeframe
        weighted_prediction = 0.0
        total_weight = 0.0
        
        for timeframe, prediction in predictions.items():
            weight = self.timeframe_weights.get(timeframe, 0.1)
            
            # Factor de dirección (si coincide con señal original)
            if (original_signal > 0 and prediction.predicted_impact > 0) or \
               (original_signal < 0 and prediction.predicted_impact < 0):
                direction_bonus = 1.0
            else:
                direction_bonus = -0.5  # Penalizar predicciones contrarias
            
            # Factor de magnitud
            magnitude_factor = abs(prediction.predicted_impact) * 10  # Escalar a 0-1 aprox
            
            # Factor de confianza
            confidence_factor = prediction.confidence
            
            prediction_value = direction_bonus * magnitude_factor * confidence_factor
            
            weighted_prediction += prediction_value * weight
            total_weight += weight
        
        if total_weight > 0:
            weighted_prediction /= total_weight
        
        return np.clip(weighted_prediction, -1.0, 1.0)
    
    def _generate_recommendation(self, original_signal: float, adjusted_signal: float,
                               sentiment_result: SentimentResult,
                               emergency_status: Optional[EmergencyAlert]) -> str:
        """Genera recomendación textual"""
        
        if emergency_status and emergency_status.alert_level >= AlertLevel.EMERGENCY:
            return f"EMERGENCY STOP: {emergency_status.trigger_reason}"
        
        if emergency_status and emergency_status.alert_level >= AlertLevel.CRITICAL:
            return f"CRITICAL RISK: {emergency_status.trigger_reason} - Avoid new positions"
        
        change_pct = ((adjusted_signal / original_signal) - 1) * 100 if original_signal != 0 else 0
        
        if abs(change_pct) < 5:
            return f"Minimal AI adjustment ({change_pct:+.1f}%) - Standard execution"
        elif change_pct > 20:
            return f"Strong AI boost ({change_pct:+.1f}%) - Positive sentiment and predictions"
        elif change_pct < -20:
            return f"Strong AI penalty ({change_pct:+.1f}%) - Negative sentiment or contrary predictions"
        else:
            return f"Moderate AI adjustment ({change_pct:+.1f}%) - Mixed signals"
    
    def get_adjustment_statistics(self) -> Dict:
        """Estadísticas de ajustes realizados"""
        if not self.adjustment_history:
            return {"message": "No adjustments recorded"}
        
        adjustments = list(self.adjustment_history)
        
        boost_factors = [a.boost_factor for a in adjustments]
        penalty_factors = [a.penalty_factor for a in adjustments]
        sentiment_scores = [a.sentiment_score for a in adjustments]
        
        return {
            "total_adjustments": len(adjustments),
            "avg_boost_factor": np.mean(boost_factors),
            "avg_penalty_factor": np.mean(penalty_factors),
            "avg_sentiment": np.mean(sentiment_scores),
            "emergency_stops": sum(1 for a in adjustments if a.emergency_stop),
            "positive_adjustments": sum(1 for a in adjustments if a.ai_adjusted_signal > a.original_signal),
            "negative_adjustments": sum(1 for a in adjustments if a.ai_adjusted_signal < a.original_signal)
        }

class AITradingIntegrator:
    """
    🚀 Integrador principal del sistema AI Trading
    Coordina análisis de noticias, sentiment y ajustes de trading
    """
    
    def __init__(self):
        self.emergency_manager = NewsBasedEmergencyManager()
        self.signal_booster = AISignalBooster()
        
        # Estado del sistema
        self.last_analysis_time = 0
        self.analysis_interval = 300  # 5 minutos
        self.active_analysis = False
        
        # Cache de análisis reciente
        self.recent_analysis = {
            "sentiment_summary": None,
            "news_articles": [],
            "emergency_alerts": {},
            "timestamp": 0
        }
        
        # Configuración de análisis
        self.analysis_config = {
            "max_news_articles": 30,
            "min_confidence_threshold": 0.3,
            "emergency_recheck_interval": 60,  # 1 minuto para emergencias
            "symbols_to_analyze": settings.symbols
        }
        
        logger.info("🚀 AI Trading Integrator inicializado")
    
    async def run_comprehensive_analysis(self, force_refresh: bool = False) -> Dict:
        """
        🔍 Ejecuta análisis completo de noticias y sentiment
        """
        current_time = time.time()
        
        # Verificar si necesita análisis
        if (not force_refresh and 
            current_time - self.last_analysis_time < self.analysis_interval and
            self.recent_analysis["sentiment_summary"] is not None):
            logger.debug("📋 Usando análisis reciente del cache")
            return self.recent_analysis
        
        if self.active_analysis:
            logger.debug("⏳ Análisis ya en progreso...")
            return self.recent_analysis
        
        self.active_analysis = True
        logger.info("🔍 Iniciando análisis completo AI Trading...")
        
        try:
            # 1. Obtener noticias recientes
            news_articles = await get_latest_news(
                self.analysis_config["symbols_to_analyze"],
                self.analysis_config["max_news_articles"]
            )
            
            if not news_articles:
                logger.warning("⚠️ No se obtuvieron noticias para análisis")
                return self.recent_analysis
            
            # 2. Análizar sentiment
            sentiment_summary = await analyze_news_sentiment(
                news_articles, 
                self.analysis_config["symbols_to_analyze"]
            )
            
            # 3. Evaluar emergencias
            emergency_alerts = self.emergency_manager.evaluate_emergency_conditions(
                sentiment_summary, news_articles
            )
            
            # 4. Actualizar cache
            self.recent_analysis = {
                "sentiment_summary": sentiment_summary,
                "news_articles": news_articles,
                "emergency_alerts": emergency_alerts,
                "timestamp": current_time
            }
            
            self.last_analysis_time = current_time
            
            logger.info(f"✅ Análisis completado: {len(news_articles)} noticias, "
                       f"sentiment {sentiment_summary.overall_sentiment:.3f}, "
                       f"{len(emergency_alerts)} emergencias")
            
            return self.recent_analysis
            
        except Exception as e:
            logger.error(f"❌ Error en análisis AI: {e}")
            return self.recent_analysis
        
        finally:
            self.active_analysis = False
    
    async def adjust_trading_signal(self, symbol: str, original_signal: float,
                                  current_price: float = 0.0,
                                  market_volatility: float = 0.02) -> TradingSignalAdjustment:
        """
        🎯 Función principal: ajusta señal de trading basada en análisis AI
        """
        
        # Ejecutar análisis si es necesario
        analysis_data = await self.run_comprehensive_analysis()
        
        # Verificar emergencias activas para el símbolo
        emergency_alert = analysis_data["emergency_alerts"].get(symbol)
        market_emergency = analysis_data["emergency_alerts"].get("MARKET")
        
        # Usar emergencia más severa
        if emergency_alert and market_emergency:
            emergency_status = emergency_alert if emergency_alert.alert_level >= market_emergency.alert_level else market_emergency
        else:
            emergency_status = emergency_alert or market_emergency
        
        # Obtener sentiment específico del símbolo
        sentiment_summary = analysis_data["sentiment_summary"]
        symbol_sentiment = sentiment_summary.symbol_sentiments.get(symbol, 0.0)
        
        # Crear SentimentResult básico para el símbolo
        sentiment_result = SentimentResult(
            article_id=f"summary_{symbol}_{time.time()}",
            symbol=symbol,
            sentiment_score=symbol_sentiment,
            confidence=sentiment_summary.confidence,
            sentiment_label=sentiment_summary.market_condition,
            critical_keywords=[e["keywords"][0] if e["keywords"] else "general" 
                             for e in sentiment_summary.critical_events],
            price_impact_prediction={},
            reasoning=sentiment_summary.recommendation,
            timestamp=datetime.now(),
            emotional_intensity=abs(symbol_sentiment),
            market_relevance=0.8,
            urgency_level=3,
            event_type="market_analysis"
        )
        
        # Obtener predicciones de precio si hay precio actual
        price_predictions = {}
        if current_price > 0:
            try:
                price_predictions = await predict_news_price_impact(
                    sentiment_result, current_price, market_volatility
                )
            except Exception as e:
                logger.debug(f"Error obteniendo predicciones de precio: {e}")
        
        # Calcular ajuste de señal
        adjustment = self.signal_booster.calculate_signal_adjustment(
            original_signal, sentiment_result, price_predictions, emergency_status
        )
        
        # Log del ajuste
        change_pct = ((adjustment.ai_adjusted_signal / original_signal) - 1) * 100 if original_signal != 0 else 0
        logger.info(f"🎯 AI Adjustment {symbol}: {original_signal:.3f} → {adjustment.ai_adjusted_signal:.3f} "
                   f"({change_pct:+.1f}%) | Sentiment: {symbol_sentiment:.3f}")
        
        if emergency_status:
            logger.warning(f"⚠️ {symbol} Emergency: {emergency_status.alert_level.name} - {emergency_status.trigger_reason}")
        
        return adjustment
    
    async def get_market_overview(self) -> Dict:
        """
        📊 Obtiene overview completo del mercado con análisis AI
        """
        analysis_data = await self.run_comprehensive_analysis()
        
        sentiment_summary = analysis_data["sentiment_summary"]
        emergency_alerts = analysis_data["emergency_alerts"]
        
        # Estadísticas del sistema
        booster_stats = self.signal_booster.get_adjustment_statistics()
        active_emergencies = self.emergency_manager.get_active_emergencies()
        
        return {
            "market_sentiment": {
                "overall_score": sentiment_summary.overall_sentiment if sentiment_summary else 0.0,
                "market_condition": sentiment_summary.market_condition if sentiment_summary else "unknown",
                "confidence": sentiment_summary.confidence if sentiment_summary else 0.0,
                "symbol_sentiments": sentiment_summary.symbol_sentiments if sentiment_summary else {}
            },
            "emergency_status": {
                "active_alerts": len(active_emergencies),
                "highest_level": max([a.alert_level.value for a in active_emergencies.values()]) if active_emergencies else 0,
                "affected_symbols": list(active_emergencies.keys())
            },
            "ai_adjustments": booster_stats,
            "system_status": {
                "last_analysis": datetime.fromtimestamp(self.last_analysis_time) if self.last_analysis_time > 0 else None,
                "news_articles_count": len(analysis_data["news_articles"]),
                "analysis_active": self.active_analysis
            },
            "recommendations": sentiment_summary.recommendation if sentiment_summary else "No analysis available"
        }
    
    def get_symbol_ai_status(self, symbol: str) -> Dict:
        """Estado de IA específico para un símbolo"""
        
        analysis_data = self.recent_analysis
        
        if not analysis_data["sentiment_summary"]:
            return {"status": "no_analysis", "message": "No AI analysis available"}
        
        sentiment_summary = analysis_data["sentiment_summary"]
        emergency_alerts = analysis_data["emergency_alerts"]
        
        symbol_sentiment = sentiment_summary.symbol_sentiments.get(symbol, 0.0)
        symbol_emergency = emergency_alerts.get(symbol)
        
        return {
            "sentiment_score": symbol_sentiment,
            "market_condition": sentiment_summary.market_condition,
            "emergency_status": {
                "active": symbol_emergency is not None,
                "level": symbol_emergency.alert_level.name if symbol_emergency else "NONE",
                "reason": symbol_emergency.trigger_reason if symbol_emergency else None
            },
            "last_analysis": datetime.fromtimestamp(analysis_data["timestamp"]) if analysis_data["timestamp"] > 0 else None
        }

# Instancia global del integrador
ai_trading_integrator = AITradingIntegrator()

# Funciones de conveniencia para el bot principal
async def get_ai_adjusted_signal(symbol: str, original_signal: float,
                               current_price: float = 0.0,
                               market_volatility: float = 0.02) -> TradingSignalAdjustment:
    """
    🎯 Función principal para obtener señal ajustada por IA
    """
    return await ai_trading_integrator.adjust_trading_signal(
        symbol, original_signal, current_price, market_volatility
    )

async def check_emergency_stops() -> Dict[str, EmergencyAlert]:
    """
    🚨 Verificar stops de emergencia activos
    """
    analysis_data = await ai_trading_integrator.run_comprehensive_analysis()
    return analysis_data["emergency_alerts"]

async def get_ai_market_overview() -> Dict:
    """
    📊 Overview completo del mercado con IA
    """
    return await ai_trading_integrator.get_market_overview()

def get_ai_symbol_status(symbol: str) -> Dict:
    """
    📈 Estado de IA para un símbolo específico
    """
    return ai_trading_integrator.get_symbol_ai_status(symbol)

def force_emergency_resolution(symbol: str, reason: str = "Manual override"):
    """
    🔧 Forzar resolución de emergencia
    """
    ai_trading_integrator.emergency_manager.resolve_emergency(symbol, reason)

# Background task para monitoreo continuo
async def start_ai_monitoring_background():
    """
    🔄 Inicia monitoreo de IA en background
    """
    logger.info("🔄 Iniciando monitoreo AI en background...")
    
    while True:
        try:
            # Análisis cada 5 minutos
            await ai_trading_integrator.run_comprehensive_analysis()
            
            # Verificar emergencias cada minuto
            for _ in range(5):
                await asyncio.sleep(60)
                
                # Re-evaluar emergencias si están activas
                active_emergencies = ai_trading_integrator.emergency_manager.get_active_emergencies()
                if active_emergencies:
                    logger.debug("🔍 Re-evaluando emergencias activas...")
                    await ai_trading_integrator.run_comprehensive_analysis(force_refresh=True)
        
        except Exception as e:
            logger.error(f"❌ Error en monitoreo AI background: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    # Test del sistema
    async def test_ai_integration():
        logger.info("🧪 Testing AI Trading Integration...")
        
        # Test de ajuste de señal
        test_signal = 0.5
        test_symbol = "BTC/USD"
        
        adjustment = await get_ai_adjusted_signal(
            test_symbol, test_signal, 45000.0, 0.03
        )
        
        print(f"\n✅ Ajuste de señal:")
        print(f"Original: {adjustment.original_signal:.3f}")
        print(f"Ajustada: {adjustment.ai_adjusted_signal:.3f}")
        print(f"Sentiment: {adjustment.sentiment_score:.3f}")
        print(f"Emergency: {adjustment.emergency_stop}")
        print(f"Recomendación: {adjustment.recommendation}")
        
        # Test de overview del mercado
        overview = await get_ai_market_overview()
        print(f"\n📊 Market Overview:")
        print(f"Sentiment general: {overview['market_sentiment']['overall_score']:.3f}")
        print(f"Condición: {overview['market_sentiment']['market_condition']}")
        print(f"Emergencias activas: {overview['emergency_status']['active_alerts']}")
    
    asyncio.run(test_ai_integration())