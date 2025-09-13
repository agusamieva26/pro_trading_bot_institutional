#!/usr/bin/env python3
"""
🏛️ INSTITUTIONAL STRATEGY LIBRARY - ENTERPRISE GRADE
Advanced repository system for trading strategy management and analytics
- Comprehensive Strategy Repository with Version Control
- Performance Tracking & Analytics Dashboard  
- Strategy Categorization & Taxonomy System
- Advanced Search & Discovery Engine
- Performance Benchmarking & Ranking
- Strategy Lifecycle Management
- Institutional Compliance & Audit Trail
"""
import os
import json
import asyncio
import time
import uuid
import hashlib
import sqlite3
import pickle
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from collections import defaultdict, deque
import numpy as np
import pandas as pd
from loguru import logger
import warnings
warnings.filterwarnings("ignore")

# Analytics and visualization
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    logger.warning("Visualization libraries not available")

from .config import settings
from .util import logger

try:
    from .ai_strategy_generator import (
        StrategyDNA, StrategyPerformance, StrategyType, MarketRegime,
        StrategyObjective, StrategyGenerationTask
    )
    from .strategy_validation_engine import ValidationResult, ValidationLevel, ValidationStatus
    from .market_regime_analyzer import RegimeAnalysis
    from .advanced_memory_rag_system import KnowledgeEntry, KnowledgeType
except ImportError as e:
    logger.warning(f"Some strategy library dependencies not available: {e}")

class StrategyCategory(Enum):
    """Strategy categorization taxonomy"""
    # Primary categories
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    TREND_FOLLOWING = "trend_following"
    ARBITRAGE = "arbitrage"
    VOLATILITY = "volatility"
    NEWS_DRIVEN = "news_driven"
    
    # Advanced categories
    MULTI_TIMEFRAME = "multi_timeframe"
    REGIME_ADAPTIVE = "regime_adaptive"
    MACHINE_LEARNING = "machine_learning"
    STATISTICAL = "statistical"
    
    # Meta categories
    HYBRID = "hybrid"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"

class StrategyStatus(Enum):
    """Strategy lifecycle status"""
    DEVELOPMENT = "development"          # Under development
    TESTING = "testing"                  # In testing phase
    VALIDATED = "validated"              # Passed validation
    DEPLOYED = "deployed"                # Live trading
    MONITORING = "monitoring"            # Performance monitoring
    OPTIMIZING = "optimizing"            # Being optimized
    RETIRING = "retiring"                # Being phased out
    RETIRED = "retired"                  # No longer active
    ARCHIVED = "archived"                # Archived for reference

class PerformanceRating(Enum):
    """Performance rating classification"""
    OUTSTANDING = "outstanding"          # Top 5%
    EXCELLENT = "excellent"              # Top 10%
    VERY_GOOD = "very_good"             # Top 25%
    GOOD = "good"                       # Top 50%
    AVERAGE = "average"                 # Middle 50%
    BELOW_AVERAGE = "below_average"     # Bottom 50%
    POOR = "poor"                       # Bottom 25%
    VERY_POOR = "very_poor"            # Bottom 10%

@dataclass
class StrategyMetadata:
    """Comprehensive strategy metadata"""
    strategy_id: str
    name: str
    version: str
    category: StrategyCategory
    status: StrategyStatus
    
    # Classification
    tags: List[str] = field(default_factory=list)
    market_focus: List[str] = field(default_factory=list)  # Asset classes
    timeframe_focus: List[str] = field(default_factory=list)  # Trading timeframes
    complexity_level: str = "medium"  # simple, medium, complex, advanced
    
    # Authorship and provenance
    creator: str = "ai_generator"
    created_timestamp: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    parent_strategies: List[str] = field(default_factory=list)
    child_strategies: List[str] = field(default_factory=list)
    
    # Performance summary
    current_rating: PerformanceRating = PerformanceRating.AVERAGE
    best_rating_achieved: PerformanceRating = PerformanceRating.AVERAGE
    total_evaluations: int = 0
    
    # Usage statistics
    deployment_count: int = 0
    total_runtime_hours: float = 0.0
    total_trades_executed: int = 0
    
    # Risk profile
    risk_category: str = "medium"  # low, medium, high, very_high
    max_leverage: float = 1.0
    typical_drawdown: float = 0.1
    
    # Institutional compliance
    compliance_status: str = "pending"  # pending, approved, restricted, banned
    last_compliance_review: Optional[datetime] = None
    compliance_notes: str = ""
    
    # Documentation
    description: str = ""
    methodology: str = ""
    assumptions: str = ""
    limitations: str = ""
    notes: str = ""

@dataclass
class StrategyVersion:
    """Strategy version information"""
    version_id: str
    strategy_id: str
    version_number: str
    strategy_dna: StrategyDNA
    created_timestamp: datetime
    change_description: str
    performance_delta: Dict[str, float] = field(default_factory=dict)
    validation_results: Optional[ValidationResult] = None
    is_active: bool = False

@dataclass
class PerformanceRecord:
    """Detailed performance record"""
    record_id: str
    strategy_id: str
    version_id: str
    
    # Performance data
    performance_metrics: StrategyPerformance
    
    # Context (required parameters)
    evaluation_period: Tuple[datetime, datetime]
    market_regime: MarketRegime
    symbols_traded: List[str]
    
    # Optional parameters with defaults
    validation_results: Optional[ValidationResult] = None
    
    # Environment
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    external_factors: Dict[str, Any] = field(default_factory=dict)
    
    # Quality metrics
    data_quality_score: float = 1.0
    confidence_level: float = 0.8
    
    # Metadata
    recorded_timestamp: datetime = field(default_factory=datetime.now)
    recorded_by: str = "system"
    notes: str = ""

@dataclass 
class StrategyComparison:
    """Strategy comparison analysis"""
    comparison_id: str
    strategies: List[str]
    comparison_metrics: Dict[str, Dict[str, float]]
    winner: str
    confidence: float
    analysis_summary: str
    recommendation: str
    timestamp: datetime = field(default_factory=datetime.now)

