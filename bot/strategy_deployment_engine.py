#!/usr/bin/env python3
"""
🚀 REAL-TIME STRATEGY DEPLOYMENT ENGINE - INSTITUTIONAL GRADE
Advanced deployment system for live strategy execution with A/B testing and risk management
- Real-time Strategy Deployment Pipeline
- A/B Testing Framework with Statistical Analysis
- Dynamic Strategy Allocation & Rebalancing
- Performance Monitoring & Health Checks
- Automated Strategy Lifecycle Management
- Risk Control & Circuit Breakers
- Seamless Trading Bot Integration
"""
import os
import json
import asyncio
import time
import uuid
import threading
import signal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, Callable, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
import numpy as np
import pandas as pd
from loguru import logger
import warnings
warnings.filterwarnings("ignore")

# Statistical libraries for A/B testing
from scipy import stats
from scipy.stats import ttest_ind, mannwhitneyu, chi2_contingency

from .config import settings
from .util import logger

try:
    from .ai_strategy_generator import (
        StrategyDNA, StrategyPerformance, StrategyType, MarketRegime, AIStrategyGenerator
    )
    from .strategy_validation_engine import ValidationResult, ValidationStatus
    from .institutional_strategy_library import InstitutionalStrategyLibrary, PerformanceRecord
    from .market_regime_analyzer import RegimeAnalysis, AdvancedRegimeDetector
    from .advanced_memory_rag_system import KnowledgeEntry, KnowledgeType
except ImportError as e:
    logger.warning(f"Some deployment dependencies not available: {e}")

class DeploymentStatus(Enum):
    """Strategy deployment status"""
    PREPARING = "preparing"              # Being prepared for deployment
    WARMING_UP = "warming_up"            # Warming up with paper trading
    LIVE = "live"                        # Live trading
    TESTING = "testing"                  # A/B testing phase
    MONITORING = "monitoring"            # Under performance monitoring
    SCALING_UP = "scaling_up"            # Increasing allocation
    SCALING_DOWN = "scaling_down"        # Decreasing allocation
    PAUSED = "paused"                    # Temporarily paused
    RETIRING = "retiring"                # Being retired
    RETIRED = "retired"                  # Retired from trading

class DeploymentTier(Enum):
    """Deployment tier classification"""
    PAPER = "paper"                      # Paper trading only
    MICRO = "micro"                      # Very small allocation (0.1-1%)
    SMALL = "small"                      # Small allocation (1-5%)
    MEDIUM = "medium"                    # Medium allocation (5-15%)
    LARGE = "large"                      # Large allocation (15-30%)
    CORE = "core"                        # Core allocation (30%+)

class ABTestStatus(Enum):
    """A/B test status"""
    DESIGNING = "designing"              # Test being designed
    RUNNING = "running"                  # Test in progress
    ANALYZING = "analyzing"              # Results being analyzed
    CONCLUDED = "concluded"              # Test concluded
    CANCELLED = "cancelled"              # Test cancelled

class HealthStatus(Enum):
    """Strategy health status"""
    HEALTHY = "healthy"                  # Performing as expected
    WARNING = "warning"                  # Minor performance issues
    CRITICAL = "critical"                # Major performance issues
    EMERGENCY = "emergency"              # Emergency shutdown required

@dataclass
class DeploymentConfig:
    """Strategy deployment configuration"""
    strategy_id: str
    deployment_id: str
    
    # Deployment settings
    tier: DeploymentTier
    initial_allocation: float  # Percentage of portfolio
    max_allocation: float      # Maximum allowed allocation
    symbols: List[str]         # Symbols to trade
    
    # Risk controls
    daily_loss_limit: float = 0.02    # 2% daily loss limit
    weekly_loss_limit: float = 0.05   # 5% weekly loss limit
    max_drawdown_limit: float = 0.15  # 15% max drawdown
    min_sharpe_threshold: float = 0.3 # Minimum Sharpe to continue
    
    # Performance thresholds
    retirement_threshold: float = -0.1  # Retire if return < -10%
    scaling_up_threshold: float = 0.1   # Scale up if return > 10%
    health_check_interval: int = 300    # Health check every 5 minutes
    
    # Metadata
    deployment_timestamp: datetime = field(default_factory=datetime.now)
    deployed_by: str = "system"
    notes: str = ""

@dataclass
class ABTestConfig:
    """A/B test configuration"""
    test_id: str
    test_name: str
    
    # Test strategies
    control_strategy: str      # Existing strategy (A)
    test_strategy: str         # New strategy (B)
    
    # Test parameters
    allocation_split: float = 0.5  # 50-50 split
    min_test_duration_days: int = 7
    max_test_duration_days: int = 30
    min_trades_per_strategy: int = 20
    significance_level: float = 0.05
    
    # Success criteria
    primary_metric: str = "sharpe_ratio"  # Primary metric to test
    secondary_metrics: List[str] = field(default_factory=lambda: ["total_return", "max_drawdown"])
    minimum_improvement: float = 0.1  # Minimum 10% improvement needed
    
    # Test metadata
    start_timestamp: datetime = field(default_factory=datetime.now)
    expected_end_timestamp: Optional[datetime] = None
    status: ABTestStatus = ABTestStatus.DESIGNING
    description: str = ""

@dataclass
class StrategyHealthMetrics:
    """Strategy health monitoring metrics"""
    strategy_id: str
    deployment_id: str
    
    # Performance metrics
    current_pnl: float
    daily_pnl: float
    weekly_pnl: float
    mtd_pnl: float
    ytd_pnl: float
    
    # Risk metrics
    current_drawdown: float
    max_drawdown_7d: float
    volatility_7d: float
    sharpe_7d: float
    
    # Trade statistics
    trades_today: int
    win_rate_7d: float
    avg_trade_pnl: float
    largest_loss_today: float
    
    # Health indicators
    health_status: HealthStatus
    last_trade_timestamp: Optional[datetime]
    consecutive_losses: int
    time_since_profit: float  # Hours since last profit
    
    # System metrics
    last_updated: datetime = field(default_factory=datetime.now)
    data_freshness: float = 1.0  # 1.0 = fresh, 0.0 = stale

