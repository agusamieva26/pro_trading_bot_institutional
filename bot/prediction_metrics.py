"""
📊 PREDICTION PERFORMANCE ANALYTICS SYSTEM
Advanced performance monitoring and analytics for ML trading predictions with degradation detection,
A/B testing, and comprehensive reporting for institutional-grade trading systems.

Features:
- Real-time accuracy tracking by timeframe and symbol
- Model performance degradation detection
- Prediction vs reality analysis with detailed breakdowns
- A/B testing framework for model comparison
- Comprehensive performance reporting and alerting
- Risk-adjusted performance metrics
- Production monitoring dashboards
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from datetime import datetime, timedelta
import json
import warnings
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import threading
import time
from collections import defaultdict, deque
import sqlite3
from contextlib import contextmanager
import statistics

# Suppress warnings for production
warnings.filterwarnings('ignore', category=FutureWarning)

# Statistical and ML libraries
from scipy import stats
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, roc_auc_score, mean_squared_error

from .util import logger
from .predictive_analytics import PredictionResult, PredictionDirection, PredictionTimeframe
from .real_time_predictor import RealTimePrediction, SignalQuality


class PerformanceAlert(Enum):
    """Performance alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class PredictionRecord:
    """Record of a prediction and its outcome."""
    prediction_id: str
    symbol: str
    timestamp: datetime
    prediction_class: PredictionDirection
    actual_class: Optional[PredictionDirection]
    confidence: float
    signal_strength: float
    signal_quality: SignalQuality
    timeframe: PredictionTimeframe
    market_regime: str
    position_size_pct: float
    model_votes: Dict[str, str]
    
    # Outcome metrics
    prediction_correct: Optional[bool] = None
    actual_return: Optional[float] = None
    prediction_error: Optional[float] = None
    realized_pnl: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'prediction_id': self.prediction_id,
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'prediction_class': self.prediction_class.name if self.prediction_class else None,
            'actual_class': self.actual_class.name if self.actual_class else None,
            'confidence': float(self.confidence),
            'signal_strength': float(self.signal_strength),
            'signal_quality': self.signal_quality.value,
            'timeframe': self.timeframe.value,
            'market_regime': self.market_regime,
            'position_size_pct': float(self.position_size_pct),
            'model_votes': {k: v for k, v in self.model_votes.items()},
            'prediction_correct': self.prediction_correct,
            'actual_return': float(self.actual_return) if self.actual_return is not None else None,
            'prediction_error': float(self.prediction_error) if self.prediction_error is not None else None,
            'realized_pnl': float(self.realized_pnl) if self.realized_pnl is not None else None
        }


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics."""
    # Basic accuracy metrics
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    
    # Trading-specific metrics
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    avg_return_per_prediction: float = 0.0
    
    # Quality metrics
    confidence_reliability: float = 0.0  # How well confidence predicts correctness
    signal_quality_distribution: Dict[str, float] = field(default_factory=dict)
    model_consensus_accuracy: float = 0.0
    
    # Volume metrics
    total_predictions: int = 0
    correct_predictions: int = 0
    predictions_per_hour: float = 0.0
    
    # Risk metrics
    risk_adjusted_return: float = 0.0
    value_at_risk_95: float = 0.0
    expected_shortfall: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'accuracy': float(self.accuracy),
            'precision': float(self.precision),
            'recall': float(self.recall),
            'f1_score': float(self.f1_score),
            'win_rate': float(self.win_rate),
            'profit_factor': float(self.profit_factor),
            'sharpe_ratio': float(self.sharpe_ratio),
            'max_drawdown': float(self.max_drawdown),
            'avg_return_per_prediction': float(self.avg_return_per_prediction),
            'confidence_reliability': float(self.confidence_reliability),
            'signal_quality_distribution': {k: float(v) for k, v in self.signal_quality_distribution.items()},
            'model_consensus_accuracy': float(self.model_consensus_accuracy),
            'total_predictions': int(self.total_predictions),
            'correct_predictions': int(self.correct_predictions),
            'predictions_per_hour': float(self.predictions_per_hour),
            'risk_adjusted_return': float(self.risk_adjusted_return),
            'value_at_risk_95': float(self.value_at_risk_95),
            'expected_shortfall': float(self.expected_shortfall)
        }


@dataclass
class ModelComparisonResult:
    """Results from A/B testing model comparison."""
    model_a_name: str
    model_b_name: str
    test_period_days: int
    statistical_significance: float  # p-value
    performance_difference: float    # Model A - Model B accuracy
    confidence_interval: Tuple[float, float]
    winner: str  # 'model_a', 'model_b', or 'no_difference'
    recommendation: str
    detailed_metrics: Dict[str, Dict[str, float]]


class PredictionDatabase:
    """
    SQLite database for storing prediction records and performance metrics.
    """
    
    def __init__(self, db_path: str = "data/predictions.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
    def _init_database(self):
        """Initialize database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Predictions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    prediction_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    prediction_class TEXT,
                    actual_class TEXT,
                    confidence REAL,
                    signal_strength REAL,
                    signal_quality TEXT,
                    timeframe TEXT,
                    market_regime TEXT,
                    position_size_pct REAL,
                    model_votes TEXT,
                    prediction_correct INTEGER,
                    actual_return REAL,
                    prediction_error REAL,
                    realized_pnl REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Performance metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    timeframe TEXT,
                    period_start TEXT,
                    period_end TEXT,
                    metrics TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Model performance comparison table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_comparisons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_a TEXT,
                    model_b TEXT,
                    test_period_days INTEGER,
                    results TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_symbol ON predictions(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_timeframe ON predictions(timeframe)")
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with automatic cleanup."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            yield conn
        finally:
            conn.close()
    
    def insert_prediction(self, record: PredictionRecord):
        """Insert prediction record."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO predictions 
                    (prediction_id, symbol, timestamp, prediction_class, actual_class,
                     confidence, signal_strength, signal_quality, timeframe, market_regime,
                     position_size_pct, model_votes, prediction_correct, actual_return,
                     prediction_error, realized_pnl)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.prediction_id,
                    record.symbol,
                    record.timestamp.isoformat(),
                    record.prediction_class.name if record.prediction_class else None,
                    record.actual_class.name if record.actual_class else None,
                    record.confidence,
                    record.signal_strength,
                    record.signal_quality.value,
                    record.timeframe.value,
                    record.market_regime,
                    record.position_size_pct,
                    json.dumps(record.model_votes),
                    record.prediction_correct,
                    record.actual_return,
                    record.prediction_error,
                    record.realized_pnl
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ Database insert error: {e}")
    
    def get_predictions(self, symbol: Optional[str] = None, 
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None,
                       timeframe: Optional[str] = None) -> List[PredictionRecord]:
        """Get prediction records with optional filtering."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM predictions WHERE 1=1"
                params = []
                
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                
                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date.isoformat())
                
                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date.isoformat())
                
                if timeframe:
                    query += " AND timeframe = ?"
                    params.append(timeframe)
                
                query += " ORDER BY timestamp DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                records = []
                for row in rows:
                    record = PredictionRecord(
                        prediction_id=row[0],
                        symbol=row[1],
                        timestamp=datetime.fromisoformat(row[2]),
                        prediction_class=PredictionDirection[row[3]] if row[3] else None,
                        actual_class=PredictionDirection[row[4]] if row[4] else None,
                        confidence=row[5],
                        signal_strength=row[6],
                        signal_quality=SignalQuality(row[7]),
                        timeframe=PredictionTimeframe(row[8]),
                        market_regime=row[9],
                        position_size_pct=row[10],
                        model_votes=json.loads(row[11]),
                        prediction_correct=row[12],
                        actual_return=row[13],
                        prediction_error=row[14],
                        realized_pnl=row[15]
                    )
                    records.append(record)
                
                return records
                
        except Exception as e:
            logger.error(f"❌ Database query error: {e}")
            return []


