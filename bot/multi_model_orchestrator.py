#!/usr/bin/env python3
"""
🎭 MULTI-MODEL ORCHESTRATOR - INSTITUTIONAL GRADE
Advanced ensemble orchestration system for superior trading predictions
- Ensemble Intelligence Engine with Weighted Voting
- Model Specialization Router for Dynamic Selection
- Performance Optimization Layer with Caching & Parallelism
- Advanced Analytics Integration with Consensus Scoring
- Real-time Learning System with Adaptive Weights
- Uncertainty Quantification & Disagreement Analysis
"""
import os
import json
import asyncio
import time
import hashlib
import pickle
import sqlite3
import threading
import statistics
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from loguru import logger
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, deque
import psutil
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.ensemble import VotingClassifier, VotingRegressor
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings("ignore")

# Import existing LocalAI components
from .localai_institutional_manager import LocalAIInstitutionalManager, ModelConfig, PerformanceMetrics
from .localai_trading_models import TradingModelOutput, ModelPerformance, FinancialSentimentModel, TechnicalAnalysisModel
from .localai_performance_optimizer import SystemResources, PerformanceProfile

class ModelRole(Enum):
    """Specialized roles for different models"""
    SENTIMENT_ANALYZER = "sentiment_analyzer"
    TECHNICAL_PREDICTOR = "technical_predictor" 
    RISK_ASSESSOR = "risk_assessor"
    NEWS_ANALYZER = "news_analyzer"
    MARKET_SCANNER = "market_scanner"
    VOLATILITY_PREDICTOR = "volatility_predictor"
    MOMENTUM_DETECTOR = "momentum_detector"
    ARBITRAGE_FINDER = "arbitrage_finder"

class ConsensusType(Enum):
    """Types of consensus mechanisms"""
    SIMPLE_MAJORITY = "simple_majority"
    WEIGHTED_AVERAGE = "weighted_average"
    CONFIDENCE_WEIGHTED = "confidence_weighted"
    PERFORMANCE_WEIGHTED = "performance_weighted"
    DYNAMIC_WEIGHTED = "dynamic_weighted"
    BAYESIAN_ENSEMBLE = "bayesian_ensemble"

class OrchestrationMode(Enum):
    """Orchestration operation modes"""
    SPEED_OPTIMIZED = "speed_optimized"        # Fastest models first
    ACCURACY_OPTIMIZED = "accuracy_optimized"  # Best models regardless of speed
    BALANCED = "balanced"                      # Balance speed vs accuracy
    CONSENSUS_REQUIRED = "consensus_required"  # Wait for all models
    ADAPTIVE = "adaptive"                      # Dynamic based on market conditions

@dataclass
class ModelWeight:
    """Dynamic weight for each model in ensemble"""
    model_name: str
    base_weight: float
    performance_weight: float
    confidence_weight: float
    recency_weight: float
    specialization_weight: float
    final_weight: float
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class EnsemblePrediction:
    """Result from ensemble model orchestration"""
    prediction_value: Union[float, str, Dict]
    confidence_score: float
    consensus_strength: float
    disagreement_score: float
    models_used: List[str]
    model_weights: Dict[str, float]
    individual_predictions: Dict[str, TradingModelOutput]
    execution_time: float
    reasoning: str
    uncertainty_bounds: Tuple[float, float]
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OrchestrationTask:
    """Task for model orchestration"""
    task_id: str
    query: str
    symbol: str
    analysis_type: str  # sentiment, technical, risk, news, comprehensive
    priority: int  # 1-10
    timeout: float  # seconds
    required_models: List[str]
    optional_models: List[str]
    consensus_type: ConsensusType
    min_confidence: float
    context: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