@dataclass
class ABTestResult:
    """A/B test result analysis"""
    test_id: str
    
    # Test summary
    duration_days: float
    control_trades: int
    test_trades: int
    
    # Performance comparison
    control_metrics: Dict[str, float]
    test_metrics: Dict[str, float]
    
    # Statistical analysis
    statistical_results: Dict[str, Dict[str, Any]]  # metric -> test results
    overall_significance: bool
    confidence_level: float
    
    # Business impact
    expected_improvement: float
    risk_assessment: str
    recommendation: str
    
    # Meta information
    analysis_timestamp: datetime = field(default_factory=datetime.now)

class StrategyDeploymentManager:
    """
    🎯 Core Strategy Deployment Management System
    """
    
    def __init__(self, max_concurrent_deployments: int = 10):
        self.max_concurrent_deployments = max_concurrent_deployments
        
        # Active deployments
        self.active_deployments: Dict[str, DeploymentConfig] = {}
        self.deployment_health: Dict[str, StrategyHealthMetrics] = {}
        self.deployment_history: List[Dict[str, Any]] = []
        
        # Strategy instances and performance tracking
        self.strategy_instances: Dict[str, StrategyDNA] = {}
        self.performance_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Risk controls
        self.circuit_breakers: Dict[str, bool] = {}
        self.daily_pnl_by_strategy: Dict[str, float] = defaultdict(float)
        self.portfolio_exposure: float = 0.0
        
        # Health monitoring
        self.health_monitor_active = False
        self.health_monitor_thread: Optional[threading.Thread] = None
        
        logger.info("🎯 Strategy Deployment Manager initialized")
    
    async def deploy_strategy(self, strategy_id: str, 
                            config: Optional[DeploymentConfig] = None,
                            tier: DeploymentTier = DeploymentTier.PAPER) -> str:
        """Deploy strategy to live trading"""
        
        try:
            # Check deployment limits
            if len(self.active_deployments) >= self.max_concurrent_deployments:
                raise ValueError(f"Maximum concurrent deployments ({self.max_concurrent_deployments}) reached")
            
            # Generate deployment ID
            deployment_id = f"deploy_{strategy_id}_{int(time.time())}"
            
            # Create default config if not provided
            if config is None:
                config = DeploymentConfig(
                    strategy_id=strategy_id,
                    deployment_id=deployment_id,
                    tier=tier,
                    initial_allocation=self._get_tier_allocation(tier),
                    max_allocation=self._get_tier_allocation(tier) * 2,
                    symbols=settings.symbols[:5]  # Default to top 5 symbols
                )
            
            # Validate deployment
            validation_result = await self._validate_deployment(strategy_id, config)
            if not validation_result["valid"]:
                raise ValueError(f"Deployment validation failed: {validation_result['reason']}")
            
            # Load strategy
            strategy_dna = await self._load_strategy(strategy_id)
            if not strategy_dna:
                raise ValueError(f"Could not load strategy {strategy_id}")
            
            # Initialize deployment
            await self._initialize_deployment(deployment_id, config, strategy_dna)
            
            # Start health monitoring if not already running
            if not self.health_monitor_active:
                await self._start_health_monitoring()
            
            # Record deployment event
            self._record_deployment_event(deployment_id, "deployed", {
                "strategy_id": strategy_id,
                "tier": tier.value,
                "allocation": config.initial_allocation
            })
            
            logger.info(f"🚀 Strategy {strategy_id} deployed successfully (ID: {deployment_id}, Tier: {tier.value})")
            
            return deployment_id
            
        except Exception as e:
            logger.error(f"❌ Strategy deployment failed: {e}")
            raise
    
    def _get_tier_allocation(self, tier: DeploymentTier) -> float:
        """Get allocation percentage for deployment tier"""
        
        tier_allocations = {
            DeploymentTier.PAPER: 0.0,
            DeploymentTier.MICRO: 0.005,  # 0.5%
            DeploymentTier.SMALL: 0.02,   # 2%
            DeploymentTier.MEDIUM: 0.08,  # 8%
            DeploymentTier.LARGE: 0.20,   # 20%
            DeploymentTier.CORE: 0.35     # 35%
        }
        
        return tier_allocations.get(tier, 0.02)
    
    async def _validate_deployment(self, strategy_id: str, config: DeploymentConfig) -> Dict[str, Any]:
        """Validate deployment configuration"""
        
        # Basic validations
        if config.initial_allocation <= 0:
            return {"valid": False, "reason": "Invalid allocation"}
        
        if config.initial_allocation > 0.5:  # Max 50% allocation
            return {"valid": False, "reason": "Allocation too large"}
        
        # Check portfolio exposure
        total_new_exposure = self.portfolio_exposure + config.initial_allocation
        if total_new_exposure > 0.95:  # Max 95% total exposure
            return {"valid": False, "reason": "Portfolio exposure limit exceeded"}
        
        # Check if strategy exists and is validated
        # This would integrate with the Strategy Library
        
        return {"valid": True, "reason": "Deployment validated"}
    
    async def _load_strategy(self, strategy_id: str) -> Optional[StrategyDNA]:
        """Load strategy from library"""
        
        try:
            # This would integrate with InstitutionalStrategyLibrary
            # For now, create a mock strategy
            
            strategy_dna = StrategyDNA(
                strategy_id=strategy_id,
                name=f"Strategy_{strategy_id}",
                strategy_type=StrategyType.HYBRID_AI,
                indicators={"moving_averages": {"fast_period": 12, "slow_period": 26}},
                entry_conditions=[{"indicator": "ma_cross", "operator": ">", "threshold": 0.02}],
                exit_conditions=[{"type": "profit_target", "parameter": 0.03}],
                position_sizing={"method": "fixed", "base_size": 0.02},
                stop_loss_config={"type": "fixed", "threshold": 0.015},
                take_profit_config={"type": "fixed", "threshold": 0.025},
                regime_sensitivity={MarketRegime.BULL_TRENDING: 0.8}
            )
            
            return strategy_dna
            
        except Exception as e:
            logger.error(f"❌ Failed to load strategy {strategy_id}: {e}")
            return None
    
    async def _initialize_deployment(self, deployment_id: str, config: DeploymentConfig, 
                                   strategy_dna: StrategyDNA):
        """Initialize deployment structures"""
        
        # Store deployment config
        self.active_deployments[deployment_id] = config
        
        # Store strategy instance
        self.strategy_instances[deployment_id] = strategy_dna
        
        # Initialize health metrics
        self.deployment_health[deployment_id] = StrategyHealthMetrics(
            strategy_id=config.strategy_id,
            deployment_id=deployment_id,
            current_pnl=0.0,
            daily_pnl=0.0,
            weekly_pnl=0.0,
            mtd_pnl=0.0,
            ytd_pnl=0.0,
            current_drawdown=0.0,
            max_drawdown_7d=0.0,
            volatility_7d=0.0,
            sharpe_7d=0.0,
            trades_today=0,
            win_rate_7d=0.5,
            avg_trade_pnl=0.0,
            largest_loss_today=0.0,
            health_status=HealthStatus.HEALTHY,
            last_trade_timestamp=None,
            consecutive_losses=0,
            time_since_profit=0.0
        )
        
        # Initialize circuit breaker
        self.circuit_breakers[deployment_id] = False
        
        # Update portfolio exposure
        self.portfolio_exposure += config.initial_allocation
        
        logger.info(f"✅ Deployment {deployment_id} initialized")
    
    async def retire_strategy(self, deployment_id: str, reason: str = "performance"):
        """Retire strategy from live trading"""
        
        try:
            if deployment_id not in self.active_deployments:
                raise ValueError(f"Deployment {deployment_id} not found")
            
            config = self.active_deployments[deployment_id]
            
            # Update status
            config.tier = DeploymentTier.PAPER  # Move to paper trading
            
            # Reduce portfolio exposure
            self.portfolio_exposure -= config.initial_allocation
            self.portfolio_exposure = max(0.0, self.portfolio_exposure)
            
            # Update health status
            if deployment_id in self.deployment_health:
                self.deployment_health[deployment_id].health_status = HealthStatus.EMERGENCY
            
            # Record retirement
            self._record_deployment_event(deployment_id, "retired", {"reason": reason})
            
            # Clean up resources
            await self._cleanup_deployment(deployment_id)
            
            logger.info(f"🏁 Strategy {config.strategy_id} retired (reason: {reason})")
            
        except Exception as e:
            logger.error(f"❌ Strategy retirement failed: {e}")
            raise
    
    async def _cleanup_deployment(self, deployment_id: str):
        """Clean up deployment resources"""
        
        try:
            # Move to history
            if deployment_id in self.active_deployments:
                config = self.active_deployments[deployment_id]
                self.deployment_history.append({
                    "deployment_id": deployment_id,
                    "strategy_id": config.strategy_id,
                    "config": asdict(config),
                    "retirement_timestamp": datetime.now(),
                    "final_health": asdict(self.deployment_health.get(deployment_id)) if deployment_id in self.deployment_health else None
                })
            
            # Clean up active structures
            self.active_deployments.pop(deployment_id, None)
            self.deployment_health.pop(deployment_id, None)
            self.strategy_instances.pop(deployment_id, None)
            self.circuit_breakers.pop(deployment_id, None)
            
        except Exception as e:
            logger.error(f"❌ Deployment cleanup failed: {e}")
    
    def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get deployment status and health metrics"""
        
        if deployment_id not in self.active_deployments:
            return {"error": f"Deployment {deployment_id} not found"}
        
        config = self.active_deployments[deployment_id]
        health = self.deployment_health.get(deployment_id)
        strategy = self.strategy_instances.get(deployment_id)
        
        return {
            "deployment_id": deployment_id,
            "strategy_id": config.strategy_id,
            "strategy_name": strategy.name if strategy else "Unknown",
            "tier": config.tier.value,
            "status": DeploymentStatus.LIVE.value,
            "allocation": config.initial_allocation,
            "health_status": health.health_status.value if health else "unknown",
            "current_pnl": health.current_pnl if health else 0.0,
            "daily_pnl": health.daily_pnl if health else 0.0,
            "trades_today": health.trades_today if health else 0,
            "circuit_breaker": self.circuit_breakers.get(deployment_id, False),
            "deployment_time": config.deployment_timestamp,
            "symbols": config.symbols
        }
    
    def get_all_deployments_status(self) -> List[Dict[str, Any]]:
        """Get status of all active deployments"""
        
        statuses = []
        
        for deployment_id in self.active_deployments:
            status = self.get_deployment_status(deployment_id)
            statuses.append(status)
        
        return statuses
    
    async def _start_health_monitoring(self):
        """Start health monitoring thread"""
        
        if self.health_monitor_active:
            return
        
        self.health_monitor_active = True
        self.health_monitor_thread = threading.Thread(
            target=self._health_monitoring_loop,
            daemon=True
        )
        self.health_monitor_thread.start()
        
        logger.info("🏥 Health monitoring started")
    
    def _health_monitoring_loop(self):
        """Health monitoring loop"""
        
        while self.health_monitor_active:
            try:
                # Check health of all deployments
                for deployment_id in list(self.active_deployments.keys()):
                    asyncio.run(self._check_deployment_health(deployment_id))
                
                # Sleep for health check interval
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Health monitoring error: {e}")
                time.sleep(60)  # Wait longer on error
    
    async def _check_deployment_health(self, deployment_id: str):
        """Check health of specific deployment"""
        
        try:
            if deployment_id not in self.active_deployments:
                return
            
            config = self.active_deployments[deployment_id]
            health = self.deployment_health[deployment_id]
            
            # Update health metrics (simplified simulation)
            current_time = datetime.now()
            
            # Simulate some performance metrics
            health.daily_pnl += np.random.normal(0, 0.01)  # Random daily PnL
            health.current_pnl += health.daily_pnl
            
            # Update drawdown
            if health.current_pnl < 0:
                health.current_drawdown = abs(health.current_pnl)
                health.max_drawdown_7d = max(health.max_drawdown_7d, health.current_drawdown)
            else:
                health.current_drawdown = 0.0
            
            # Check health thresholds
            new_health_status = self._assess_health_status(config, health)
            
            if new_health_status != health.health_status:
                old_status = health.health_status
                health.health_status = new_health_status
                
                logger.warning(f"🚨 Health status changed for {deployment_id}: "
                             f"{old_status.value} -> {new_health_status.value}")
                
                # Take action based on health status
                await self._handle_health_status_change(deployment_id, new_health_status)
            
            # Update timestamp
            health.last_updated = current_time
            
        except Exception as e:
            logger.error(f"❌ Health check failed for {deployment_id}: {e}")
    
    def _assess_health_status(self, config: DeploymentConfig, 
                            health: StrategyHealthMetrics) -> HealthStatus:
        """Assess strategy health status"""
        
        # Emergency conditions
        if health.current_drawdown > config.max_drawdown_limit:
            return HealthStatus.EMERGENCY
        
        if health.daily_pnl < -config.daily_loss_limit:
            return HealthStatus.EMERGENCY
        
        # Critical conditions
        if health.consecutive_losses >= 5:
            return HealthStatus.CRITICAL
        
        if health.current_drawdown > config.max_drawdown_limit * 0.8:
            return HealthStatus.CRITICAL
        
        # Warning conditions
        if health.sharpe_7d < config.min_sharpe_threshold:
            return HealthStatus.WARNING
        
        if health.current_drawdown > config.max_drawdown_limit * 0.5:
            return HealthStatus.WARNING
        
        # Default to healthy
        return HealthStatus.HEALTHY
    
    async def _handle_health_status_change(self, deployment_id: str, new_status: HealthStatus):
        """Handle health status changes"""
        
        try:
            config = self.active_deployments[deployment_id]
            
            if new_status == HealthStatus.EMERGENCY:
                # Emergency shutdown
                self.circuit_breakers[deployment_id] = True
                await self.retire_strategy(deployment_id, "emergency_health_check")
                
            elif new_status == HealthStatus.CRITICAL:
                # Reduce allocation
                config.initial_allocation *= 0.5  # Cut allocation in half
                self.circuit_breakers[deployment_id] = True
                
                logger.warning(f"⚠️ Reduced allocation for {deployment_id} due to critical health")
                
            elif new_status == HealthStatus.WARNING:
                # Monitor more closely
                logger.info(f"👁️ Monitoring {deployment_id} more closely due to warning status")
        
        except Exception as e:
            logger.error(f"❌ Error handling health status change: {e}")
    
    def _record_deployment_event(self, deployment_id: str, event_type: str, 
                                details: Dict[str, Any]):
        """Record deployment event for audit trail"""
        
        event = {
            "deployment_id": deployment_id,
            "event_type": event_type,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store event (simplified)
        logger.info(f"📝 Deployment event: {event_type} for {deployment_id}")

class ABTestingFramework:
    """
    🧪 Advanced A/B Testing Framework for Strategy Comparison
    """
    
    def __init__(self, deployment_manager: StrategyDeploymentManager):
        self.deployment_manager = deployment_manager
        self.active_tests: Dict[str, ABTestConfig] = {}
        self.test_results: Dict[str, ABTestResult] = {}
        self.test_history: List[Dict[str, Any]] = []
        
        # Performance tracking for tests
        self.test_performance: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        
        logger.info("🧪 A/B Testing Framework initialized")
    
    async def create_ab_test(self, control_strategy_id: str, test_strategy_id: str,
                           test_config: Optional[ABTestConfig] = None) -> str:
        """Create and start A/B test"""
        
        try:
            # Generate test ID
            test_id = f"abtest_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            
            # Create default config if not provided
            if test_config is None:
                test_config = ABTestConfig(
                    test_id=test_id,
                    test_name=f"Test_{control_strategy_id}_vs_{test_strategy_id}",
                    control_strategy=control_strategy_id,
                    test_strategy=test_strategy_id
                )
            
            # Validate test configuration
            validation_result = await self._validate_ab_test(test_config)
            if not validation_result["valid"]:
                raise ValueError(f"A/B test validation failed: {validation_result['reason']}")
            
            # Deploy both strategies with split allocation
            control_allocation = self._calculate_test_allocation(test_config.allocation_split, "control")
            test_allocation = self._calculate_test_allocation(test_config.allocation_split, "test")
            
            # Deploy control strategy (if not already deployed)
            control_deployment_id = await self._ensure_strategy_deployed(
                control_strategy_id, control_allocation, "control"
            )
            
            # Deploy test strategy
            test_deployment_id = await self.deployment_manager.deploy_strategy(
                test_strategy_id,
                tier=DeploymentTier.SMALL  # Start with small allocation for test
            )
            
            # Configure test
            test_config.status = ABTestStatus.RUNNING
            test_config.expected_end_timestamp = (
                datetime.now() + timedelta(days=test_config.max_test_duration_days)
            )
            
            # Store test
            self.active_tests[test_id] = test_config
            
            # Initialize performance tracking
            self.test_performance[test_id] = {
                "control": [],
                "test": []
            }
            
            # Start monitoring
            await self._start_test_monitoring(test_id)
            
            logger.info(f"🧪 A/B test {test_id} started: {control_strategy_id} vs {test_strategy_id}")
            
            return test_id
            
        except Exception as e:
            logger.error(f"❌ A/B test creation failed: {e}")
            raise
    
    async def _validate_ab_test(self, test_config: ABTestConfig) -> Dict[str, Any]:
        """Validate A/B test configuration"""
        
        # Basic validations
        if test_config.control_strategy == test_config.test_strategy:
            return {"valid": False, "reason": "Control and test strategies cannot be the same"}
        
        if test_config.allocation_split <= 0 or test_config.allocation_split >= 1:
            return {"valid": False, "reason": "Invalid allocation split"}
        
        if test_config.min_test_duration_days <= 0:
            return {"valid": False, "reason": "Invalid test duration"}
        
        return {"valid": True, "reason": "Test configuration validated"}
    
    def _calculate_test_allocation(self, split: float, group: str) -> float:
        """Calculate allocation for test group"""
        
        base_allocation = 0.05  # 5% base allocation for A/B tests
        
        if group == "control":
            return base_allocation * split
        else:  # test
            return base_allocation * (1 - split)
    
    async def _ensure_strategy_deployed(self, strategy_id: str, allocation: float, 
                                      group: str) -> str:
        """Ensure strategy is deployed for testing"""
        
        # Check if strategy is already deployed
        for deployment_id, config in self.deployment_manager.active_deployments.items():
            if config.strategy_id == strategy_id:
                return deployment_id
        
        # Deploy strategy if not already deployed
        return await self.deployment_manager.deploy_strategy(
            strategy_id, tier=DeploymentTier.SMALL
        )
    
    async def _start_test_monitoring(self, test_id: str):
        """Start monitoring A/B test"""
        
        # This would be enhanced with real-time performance tracking
        # For now, we'll rely on the deployment manager's health monitoring
        logger.info(f"📊 Started monitoring A/B test {test_id}")
    
    async def analyze_ab_test(self, test_id: str, force_analysis: bool = False) -> ABTestResult:
        """Analyze A/B test results"""
        
        try:
            if test_id not in self.active_tests:
                raise ValueError(f"A/B test {test_id} not found")
            
            test_config = self.active_tests[test_id]
            
            # Check if test is ready for analysis
            if not force_analysis and not self._is_test_ready_for_analysis(test_config):
                raise ValueError("Test not ready for analysis")
            
            # Collect performance data
            control_data = self._collect_strategy_performance_data(test_config.control_strategy)
            test_data = self._collect_strategy_performance_data(test_config.test_strategy)
            
            # Perform statistical analysis
            statistical_results = await self._perform_statistical_analysis(
                control_data, test_data, test_config
            )
            
            # Calculate business impact
            business_impact = self._calculate_business_impact(control_data, test_data, test_config)
            
            # Generate recommendation
            recommendation = self._generate_test_recommendation(
                statistical_results, business_impact, test_config
            )
            
            # Create result
            result = ABTestResult(
                test_id=test_id,
                duration_days=(datetime.now() - test_config.start_timestamp).total_seconds() / 86400,
                control_trades=len(control_data.get("trades", [])),
                test_trades=len(test_data.get("trades", [])),
                control_metrics=control_data.get("metrics", {}),
                test_metrics=test_data.get("metrics", {}),
                statistical_results=statistical_results,
                overall_significance=statistical_results.get("overall_significant", False),
                confidence_level=1 - test_config.significance_level,
                expected_improvement=business_impact.get("expected_improvement", 0.0),
                risk_assessment=business_impact.get("risk_assessment", "Unknown"),
                recommendation=recommendation
            )
            
            # Store result
            self.test_results[test_id] = result
            
            # Update test status
            test_config.status = ABTestStatus.CONCLUDED
            
            logger.info(f"📊 A/B test {test_id} analysis complete: {recommendation}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ A/B test analysis failed: {e}")
            raise
    
    def _is_test_ready_for_analysis(self, test_config: ABTestConfig) -> bool:
        """Check if test is ready for analysis"""
        
        # Check minimum duration
        if (datetime.now() - test_config.start_timestamp).days < test_config.min_test_duration_days:
            return False
        
        # Check minimum trades
        control_trades = len(self._collect_strategy_performance_data(test_config.control_strategy).get("trades", []))
        test_trades = len(self._collect_strategy_performance_data(test_config.test_strategy).get("trades", []))
        
        if control_trades < test_config.min_trades_per_strategy or test_trades < test_config.min_trades_per_strategy:
            return False
        
        return True
    
    def _collect_strategy_performance_data(self, strategy_id: str) -> Dict[str, Any]:
        """Collect performance data for strategy"""
        
        # This would integrate with actual performance tracking
        # For now, simulate some data
        
        # Simulate trades
        num_trades = np.random.randint(20, 100)
        trades = []
        
        for i in range(num_trades):
            trade_pnl = np.random.normal(0.002, 0.01)  # 0.2% avg with 1% std
            trades.append({
                "timestamp": datetime.now() - timedelta(hours=i),
                "pnl": trade_pnl,
                "symbol": np.random.choice(["BTC/USD", "ETH/USD", "SPY"])
            })
        
        # Calculate metrics
        trade_pnls = [t["pnl"] for t in trades]
        total_return = sum(trade_pnls)
        volatility = np.std(trade_pnls) * np.sqrt(252) if trade_pnls else 0
        sharpe_ratio = (np.mean(trade_pnls) * 252) / volatility if volatility > 0 else 0
        win_rate = len([p for p in trade_pnls if p > 0]) / len(trade_pnls) if trade_pnls else 0
        max_drawdown = self._calculate_max_drawdown(trade_pnls)
        
        metrics = {
            "total_return": total_return,
            "sharpe_ratio": sharpe_ratio,
            "volatility": volatility,
            "win_rate": win_rate,
            "max_drawdown": max_drawdown,
            "total_trades": len(trades)
        }
        
        return {
            "trades": trades,
            "metrics": metrics
        }
    
    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """Calculate maximum drawdown from returns"""
        
        if not returns:
            return 0.0
        
        cumulative = np.cumprod([1 + r for r in returns])
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        
        return abs(np.min(drawdown))
    
    async def _perform_statistical_analysis(self, control_data: Dict[str, Any], 
                                          test_data: Dict[str, Any],
                                          test_config: ABTestConfig) -> Dict[str, Dict[str, Any]]:
        """Perform statistical analysis on A/B test data"""
        
        try:
            results = {}
            
            control_metrics = control_data["metrics"]
            test_metrics = test_data["metrics"]
            
            # Primary metric analysis
            primary_metric = test_config.primary_metric
            
            if primary_metric in control_metrics and primary_metric in test_metrics:
                control_values = [t["pnl"] for t in control_data["trades"]]
                test_values = [t["pnl"] for t in test_data["trades"]]
                
                # T-test for means
                t_stat, p_value = ttest_ind(test_values, control_values)
                
                # Mann-Whitney U test (non-parametric)
                u_stat, u_p_value = mannwhitneyu(test_values, control_values, alternative='two-sided')
                
                results[primary_metric] = {
                    "control_mean": control_metrics[primary_metric],
                    "test_mean": test_metrics[primary_metric],
                    "improvement": (test_metrics[primary_metric] - control_metrics[primary_metric]) / abs(control_metrics[primary_metric]) if control_metrics[primary_metric] != 0 else 0,
                    "t_test": {"statistic": t_stat, "p_value": p_value},
                    "mann_whitney": {"statistic": u_stat, "p_value": u_p_value},
                    "significant": p_value < test_config.significance_level,
                    "effect_size": self._calculate_cohens_d(test_values, control_values)
                }
            
            # Secondary metrics analysis
            for metric in test_config.secondary_metrics:
                if metric in control_metrics and metric in test_metrics:
                    results[metric] = {
                        "control_value": control_metrics[metric],
                        "test_value": test_metrics[metric],
                        "improvement": (test_metrics[metric] - control_metrics[metric]) / abs(control_metrics[metric]) if control_metrics[metric] != 0 else 0
                    }
            
            # Overall significance
            primary_significant = results.get(primary_metric, {}).get("significant", False)
            results["overall_significant"] = primary_significant
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Statistical analysis failed: {e}")
            return {}
    
    def _calculate_cohens_d(self, group1: List[float], group2: List[float]) -> float:
        """Calculate Cohen's d effect size"""
        
        if not group1 or not group2:
            return 0.0
        
        n1, n2 = len(group1), len(group2)
        
        # Calculate means
        mean1, mean2 = np.mean(group1), np.mean(group2)
        
        # Calculate pooled standard deviation
        s1, s2 = np.std(group1, ddof=1), np.std(group2, ddof=1)
        pooled_std = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
        
        # Cohen's d
        d = (mean2 - mean1) / pooled_std if pooled_std > 0 else 0
        
        return d
    
    def _calculate_business_impact(self, control_data: Dict[str, Any], 
                                 test_data: Dict[str, Any],
                                 test_config: ABTestConfig) -> Dict[str, Any]:
        """Calculate business impact of test results"""
        
        control_metrics = control_data["metrics"]
        test_metrics = test_data["metrics"]
        
        # Expected improvement in primary metric
        primary_metric = test_config.primary_metric
        expected_improvement = 0.0
        
        if primary_metric in control_metrics and primary_metric in test_metrics:
            if control_metrics[primary_metric] != 0:
                expected_improvement = (test_metrics[primary_metric] - control_metrics[primary_metric]) / abs(control_metrics[primary_metric])
        
        # Risk assessment
        risk_factors = []
        
        if test_metrics.get("max_drawdown", 0) > control_metrics.get("max_drawdown", 0) * 1.2:
            risk_factors.append("Higher drawdown risk")
        
        if test_metrics.get("volatility", 0) > control_metrics.get("volatility", 0) * 1.3:
            risk_factors.append("Higher volatility")
        
        if len(test_data.get("trades", [])) < len(control_data.get("trades", [])) * 0.7:
            risk_factors.append("Lower trade frequency")
        
        risk_assessment = "Low" if not risk_factors else "Medium" if len(risk_factors) <= 2 else "High"
        
        return {
            "expected_improvement": expected_improvement,
            "risk_assessment": risk_assessment,
            "risk_factors": risk_factors,
            "confidence": 1.0 - test_config.significance_level
        }
    
    def _generate_test_recommendation(self, statistical_results: Dict[str, Dict[str, Any]],
                                    business_impact: Dict[str, Any],
                                    test_config: ABTestConfig) -> str:
        """Generate recommendation based on test results"""
        
        primary_metric = test_config.primary_metric
        improvement = business_impact.get("expected_improvement", 0.0)
        risk = business_impact.get("risk_assessment", "Unknown")
        significant = statistical_results.get("overall_significant", False)
        
        # Decision logic
        if significant and improvement >= test_config.minimum_improvement and risk == "Low":
            return "ADOPT_TEST_STRATEGY - Test strategy shows significant improvement with acceptable risk"
        
        elif significant and improvement >= test_config.minimum_improvement and risk == "Medium":
            return "CONDITIONAL_ADOPT - Test strategy shows improvement but with elevated risk. Consider gradual rollout"
        
        elif significant and improvement >= test_config.minimum_improvement and risk == "High":
            return "REJECT_HIGH_RISK - Test strategy shows improvement but risk is too high"
        
        elif significant and improvement < test_config.minimum_improvement:
            return "REJECT_INSUFFICIENT_IMPROVEMENT - Improvement is statistically significant but below business threshold"
        
        elif not significant and improvement >= test_config.minimum_improvement:
            return "EXTEND_TEST - Improvement looks promising but not statistically significant. Extend test duration"
        
        else:
            return "REJECT_NO_IMPROVEMENT - Test strategy does not show meaningful improvement"
    
    def get_test_status(self, test_id: str) -> Dict[str, Any]:
        """Get current status of A/B test"""
        
        if test_id not in self.active_tests:
            return {"error": f"Test {test_id} not found"}
        
        test_config = self.active_tests[test_id]
        
        # Get current performance
        control_data = self._collect_strategy_performance_data(test_config.control_strategy)
        test_data = self._collect_strategy_performance_data(test_config.test_strategy)
        
        return {
            "test_id": test_id,
            "test_name": test_config.test_name,
            "status": test_config.status.value,
            "start_date": test_config.start_timestamp,
            "expected_end_date": test_config.expected_end_timestamp,
            "days_running": (datetime.now() - test_config.start_timestamp).days,
            "control_strategy": test_config.control_strategy,
            "test_strategy": test_config.test_strategy,
            "control_performance": control_data["metrics"],
            "test_performance": test_data["metrics"],
            "ready_for_analysis": self._is_test_ready_for_analysis(test_config)
        }
    
    async def stop_ab_test(self, test_id: str, reason: str = "manual_stop") -> bool:
        """Stop A/B test"""
        
        try:
            if test_id not in self.active_tests:
                raise ValueError(f"Test {test_id} not found")
            
            test_config = self.active_tests[test_id]
            test_config.status = ABTestStatus.CANCELLED
            
            # Move to history
            self.test_history.append({
                "test_id": test_id,
                "config": asdict(test_config),
                "stop_reason": reason,
                "stop_timestamp": datetime.now()
            })
            
            # Clean up
            del self.active_tests[test_id]
            
            logger.info(f"⏹️ A/B test {test_id} stopped: {reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to stop A/B test: {e}")
            return False