class PerformanceAnalyzer:
    """
    Core performance analysis engine with advanced metrics and degradation detection.
    """
    
    def __init__(self, db_path: str = "data/predictions.db"):
        self.database = PredictionDatabase(db_path)
        
        # Performance thresholds
        self.accuracy_threshold = 0.70  # 70% target accuracy
        self.degradation_threshold = 0.05  # 5% accuracy drop triggers alert
        self.min_predictions_for_analysis = 50
        
        # Rolling metrics
        self.rolling_window_hours = 24
        self.rolling_metrics_cache = {}
        
    def calculate_performance_metrics(self, records: List[PredictionRecord]) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics."""
        try:
            if not records:
                return PerformanceMetrics()
            
            # Filter records with outcomes
            completed_records = [r for r in records if r.prediction_correct is not None]
            
            if len(completed_records) < self.min_predictions_for_analysis:
                logger.warning(f"⚠️ Insufficient completed predictions: {len(completed_records)}")
                return PerformanceMetrics(total_predictions=len(records))
            
            metrics = PerformanceMetrics()
            
            # Basic accuracy metrics
            correct_predictions = sum(1 for r in completed_records if r.prediction_correct)
            metrics.total_predictions = len(records)
            metrics.correct_predictions = correct_predictions
            metrics.accuracy = correct_predictions / len(completed_records) if completed_records else 0.0
            
            # Classification metrics
            if len(completed_records) > 10:
                y_true = [r.actual_class.value for r in completed_records if r.actual_class]
                y_pred = [r.prediction_class.value for r in completed_records if r.prediction_class]
                
                if len(y_true) == len(y_pred) and len(y_true) > 0:
                    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='weighted', zero_division=0)
                    metrics.precision = precision
                    metrics.recall = recall
                    metrics.f1_score = f1
            
            # Trading-specific metrics
            returns = [r.actual_return for r in completed_records if r.actual_return is not None]
            if returns:
                positive_returns = [r for r in returns if r > 0]
                negative_returns = [r for r in returns if r < 0]
                
                metrics.win_rate = len(positive_returns) / len(returns)
                metrics.avg_return_per_prediction = np.mean(returns)
                
                if positive_returns and negative_returns:
                    avg_win = np.mean(positive_returns)
                    avg_loss = abs(np.mean(negative_returns))
                    metrics.profit_factor = (avg_win * len(positive_returns)) / (avg_loss * len(negative_returns))
                
                # Sharpe ratio (annualized)
                if len(returns) > 1 and np.std(returns) > 0:
                    metrics.sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252 * 24)  # 24 predictions per day
                
                # Risk metrics
                metrics.value_at_risk_95 = np.percentile(returns, 5)
                worst_5_percent = [r for r in returns if r <= metrics.value_at_risk_95]
                if worst_5_percent:
                    metrics.expected_shortfall = np.mean(worst_5_percent)
            
            # Confidence reliability
            confidence_bins = defaultdict(list)
            for record in completed_records:
                bin_key = int(record.confidence * 10) / 10  # 0.1 bins
                confidence_bins[bin_key].append(record.prediction_correct)
            
            if confidence_bins:
                reliability_scores = []
                for conf_level, correctness in confidence_bins.items():
                    if len(correctness) >= 5:  # Minimum sample size
                        actual_accuracy = np.mean(correctness)
                        reliability_scores.append(abs(conf_level - actual_accuracy))
                
                if reliability_scores:
                    metrics.confidence_reliability = 1.0 - np.mean(reliability_scores)  # Higher is better
            
            # Signal quality distribution
            quality_counts = defaultdict(int)
            for record in records:
                quality_counts[record.signal_quality.value] += 1
            
            total_records = len(records)
            metrics.signal_quality_distribution = {
                quality: count / total_records 
                for quality, count in quality_counts.items()
            }
            
            # Model consensus accuracy
            consensus_correct = 0
            consensus_total = 0
            for record in completed_records:
                if len(record.model_votes) > 1:
                    votes = list(record.model_votes.values())
                    most_common = statistics.mode(votes) if len(set(votes)) < len(votes) else None
                    if most_common and most_common == record.prediction_class.name:
                        consensus_total += 1
                        if record.prediction_correct:
                            consensus_correct += 1
                    else:
                        consensus_total += 1  # Count non-consensus predictions too
            
            if consensus_total > 0:
                metrics.model_consensus_accuracy = consensus_correct / consensus_total
            
            # Prediction rate
            if len(records) > 1:
                time_span = (records[0].timestamp - records[-1].timestamp).total_seconds() / 3600
                if time_span > 0:
                    metrics.predictions_per_hour = len(records) / time_span
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Performance metrics calculation error: {e}")
            return PerformanceMetrics()
    
    def detect_performance_degradation(self, symbol: str, timeframe: str = "5m", 
                                     lookback_hours: int = 24) -> Dict[str, Any]:
        """Detect performance degradation over time."""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=lookback_hours)
            
            # Get recent predictions
            recent_records = self.database.get_predictions(
                symbol=symbol,
                start_date=start_time,
                end_date=end_time,
                timeframe=timeframe
            )
            
            if len(recent_records) < self.min_predictions_for_analysis:
                return {'status': 'insufficient_data', 'sample_size': len(recent_records)}
            
            # Split into periods for trend analysis
            mid_time = start_time + timedelta(hours=lookback_hours // 2)
            
            earlier_records = [r for r in recent_records if r.timestamp < mid_time]
            later_records = [r for r in recent_records if r.timestamp >= mid_time]
            
            if not earlier_records or not later_records:
                return {'status': 'insufficient_period_split'}
            
            # Calculate metrics for each period
            earlier_metrics = self.calculate_performance_metrics(earlier_records)
            later_metrics = self.calculate_performance_metrics(later_records)
            
            # Detect degradation
            accuracy_change = later_metrics.accuracy - earlier_metrics.accuracy
            win_rate_change = later_metrics.win_rate - earlier_metrics.win_rate
            confidence_reliability_change = (later_metrics.confidence_reliability - 
                                           earlier_metrics.confidence_reliability)
            
            # Determine alert level
            alert_level = PerformanceAlert.INFO
            if accuracy_change < -self.degradation_threshold:
                alert_level = PerformanceAlert.CRITICAL
            elif accuracy_change < -self.degradation_threshold / 2:
                alert_level = PerformanceAlert.WARNING
            
            # Statistical significance test
            earlier_correct = [r.prediction_correct for r in earlier_records if r.prediction_correct is not None]
            later_correct = [r.prediction_correct for r in later_records if r.prediction_correct is not None]
            
            p_value = 1.0
            if len(earlier_correct) > 10 and len(later_correct) > 10:
                try:
                    statistic, p_value = stats.ttest_ind(earlier_correct, later_correct)
                except:
                    p_value = 1.0
            
            return {
                'status': 'analysis_complete',
                'symbol': symbol,
                'timeframe': timeframe,
                'lookback_hours': lookback_hours,
                'alert_level': alert_level.value,
                'accuracy_change': accuracy_change,
                'win_rate_change': win_rate_change,
                'confidence_reliability_change': confidence_reliability_change,
                'statistical_significance': p_value,
                'earlier_period': {
                    'accuracy': earlier_metrics.accuracy,
                    'win_rate': earlier_metrics.win_rate,
                    'total_predictions': len(earlier_records)
                },
                'later_period': {
                    'accuracy': later_metrics.accuracy,
                    'win_rate': later_metrics.win_rate,
                    'total_predictions': len(later_records)
                },
                'recommendation': self._get_degradation_recommendation(alert_level, accuracy_change, p_value)
            }
            
        except Exception as e:
            logger.error(f"❌ Performance degradation detection error: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _get_degradation_recommendation(self, alert_level: PerformanceAlert, 
                                      accuracy_change: float, p_value: float) -> str:
        """Get recommendation based on degradation analysis."""
        if alert_level == PerformanceAlert.CRITICAL:
            if p_value < 0.05:
                return "URGENT: Significant performance degradation detected. Recommend immediate model retraining."
            else:
                return "WARNING: Performance degradation detected but not statistically significant. Monitor closely."
        elif alert_level == PerformanceAlert.WARNING:
            return "NOTICE: Minor performance decline detected. Consider model validation and potential retraining."
        else:
            if accuracy_change > 0:
                return "POSITIVE: Performance improving. Continue current operations."
            else:
                return "STABLE: Performance within normal ranges. Continue monitoring."
    
    def compare_models(self, model_a_predictions: List[PredictionRecord],
                      model_b_predictions: List[PredictionRecord],
                      model_a_name: str, model_b_name: str) -> ModelComparisonResult:
        """A/B test comparison between two models."""
        try:
            # Calculate metrics for both models
            metrics_a = self.calculate_performance_metrics(model_a_predictions)
            metrics_b = self.calculate_performance_metrics(model_b_predictions)
            
            # Statistical significance test
            completed_a = [r for r in model_a_predictions if r.prediction_correct is not None]
            completed_b = [r for r in model_b_predictions if r.prediction_correct is not None]
            
            if len(completed_a) < 30 or len(completed_b) < 30:
                p_value = 1.0
            else:
                correct_a = [r.prediction_correct for r in completed_a]
                correct_b = [r.prediction_correct for r in completed_b]
                
                statistic, p_value = stats.ttest_ind(correct_a, correct_b)
            
            # Performance difference
            accuracy_diff = metrics_a.accuracy - metrics_b.accuracy
            
            # Confidence interval (simplified)
            se_diff = np.sqrt(
                (metrics_a.accuracy * (1 - metrics_a.accuracy) / len(completed_a)) +
                (metrics_b.accuracy * (1 - metrics_b.accuracy) / len(completed_b))
            ) if completed_a and completed_b else 0.1
            
            confidence_interval = (
                accuracy_diff - 1.96 * se_diff,
                accuracy_diff + 1.96 * se_diff
            )
            
            # Determine winner
            if p_value < 0.05:
                if accuracy_diff > 0:
                    winner = 'model_a'
                    recommendation = f"{model_a_name} significantly outperforms {model_b_name}"
                else:
                    winner = 'model_b'
                    recommendation = f"{model_b_name} significantly outperforms {model_a_name}"
            else:
                winner = 'no_difference'
                recommendation = "No statistically significant difference between models"
            
            return ModelComparisonResult(
                model_a_name=model_a_name,
                model_b_name=model_b_name,
                test_period_days=30,  # Estimated
                statistical_significance=p_value,
                performance_difference=accuracy_diff,
                confidence_interval=confidence_interval,
                winner=winner,
                recommendation=recommendation,
                detailed_metrics={
                    model_a_name: metrics_a.to_dict(),
                    model_b_name: metrics_b.to_dict()
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Model comparison error: {e}")
            return ModelComparisonResult(
                model_a_name=model_a_name,
                model_b_name=model_b_name,
                test_period_days=0,
                statistical_significance=1.0,
                performance_difference=0.0,
                confidence_interval=(0.0, 0.0),
                winner='no_difference',
                recommendation=f"Error in comparison: {str(e)}",
                detailed_metrics={}
            )


class PredictionTracker:
    """
    Main system for tracking predictions and analyzing performance.
    """
    
    def __init__(self, db_path: str = "data/predictions.db"):
        """Initialize prediction tracker."""
        self.analyzer = PerformanceAnalyzer(db_path)
        self.database = self.analyzer.database
        
        # Prediction tracking
        self.active_predictions = {}  # prediction_id -> PredictionRecord
        self.outcome_callbacks = []
        
        # Performance monitoring
        self.performance_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Thread safety
        self._tracking_lock = threading.Lock()
        
        logger.info("📊 Prediction Performance Analytics System initialized")
    
    def record_prediction(self, prediction: RealTimePrediction) -> str:
        """Record a new prediction for tracking."""
        try:
            prediction_id = f"{prediction.symbol}_{prediction.timestamp.isoformat()}_{hash(str(prediction.prediction_result.to_dict()))}"
            
            record = PredictionRecord(
                prediction_id=prediction_id,
                symbol=prediction.symbol,
                timestamp=prediction.timestamp,
                prediction_class=prediction.prediction_result.prediction_class,
                actual_class=None,  # Will be filled when outcome is known
                confidence=prediction.prediction_result.confidence,
                signal_strength=prediction.prediction_result.signal_strength,
                signal_quality=prediction.signal_quality,
                timeframe=prediction.prediction_result.timeframe,
                market_regime=prediction.market_regime,
                position_size_pct=prediction.position_size_pct,
                model_votes={k: v.name for k, v in prediction.prediction_result.model_votes.items()}
            )
            
            with self._tracking_lock:
                self.active_predictions[prediction_id] = record
            
            # Store in database
            self.database.insert_prediction(record)
            
            logger.debug(f"📊 Recorded prediction {prediction_id[:8]}... for {prediction.symbol}")
            
            return prediction_id
            
        except Exception as e:
            logger.error(f"❌ Prediction recording error: {e}")
            return ""
    
    def update_prediction_outcome(self, prediction_id: str, actual_return: float, 
                                actual_class: PredictionDirection, realized_pnl: Optional[float] = None):
        """Update prediction with actual outcome."""
        try:
            with self._tracking_lock:
                if prediction_id not in self.active_predictions:
                    logger.warning(f"⚠️ Prediction {prediction_id[:8]}... not found in active predictions")
                    return
                
                record = self.active_predictions[prediction_id]
                
                # Update outcome
                record.actual_class = actual_class
                record.actual_return = actual_return
                record.realized_pnl = realized_pnl
                
                # Calculate correctness
                record.prediction_correct = (record.prediction_class == actual_class)
                
                # Calculate prediction error
                if record.prediction_class == PredictionDirection.BUY:
                    expected_return = abs(record.signal_strength) * 0.01  # Convert to percentage
                elif record.prediction_class == PredictionDirection.SELL:
                    expected_return = -abs(record.signal_strength) * 0.01
                else:
                    expected_return = 0.0
                
                record.prediction_error = abs(actual_return - expected_return)
            
            # Update in database
            self.database.insert_prediction(record)
            
            # Remove from active tracking after some time
            if len(self.active_predictions) > 1000:
                oldest_items = list(self.active_predictions.items())[:100]
                for old_id, _ in oldest_items:
                    del self.active_predictions[old_id]
            
            # Trigger callbacks
            for callback in self.outcome_callbacks:
                try:
                    callback(record)
                except Exception as e:
                    logger.error(f"❌ Outcome callback error: {e}")
            
            logger.debug(f"📊 Updated outcome for {prediction_id[:8]}... "
                        f"correct={record.prediction_correct}, return={actual_return:.4f}")
            
        except Exception as e:
            logger.error(f"❌ Prediction outcome update error: {e}")
    
    def get_performance_report(self, symbol: Optional[str] = None, 
                             timeframe: Optional[str] = None,
                             lookback_hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        try:
            cache_key = f"{symbol}_{timeframe}_{lookback_hours}_{int(time.time() / self.cache_ttl)}"
            
            if cache_key in self.performance_cache:
                return self.performance_cache[cache_key]
            
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=lookback_hours)
            
            # Get predictions
            predictions = self.database.get_predictions(
                symbol=symbol,
                start_date=start_time,
                end_date=end_time,
                timeframe=timeframe
            )
            
            if not predictions:
                return {
                    'status': 'no_data',
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'lookback_hours': lookback_hours
                }
            
            # Calculate metrics
            metrics = self.analyzer.calculate_performance_metrics(predictions)
            
            # Performance degradation analysis
            degradation = self.analyzer.detect_performance_degradation(
                symbol or "ALL", timeframe or "5m", lookback_hours
            )
            
            # Breakdown by signal quality
            quality_breakdown = self._analyze_by_signal_quality(predictions)
            
            # Model performance breakdown
            model_breakdown = self._analyze_by_model_votes(predictions)
            
            # Time-based breakdown
            time_breakdown = self._analyze_by_time_periods(predictions)
            
            report = {
                'status': 'success',
                'symbol': symbol,
                'timeframe': timeframe,
                'lookback_hours': lookback_hours,
                'report_timestamp': datetime.now().isoformat(),
                'overall_metrics': metrics.to_dict(),
                'degradation_analysis': degradation,
                'signal_quality_breakdown': quality_breakdown,
                'model_performance_breakdown': model_breakdown,
                'time_period_breakdown': time_breakdown,
                'summary': {
                    'meets_accuracy_target': metrics.accuracy >= self.analyzer.accuracy_threshold,
                    'total_predictions': len(predictions),
                    'completed_predictions': len([p for p in predictions if p.prediction_correct is not None]),
                    'accuracy_vs_target': metrics.accuracy - self.analyzer.accuracy_threshold,
                    'top_performing_quality': max(quality_breakdown, key=lambda x: x['accuracy'])['quality'] if quality_breakdown else None
                }
            }
            
            # Cache result
            self.performance_cache[cache_key] = report
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Performance report error: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _analyze_by_signal_quality(self, predictions: List[PredictionRecord]) -> List[Dict[str, Any]]:
        """Analyze performance by signal quality."""
        try:
            quality_groups = defaultdict(list)
            
            for pred in predictions:
                if pred.prediction_correct is not None:
                    quality_groups[pred.signal_quality.value].append(pred)
            
            breakdown = []
            for quality, group_predictions in quality_groups.items():
                if len(group_predictions) >= 5:  # Minimum sample size
                    metrics = self.analyzer.calculate_performance_metrics(group_predictions)
                    
                    breakdown.append({
                        'quality': quality,
                        'count': len(group_predictions),
                        'accuracy': metrics.accuracy,
                        'win_rate': metrics.win_rate,
                        'avg_return': metrics.avg_return_per_prediction,
                        'avg_confidence': np.mean([p.confidence for p in group_predictions])
                    })
            
            return sorted(breakdown, key=lambda x: x['accuracy'], reverse=True)
            
        except Exception as e:
            logger.error(f"❌ Signal quality analysis error: {e}")
            return []
    
    def _analyze_by_model_votes(self, predictions: List[PredictionRecord]) -> Dict[str, Dict[str, float]]:
        """Analyze performance by individual model votes."""
        try:
            model_performance = defaultdict(lambda: {'correct': 0, 'total': 0, 'returns': []})
            
            for pred in predictions:
                if pred.prediction_correct is not None and pred.model_votes:
                    for model_name, vote in pred.model_votes.items():
                        model_performance[model_name]['total'] += 1
                        
                        # Check if this model's vote was correct
                        if vote == pred.actual_class.name:
                            model_performance[model_name]['correct'] += 1
                        
                        if pred.actual_return is not None:
                            model_performance[model_name]['returns'].append(pred.actual_return)
            
            # Calculate final metrics
            breakdown = {}
            for model_name, stats in model_performance.items():
                if stats['total'] >= 10:  # Minimum sample size
                    accuracy = stats['correct'] / stats['total']
                    avg_return = np.mean(stats['returns']) if stats['returns'] else 0.0
                    
                    breakdown[model_name] = {
                        'accuracy': accuracy,
                        'total_votes': stats['total'],
                        'avg_return': avg_return
                    }
            
            return breakdown
            
        except Exception as e:
            logger.error(f"❌ Model votes analysis error: {e}")
            return {}
    
    def _analyze_by_time_periods(self, predictions: List[PredictionRecord]) -> List[Dict[str, Any]]:
        """Analyze performance by time periods."""
        try:
            if not predictions:
                return []
            
            # Sort by timestamp
            sorted_predictions = sorted(predictions, key=lambda x: x.timestamp)
            
            # Split into 4 periods
            n_periods = 4
            period_size = len(sorted_predictions) // n_periods
            
            breakdown = []
            
            for i in range(n_periods):
                start_idx = i * period_size
                end_idx = (i + 1) * period_size if i < n_periods - 1 else len(sorted_predictions)
                
                period_predictions = sorted_predictions[start_idx:end_idx]
                
                if period_predictions:
                    metrics = self.analyzer.calculate_performance_metrics(period_predictions)
                    
                    breakdown.append({
                        'period': i + 1,
                        'start_time': period_predictions[0].timestamp.isoformat(),
                        'end_time': period_predictions[-1].timestamp.isoformat(),
                        'count': len(period_predictions),
                        'accuracy': metrics.accuracy,
                        'win_rate': metrics.win_rate,
                        'avg_return': metrics.avg_return_per_prediction
                    })
            
            return breakdown
            
        except Exception as e:
            logger.error(f"❌ Time periods analysis error: {e}")
            return []
    
    def add_outcome_callback(self, callback: Callable[[PredictionRecord], None]):
        """Add callback function to be called when prediction outcomes are updated."""
        self.outcome_callbacks.append(callback)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status and health metrics."""
        try:
            current_time = datetime.now()
            
            # Count active predictions
            active_count = len(self.active_predictions)
            
            # Get recent performance
            recent_predictions = self.database.get_predictions(
                start_date=current_time - timedelta(hours=1),
                end_date=current_time
            )
            
            hourly_rate = len(recent_predictions)
            
            # Cache statistics
            cache_size = len(self.performance_cache)
            
            return {
                'status': 'operational',
                'timestamp': current_time.isoformat(),
                'active_predictions': active_count,
                'predictions_last_hour': hourly_rate,
                'cache_size': cache_size,
                'database_path': self.database.db_path,
                'accuracy_threshold': self.analyzer.accuracy_threshold,
                'degradation_threshold': self.analyzer.degradation_threshold,
                'callbacks_registered': len(self.outcome_callbacks)
            }
            
        except Exception as e:
            logger.error(f"❌ System status error: {e}")
            return {'status': 'error', 'error': str(e)}


# Global instance
prediction_tracker = PredictionTracker()


def record_prediction(prediction: RealTimePrediction) -> str:
    """Record a prediction for performance tracking."""
    return prediction_tracker.record_prediction(prediction)


def update_prediction_outcome(prediction_id: str, actual_return: float, 
                            actual_class: PredictionDirection, realized_pnl: Optional[float] = None):
    """Update prediction with actual outcome."""
    prediction_tracker.update_prediction_outcome(prediction_id, actual_return, actual_class, realized_pnl)


def get_performance_report(symbol: Optional[str] = None, timeframe: Optional[str] = None,
                          lookback_hours: int = 24) -> Dict[str, Any]:
    """Get comprehensive performance report."""
    return prediction_tracker.get_performance_report(symbol, timeframe, lookback_hours)


def detect_performance_degradation(symbol: str, timeframe: str = "5m", 
                                  lookback_hours: int = 24) -> Dict[str, Any]:
    """Detect performance degradation."""
    return prediction_tracker.analyzer.detect_performance_degradation(symbol, timeframe, lookback_hours)


def get_system_status() -> Dict[str, Any]:
    """Get prediction tracking system status."""
    return prediction_tracker.get_system_status()