class StrategyRepository:
    """
    📚 Advanced Strategy Repository with Version Control
    """
    
    def __init__(self, db_path: str = "bot/institutional_library.db", 
                 storage_path: str = "bot/strategy_repository"):
        self.db_path = Path(db_path)
        self.storage_path = Path(storage_path)
        
        # Ensure directories exist
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory caches
        self.metadata_cache: Dict[str, StrategyMetadata] = {}
        self.performance_cache: Dict[str, List[PerformanceRecord]] = defaultdict(list)
        self.version_cache: Dict[str, List[StrategyVersion]] = defaultdict(list)
        
        # Search indices
        self.tag_index: Dict[str, Set[str]] = defaultdict(set)
        self.category_index: Dict[StrategyCategory, Set[str]] = defaultdict(set)
        self.performance_index: Dict[PerformanceRating, Set[str]] = defaultdict(set)
        
        self._initialize_database()
        self._load_repository()
        
        logger.info(f"📚 Strategy Repository initialized: {len(self.metadata_cache)} strategies loaded")
    
    def _initialize_database(self):
        """Initialize SQLite database schema"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Strategy metadata table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS strategy_metadata (
                        strategy_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        version TEXT NOT NULL,
                        category TEXT NOT NULL,
                        status TEXT NOT NULL,
                        metadata_json TEXT NOT NULL,
                        created_timestamp TEXT NOT NULL,
                        last_modified TEXT NOT NULL,
                        current_rating TEXT NOT NULL,
                        compliance_status TEXT NOT NULL
                    )
                """)
                
                # Strategy versions table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS strategy_versions (
                        version_id TEXT PRIMARY KEY,
                        strategy_id TEXT NOT NULL,
                        version_number TEXT NOT NULL,
                        strategy_dna_json TEXT NOT NULL,
                        created_timestamp TEXT NOT NULL,
                        change_description TEXT,
                        is_active BOOLEAN DEFAULT FALSE,
                        FOREIGN KEY (strategy_id) REFERENCES strategy_metadata (strategy_id)
                    )
                """)
                
                # Performance records table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS performance_records (
                        record_id TEXT PRIMARY KEY,
                        strategy_id TEXT NOT NULL,
                        version_id TEXT NOT NULL,
                        performance_json TEXT NOT NULL,
                        evaluation_start TEXT NOT NULL,
                        evaluation_end TEXT NOT NULL,
                        market_regime TEXT,
                        recorded_timestamp TEXT NOT NULL,
                        data_quality_score REAL DEFAULT 1.0,
                        confidence_level REAL DEFAULT 0.8,
                        FOREIGN KEY (strategy_id) REFERENCES strategy_metadata (strategy_id),
                        FOREIGN KEY (version_id) REFERENCES strategy_versions (version_id)
                    )
                """)
                
                # Strategy comparisons table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS strategy_comparisons (
                        comparison_id TEXT PRIMARY KEY,
                        strategies_json TEXT NOT NULL,
                        comparison_results_json TEXT NOT NULL,
                        winner TEXT,
                        confidence REAL,
                        timestamp TEXT NOT NULL
                    )
                """)
                
                # Audit trail table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_trail (
                        audit_id TEXT PRIMARY KEY,
                        entity_type TEXT NOT NULL,
                        entity_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        details_json TEXT,
                        timestamp TEXT NOT NULL,
                        user_id TEXT
                    )
                """)
                
                # Create indices for performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_strategy_category ON strategy_metadata(category)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_strategy_status ON strategy_metadata(status)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_strategy_rating ON strategy_metadata(current_rating)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_performance_strategy ON performance_records(strategy_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON performance_records(recorded_timestamp)")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize repository database: {e}")
            raise
    
    def _load_repository(self):
        """Load repository data from database"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Load metadata
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM strategy_metadata")
                
                for row in cursor.fetchall():
                    strategy_id, name, version, category, status, metadata_json, created, modified, rating, compliance = row
                    
                    try:
                        metadata_dict = json.loads(metadata_json)
                        metadata = StrategyMetadata(**metadata_dict)
                        self.metadata_cache[strategy_id] = metadata
                        
                        # Update indices
                        self._update_indices(strategy_id, metadata)
                        
                    except Exception as e:
                        logger.debug(f"Error loading metadata for {strategy_id}: {e}")
                
                # Load versions
                cursor.execute("SELECT * FROM strategy_versions")
                for row in cursor.fetchall():
                    version_id, strategy_id, version_num, dna_json, created, change_desc, is_active = row
                    
                    try:
                        dna_dict = json.loads(dna_json)
                        # Reconstruct StrategyDNA object
                        strategy_dna = StrategyDNA(**dna_dict)
                        
                        version = StrategyVersion(
                            version_id=version_id,
                            strategy_id=strategy_id,
                            version_number=version_num,
                            strategy_dna=strategy_dna,
                            created_timestamp=datetime.fromisoformat(created),
                            change_description=change_desc or "",
                            is_active=bool(is_active)
                        )
                        
                        self.version_cache[strategy_id].append(version)
                        
                    except Exception as e:
                        logger.debug(f"Error loading version {version_id}: {e}")
                
                # Load performance records
                cursor.execute("SELECT * FROM performance_records LIMIT 1000")  # Limit for memory
                for row in cursor.fetchall():
                    record_id, strategy_id, version_id, perf_json, start, end, regime, recorded, quality, confidence = row
                    
                    try:
                        perf_dict = json.loads(perf_json)
                        performance_metrics = StrategyPerformance(**perf_dict)
                        
                        record = PerformanceRecord(
                            record_id=record_id,
                            strategy_id=strategy_id,
                            version_id=version_id,
                            performance_metrics=performance_metrics,
                            evaluation_period=(datetime.fromisoformat(start), datetime.fromisoformat(end)),
                            market_regime=MarketRegime(regime) if regime else MarketRegime.SIDEWAYS,
                            symbols_traded=[],
                            recorded_timestamp=datetime.fromisoformat(recorded),
                            data_quality_score=quality,
                            confidence_level=confidence
                        )
                        
                        self.performance_cache[strategy_id].append(record)
                        
                    except Exception as e:
                        logger.debug(f"Error loading performance record {record_id}: {e}")
                
        except Exception as e:
            logger.error(f"❌ Failed to load repository: {e}")
    
    def _update_indices(self, strategy_id: str, metadata: StrategyMetadata):
        """Update search indices"""
        
        # Tag index
        for tag in metadata.tags:
            self.tag_index[tag.lower()].add(strategy_id)
        
        # Category index
        self.category_index[metadata.category].add(strategy_id)
        
        # Performance index
        self.performance_index[metadata.current_rating].add(strategy_id)
    
    def add_strategy(self, strategy_dna: StrategyDNA, 
                    metadata: Optional[StrategyMetadata] = None) -> str:
        """Add new strategy to repository"""
        
        strategy_id = strategy_dna.strategy_id
        
        try:
            # Create metadata if not provided
            if metadata is None:
                metadata = StrategyMetadata(
                    strategy_id=strategy_id,
                    name=strategy_dna.name,
                    version="1.0.0",
                    category=self._infer_category(strategy_dna),
                    status=StrategyStatus.DEVELOPMENT
                )
            
            # Create initial version
            version = StrategyVersion(
                version_id=f"{strategy_id}_v1.0.0",
                strategy_id=strategy_id,
                version_number="1.0.0",
                strategy_dna=strategy_dna,
                created_timestamp=datetime.now(),
                change_description="Initial version",
                is_active=True
            )
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                # Store metadata
                conn.execute("""
                    INSERT OR REPLACE INTO strategy_metadata 
                    (strategy_id, name, version, category, status, metadata_json, 
                     created_timestamp, last_modified, current_rating, compliance_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy_id, metadata.name, metadata.version, metadata.category.value,
                    metadata.status.value, json.dumps(asdict(metadata), default=str),
                    metadata.created_timestamp.isoformat(), metadata.last_modified.isoformat(),
                    metadata.current_rating.value, metadata.compliance_status
                ))
                
                # Store version
                conn.execute("""
                    INSERT INTO strategy_versions 
                    (version_id, strategy_id, version_number, strategy_dna_json, 
                     created_timestamp, change_description, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    version.version_id, version.strategy_id, version.version_number,
                    json.dumps(asdict(version.strategy_dna), default=str),
                    version.created_timestamp.isoformat(), version.change_description,
                    version.is_active
                ))
                
                conn.commit()
            
            # Update caches
            self.metadata_cache[strategy_id] = metadata
            self.version_cache[strategy_id].append(version)
            self._update_indices(strategy_id, metadata)
            
            # Create audit trail
            self._create_audit_entry("strategy", strategy_id, "created", {"version": "1.0.0"})
            
            logger.info(f"📚 Added strategy {metadata.name} to repository")
            
            return strategy_id
            
        except Exception as e:
            logger.error(f"❌ Failed to add strategy to repository: {e}")
            raise
    
    def create_new_version(self, strategy_id: str, updated_dna: StrategyDNA, 
                          change_description: str = "") -> str:
        """Create new version of existing strategy"""
        
        if strategy_id not in self.metadata_cache:
            raise ValueError(f"Strategy {strategy_id} not found in repository")
        
        try:
            # Get current versions
            current_versions = self.version_cache[strategy_id]
            
            # Generate new version number
            if current_versions:
                latest_version = max(current_versions, key=lambda v: v.created_timestamp)
                version_parts = latest_version.version_number.split('.')
                new_version_num = f"{version_parts[0]}.{version_parts[1]}.{int(version_parts[2]) + 1}"
            else:
                new_version_num = "1.0.0"
            
            # Create new version
            version_id = f"{strategy_id}_v{new_version_num}"
            new_version = StrategyVersion(
                version_id=version_id,
                strategy_id=strategy_id,
                version_number=new_version_num,
                strategy_dna=updated_dna,
                created_timestamp=datetime.now(),
                change_description=change_description,
                is_active=False  # New versions start inactive
            )
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO strategy_versions 
                    (version_id, strategy_id, version_number, strategy_dna_json, 
                     created_timestamp, change_description, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    version_id, strategy_id, new_version_num,
                    json.dumps(asdict(updated_dna), default=str),
                    new_version.created_timestamp.isoformat(), change_description, False
                ))
                
                conn.commit()
            
            # Update cache
            self.version_cache[strategy_id].append(new_version)
            
            # Update metadata
            metadata = self.metadata_cache[strategy_id]
            metadata.last_modified = datetime.now()
            metadata.version = new_version_num
            
            # Create audit trail
            self._create_audit_entry("strategy", strategy_id, "version_created", {
                "version": new_version_num,
                "change_description": change_description
            })
            
            logger.info(f"📝 Created version {new_version_num} for strategy {strategy_id}")
            
            return version_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create new version: {e}")
            raise
    
    def add_performance_record(self, strategy_id: str, version_id: str, 
                             performance: StrategyPerformance,
                             validation_result: Optional[ValidationResult] = None) -> str:
        """Add performance record for strategy version"""
        
        try:
            record_id = str(uuid.uuid4())
            
            # Create performance record
            record = PerformanceRecord(
                record_id=record_id,
                strategy_id=strategy_id,
                version_id=version_id,
                performance_metrics=performance,
                validation_results=validation_result,
                evaluation_period=(performance.start_date, performance.end_date),
                market_regime=MarketRegime.SIDEWAYS,  # Would be determined from market analysis
                symbols_traded=[]
            )
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO performance_records 
                    (record_id, strategy_id, version_id, performance_json, 
                     evaluation_start, evaluation_end, market_regime,
                     recorded_timestamp, data_quality_score, confidence_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record_id, strategy_id, version_id,
                    json.dumps(asdict(performance), default=str),
                    record.evaluation_period[0].isoformat(),
                    record.evaluation_period[1].isoformat(),
                    record.market_regime.value,
                    record.recorded_timestamp.isoformat(),
                    record.data_quality_score, record.confidence_level
                ))
                
                conn.commit()
            
            # Update cache
            self.performance_cache[strategy_id].append(record)
            
            # Update metadata with new rating
            self._update_strategy_rating(strategy_id)
            
            # Create audit trail
            self._create_audit_entry("performance", record_id, "recorded", {
                "strategy_id": strategy_id,
                "version_id": version_id,
                "sharpe_ratio": performance.sharpe_ratio
            })
            
            logger.info(f"📊 Added performance record for {strategy_id}")
            
            return record_id
            
        except Exception as e:
            logger.error(f"❌ Failed to add performance record: {e}")
            raise
    
    def _infer_category(self, strategy_dna: StrategyDNA) -> StrategyCategory:
        """Infer strategy category from DNA"""
        
        # Simple heuristics for categorization
        strategy_type = strategy_dna.strategy_type
        
        if strategy_type == StrategyType.MOMENTUM:
            return StrategyCategory.MOMENTUM
        elif strategy_type == StrategyType.MEAN_REVERSION:
            return StrategyCategory.MEAN_REVERSION
        elif strategy_type == StrategyType.TREND_FOLLOWING:
            return StrategyCategory.TREND_FOLLOWING
        elif strategy_type == StrategyType.STATISTICAL_ARBITRAGE:
            return StrategyCategory.ARBITRAGE
        elif strategy_type == StrategyType.VOLATILITY_TRADING:
            return StrategyCategory.VOLATILITY
        else:
            return StrategyCategory.HYBRID
    
    def _update_strategy_rating(self, strategy_id: str):
        """Update strategy performance rating based on recent performance"""
        
        if strategy_id not in self.performance_cache:
            return
        
        recent_records = sorted(
            self.performance_cache[strategy_id], 
            key=lambda r: r.recorded_timestamp,
            reverse=True
        )[:5]  # Last 5 records
        
        if not recent_records:
            return
        
        # Calculate average Sharpe ratio
        avg_sharpe = np.mean([r.performance_metrics.sharpe_ratio for r in recent_records])
        
        # Determine rating based on Sharpe ratio
        if avg_sharpe >= 2.0:
            new_rating = PerformanceRating.OUTSTANDING
        elif avg_sharpe >= 1.5:
            new_rating = PerformanceRating.EXCELLENT
        elif avg_sharpe >= 1.0:
            new_rating = PerformanceRating.VERY_GOOD
        elif avg_sharpe >= 0.5:
            new_rating = PerformanceRating.GOOD
        elif avg_sharpe >= 0.0:
            new_rating = PerformanceRating.AVERAGE
        elif avg_sharpe >= -0.5:
            new_rating = PerformanceRating.BELOW_AVERAGE
        elif avg_sharpe >= -1.0:
            new_rating = PerformanceRating.POOR
        else:
            new_rating = PerformanceRating.VERY_POOR
        
        # Update metadata
        metadata = self.metadata_cache[strategy_id]
        old_rating = metadata.current_rating
        metadata.current_rating = new_rating
        
        # Update best rating if improved
        if self._rating_value(new_rating) > self._rating_value(metadata.best_rating_achieved):
            metadata.best_rating_achieved = new_rating
        
        # Update database
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE strategy_metadata 
                    SET current_rating = ?, metadata_json = ?, last_modified = ?
                    WHERE strategy_id = ?
                """, (
                    new_rating.value,
                    json.dumps(asdict(metadata), default=str),
                    datetime.now().isoformat(),
                    strategy_id
                ))
                conn.commit()
            
            # Update performance index
            self.performance_index[old_rating].discard(strategy_id)
            self.performance_index[new_rating].add(strategy_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to update strategy rating: {e}")
    
    def _rating_value(self, rating: PerformanceRating) -> int:
        """Convert rating to numeric value for comparison"""
        rating_values = {
            PerformanceRating.OUTSTANDING: 8,
            PerformanceRating.EXCELLENT: 7,
            PerformanceRating.VERY_GOOD: 6,
            PerformanceRating.GOOD: 5,
            PerformanceRating.AVERAGE: 4,
            PerformanceRating.BELOW_AVERAGE: 3,
            PerformanceRating.POOR: 2,
            PerformanceRating.VERY_POOR: 1
        }
        return rating_values.get(rating, 4)
    
    def _create_audit_entry(self, entity_type: str, entity_id: str, action: str, 
                          details: Dict[str, Any], user_id: str = "system"):
        """Create audit trail entry"""
        
        try:
            audit_id = str(uuid.uuid4())
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO audit_trail 
                    (audit_id, entity_type, entity_id, action, details_json, timestamp, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    audit_id, entity_type, entity_id, action,
                    json.dumps(details, default=str),
                    datetime.now().isoformat(), user_id
                ))
                conn.commit()
                
        except Exception as e:
            logger.debug(f"Failed to create audit entry: {e}")