class StrategyDeploymentEngine:
    """
    🚀 MAIN STRATEGY DEPLOYMENT ENGINE
    Orchestrates the entire deployment pipeline with A/B testing and monitoring
    """
    
    def __init__(self):
        self.deployment_manager = StrategyDeploymentManager()
        self.ab_testing_framework = ABTestingFramework(self.deployment_manager)
        
        # Integration with other systems
        self.ai_strategy_generator: Optional['AIStrategyGenerator'] = None
        self.institutional_library: Optional['InstitutionalStrategyLibrary'] = None
        
        # System state
        self.system_active = False
        self.deployment_history = []
        
        logger.info("🚀 Strategy Deployment Engine initialized")
    
    async def initialize(self):
        """Initialize deployment engine with integrations"""
        
        try:
            # Initialize integrations
            from .ai_strategy_generator import get_ai_strategy_generator
            from .institutional_strategy_library import get_institutional_library
            
            self.ai_strategy_generator = await get_ai_strategy_generator()
            self.institutional_library = get_institutional_library()
            
            self.system_active = True
            logger.info("✅ Deployment engine fully initialized")
            
        except Exception as e:
            logger.error(f"❌ Deployment engine initialization failed: {e}")
            raise
    
    async def deploy_strategy_with_validation(self, strategy_id: str, 
                                            tier: DeploymentTier = DeploymentTier.PAPER,
                                            require_validation: bool = True) -> str:
        """Deploy strategy with validation requirements"""
        
        try:
            if require_validation:
                # Check if strategy is validated
                if self.institutional_library:
                    # This would check validation status from library
                    pass
                else:
                    logger.warning("⚠️ Institutional library not available for validation check")
            
            # Deploy strategy
            deployment_id = await self.deployment_manager.deploy_strategy(strategy_id, tier=tier)
            
            # Record in library if available
            if self.institutional_library:
                # This would update deployment status in library
                pass
            
            return deployment_id
            
        except Exception as e:
            logger.error(f"❌ Validated deployment failed: {e}")
            raise
    
    async def run_strategy_competition(self, strategy_ids: List[str], 
                                     duration_days: int = 14) -> Dict[str, Any]:
        """Run competition between multiple strategies"""
        
        try:
            if len(strategy_ids) < 2:
                raise ValueError("At least 2 strategies required for competition")
            
            logger.info(f"🏆 Starting strategy competition with {len(strategy_ids)} strategies")
            
            # Deploy all strategies with equal allocation
            base_allocation = 0.20 / len(strategy_ids)  # Split 20% among all strategies
            
            deployment_ids = []
            for strategy_id in strategy_ids:
                deployment_id = await self.deployment_manager.deploy_strategy(
                    strategy_id, tier=DeploymentTier.SMALL
                )
                deployment_ids.append(deployment_id)
            
            # Monitor competition
            start_time = datetime.now()
            competition_id = f"competition_{int(time.time())}"
            
            competition_data = {
                "competition_id": competition_id,
                "strategy_ids": strategy_ids,
                "deployment_ids": deployment_ids,
                "start_time": start_time,
                "duration_days": duration_days,
                "status": "running"
            }
            
            logger.info(f"🏁 Competition {competition_id} started, duration: {duration_days} days")
            
            return competition_data
            
        except Exception as e:
            logger.error(f"❌ Strategy competition failed: {e}")
            raise
    
    async def auto_deploy_best_strategies(self, min_sharpe: float = 1.0, 
                                        max_strategies: int = 5) -> List[str]:
        """Automatically deploy best performing strategies"""
        
        try:
            if not self.institutional_library:
                raise ValueError("Institutional library required for auto-deployment")
            
            # Get top performing strategies
            top_strategies = self.institutional_library.get_top_performers(
                limit=max_strategies * 2  # Get extra to filter
            )
            
            deployed_strategies = []
            
            for strategy_info in top_strategies[:max_strategies]:
                strategy_id = strategy_info["strategy_id"]
                latest_perf = strategy_info.get("latest_performance", {})
                
                if latest_perf.get("sharpe_ratio", 0) >= min_sharpe:
                    try:
                        deployment_id = await self.deploy_strategy_with_validation(
                            strategy_id, DeploymentTier.SMALL
                        )
                        deployed_strategies.append(deployment_id)
                        
                        logger.info(f"🚀 Auto-deployed {strategy_id} (Sharpe: {latest_perf.get('sharpe_ratio', 0):.2f})")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to auto-deploy {strategy_id}: {e}")
            
            logger.info(f"✅ Auto-deployment complete: {len(deployed_strategies)} strategies deployed")
            
            return deployed_strategies
            
        except Exception as e:
            logger.error(f"❌ Auto-deployment failed: {e}")
            raise
    
    def get_deployment_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive deployment dashboard"""
        
        try:
            # Get all deployment statuses
            all_deployments = self.deployment_manager.get_all_deployments_status()
            
            # Get A/B test statuses
            ab_tests = []
            for test_id in self.ab_testing_framework.active_tests:
                test_status = self.ab_testing_framework.get_test_status(test_id)
                ab_tests.append(test_status)
            
            # Calculate summary statistics
            total_deployments = len(all_deployments)
            active_deployments = len([d for d in all_deployments if d.get("health_status") != "emergency"])
            total_allocation = sum([d.get("allocation", 0) for d in all_deployments])
            
            # Health distribution
            health_distribution = defaultdict(int)
            for deployment in all_deployments:
                health_distribution[deployment.get("health_status", "unknown")] += 1
            
            # Performance summary
            total_pnl = sum([d.get("current_pnl", 0) for d in all_deployments])
            daily_pnl = sum([d.get("daily_pnl", 0) for d in all_deployments])
            
            return {
                "summary": {
                    "total_deployments": total_deployments,
                    "active_deployments": active_deployments,
                    "total_allocation": total_allocation,
                    "system_active": self.system_active
                },
                "performance": {
                    "total_pnl": total_pnl,
                    "daily_pnl": daily_pnl,
                    "portfolio_exposure": self.deployment_manager.portfolio_exposure
                },
                "health_distribution": dict(health_distribution),
                "deployments": all_deployments,
                "ab_tests": {
                    "active_tests": len(ab_tests),
                    "tests": ab_tests
                },
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate deployment dashboard: {e}")
            return {"error": str(e)}
    
    async def emergency_shutdown_all(self, reason: str = "emergency") -> bool:
        """Emergency shutdown of all deployments"""
        
        try:
            logger.warning(f"🚨 EMERGENCY SHUTDOWN: {reason}")
            
            # Retire all active deployments
            deployment_ids = list(self.deployment_manager.active_deployments.keys())
            
            for deployment_id in deployment_ids:
                try:
                    await self.deployment_manager.retire_strategy(deployment_id, f"emergency_{reason}")
                except Exception as e:
                    logger.error(f"❌ Failed to retire {deployment_id}: {e}")
            
            # Stop all A/B tests
            test_ids = list(self.ab_testing_framework.active_tests.keys())
            
            for test_id in test_ids:
                try:
                    await self.ab_testing_framework.stop_ab_test(test_id, f"emergency_{reason}")
                except Exception as e:
                    logger.error(f"❌ Failed to stop test {test_id}: {e}")
            
            self.system_active = False
            
            logger.warning(f"🛑 Emergency shutdown complete: {len(deployment_ids)} deployments, {len(test_ids)} tests stopped")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Emergency shutdown failed: {e}")
            return False

# Global deployment engine instance
_deployment_engine: Optional[StrategyDeploymentEngine] = None

async def get_deployment_engine() -> StrategyDeploymentEngine:
    """Get global deployment engine instance"""
    global _deployment_engine
    
    if _deployment_engine is None:
        _deployment_engine = StrategyDeploymentEngine()
        await _deployment_engine.initialize()
    
    return _deployment_engine

# Integration functions for main trading system

async def deploy_ai_generated_strategy(strategy_dna: StrategyDNA, 
                                     validation_result: Optional[ValidationResult] = None,
                                     tier: DeploymentTier = DeploymentTier.PAPER) -> str:
    """Deploy AI-generated strategy to live trading"""
    
    engine = await get_deployment_engine()
    
    # Add to library first
    if engine.institutional_library:
        library_strategy_id = engine.institutional_library.add_strategy(strategy_dna)
        
        # Record validation if available
        if validation_result:
            # This would record validation results
            pass
    
    # Deploy to live trading
    return await engine.deploy_strategy_with_validation(strategy_dna.strategy_id, tier)

async def create_strategy_ab_test(existing_strategy_id: str, 
                                new_strategy_dna: StrategyDNA,
                                test_duration_days: int = 14) -> str:
    """Create A/B test between existing and new strategy"""
    
    engine = await get_deployment_engine()
    
    # Add new strategy to library
    if engine.institutional_library:
        engine.institutional_library.add_strategy(new_strategy_dna)
    
    # Create A/B test
    test_config = ABTestConfig(
        test_id=f"test_{int(time.time())}",
        test_name=f"Test_{existing_strategy_id}_vs_{new_strategy_dna.strategy_id}",
        control_strategy=existing_strategy_id,
        test_strategy=new_strategy_dna.strategy_id,
        max_test_duration_days=test_duration_days
    )
    
    return await engine.ab_testing_framework.create_ab_test(
        existing_strategy_id, new_strategy_dna.strategy_id, test_config
    )

def get_deployment_status_for_trading_bot() -> Dict[str, Any]:
    """Get deployment status for integration with trading bot"""
    
    try:
        if _deployment_engine:
            dashboard = _deployment_engine.get_deployment_dashboard()
            
            # Extract relevant information for trading bot
            return {
                "active_strategies": len(dashboard.get("deployments", [])),
                "total_allocation": dashboard.get("summary", {}).get("total_allocation", 0),
                "system_health": "healthy" if dashboard.get("summary", {}).get("system_active", False) else "inactive",
                "emergency_shutdown": not dashboard.get("summary", {}).get("system_active", False),
                "performance": dashboard.get("performance", {}),
                "last_update": datetime.now()
            }
        else:
            return {"status": "engine_not_initialized"}
            
    except Exception as e:
        logger.error(f"❌ Error getting deployment status: {e}")
        return {"status": "error", "message": str(e)}

# Signal handlers for graceful shutdown
def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    
    def signal_handler(signum, frame):
        logger.warning(f"🛑 Received signal {signum}, initiating graceful shutdown...")
        
        if _deployment_engine:
            asyncio.create_task(_deployment_engine.emergency_shutdown_all("signal_shutdown"))
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    # Example usage and testing
    async def test_deployment_engine():
        """Test the deployment engine"""
        
        # Initialize engine
        engine = await get_deployment_engine()
        
        # Test basic deployment
        try:
            deployment_id = await engine.deploy_strategy_with_validation(
                "test_strategy_001", DeploymentTier.PAPER
            )
            print(f"Deployed strategy: {deployment_id}")
            
            # Get dashboard
            dashboard = engine.get_deployment_dashboard()
            print(f"Dashboard: {dashboard['summary']}")
            
            # Test A/B testing
            test_id = await engine.ab_testing_framework.create_ab_test(
                "control_strategy", "test_strategy"
            )
            print(f"Created A/B test: {test_id}")
            
        except Exception as e:
            print(f"Test error: {e}")
        
        return engine
    
    # Setup signal handlers
    setup_signal_handlers()
    
    # Run test
    asyncio.run(test_deployment_engine())