class ModelCache:
    """
    🗄️ Intelligent Model Result Caching System
    """
    
    def __init__(self, cache_dir: str = "data_cache/model_cache", max_size_mb: int = 512):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_mb = max_size_mb
        self.cache_index = {}
        self.access_times = {}
        self.hit_count = 0
        self.miss_count = 0
        
        # Load existing cache index
        self._load_cache_index()
        
        # Setup periodic cleanup
        self.cleanup_thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
        self.cleanup_thread.start()
    
    def _generate_cache_key(self, query: str, symbol: str, model_name: str, context: Dict) -> str:
        """Generate unique cache key"""
        cache_data = {
            "query": query.lower().strip(),
            "symbol": symbol.upper(),
            "model": model_name,
            "context_hash": hashlib.md5(json.dumps(context, sort_keys=True).encode()).hexdigest()[:8]
        }
        key_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]
    
    def get(self, query: str, symbol: str, model_name: str, context: Dict, max_age_minutes: int = 5) -> Optional[TradingModelOutput]:
        """Get cached result if available and not expired"""
        cache_key = self._generate_cache_key(query, symbol, model_name, context)
        
        if cache_key not in self.cache_index:
            self.miss_count += 1
            return None
        
        cache_entry = self.cache_index[cache_key]
        
        # Check if expired
        age_minutes = (datetime.now() - cache_entry["timestamp"]).total_seconds() / 60
        if age_minutes > max_age_minutes:
            self._remove_cache_entry(cache_key)
            self.miss_count += 1
            return None
        
        # Load from disk
        try:
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            with open(cache_file, 'rb') as f:
                result = pickle.load(f)
            
            self.access_times[cache_key] = datetime.now()
            self.hit_count += 1
            return result
            
        except Exception as e:
            logger.debug(f"Cache read error for {cache_key}: {e}")
            self._remove_cache_entry(cache_key)
            self.miss_count += 1
            return None
    
    def put(self, query: str, symbol: str, model_name: str, context: Dict, result: TradingModelOutput):
        """Cache model result"""
        cache_key = self._generate_cache_key(query, symbol, model_name, context)
        
        try:
            # Save to disk
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            with open(cache_file, 'wb') as f:
                pickle.dump(result, f)
            
            # Update index
            self.cache_index[cache_key] = {
                "timestamp": datetime.now(),
                "size": cache_file.stat().st_size,
                "model": model_name,
                "symbol": symbol
            }
            self.access_times[cache_key] = datetime.now()
            
            self._save_cache_index()
            self._check_cache_size()
            
        except Exception as e:
            logger.debug(f"Cache write error for {cache_key}: {e}")
    
    def _load_cache_index(self):
        """Load cache index from disk"""
        index_file = self.cache_dir / "cache_index.json"
        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    data = json.load(f)
                    for key, entry in data.items():
                        entry["timestamp"] = datetime.fromisoformat(entry["timestamp"])
                    self.cache_index = data
            except Exception as e:
                logger.debug(f"Cache index load error: {e}")
                self.cache_index = {}
    
    def _save_cache_index(self):
        """Save cache index to disk"""
        try:
            index_file = self.cache_dir / "cache_index.json"
            data = {}
            for key, entry in self.cache_index.items():
                data[key] = entry.copy()
                data[key]["timestamp"] = entry["timestamp"].isoformat()
            
            with open(index_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.debug(f"Cache index save error: {e}")
    
    def _check_cache_size(self):
        """Check and manage cache size"""
        total_size = sum(entry["size"] for entry in self.cache_index.values())
        max_size_bytes = self.max_size_mb * 1024 * 1024
        
        if total_size > max_size_bytes:
            # Remove oldest accessed entries
            sorted_keys = sorted(
                self.cache_index.keys(),
                key=lambda k: self.access_times.get(k, datetime.min)
            )
            
            removed_size = 0
            target_removal = total_size - (max_size_bytes * 0.8)  # Remove to 80% capacity
            
            for key in sorted_keys:
                if removed_size >= target_removal:
                    break
                
                removed_size += self.cache_index[key]["size"]
                self._remove_cache_entry(key)
    
    def _remove_cache_entry(self, cache_key: str):
        """Remove cache entry"""
        try:
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            if cache_file.exists():
                cache_file.unlink()
            
            self.cache_index.pop(cache_key, None)
            self.access_times.pop(cache_key, None)
        except Exception as e:
            logger.debug(f"Cache entry removal error: {e}")
    
    def _periodic_cleanup(self):
        """Periodic cache cleanup"""
        while True:
            try:
                time.sleep(300)  # Every 5 minutes
                self._check_cache_size()
                self._save_cache_index()
            except Exception as e:
                logger.debug(f"Cache cleanup error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0
        
        total_size = sum(entry["size"] for entry in self.cache_index.values())
        
        return {
            "hit_rate": hit_rate,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "total_entries": len(self.cache_index),
            "total_size_mb": total_size / (1024 * 1024),
            "max_size_mb": self.max_size_mb
        }

class EnsembleIntelligence:
    """
    🧠 Advanced Ensemble Intelligence Engine
    Combines multiple models with sophisticated weighting and consensus mechanisms
    """
    
    def __init__(self):
        self.model_weights: Dict[str, ModelWeight] = {}
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.consensus_weights = {
            ConsensusType.SIMPLE_MAJORITY: 1.0,
            ConsensusType.WEIGHTED_AVERAGE: 1.2,
            ConsensusType.CONFIDENCE_WEIGHTED: 1.5,
            ConsensusType.PERFORMANCE_WEIGHTED: 1.8,
            ConsensusType.DYNAMIC_WEIGHTED: 2.0,
            ConsensusType.BAYESIAN_ENSEMBLE: 2.5
        }
        
        # Load historical weights
        self._load_model_weights()
    
    def calculate_ensemble_prediction(
        self,
        predictions: Dict[str, TradingModelOutput],
        consensus_type: ConsensusType = ConsensusType.DYNAMIC_WEIGHTED,
        context: Dict[str, Any] = None
    ) -> EnsemblePrediction:
        """Calculate ensemble prediction from multiple model outputs"""
        start_time = time.time()
        
        if not predictions:
            raise ValueError("No predictions provided for ensemble")
        
        # Update model weights based on recent performance
        self._update_dynamic_weights(predictions, context)
        
        # Calculate ensemble prediction based on consensus type
        if consensus_type == ConsensusType.SIMPLE_MAJORITY:
            result = self._simple_majority_consensus(predictions)
        elif consensus_type == ConsensusType.WEIGHTED_AVERAGE:
            result = self._weighted_average_consensus(predictions)
        elif consensus_type == ConsensusType.CONFIDENCE_WEIGHTED:
            result = self._confidence_weighted_consensus(predictions)
        elif consensus_type == ConsensusType.PERFORMANCE_WEIGHTED:
            result = self._performance_weighted_consensus(predictions)
        elif consensus_type == ConsensusType.DYNAMIC_WEIGHTED:
            result = self._dynamic_weighted_consensus(predictions, context)
        elif consensus_type == ConsensusType.BAYESIAN_ENSEMBLE:
            result = self._bayesian_ensemble_consensus(predictions)
        else:
            result = self._weighted_average_consensus(predictions)
        
        # Calculate consensus metrics
        consensus_strength = self._calculate_consensus_strength(predictions)
        disagreement_score = self._calculate_disagreement_score(predictions)
        uncertainty_bounds = self._calculate_uncertainty_bounds(predictions)
        
        # Generate reasoning
        reasoning = self._generate_ensemble_reasoning(predictions, consensus_type, context)
        
        execution_time = time.time() - start_time
        
        return EnsemblePrediction(
            prediction_value=result["prediction"],
            confidence_score=result["confidence"],
            consensus_strength=consensus_strength,
            disagreement_score=disagreement_score,
            models_used=list(predictions.keys()),
            model_weights=result["weights"],
            individual_predictions=predictions,
            execution_time=execution_time,
            reasoning=reasoning,
            uncertainty_bounds=uncertainty_bounds,
            metadata={
                "consensus_type": consensus_type.value,
                "total_models": len(predictions),
                "context_included": context is not None
            }
        )
    
    def _simple_majority_consensus(self, predictions: Dict[str, TradingModelOutput]) -> Dict[str, Any]:
        """Simple majority voting consensus"""
        if not predictions:
            return {"prediction": 0.0, "confidence": 0.0, "weights": {}}
        
        # For numerical predictions, use average
        values = []
        confidences = []
        
        for model_name, pred in predictions.items():
            if isinstance(pred.prediction, (int, float)):
                values.append(pred.prediction)
                confidences.append(pred.confidence)
        
        if not values:
            return {"prediction": 0.0, "confidence": 0.0, "weights": {}}
        
        prediction = statistics.mean(values)
        confidence = statistics.mean(confidences)
        weights = {name: 1.0/len(predictions) for name in predictions.keys()}
        
        return {"prediction": prediction, "confidence": confidence, "weights": weights}
    
    def _weighted_average_consensus(self, predictions: Dict[str, TradingModelOutput]) -> Dict[str, Any]:
        """Weighted average based on base model weights"""
        if not predictions:
            return {"prediction": 0.0, "confidence": 0.0, "weights": {}}
        
        total_weight = 0.0
        weighted_sum = 0.0
        weighted_confidence = 0.0
        weights = {}
        
        for model_name, pred in predictions.items():
            weight = self.model_weights.get(model_name, ModelWeight(
                model_name=model_name, base_weight=1.0, performance_weight=1.0,
                confidence_weight=1.0, recency_weight=1.0, specialization_weight=1.0,
                final_weight=1.0
            )).final_weight
            
            if isinstance(pred.prediction, (int, float)):
                weighted_sum += pred.prediction * weight
                weighted_confidence += pred.confidence * weight
                total_weight += weight
                weights[model_name] = weight
        
        if total_weight == 0:
            return {"prediction": 0.0, "confidence": 0.0, "weights": weights}
        
        prediction = weighted_sum / total_weight
        confidence = weighted_confidence / total_weight
        
        # Normalize weights
        weights = {name: w/total_weight for name, w in weights.items()}
        
        return {"prediction": prediction, "confidence": confidence, "weights": weights}
    
    def _confidence_weighted_consensus(self, predictions: Dict[str, TradingModelOutput]) -> Dict[str, Any]:
        """Weighted consensus based on prediction confidence"""
        if not predictions:
            return {"prediction": 0.0, "confidence": 0.0, "weights": {}}
        
        total_weight = 0.0
        weighted_sum = 0.0
        avg_confidence = 0.0
        weights = {}
        
        for model_name, pred in predictions.items():
            weight = pred.confidence
            
            if isinstance(pred.prediction, (int, float)):
                weighted_sum += pred.prediction * weight
                total_weight += weight
                weights[model_name] = weight
                avg_confidence += pred.confidence
        
        if total_weight == 0:
            return {"prediction": 0.0, "confidence": 0.0, "weights": weights}
        
        prediction = weighted_sum / total_weight
        confidence = avg_confidence / len(predictions)
        
        # Normalize weights
        weights = {name: w/total_weight for name, w in weights.items()}
        
        return {"prediction": prediction, "confidence": confidence, "weights": weights}
    
    def _performance_weighted_consensus(self, predictions: Dict[str, TradingModelOutput]) -> Dict[str, Any]:
        """Weighted consensus based on historical model performance"""
        if not predictions:
            return {"prediction": 0.0, "confidence": 0.0, "weights": {}}
        
        total_weight = 0.0
        weighted_sum = 0.0
        weighted_confidence = 0.0
        weights = {}
        
        for model_name, pred in predictions.items():
            # Use performance history for weighting
            performance_history = self.performance_history.get(model_name, deque())
            if performance_history:
                # Recent performance average
                recent_performance = statistics.mean(list(performance_history)[-10:])
                weight = max(0.1, recent_performance)  # Minimum weight of 0.1
            else:
                weight = 0.5  # Default weight for new models
            
            if isinstance(pred.prediction, (int, float)):
                weighted_sum += pred.prediction * weight
                weighted_confidence += pred.confidence * weight
                total_weight += weight
                weights[model_name] = weight
        
        if total_weight == 0:
            return {"prediction": 0.0, "confidence": 0.0, "weights": weights}
        
        prediction = weighted_sum / total_weight
        confidence = weighted_confidence / total_weight
        
        # Normalize weights
        weights = {name: w/total_weight for name, w in weights.items()}
        
        return {"prediction": prediction, "confidence": confidence, "weights": weights}
    
    def _dynamic_weighted_consensus(self, predictions: Dict[str, TradingModelOutput], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Advanced dynamic weighting based on multiple factors"""
        if not predictions:
            return {"prediction": 0.0, "confidence": 0.0, "weights": {}}
        
        total_weight = 0.0
        weighted_sum = 0.0
        weighted_confidence = 0.0
        weights = {}
        
        # Context-based adjustments
        market_volatility = context.get("volatility", 0.5) if context else 0.5
        time_of_day_factor = context.get("time_factor", 1.0) if context else 1.0
        
        for model_name, pred in predictions.items():
            model_weight = self.model_weights.get(model_name)
            if not model_weight:
                # Create default weight
                model_weight = ModelWeight(
                    model_name=model_name,
                    base_weight=1.0,
                    performance_weight=1.0,
                    confidence_weight=pred.confidence,
                    recency_weight=1.0,
                    specialization_weight=1.0,
                    final_weight=1.0
                )
                self.model_weights[model_name] = model_weight
            
            # Dynamic weight calculation
            dynamic_weight = (
                model_weight.base_weight * 0.3 +
                model_weight.performance_weight * 0.25 +
                model_weight.confidence_weight * 0.2 +
                model_weight.recency_weight * 0.15 +
                model_weight.specialization_weight * 0.1
            )
            
            # Adjust for market conditions
            if market_volatility > 0.7:  # High volatility
                if "risk" in model_name.lower():
                    dynamic_weight *= 1.5  # Increase risk model weight
                elif "technical" in model_name.lower():
                    dynamic_weight *= 1.2  # Increase technical analysis weight
            
            # Time-based adjustments
            dynamic_weight *= time_of_day_factor
            
            if isinstance(pred.prediction, (int, float)):
                weighted_sum += pred.prediction * dynamic_weight
                weighted_confidence += pred.confidence * dynamic_weight
                total_weight += dynamic_weight
                weights[model_name] = dynamic_weight
        
        if total_weight == 0:
            return {"prediction": 0.0, "confidence": 0.0, "weights": weights}
        
        prediction = weighted_sum / total_weight
        confidence = weighted_confidence / total_weight
        
        # Normalize weights
        weights = {name: w/total_weight for name, w in weights.items()}
        
        return {"prediction": prediction, "confidence": confidence, "weights": weights}
    
    def _bayesian_ensemble_consensus(self, predictions: Dict[str, TradingModelOutput]) -> Dict[str, Any]:
        """Bayesian ensemble with uncertainty quantification"""
        if not predictions:
            return {"prediction": 0.0, "confidence": 0.0, "weights": {}}
        
        # Bayesian updating based on confidence and historical accuracy
        total_precision = 0.0
        weighted_sum = 0.0
        weights = {}
        
        for model_name, pred in predictions.items():
            # Use confidence as precision (inverse of variance)
            precision = pred.confidence ** 2
            
            # Adjust precision based on historical performance
            performance_history = self.performance_history.get(model_name, deque())
            if performance_history:
                accuracy_factor = statistics.mean(list(performance_history)[-5:])
                precision *= accuracy_factor
            
            if isinstance(pred.prediction, (int, float)):
                weighted_sum += pred.prediction * precision
                total_precision += precision
                weights[model_name] = precision
        
        if total_precision == 0:
            return {"prediction": 0.0, "confidence": 0.0, "weights": weights}
        
        prediction = weighted_sum / total_precision
        confidence = min(0.95, total_precision / len(predictions))  # Ensemble confidence
        
        # Normalize weights
        weights = {name: w/total_precision for name, w in weights.items()}
        
        return {"prediction": prediction, "confidence": confidence, "weights": weights}
    
    def _calculate_consensus_strength(self, predictions: Dict[str, TradingModelOutput]) -> float:
        """Calculate how much models agree"""
        if len(predictions) < 2:
            return 1.0
        
        values = []
        for pred in predictions.values():
            if isinstance(pred.prediction, (int, float)):
                values.append(pred.prediction)
        
        if len(values) < 2:
            return 1.0
        
        # Calculate coefficient of variation (lower = higher consensus)
        mean_val = statistics.mean(values)
        if mean_val == 0:
            return 1.0
        
        std_val = statistics.stdev(values) if len(values) > 1 else 0
        cv = std_val / abs(mean_val)
        
        # Convert to consensus strength (0-1, higher = better consensus)
        consensus_strength = max(0.0, 1.0 - min(1.0, cv))
        return consensus_strength
    
    def _calculate_disagreement_score(self, predictions: Dict[str, TradingModelOutput]) -> float:
        """Calculate disagreement score between models"""
        if len(predictions) < 2:
            return 0.0
        
        values = []
        confidences = []
        
        for pred in predictions.values():
            if isinstance(pred.prediction, (int, float)):
                values.append(pred.prediction)
                confidences.append(pred.confidence)
        
        if len(values) < 2:
            return 0.0
        
        # Calculate range normalized by confidence
        value_range = max(values) - min(values)
        avg_confidence = statistics.mean(confidences)
        
        # Disagreement is higher when range is large and confidence is high
        disagreement = value_range * avg_confidence
        
        return min(1.0, disagreement)
    
    def _calculate_uncertainty_bounds(self, predictions: Dict[str, TradingModelOutput]) -> Tuple[float, float]:
        """Calculate uncertainty bounds for ensemble prediction"""
        values = []
        confidences = []
        
        for pred in predictions.values():
            if isinstance(pred.prediction, (int, float)):
                values.append(pred.prediction)
                confidences.append(pred.confidence)
        
        if not values:
            return (0.0, 0.0)
        
        mean_val = statistics.mean(values)
        
        if len(values) == 1:
            confidence = confidences[0]
            uncertainty = (1.0 - confidence) * abs(mean_val) * 0.5
            return (mean_val - uncertainty, mean_val + uncertainty)
        
        std_val = statistics.stdev(values)
        avg_confidence = statistics.mean(confidences)
        
        # Uncertainty based on standard deviation and confidence
        uncertainty = std_val * (2.0 - avg_confidence)  # Lower confidence = higher uncertainty
        
        return (mean_val - uncertainty, mean_val + uncertainty)
    
    def _generate_ensemble_reasoning(
        self,
        predictions: Dict[str, TradingModelOutput],
        consensus_type: ConsensusType,
        context: Dict[str, Any] = None
    ) -> str:
        """Generate human-readable reasoning for ensemble decision"""
        reasoning_parts = []
        
        # Consensus information
        reasoning_parts.append(f"Ensemble of {len(predictions)} models using {consensus_type.value}")
        
        # Individual model contributions
        top_models = sorted(
            predictions.items(),
            key=lambda x: x[1].confidence,
            reverse=True
        )[:3]  # Top 3 models
        
        for model_name, pred in top_models:
            weight = self.model_weights.get(model_name)
            weight_val = weight.final_weight if weight else 1.0
            reasoning_parts.append(
                f"{model_name}: {pred.prediction:.3f} (confidence: {pred.confidence:.2f}, weight: {weight_val:.2f})"
            )
        
        # Consensus metrics
        consensus_strength = self._calculate_consensus_strength(predictions)
        disagreement_score = self._calculate_disagreement_score(predictions)
        
        reasoning_parts.append(f"Consensus strength: {consensus_strength:.2f}")
        reasoning_parts.append(f"Disagreement score: {disagreement_score:.2f}")
        
        # Context considerations
        if context:
            if context.get("volatility", 0) > 0.7:
                reasoning_parts.append("High volatility detected - increased risk model weighting")
            if context.get("time_factor", 1.0) != 1.0:
                reasoning_parts.append(f"Time-based adjustment applied: {context['time_factor']:.2f}")
        
        return " | ".join(reasoning_parts)
    
    def _update_dynamic_weights(self, predictions: Dict[str, TradingModelOutput], context: Dict[str, Any] = None):
        """Update model weights based on current predictions and context"""
        for model_name, pred in predictions.items():
            if model_name not in self.model_weights:
                self.model_weights[model_name] = ModelWeight(
                    model_name=model_name,
                    base_weight=1.0,
                    performance_weight=1.0,
                    confidence_weight=pred.confidence,
                    recency_weight=1.0,
                    specialization_weight=1.0,
                    final_weight=1.0
                )
            
            weight = self.model_weights[model_name]
            
            # Update confidence weight
            weight.confidence_weight = 0.8 * weight.confidence_weight + 0.2 * pred.confidence
            
            # Update recency weight (decay over time)
            time_since_update = (datetime.now() - weight.last_updated).total_seconds() / 3600  # hours
            decay_factor = np.exp(-time_since_update / 24)  # 24-hour half-life
            weight.recency_weight *= decay_factor
            
            # Calculate final weight
            weight.final_weight = (
                weight.base_weight * 0.3 +
                weight.performance_weight * 0.25 +
                weight.confidence_weight * 0.2 +
                weight.recency_weight * 0.15 +
                weight.specialization_weight * 0.1
            )
            
            weight.last_updated = datetime.now()
    
    def update_model_performance(self, model_name: str, accuracy: float, prediction_correct: bool):
        """Update model performance tracking"""
        if model_name not in self.performance_history:
            self.performance_history[model_name] = deque(maxlen=1000)
        
        self.performance_history[model_name].append(accuracy)
        
        # Update performance weight
        if model_name in self.model_weights:
            weight = self.model_weights[model_name]
            recent_performance = statistics.mean(list(self.performance_history[model_name])[-10:])
            weight.performance_weight = 0.7 * weight.performance_weight + 0.3 * recent_performance
    
    def _load_model_weights(self):
        """Load model weights from disk"""
        weights_file = Path("bot/ensemble_weights.json")
        if weights_file.exists():
            try:
                with open(weights_file, 'r') as f:
                    data = json.load(f)
                    for model_name, weight_data in data.items():
                        weight_data["last_updated"] = datetime.fromisoformat(weight_data["last_updated"])
                        self.model_weights[model_name] = ModelWeight(**weight_data)
                logger.info(f"✅ Loaded {len(self.model_weights)} model weights")
            except Exception as e:
                logger.debug(f"Weight loading error: {e}")
    
    def save_model_weights(self):
        """Save model weights to disk"""
        try:
            weights_file = Path("bot/ensemble_weights.json")
            data = {}
            for model_name, weight in self.model_weights.items():
                data[model_name] = asdict(weight)
                data[model_name]["last_updated"] = weight.last_updated.isoformat()
            
            with open(weights_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.debug(f"Weight saving error: {e}")

class ModelSpecializationRouter:
    """
    🎯 Intelligent Model Specialization Router
    Dynamically selects optimal models based on query type and market conditions
    """
    
    def __init__(self):
        self.model_specializations = {
            # Sentiment Analysis Tasks
            "sentiment": [ModelRole.SENTIMENT_ANALYZER, ModelRole.NEWS_ANALYZER],
            "news_impact": [ModelRole.NEWS_ANALYZER, ModelRole.SENTIMENT_ANALYZER, ModelRole.MARKET_SCANNER],
            
            # Technical Analysis Tasks
            "technical": [ModelRole.TECHNICAL_PREDICTOR, ModelRole.MOMENTUM_DETECTOR],
            "price_prediction": [ModelRole.TECHNICAL_PREDICTOR, ModelRole.VOLATILITY_PREDICTOR],
            "trend_analysis": [ModelRole.TECHNICAL_PREDICTOR, ModelRole.MOMENTUM_DETECTOR, ModelRole.MARKET_SCANNER],
            
            # Risk Assessment Tasks
            "risk": [ModelRole.RISK_ASSESSOR, ModelRole.VOLATILITY_PREDICTOR],
            "portfolio_risk": [ModelRole.RISK_ASSESSOR, ModelRole.MARKET_SCANNER],
            
            # Market Analysis Tasks
            "market_overview": [ModelRole.MARKET_SCANNER, ModelRole.SENTIMENT_ANALYZER, ModelRole.TECHNICAL_PREDICTOR],
            "comprehensive": [role for role in ModelRole],  # All models
            
            # Specialized Tasks
            "arbitrage": [ModelRole.ARBITRAGE_FINDER, ModelRole.TECHNICAL_PREDICTOR],
            "volatility": [ModelRole.VOLATILITY_PREDICTOR, ModelRole.RISK_ASSESSOR],
            "momentum": [ModelRole.MOMENTUM_DETECTOR, ModelRole.TECHNICAL_PREDICTOR]
        }
        
        self.market_condition_adjustments = {
            "high_volatility": {
                ModelRole.RISK_ASSESSOR: 1.5,
                ModelRole.VOLATILITY_PREDICTOR: 1.4,
                ModelRole.TECHNICAL_PREDICTOR: 0.8
            },
            "low_volatility": {
                ModelRole.TECHNICAL_PREDICTOR: 1.3,
                ModelRole.MOMENTUM_DETECTOR: 1.2,
                ModelRole.RISK_ASSESSOR: 0.9
            },
            "trending_market": {
                ModelRole.MOMENTUM_DETECTOR: 1.5,
                ModelRole.TECHNICAL_PREDICTOR: 1.3,
                ModelRole.SENTIMENT_ANALYZER: 1.2
            },
            "sideways_market": {
                ModelRole.MARKET_SCANNER: 1.3,
                ModelRole.ARBITRAGE_FINDER: 1.4,
                ModelRole.RISK_ASSESSOR: 1.1
            }
        }
        
        self.model_registry = {}  # Maps model names to roles
        self.performance_tracker = defaultdict(list)
    
    def register_model(self, model_name: str, role: ModelRole, capabilities: List[str] = None):
        """Register a model with its specialization"""
        self.model_registry[model_name] = {
            "role": role,
            "capabilities": capabilities or [],
            "registered": datetime.now()
        }
        logger.info(f"🎯 Registered model {model_name} with role {role.value}")
    
    def select_models_for_task(
        self,
        analysis_type: str,
        symbol: str = "",
        market_conditions: Dict[str, Any] = None,
        max_models: int = 5,
        min_models: int = 2
    ) -> List[str]:
        """Select optimal models for a given task"""
        
        # Get base model roles for this analysis type
        required_roles = self.model_specializations.get(analysis_type, [ModelRole.MARKET_SCANNER])
        
        # Apply market condition adjustments
        role_weights = {}
        for role in required_roles:
            role_weights[role] = 1.0
        
        if market_conditions:
            for condition, adjustments in self.market_condition_adjustments.items():
                if market_conditions.get(condition, False):
                    for role, multiplier in adjustments.items():
                        if role in role_weights:
                            role_weights[role] *= multiplier
        
        # Find models that match required roles
        selected_models = []
        role_coverage = defaultdict(list)
        
        for model_name, model_info in self.model_registry.items():
            model_role = model_info["role"]
            if model_role in required_roles:
                role_coverage[model_role].append(model_name)
        
        # Select best models for each role
        for role, models in role_coverage.items():
            if not models:
                continue
            
            # Sort by recent performance
            models_with_performance = []
            for model in models:
                recent_performance = self._get_recent_performance(model)
                models_with_performance.append((model, recent_performance))
            
            models_with_performance.sort(key=lambda x: x[1], reverse=True)
            
            # Select top models for this role (considering weight)
            weight = role_weights.get(role, 1.0)
            models_to_select = max(1, int(weight * 2))  # At least 1, up to 2x weight
            
            for model, _ in models_with_performance[:models_to_select]:
                if model not in selected_models:
                    selected_models.append(model)
        
        # Ensure we have minimum required models
        if len(selected_models) < min_models:
            # Add any remaining models to meet minimum
            for model_name in self.model_registry.keys():
                if model_name not in selected_models:
                    selected_models.append(model_name)
                    if len(selected_models) >= min_models:
                        break
        
        # Limit to maximum models
        if len(selected_models) > max_models:
            # Keep the best performing models
            models_with_performance = []
            for model in selected_models:
                performance = self._get_recent_performance(model)
                models_with_performance.append((model, performance))
            
            models_with_performance.sort(key=lambda x: x[1], reverse=True)
            selected_models = [model for model, _ in models_with_performance[:max_models]]
        
        logger.info(f"🎯 Selected {len(selected_models)} models for {analysis_type}: {selected_models}")
        return selected_models
    
    def _get_recent_performance(self, model_name: str) -> float:
        """Get recent performance score for a model"""
        performances = self.performance_tracker.get(model_name, [])
        if not performances:
            return 0.5  # Default for new models
        
        # Return average of last 10 performances
        recent = performances[-10:]
        return statistics.mean(recent)
    
    def update_model_performance(self, model_name: str, performance_score: float):
        """Update performance tracking for a model"""
        self.performance_tracker[model_name].append(performance_score)
        # Keep only last 100 performances
        if len(self.performance_tracker[model_name]) > 100:
            self.performance_tracker[model_name] = self.performance_tracker[model_name][-100:]
    
    def get_model_capabilities(self, model_name: str) -> Dict[str, Any]:
        """Get detailed capabilities of a model"""
        if model_name not in self.model_registry:
            return {}
        
        model_info = self.model_registry[model_name]
        performance = self._get_recent_performance(model_name)
        
        return {
            "role": model_info["role"].value,
            "capabilities": model_info["capabilities"],
            "recent_performance": performance,
            "total_predictions": len(self.performance_tracker.get(model_name, [])),
            "registered": model_info["registered"]
        }

class MultiModelOrchestrator:
    """
    🎭 ADVANCED MULTI-MODEL ORCHESTRATOR
    Institutional-grade orchestration system for superior trading predictions
    """
    
    def __init__(self, config_path: str = "bot/orchestrator_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # Core components
        self.ensemble_intelligence = EnsembleIntelligence()
        self.model_router = ModelSpecializationRouter()
        self.model_cache = ModelCache(
            cache_dir=self.config.get("cache_dir", "data_cache/model_cache"),
            max_size_mb=self.config.get("cache_size_mb", 512)
        )
        
        # Model management
        self.active_models = {}
        self.model_pool = ThreadPoolExecutor(max_workers=self.config.get("max_workers", 8))
        
        # Performance tracking
        self.orchestration_metrics = {
            "total_predictions": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_response_time": 0.0,
            "consensus_scores": [],
            "model_agreement_scores": []
        }
        
        # Learning system
        self.learning_enabled = self.config.get("learning_enabled", True)
        self.adaptation_rate = self.config.get("adaptation_rate", 0.1)
        
        # Initialize database for tracking
        self._init_tracking_database()
        
        logger.info("🎭 Multi-Model Orchestrator initialized with institutional-grade features")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load orchestrator configuration"""
        default_config = {
            "max_workers": 8,
            "cache_size_mb": 512,
            "cache_dir": "data_cache/model_cache",
            "learning_enabled": True,
            "adaptation_rate": 0.1,
            "default_timeout": 30.0,
            "min_confidence": 0.3,
            "consensus_types": {
                "sentiment": "confidence_weighted",
                "technical": "performance_weighted", 
                "risk": "bayesian_ensemble",
                "comprehensive": "dynamic_weighted"
            }
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                logger.warning(f"Config loading error: {e}")
        
        return default_config
    
    def _init_tracking_database(self):
        """Initialize SQLite database for performance tracking"""
        db_path = Path("bot/orchestrator_tracking.db")
        self.db_connection = sqlite3.connect(str(db_path), check_same_thread=False)
        
        # Create tables
        cursor = self.db_connection.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                task_id TEXT,
                symbol TEXT,
                analysis_type TEXT,
                ensemble_prediction REAL,
                confidence_score REAL,
                consensus_strength REAL,
                disagreement_score REAL,
                models_used TEXT,
                execution_time REAL,
                actual_outcome REAL,
                accuracy REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                model_name TEXT,
                symbol TEXT,
                prediction REAL,
                confidence REAL,
                actual_outcome REAL,
                accuracy REAL,
                response_time REAL
            )
        """)
        
        self.db_connection.commit()
    
    async def orchestrate_prediction(
        self,
        task: OrchestrationTask
    ) -> EnsemblePrediction:
        """
        🎯 Main orchestration method - coordinates multiple models for superior predictions
        """
        start_time = time.time()
        
        logger.info(f"🎭 Orchestrating prediction for {task.symbol} - {task.analysis_type}")
        
        try:
            # 1. Model Selection Phase
            selected_models = self.model_router.select_models_for_task(
                analysis_type=task.analysis_type,
                symbol=task.symbol,
                market_conditions=task.context.get("market_conditions"),
                max_models=len(task.required_models) + len(task.optional_models) if task.required_models else 5
            )
            
            # Ensure required models are included
            for required_model in task.required_models:
                if required_model not in selected_models:
                    selected_models.append(required_model)
            
            # 2. Cache Check Phase
            cached_predictions = {}
            models_to_run = []
            
            for model_name in selected_models:
                cached_result = self.model_cache.get(
                    query=task.query,
                    symbol=task.symbol,
                    model_name=model_name,
                    context=task.context,
                    max_age_minutes=self.config.get("cache_max_age_minutes", 5)
                )
                
                if cached_result:
                    cached_predictions[model_name] = cached_result
                    self.orchestration_metrics["cache_hits"] += 1
                else:
                    models_to_run.append(model_name)
                    self.orchestration_metrics["cache_misses"] += 1
            
            # 3. Parallel Model Execution Phase
            fresh_predictions = {}
            if models_to_run:
                fresh_predictions = await self._execute_models_parallel(
                    models=models_to_run,
                    task=task
                )
                
                # Cache fresh predictions
                for model_name, prediction in fresh_predictions.items():
                    self.model_cache.put(
                        query=task.query,
                        symbol=task.symbol,
                        model_name=model_name,
                        context=task.context,
                        result=prediction
                    )
            
            # 4. Combine Cached and Fresh Predictions
            all_predictions = {**cached_predictions, **fresh_predictions}
            
            if not all_predictions:
                raise ValueError("No predictions available from any model")
            
            # 5. Ensemble Intelligence Phase
            ensemble_result = self.ensemble_intelligence.calculate_ensemble_prediction(
                predictions=all_predictions,
                consensus_type=ConsensusType(self.config["consensus_types"].get(task.analysis_type, "dynamic_weighted")),
                context=task.context
            )
            
            # 6. Quality Assessment Phase
            if ensemble_result.confidence_score < task.min_confidence:
                logger.warning(f"⚠️ Low confidence prediction: {ensemble_result.confidence_score:.2f}")
                
                # Try to improve by adding more models or adjusting consensus
                if len(all_predictions) < 5:  # Try adding more models
                    additional_models = self._get_additional_models(task, selected_models)
                    if additional_models:
                        additional_predictions = await self._execute_models_parallel(
                            models=additional_models,
                            task=task
                        )
                        all_predictions.update(additional_predictions)
                        
                        # Recalculate ensemble
                        ensemble_result = self.ensemble_intelligence.calculate_ensemble_prediction(
                            predictions=all_predictions,
                            consensus_type=task.consensus_type,
                            context=task.context
                        )
            
            # 7. Update Metrics and Learning
            execution_time = time.time() - start_time
            ensemble_result.execution_time = execution_time
            
            self._update_orchestration_metrics(ensemble_result)
            
            if self.learning_enabled:
                await self._update_learning_system(task, ensemble_result, all_predictions)
            
            # 8. Store Prediction for Future Learning
            self._store_prediction(task, ensemble_result)
            
            logger.info(f"✅ Orchestration complete: {ensemble_result.confidence_score:.2f} confidence, {execution_time:.2f}s")
            
            return ensemble_result
            
        except Exception as e:
            logger.error(f"❌ Orchestration failed: {e}")
            # Return a fallback prediction
            return EnsemblePrediction(
                prediction_value=0.0,
                confidence_score=0.0,
                consensus_strength=0.0,
                disagreement_score=1.0,
                models_used=[],
                model_weights={},
                individual_predictions={},
                execution_time=time.time() - start_time,
                reasoning=f"Orchestration failed: {str(e)}",
                uncertainty_bounds=(0.0, 0.0),
                metadata={"error": str(e)}
            )
    
    async def _execute_models_parallel(
        self,
        models: List[str],
        task: OrchestrationTask
    ) -> Dict[str, TradingModelOutput]:
        """Execute multiple models in parallel for optimal performance"""
        
        if not models:
            return {}
        
        # Create futures for parallel execution
        futures = {}
        predictions = {}
        
        with ThreadPoolExecutor(max_workers=min(len(models), self.config["max_workers"])) as executor:
            # Submit all model tasks
            for model_name in models:
                if model_name in self.active_models:
                    future = executor.submit(
                        self._execute_single_model,
                        model_name,
                        task
                    )
                    futures[future] = model_name
            
            # Collect results with timeout handling
            for future in as_completed(futures, timeout=task.timeout):
                model_name = futures[future]
                try:
                    result = future.result()
                    if result:
                        predictions[model_name] = result
                        
                        # Update model performance tracking
                        self.model_router.update_model_performance(
                            model_name=model_name,
                            performance_score=result.confidence
                        )
                        
                except Exception as e:
                    logger.warning(f"⚠️ Model {model_name} execution failed: {e}")
                    continue
        
        return predictions
    
    def _execute_single_model(self, model_name: str, task: OrchestrationTask) -> Optional[TradingModelOutput]:
        """Execute a single model and return its prediction"""
        try:
            if model_name not in self.active_models:
                logger.warning(f"⚠️ Model {model_name} not active")
                return None
            
            model = self.active_models[model_name]
            
            # Execute model based on its type
            if hasattr(model, 'predict'):
                # ML model interface
                result = model.predict(task.query, task.symbol, task.context)
            elif hasattr(model, 'analyze'):
                # Analysis model interface
                result = model.analyze(task.query, task.symbol, task.context)
            elif callable(model):
                # Function interface
                result = model(task.query, task.symbol, task.context)
            else:
                logger.warning(f"⚠️ Unknown model interface for {model_name}")
                return None
            
            # Ensure result is a TradingModelOutput
            if not isinstance(result, TradingModelOutput):
                # Convert to TradingModelOutput if needed
                result = TradingModelOutput(
                    model_name=model_name,
                    symbol=task.symbol,
                    prediction=result if isinstance(result, (int, float)) else 0.0,
                    confidence=0.5,
                    reasoning=f"Prediction from {model_name}",
                    features_used=["unknown"]
                )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Model {model_name} execution error: {e}")
            return None
    
    def _get_additional_models(self, task: OrchestrationTask, current_models: List[str]) -> List[str]:
        """Get additional models to improve low-confidence predictions"""
        all_possible_models = list(self.active_models.keys())
        additional_models = []
        
        for model_name in all_possible_models:
            if model_name not in current_models:
                additional_models.append(model_name)
                
                # Limit additional models
                if len(additional_models) >= 3:
                    break
        
        return additional_models
    
    def _update_orchestration_metrics(self, ensemble_result: EnsemblePrediction):
        """Update orchestration performance metrics"""
        self.orchestration_metrics["total_predictions"] += 1
        
        # Update average response time
        current_avg = self.orchestration_metrics["avg_response_time"]
        new_time = ensemble_result.execution_time
        total_predictions = self.orchestration_metrics["total_predictions"]
        
        self.orchestration_metrics["avg_response_time"] = (
            (current_avg * (total_predictions - 1) + new_time) / total_predictions
        )
        
        # Store consensus and agreement scores
        self.orchestration_metrics["consensus_scores"].append(ensemble_result.consensus_strength)
        self.orchestration_metrics["model_agreement_scores"].append(1.0 - ensemble_result.disagreement_score)
        
        # Keep only last 1000 scores
        for key in ["consensus_scores", "model_agreement_scores"]:
            if len(self.orchestration_metrics[key]) > 1000:
                self.orchestration_metrics[key] = self.orchestration_metrics[key][-1000:]
    
    async def _update_learning_system(
        self,
        task: OrchestrationTask,
        ensemble_result: EnsemblePrediction,
        individual_predictions: Dict[str, TradingModelOutput]
    ):
        """Update the learning system with new predictions"""
        try:
            # Update ensemble intelligence weights
            for model_name, prediction in individual_predictions.items():
                # Simulate performance update (in real system, this would use actual outcomes)
                performance_score = prediction.confidence * 0.8 + ensemble_result.consensus_strength * 0.2
                
                self.ensemble_intelligence.update_model_performance(
                    model_name=model_name,
                    accuracy=performance_score,
                    prediction_correct=performance_score > 0.6
                )
            
            # Save updated weights periodically
            if self.orchestration_metrics["total_predictions"] % 10 == 0:
                self.ensemble_intelligence.save_model_weights()
            
        except Exception as e:
            logger.debug(f"Learning system update error: {e}")
    
    def _store_prediction(self, task: OrchestrationTask, ensemble_result: EnsemblePrediction):
        """Store prediction in database for future analysis"""
        try:
            cursor = self.db_connection.cursor()
            
            cursor.execute("""
                INSERT INTO predictions (
                    timestamp, task_id, symbol, analysis_type, ensemble_prediction,
                    confidence_score, consensus_strength, disagreement_score,
                    models_used, execution_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ensemble_result.timestamp.isoformat(),
                task.task_id,
                task.symbol,
                task.analysis_type,
                float(ensemble_result.prediction_value) if isinstance(ensemble_result.prediction_value, (int, float)) else 0.0,
                ensemble_result.confidence_score,
                ensemble_result.consensus_strength,
                ensemble_result.disagreement_score,
                json.dumps(ensemble_result.models_used),
                ensemble_result.execution_time
            ))
            
            self.db_connection.commit()
            
        except Exception as e:
            logger.debug(f"Database storage error: {e}")
    
    def register_model(self, model_name: str, model_instance: Any, role: ModelRole, capabilities: List[str] = None):
        """Register a new model with the orchestrator"""
        self.active_models[model_name] = model_instance
        self.model_router.register_model(model_name, role, capabilities)
        
        logger.info(f"🎭 Registered model {model_name} with role {role.value}")
    
    def get_orchestrator_status(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator status"""
        cache_stats = self.model_cache.get_stats()
        
        status = {
            "active_models": len(self.active_models),
            "total_predictions": self.orchestration_metrics["total_predictions"],
            "avg_response_time": self.orchestration_metrics["avg_response_time"],
            "cache_hit_rate": cache_stats["hit_rate"],
            "cache_size_mb": cache_stats["total_size_mb"],
            "avg_consensus_score": statistics.mean(self.orchestration_metrics["consensus_scores"]) if self.orchestration_metrics["consensus_scores"] else 0.0,
            "avg_agreement_score": statistics.mean(self.orchestration_metrics["model_agreement_scores"]) if self.orchestration_metrics["model_agreement_scores"] else 0.0,
            "learning_enabled": self.learning_enabled,
            "ensemble_weights_count": len(self.ensemble_intelligence.model_weights)
        }
        
        return status
    
    async def optimize_performance(self):
        """Optimize orchestrator performance"""
        logger.info("🚀 Optimizing orchestrator performance...")
        
        try:
            # 1. Clean up cache
            self.model_cache._check_cache_size()
            
            # 2. Save model weights
            self.ensemble_intelligence.save_model_weights()
            
            # 3. Analyze performance patterns
            await self._analyze_performance_patterns()
            
            # 4. Adjust configuration if needed
            await self._adjust_configuration()
            
            logger.info("✅ Performance optimization complete")
            
        except Exception as e:
            logger.error(f"❌ Performance optimization failed: {e}")
    
    async def _analyze_performance_patterns(self):
        """Analyze performance patterns for optimization"""
        try:
            cursor = self.db_connection.cursor()
            
            # Get recent predictions
            cursor.execute("""
                SELECT analysis_type, AVG(confidence_score), AVG(consensus_strength), AVG(execution_time)
                FROM predictions 
                WHERE timestamp > datetime('now', '-7 days')
                GROUP BY analysis_type
            """)
            
            results = cursor.fetchall()
            
            for analysis_type, avg_confidence, avg_consensus, avg_time in results:
                logger.info(f"📊 {analysis_type}: conf={avg_confidence:.2f}, consensus={avg_consensus:.2f}, time={avg_time:.2f}s")
                
        except Exception as e:
            logger.debug(f"Performance analysis error: {e}")
    
    async def _adjust_configuration(self):
        """Dynamically adjust configuration based on performance"""
        try:
            # Adjust cache size based on hit rate
            cache_stats = self.model_cache.get_stats()
            
            if cache_stats["hit_rate"] > 0.8:
                # High hit rate - can increase cache size
                new_cache_size = min(1024, int(self.config["cache_size_mb"] * 1.2))
                if new_cache_size != self.config["cache_size_mb"]:
                    self.config["cache_size_mb"] = new_cache_size
                    logger.info(f"🔧 Increased cache size to {new_cache_size}MB")
            
            elif cache_stats["hit_rate"] < 0.3:
                # Low hit rate - decrease cache size
                new_cache_size = max(128, int(self.config["cache_size_mb"] * 0.8))
                if new_cache_size != self.config["cache_size_mb"]:
                    self.config["cache_size_mb"] = new_cache_size
                    logger.info(f"🔧 Decreased cache size to {new_cache_size}MB")
            
            # Save updated configuration
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
                
        except Exception as e:
            logger.debug(f"Configuration adjustment error: {e}")
    
    def __del__(self):
        """Cleanup when orchestrator is destroyed"""
        try:
            if hasattr(self, 'db_connection'):
                self.db_connection.close()
            if hasattr(self, 'model_pool'):
                self.model_pool.shutdown(wait=True)
        except Exception:
            pass

# Global orchestrator instance
_orchestrator = None

def get_orchestrator() -> MultiModelOrchestrator:
    """Get global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiModelOrchestrator()
    return _orchestrator

# Convenience functions for easy integration
async def orchestrate_trading_analysis(
    symbol: str,
    analysis_type: str = "comprehensive",
    query: str = "",
    context: Dict[str, Any] = None,
    timeout: float = 30.0
) -> EnsemblePrediction:
    """
    🎯 High-level function for trading analysis orchestration
    """
    orchestrator = get_orchestrator()
    
    task = OrchestrationTask(
        task_id=f"trading_{symbol}_{int(time.time())}",
        query=query or f"Analyze {symbol} for {analysis_type}",
        symbol=symbol,
        analysis_type=analysis_type,
        priority=8,
        timeout=timeout,
        required_models=[],
        optional_models=[],
        consensus_type=ConsensusType.DYNAMIC_WEIGHTED,
        min_confidence=0.3,
        context=context or {}
    )
    
    return await orchestrator.orchestrate_prediction(task)

async def initialize_orchestrator_with_models():
    """
    🚀 Initialize orchestrator with standard trading models
    """
    orchestrator = get_orchestrator()
    
    # This would be integrated with actual model instances
    # For now, we'll create placeholder registrations
    
    sample_models = {
        "financial_sentiment": ModelRole.SENTIMENT_ANALYZER,
        "technical_predictor": ModelRole.TECHNICAL_PREDICTOR,
        "risk_analyzer": ModelRole.RISK_ASSESSOR,
        "news_impact": ModelRole.NEWS_ANALYZER,
        "market_scanner": ModelRole.MARKET_SCANNER,
        "volatility_predictor": ModelRole.VOLATILITY_PREDICTOR
    }
    
    for model_name, role in sample_models.items():
        # In real implementation, these would be actual model instances
        orchestrator.register_model(
            model_name=model_name,
            model_instance=lambda q, s, c: TradingModelOutput(
                model_name=model_name,
                symbol=s,
                prediction=0.5,  # Placeholder
                confidence=0.7,
                reasoning=f"Analysis from {model_name}",
                features_used=["placeholder"]
            ),
            role=role,
            capabilities=[role.value]
        )
    
    logger.info("🎭 Orchestrator initialized with sample models")

if __name__ == "__main__":
    async def test_orchestrator():
        """Test the orchestrator system"""
        logger.info("🧪 Testing Multi-Model Orchestrator...")
        
        # Initialize orchestrator
        await initialize_orchestrator_with_models()
        
        # Test trading analysis
        result = await orchestrate_trading_analysis(
            symbol="BTC/USD",
            analysis_type="comprehensive",
            context={
                "market_conditions": {"high_volatility": True},
                "volatility": 0.8,
                "time_factor": 1.0
            }
        )
        
        print("\n🎭 ORCHESTRATOR TEST RESULTS:")
        print(f"Prediction: {result.prediction_value}")
        print(f"Confidence: {result.confidence_score:.2f}")
        print(f"Consensus: {result.consensus_strength:.2f}")
        print(f"Disagreement: {result.disagreement_score:.2f}")
        print(f"Models Used: {result.models_used}")
        print(f"Execution Time: {result.execution_time:.2f}s")
        print(f"Reasoning: {result.reasoning}")
        
        # Test orchestrator status
        status = get_orchestrator().get_orchestrator_status()
        print(f"\n📊 ORCHESTRATOR STATUS:")
        for key, value in status.items():
            print(f"{key}: {value}")
        
        logger.info("✅ Orchestrator testing completed")
    
    asyncio.run(test_orchestrator())