class PerformanceAnalytics:
    """
    📈 Advanced Performance Analytics Engine
    """
    
    def __init__(self, repository: StrategyRepository):
        self.repository = repository
        self.analytics_cache = {}
        self.benchmark_cache = {}
    
    def calculate_strategy_analytics(self, strategy_id: str) -> Dict[str, Any]:
        """Calculate comprehensive analytics for strategy"""
        
        try:
            if strategy_id not in self.repository.metadata_cache:
                return {"error": f"Strategy {strategy_id} not found"}
            
            metadata = self.repository.metadata_cache[strategy_id]
            performance_records = self.repository.performance_cache[strategy_id]
            
            if not performance_records:
                return {"error": "No performance data available"}
            
            # Basic statistics
            sharpe_ratios = [r.performance_metrics.sharpe_ratio for r in performance_records]
            returns = [r.performance_metrics.total_return for r in performance_records]
            drawdowns = [r.performance_metrics.max_drawdown for r in performance_records]
            
            analytics = {
                "strategy_id": strategy_id,
                "strategy_name": metadata.name,
                "current_rating": metadata.current_rating.value,
                "total_evaluations": len(performance_records),
                
                # Performance statistics
                "performance_stats": {
                    "mean_sharpe": np.mean(sharpe_ratios),
                    "median_sharpe": np.median(sharpe_ratios),
                    "std_sharpe": np.std(sharpe_ratios),
                    "min_sharpe": np.min(sharpe_ratios),
                    "max_sharpe": np.max(sharpe_ratios),
                    
                    "mean_return": np.mean(returns),
                    "std_return": np.std(returns),
                    "best_return": np.max(returns),
                    "worst_return": np.min(returns),
                    
                    "mean_drawdown": np.mean(drawdowns),
                    "worst_drawdown": np.max(drawdowns),
                    "best_drawdown": np.min(drawdowns)
                },
                
                # Consistency metrics
                "consistency": {
                    "sharpe_consistency": 1.0 - (np.std(sharpe_ratios) / max(0.1, np.mean(np.abs(sharpe_ratios)))),
                    "positive_periods": len([r for r in returns if r > 0]) / len(returns),
                    "streak_analysis": self._calculate_streaks(returns),
                    "volatility_of_volatility": np.std([r.performance_metrics.volatility for r in performance_records])
                },
                
                # Risk metrics
                "risk_analysis": {
                    "downside_capture": self._calculate_downside_capture(performance_records),
                    "upside_capture": self._calculate_upside_capture(performance_records),
                    "tail_risk": self._calculate_tail_risk(returns),
                    "maximum_adverse_excursion": max(drawdowns),
                    "risk_adjusted_return": np.mean(sharpe_ratios)
                },
                
                # Regime analysis
                "regime_performance": self._analyze_regime_performance(performance_records),
                
                # Time series analysis
                "trend_analysis": self._analyze_performance_trends(performance_records),
                
                # Quality metrics
                "data_quality": {
                    "avg_data_quality": np.mean([r.data_quality_score for r in performance_records]),
                    "avg_confidence": np.mean([r.confidence_level for r in performance_records]),
                    "recent_quality": np.mean([r.data_quality_score for r in performance_records[-5:]] if len(performance_records) >= 5 else [r.data_quality_score for r in performance_records])
                }
            }
            
            # Cache results
            self.analytics_cache[strategy_id] = analytics
            
            return analytics
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate analytics for {strategy_id}: {e}")
            return {"error": str(e)}
    
    def _calculate_streaks(self, returns: List[float]) -> Dict[str, Any]:
        """Calculate winning and losing streaks"""
        
        if not returns:
            return {}
        
        current_streak = 0
        current_type = None
        max_winning_streak = 0
        max_losing_streak = 0
        winning_streaks = []
        losing_streaks = []
        
        for ret in returns:
            if ret > 0:  # Winning period
                if current_type == "win":
                    current_streak += 1
                else:
                    if current_type == "loss" and current_streak > 0:
                        losing_streaks.append(current_streak)
                        max_losing_streak = max(max_losing_streak, current_streak)
                    current_streak = 1
                    current_type = "win"
            else:  # Losing period
                if current_type == "loss":
                    current_streak += 1
                else:
                    if current_type == "win" and current_streak > 0:
                        winning_streaks.append(current_streak)
                        max_winning_streak = max(max_winning_streak, current_streak)
                    current_streak = 1
                    current_type = "loss"
        
        # Handle final streak
        if current_type == "win":
            winning_streaks.append(current_streak)
            max_winning_streak = max(max_winning_streak, current_streak)
        elif current_type == "loss":
            losing_streaks.append(current_streak)
            max_losing_streak = max(max_losing_streak, current_streak)
        
        return {
            "max_winning_streak": max_winning_streak,
            "max_losing_streak": max_losing_streak,
            "avg_winning_streak": np.mean(winning_streaks) if winning_streaks else 0,
            "avg_losing_streak": np.mean(losing_streaks) if losing_streaks else 0,
            "total_winning_streaks": len(winning_streaks),
            "total_losing_streaks": len(losing_streaks)
        }
    
    def _calculate_downside_capture(self, records: List[PerformanceRecord]) -> float:
        """Calculate downside capture ratio"""
        
        # Simplified calculation - in practice would compare to benchmark
        negative_returns = [r.performance_metrics.total_return for r in records if r.performance_metrics.total_return < 0]
        
        if not negative_returns:
            return 0.0
        
        # Return average magnitude of negative returns
        return abs(np.mean(negative_returns))
    
    def _calculate_upside_capture(self, records: List[PerformanceRecord]) -> float:
        """Calculate upside capture ratio"""
        
        positive_returns = [r.performance_metrics.total_return for r in records if r.performance_metrics.total_return > 0]
        
        if not positive_returns:
            return 0.0
        
        return np.mean(positive_returns)
    
    def _calculate_tail_risk(self, returns: List[float]) -> Dict[str, float]:
        """Calculate tail risk metrics"""
        
        if len(returns) < 10:
            return {}
        
        returns_array = np.array(returns)
        
        return {
            "var_95": np.percentile(returns_array, 5),
            "var_99": np.percentile(returns_array, 1),
            "cvar_95": np.mean(returns_array[returns_array <= np.percentile(returns_array, 5)]),
            "cvar_99": np.mean(returns_array[returns_array <= np.percentile(returns_array, 1)]),
            "tail_ratio": abs(np.percentile(returns_array, 5)) / np.percentile(returns_array, 95) if np.percentile(returns_array, 95) > 0 else 0
        }
    
    def _analyze_regime_performance(self, records: List[PerformanceRecord]) -> Dict[str, Dict[str, float]]:
        """Analyze performance across market regimes"""
        
        regime_performance = defaultdict(list)
        
        for record in records:
            regime = record.market_regime
            regime_performance[regime.value].append({
                "return": record.performance_metrics.total_return,
                "sharpe": record.performance_metrics.sharpe_ratio,
                "drawdown": record.performance_metrics.max_drawdown
            })
        
        regime_analysis = {}
        for regime, performances in regime_performance.items():
            if performances:
                regime_analysis[regime] = {
                    "count": len(performances),
                    "avg_return": np.mean([p["return"] for p in performances]),
                    "avg_sharpe": np.mean([p["sharpe"] for p in performances]),
                    "avg_drawdown": np.mean([p["drawdown"] for p in performances]),
                    "consistency": 1.0 - np.std([p["return"] for p in performances]) / max(0.01, np.mean(np.abs([p["return"] for p in performances])))
                }
        
        return regime_analysis
    
    def _analyze_performance_trends(self, records: List[PerformanceRecord]) -> Dict[str, Any]:
        """Analyze performance trends over time"""
        
        if len(records) < 5:
            return {"error": "Insufficient data for trend analysis"}
        
        # Sort by timestamp
        sorted_records = sorted(records, key=lambda r: r.recorded_timestamp)
        
        # Extract time series
        timestamps = [r.recorded_timestamp for r in sorted_records]
        sharpe_ratios = [r.performance_metrics.sharpe_ratio for r in sorted_records]
        returns = [r.performance_metrics.total_return for r in sorted_records]
        
        # Calculate trends using simple linear regression
        n = len(timestamps)
        time_indices = np.arange(n)
        
        # Sharpe trend
        sharpe_slope = np.polyfit(time_indices, sharpe_ratios, 1)[0]
        
        # Return trend
        return_slope = np.polyfit(time_indices, returns, 1)[0]
        
        # Recent vs historical performance
        recent_count = min(5, n // 3)  # Last 1/3 or 5 records
        recent_sharpe = np.mean(sharpe_ratios[-recent_count:])
        historical_sharpe = np.mean(sharpe_ratios[:-recent_count]) if len(sharpe_ratios) > recent_count else recent_sharpe
        
        return {
            "sharpe_trend": "improving" if sharpe_slope > 0.01 else "declining" if sharpe_slope < -0.01 else "stable",
            "return_trend": "improving" if return_slope > 0.001 else "declining" if return_slope < -0.001 else "stable",
            "sharpe_slope": sharpe_slope,
            "return_slope": return_slope,
            "recent_vs_historical": {
                "recent_sharpe": recent_sharpe,
                "historical_sharpe": historical_sharpe,
                "improvement": recent_sharpe - historical_sharpe
            },
            "volatility_trend": self._calculate_volatility_trend([r.performance_metrics.volatility for r in sorted_records])
        }
    
    def _calculate_volatility_trend(self, volatilities: List[float]) -> Dict[str, float]:
        """Calculate volatility trend"""
        
        if len(volatilities) < 3:
            return {}
        
        vol_slope = np.polyfit(np.arange(len(volatilities)), volatilities, 1)[0]
        
        return {
            "volatility_slope": vol_slope,
            "trend": "increasing" if vol_slope > 0.01 else "decreasing" if vol_slope < -0.01 else "stable"
        }

class StrategySearchEngine:
    """
    🔍 Advanced Strategy Search & Discovery Engine
    """
    
    def __init__(self, repository: StrategyRepository):
        self.repository = repository
        self.search_cache = {}
    
    def search_strategies(self, 
                        query: str = "",
                        categories: List[StrategyCategory] = None,
                        status_filter: List[StrategyStatus] = None,
                        rating_filter: List[PerformanceRating] = None,
                        min_sharpe: float = None,
                        max_drawdown: float = None,
                        tags: List[str] = None,
                        limit: int = 50) -> List[Dict[str, Any]]:
        """Advanced strategy search with multiple filters"""
        
        try:
            # Start with all strategies
            candidate_ids = set(self.repository.metadata_cache.keys())
            
            # Apply filters
            if query:
                query_ids = self._text_search(query)
                candidate_ids &= query_ids
            
            if categories:
                category_ids = set()
                for category in categories:
                    category_ids.update(self.repository.category_index[category])
                candidate_ids &= category_ids
            
            if rating_filter:
                rating_ids = set()
                for rating in rating_filter:
                    rating_ids.update(self.repository.performance_index[rating])
                candidate_ids &= rating_ids
            
            if tags:
                tag_ids = set()
                for tag in tags:
                    tag_ids.update(self.repository.tag_index[tag.lower()])
                if tag_ids:  # Only filter if tags found
                    candidate_ids &= tag_ids
            
            # Performance filters
            if min_sharpe is not None or max_drawdown is not None:
                performance_filtered = self._filter_by_performance(
                    candidate_ids, min_sharpe, max_drawdown
                )
                candidate_ids &= performance_filtered
            
            # Status filter
            if status_filter:
                status_filtered = {
                    sid for sid in candidate_ids 
                    if self.repository.metadata_cache[sid].status in status_filter
                }
                candidate_ids = status_filtered
            
            # Convert to result list with metadata
            results = []
            for strategy_id in candidate_ids:
                metadata = self.repository.metadata_cache[strategy_id]
                
                # Get latest performance
                latest_performance = None
                if strategy_id in self.repository.performance_cache:
                    perf_records = self.repository.performance_cache[strategy_id]
                    if perf_records:
                        latest_performance = max(perf_records, key=lambda r: r.recorded_timestamp)
                
                result = {
                    "strategy_id": strategy_id,
                    "name": metadata.name,
                    "category": metadata.category.value,
                    "status": metadata.status.value,
                    "rating": metadata.current_rating.value,
                    "version": metadata.version,
                    "created": metadata.created_timestamp,
                    "tags": metadata.tags,
                    "description": metadata.description,
                    "latest_performance": {
                        "sharpe_ratio": latest_performance.performance_metrics.sharpe_ratio if latest_performance else 0,
                        "total_return": latest_performance.performance_metrics.total_return if latest_performance else 0,
                        "max_drawdown": latest_performance.performance_metrics.max_drawdown if latest_performance else 0
                    } if latest_performance else None
                }
                
                results.append(result)
            
            # Sort by rating and performance
            results.sort(key=lambda r: (
                self.repository._rating_value(PerformanceRating(r["rating"])),
                r["latest_performance"]["sharpe_ratio"] if r["latest_performance"] else 0
            ), reverse=True)
            
            # Apply limit
            return results[:limit]
            
        except Exception as e:
            logger.error(f"❌ Strategy search failed: {e}")
            return []
    
    def _text_search(self, query: str) -> Set[str]:
        """Perform text search across strategy names and descriptions"""
        
        query_terms = query.lower().split()
        matching_ids = set()
        
        for strategy_id, metadata in self.repository.metadata_cache.items():
            # Search in name
            name_match = any(term in metadata.name.lower() for term in query_terms)
            
            # Search in description
            desc_match = any(term in metadata.description.lower() for term in query_terms) if metadata.description else False
            
            # Search in tags
            tag_match = any(term in tag.lower() for tag in metadata.tags for term in query_terms)
            
            if name_match or desc_match or tag_match:
                matching_ids.add(strategy_id)
        
        return matching_ids
    
    def _filter_by_performance(self, candidate_ids: Set[str], 
                             min_sharpe: float = None, 
                             max_drawdown: float = None) -> Set[str]:
        """Filter strategies by performance criteria"""
        
        filtered_ids = set()
        
        for strategy_id in candidate_ids:
            if strategy_id not in self.repository.performance_cache:
                continue
            
            records = self.repository.performance_cache[strategy_id]
            if not records:
                continue
            
            # Get recent average performance
            recent_records = sorted(records, key=lambda r: r.recorded_timestamp, reverse=True)[:3]
            
            avg_sharpe = np.mean([r.performance_metrics.sharpe_ratio for r in recent_records])
            avg_drawdown = np.mean([r.performance_metrics.max_drawdown for r in recent_records])
            
            # Apply filters
            sharpe_ok = min_sharpe is None or avg_sharpe >= min_sharpe
            drawdown_ok = max_drawdown is None or avg_drawdown <= max_drawdown
            
            if sharpe_ok and drawdown_ok:
                filtered_ids.add(strategy_id)
        
        return filtered_ids
    
    def get_top_performers(self, 
                          category: Optional[StrategyCategory] = None,
                          timeframe: str = "all_time",  # all_time, recent, last_month
                          metric: str = "sharpe_ratio",  # sharpe_ratio, return, calmar_ratio
                          limit: int = 10) -> List[Dict[str, Any]]:
        """Get top performing strategies"""
        
        try:
            # Get candidate strategies
            candidate_ids = set(self.repository.metadata_cache.keys())
            
            if category:
                candidate_ids = self.repository.category_index[category]
            
            # Calculate performance scores
            strategy_scores = []
            
            for strategy_id in candidate_ids:
                if strategy_id not in self.repository.performance_cache:
                    continue
                
                records = self.repository.performance_cache[strategy_id]
                if not records:
                    continue
                
                # Filter records by timeframe
                if timeframe == "recent":
                    cutoff_date = datetime.now() - timedelta(days=90)
                    filtered_records = [r for r in records if r.recorded_timestamp >= cutoff_date]
                elif timeframe == "last_month":
                    cutoff_date = datetime.now() - timedelta(days=30)
                    filtered_records = [r for r in records if r.recorded_timestamp >= cutoff_date]
                else:
                    filtered_records = records
                
                if not filtered_records:
                    continue
                
                # Calculate average metric
                if metric == "sharpe_ratio":
                    score = np.mean([r.performance_metrics.sharpe_ratio for r in filtered_records])
                elif metric == "return":
                    score = np.mean([r.performance_metrics.total_return for r in filtered_records])
                elif metric == "calmar_ratio":
                    score = np.mean([r.performance_metrics.calmar_ratio for r in filtered_records])
                else:
                    score = np.mean([r.performance_metrics.sharpe_ratio for r in filtered_records])
                
                metadata = self.repository.metadata_cache[strategy_id]
                latest_record = max(filtered_records, key=lambda r: r.recorded_timestamp)
                
                strategy_scores.append({
                    "strategy_id": strategy_id,
                    "name": metadata.name,
                    "category": metadata.category.value,
                    "rating": metadata.current_rating.value,
                    "score": score,
                    "latest_performance": asdict(latest_record.performance_metrics),
                    "evaluation_count": len(filtered_records)
                })
            
            # Sort by score
            strategy_scores.sort(key=lambda s: s["score"], reverse=True)
            
            return strategy_scores[:limit]
            
        except Exception as e:
            logger.error(f"❌ Failed to get top performers: {e}")
            return []
    
    def recommend_strategies(self, 
                           target_sharpe: float = 1.0,
                           max_drawdown: float = 0.15,
                           preferred_categories: List[StrategyCategory] = None,
                           market_regime: MarketRegime = None,
                           limit: int = 5) -> List[Dict[str, Any]]:
        """Recommend strategies based on criteria"""
        
        try:
            recommendations = []
            
            # Search with relaxed criteria first
            candidates = self.search_strategies(
                categories=preferred_categories,
                rating_filter=[PerformanceRating.GOOD, PerformanceRating.VERY_GOOD, 
                              PerformanceRating.EXCELLENT, PerformanceRating.OUTSTANDING],
                min_sharpe=target_sharpe * 0.7,  # 70% of target
                max_drawdown=max_drawdown * 1.5,  # 150% of max
                limit=50
            )
            
            # Score candidates
            for candidate in candidates:
                strategy_id = candidate["strategy_id"]
                
                if strategy_id not in self.repository.performance_cache:
                    continue
                
                records = self.repository.performance_cache[strategy_id]
                if not records:
                    continue
                
                # Calculate recommendation score
                recent_records = sorted(records, key=lambda r: r.recorded_timestamp, reverse=True)[:3]
                
                avg_sharpe = np.mean([r.performance_metrics.sharpe_ratio for r in recent_records])
                avg_drawdown = np.mean([r.performance_metrics.max_drawdown for r in recent_records])
                consistency = 1.0 - np.std([r.performance_metrics.sharpe_ratio for r in recent_records]) / max(0.1, np.mean(np.abs([r.performance_metrics.sharpe_ratio for r in recent_records])))
                
                # Scoring formula
                sharpe_score = min(1.0, avg_sharpe / max(0.1, target_sharpe))
                drawdown_score = min(1.0, max_drawdown / max(0.01, avg_drawdown))
                consistency_score = consistency
                
                # Regime bonus if applicable
                regime_bonus = 0.0
                if market_regime:
                    # Would check strategy's regime sensitivity
                    regime_bonus = 0.1
                
                total_score = (sharpe_score * 0.4 + drawdown_score * 0.3 + 
                             consistency_score * 0.2 + regime_bonus)
                
                recommendation = candidate.copy()
                recommendation.update({
                    "recommendation_score": total_score,
                    "avg_recent_sharpe": avg_sharpe,
                    "avg_recent_drawdown": avg_drawdown,
                    "consistency": consistency,
                    "reason": self._generate_recommendation_reason(avg_sharpe, avg_drawdown, consistency, target_sharpe, max_drawdown)
                })
                
                recommendations.append(recommendation)
            
            # Sort by recommendation score
            recommendations.sort(key=lambda r: r["recommendation_score"], reverse=True)
            
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"❌ Strategy recommendation failed: {e}")
            return []
    
    def _generate_recommendation_reason(self, sharpe: float, drawdown: float, 
                                      consistency: float, target_sharpe: float, 
                                      max_drawdown: float) -> str:
        """Generate human-readable recommendation reason"""
        
        reasons = []
        
        if sharpe >= target_sharpe:
            reasons.append(f"Exceeds target Sharpe ratio ({sharpe:.2f} vs {target_sharpe:.2f})")
        
        if drawdown <= max_drawdown:
            reasons.append(f"Low drawdown risk ({drawdown:.1%} vs {max_drawdown:.1%} max)")
        
        if consistency >= 0.7:
            reasons.append("Consistent performance across periods")
        
        if not reasons:
            reasons.append("Best available option meeting relaxed criteria")
        
        return "; ".join(reasons)

class InstitutionalStrategyLibrary:
    """
    🏛️ MAIN INSTITUTIONAL STRATEGY LIBRARY SYSTEM
    Enterprise-grade strategy repository with comprehensive management capabilities
    """
    
    def __init__(self, db_path: str = "bot/institutional_library.db"):
        self.repository = StrategyRepository(db_path)
        self.analytics = PerformanceAnalytics(self.repository)
        self.search_engine = StrategySearchEngine(self.repository)
        
        # System statistics
        self.system_stats = {
            "total_strategies": 0,
            "total_versions": 0,
            "total_performance_records": 0,
            "system_uptime": datetime.now(),
            "last_updated": datetime.now()
        }
        
        self._update_system_stats()
        
        logger.info(f"🏛️ Institutional Strategy Library initialized: "
                   f"{self.system_stats['total_strategies']} strategies, "
                   f"{self.system_stats['total_performance_records']} performance records")
    
    def _update_system_stats(self):
        """Update system statistics"""
        
        self.system_stats.update({
            "total_strategies": len(self.repository.metadata_cache),
            "total_versions": sum(len(versions) for versions in self.repository.version_cache.values()),
            "total_performance_records": sum(len(records) for records in self.repository.performance_cache.values()),
            "last_updated": datetime.now()
        })
    
    # Facade methods for easy access
    def add_strategy(self, strategy_dna: StrategyDNA, 
                    metadata: Optional[StrategyMetadata] = None) -> str:
        """Add new strategy to library"""
        strategy_id = self.repository.add_strategy(strategy_dna, metadata)
        self._update_system_stats()
        return strategy_id
    
    def record_performance(self, strategy_id: str, version_id: str,
                         performance: StrategyPerformance,
                         validation_result: Optional[ValidationResult] = None) -> str:
        """Record performance for strategy"""
        record_id = self.repository.add_performance_record(
            strategy_id, version_id, performance, validation_result
        )
        self._update_system_stats()
        return record_id
    
    def search_strategies(self, **kwargs) -> List[Dict[str, Any]]:
        """Search strategies"""
        return self.search_engine.search_strategies(**kwargs)
    
    def get_top_performers(self, **kwargs) -> List[Dict[str, Any]]:
        """Get top performing strategies"""
        return self.search_engine.get_top_performers(**kwargs)
    
    def recommend_strategies(self, **kwargs) -> List[Dict[str, Any]]:
        """Get strategy recommendations"""
        return self.search_engine.recommend_strategies(**kwargs)
    
    def get_strategy_analytics(self, strategy_id: str) -> Dict[str, Any]:
        """Get comprehensive strategy analytics"""
        return self.analytics.calculate_strategy_analytics(strategy_id)
    
    def get_library_dashboard(self) -> Dict[str, Any]:
        """Get library dashboard with key metrics"""
        
        try:
            # Category distribution
            category_dist = defaultdict(int)
            rating_dist = defaultdict(int)
            status_dist = defaultdict(int)
            
            for metadata in self.repository.metadata_cache.values():
                category_dist[metadata.category.value] += 1
                rating_dist[metadata.current_rating.value] += 1
                status_dist[metadata.status.value] += 1
            
            # Recent performance
            all_recent_performances = []
            for records in self.repository.performance_cache.values():
                if records:
                    recent = sorted(records, key=lambda r: r.recorded_timestamp, reverse=True)[:1]
                    all_recent_performances.extend(recent)
            
            recent_sharpes = [r.performance_metrics.sharpe_ratio for r in all_recent_performances]
            recent_returns = [r.performance_metrics.total_return for r in all_recent_performances]
            
            # Top performers
            top_performers = self.get_top_performers(limit=5)
            
            return {
                "system_statistics": self.system_stats,
                "distributions": {
                    "by_category": dict(category_dist),
                    "by_rating": dict(rating_dist),
                    "by_status": dict(status_dist)
                },
                "performance_summary": {
                    "avg_sharpe_ratio": np.mean(recent_sharpes) if recent_sharpes else 0,
                    "median_sharpe_ratio": np.median(recent_sharpes) if recent_sharpes else 0,
                    "avg_return": np.mean(recent_returns) if recent_returns else 0,
                    "strategies_with_positive_sharpe": len([s for s in recent_sharpes if s > 0]) if recent_sharpes else 0,
                    "total_evaluated_strategies": len(recent_sharpes)
                },
                "top_performers": top_performers,
                "recent_activity": {
                    "strategies_added_last_7d": self._count_recent_strategies(7),
                    "strategies_added_last_30d": self._count_recent_strategies(30),
                    "performance_records_last_7d": self._count_recent_performance_records(7),
                    "performance_records_last_30d": self._count_recent_performance_records(30)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate library dashboard: {e}")
            return {"error": str(e)}
    
    def _count_recent_strategies(self, days: int) -> int:
        """Count strategies added in recent days"""
        
        cutoff = datetime.now() - timedelta(days=days)
        count = 0
        
        for metadata in self.repository.metadata_cache.values():
            if metadata.created_timestamp >= cutoff:
                count += 1
        
        return count
    
    def _count_recent_performance_records(self, days: int) -> int:
        """Count performance records added in recent days"""
        
        cutoff = datetime.now() - timedelta(days=days)
        count = 0
        
        for records in self.repository.performance_cache.values():
            for record in records:
                if record.recorded_timestamp >= cutoff:
                    count += 1
        
        return count
    
    def export_strategy(self, strategy_id: str, 
                       include_performance: bool = True) -> Dict[str, Any]:
        """Export strategy data"""
        
        if strategy_id not in self.repository.metadata_cache:
            return {"error": f"Strategy {strategy_id} not found"}
        
        try:
            export_data = {
                "metadata": asdict(self.repository.metadata_cache[strategy_id]),
                "versions": [asdict(v) for v in self.repository.version_cache[strategy_id]],
                "export_timestamp": datetime.now().isoformat()
            }
            
            if include_performance:
                export_data["performance_records"] = [
                    asdict(r) for r in self.repository.performance_cache[strategy_id]
                ]
                export_data["analytics"] = self.get_strategy_analytics(strategy_id)
            
            return export_data
            
        except Exception as e:
            logger.error(f"❌ Failed to export strategy {strategy_id}: {e}")
            return {"error": str(e)}
    
    def generate_strategy_report(self, strategy_id: str) -> str:
        """Generate comprehensive strategy report"""
        
        try:
            if strategy_id not in self.repository.metadata_cache:
                return f"Strategy {strategy_id} not found"
            
            metadata = self.repository.metadata_cache[strategy_id]
            analytics = self.get_strategy_analytics(strategy_id)
            
            # Generate report
            report_lines = []
            report_lines.append("="*80)
            report_lines.append(f"INSTITUTIONAL STRATEGY REPORT")
            report_lines.append("="*80)
            report_lines.append("")
            
            # Basic information
            report_lines.append("STRATEGY INFORMATION:")
            report_lines.append(f"Name: {metadata.name}")
            report_lines.append(f"ID: {strategy_id}")
            report_lines.append(f"Category: {metadata.category.value.title()}")
            report_lines.append(f"Status: {metadata.status.value.title()}")
            report_lines.append(f"Current Rating: {metadata.current_rating.value.title()}")
            report_lines.append(f"Created: {metadata.created_timestamp.strftime('%Y-%m-%d %H:%M')}")
            report_lines.append(f"Version: {metadata.version}")
            report_lines.append("")
            
            # Performance summary
            if not analytics.get("error"):
                perf_stats = analytics.get("performance_stats", {})
                report_lines.append("PERFORMANCE SUMMARY:")
                report_lines.append(f"Average Sharpe Ratio: {perf_stats.get('mean_sharpe', 0):.3f}")
                report_lines.append(f"Best Sharpe Ratio: {perf_stats.get('max_sharpe', 0):.3f}")
                report_lines.append(f"Average Return: {perf_stats.get('mean_return', 0):.2%}")
                report_lines.append(f"Worst Drawdown: {perf_stats.get('worst_drawdown', 0):.2%}")
                report_lines.append(f"Total Evaluations: {analytics.get('total_evaluations', 0)}")
                report_lines.append("")
                
                # Risk analysis
                risk_analysis = analytics.get("risk_analysis", {})
                report_lines.append("RISK ANALYSIS:")
                report_lines.append(f"Risk-Adjusted Return: {risk_analysis.get('risk_adjusted_return', 0):.3f}")
                report_lines.append(f"Maximum Adverse Excursion: {risk_analysis.get('maximum_adverse_excursion', 0):.2%}")
                report_lines.append(f"Tail Risk (VaR 95%): {risk_analysis.get('tail_risk', {}).get('var_95', 0):.2%}")
                report_lines.append("")
                
                # Consistency metrics
                consistency = analytics.get("consistency", {})
                report_lines.append("CONSISTENCY ANALYSIS:")
                report_lines.append(f"Sharpe Consistency: {consistency.get('sharpe_consistency', 0):.3f}")
                report_lines.append(f"Positive Periods: {consistency.get('positive_periods', 0):.1%}")
                report_lines.append(f"Max Winning Streak: {consistency.get('streak_analysis', {}).get('max_winning_streak', 0)}")
                report_lines.append("")
            
            # Tags and classification
            if metadata.tags:
                report_lines.append(f"Tags: {', '.join(metadata.tags)}")
                report_lines.append("")
            
            # Description
            if metadata.description:
                report_lines.append("DESCRIPTION:")
                report_lines.append(metadata.description)
                report_lines.append("")
            
            # Compliance status
            report_lines.append("COMPLIANCE STATUS:")
            report_lines.append(f"Status: {metadata.compliance_status.title()}")
            if metadata.compliance_notes:
                report_lines.append(f"Notes: {metadata.compliance_notes}")
            report_lines.append("")
            
            report_lines.append("="*80)
            report_lines.append(f"Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append("="*80)
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"❌ Failed to generate report for {strategy_id}: {e}")
            return f"Error generating report: {str(e)}"

# Global library instance
_institutional_library: Optional[InstitutionalStrategyLibrary] = None

def get_institutional_library() -> InstitutionalStrategyLibrary:
    """Get global institutional library instance"""
    global _institutional_library
    
    if _institutional_library is None:
        _institutional_library = InstitutionalStrategyLibrary()
    
    return _institutional_library

# Integration functions

def add_strategy_to_library(strategy_dna: StrategyDNA, 
                          category: Optional[StrategyCategory] = None,
                          tags: List[str] = None,
                          description: str = "") -> str:
    """Add strategy to institutional library"""
    
    library = get_institutional_library()
    
    # Create metadata
    metadata = StrategyMetadata(
        strategy_id=strategy_dna.strategy_id,
        name=strategy_dna.name,
        version="1.0.0",
        category=category or StrategyCategory.HYBRID,
        status=StrategyStatus.DEVELOPMENT,
        tags=tags or [],
        description=description
    )
    
    return library.add_strategy(strategy_dna, metadata)

def record_strategy_performance(strategy_id: str, performance: StrategyPerformance,
                              validation_result: Optional[ValidationResult] = None) -> str:
    """Record performance for strategy in library"""
    
    library = get_institutional_library()
    
    # Find latest version
    versions = library.repository.version_cache.get(strategy_id, [])
    if not versions:
        raise ValueError(f"No versions found for strategy {strategy_id}")
    
    latest_version = max(versions, key=lambda v: v.created_timestamp)
    
    return library.record_performance(strategy_id, latest_version.version_id, performance, validation_result)

def get_best_strategies_for_regime(regime: MarketRegime, limit: int = 5) -> List[Dict[str, Any]]:
    """Get best strategies for specific market regime"""
    
    library = get_institutional_library()
    
    # This would be enhanced with actual regime-specific filtering
    return library.get_top_performers(limit=limit)

def get_library_summary() -> Dict[str, Any]:
    """Get library summary statistics"""
    
    library = get_institutional_library()
    return library.get_library_dashboard()

if __name__ == "__main__":
    # Example usage and testing
    async def test_institutional_library():
        """Test the institutional library"""
        
        library = get_institutional_library()
        
        # Test library dashboard
        dashboard = library.get_library_dashboard()
        print(f"Library Dashboard: {dashboard['system_statistics']}")
        
        # Test search
        results = library.search_strategies(limit=5)
        print(f"Search results: {len(results)} strategies found")
        
        # Test recommendations
        recommendations = library.recommend_strategies(target_sharpe=0.8, limit=3)
        print(f"Recommendations: {len(recommendations)} strategies recommended")
        
        return library
    
    # Run test
    test_library = asyncio.run(test_institutional_library())