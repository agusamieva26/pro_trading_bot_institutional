#!/usr/bin/env python3
"""
🧠 AI STRATEGY GENERATOR + RAG INTEGRATION - INSTITUTIONAL GRADE
Advanced integration between AI Strategy Generator and Memory RAG system for intelligent strategy development
- Strategy Knowledge Base with Vector Embeddings
- Continuous Learning from Strategy Performance
- Intelligent Strategy Pattern Recognition
- RAG-Enhanced Strategy Generation
- Historical Strategy Performance Analysis
- Market Pattern Learning System
"""
import os
import json
import asyncio
import time
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
import numpy as np
import pandas as pd
from loguru import logger
import warnings
warnings.filterwarnings("ignore")

from .config import settings
from .util import logger

try:
    from .advanced_memory_rag_system import (
        AdvancedMemoryRAGSystem, KnowledgeEntry, KnowledgeType, 
        QueryType, EmbeddingModel, RetrievalResult
    )
    from .ai_strategy_generator import (
        StrategyDNA, StrategyPerformance, StrategyType, MarketRegime,
        StrategyObjective, AIStrategyGenerator
    )
    from .strategy_validation_engine import ValidationResult, ValidationLevel
    from .institutional_strategy_library import InstitutionalStrategyLibrary
    from .market_regime_analyzer import RegimeAnalysis, AdvancedRegimeDetector
except ImportError as e:
    logger.warning(f"Some RAG integration dependencies not available: {e}")

class StrategyKnowledgeType(Enum):
    """Extended knowledge types for strategy generation"""
    STRATEGY_PATTERN = "strategy_pattern"           # Successful strategy patterns
    FAILURE_PATTERN = "failure_pattern"             # Failed strategy patterns
    MARKET_INSIGHT = "market_insight"              # Market behavior insights
    REGIME_ADAPTATION = "regime_adaptation"        # Regime-specific adaptations
    PERFORMANCE_LESSON = "performance_lesson"      # Performance lessons learned
    OPTIMIZATION_INSIGHT = "optimization_insight"  # Parameter optimization insights
    RISK_LESSON = "risk_lesson"                    # Risk management lessons
    STRATEGY_EVOLUTION = "strategy_evolution"      # How strategies evolved
    CORRELATION_PATTERN = "correlation_pattern"    # Cross-strategy correlations

@dataclass
class StrategyKnowledgeEntry:
    """Specialized knowledge entry for strategy information"""
    id: str
    strategy_id: str
    strategy_name: str
    content: str
    knowledge_type: StrategyKnowledgeType
    
    # Strategy-specific metadata
    strategy_type: StrategyType
    market_regime: MarketRegime
    performance_metrics: Dict[str, float]
    symbols_traded: List[str]
    timeframe: str
    
    # Learning context
    success_factors: List[str] = field(default_factory=list)
    failure_factors: List[str] = field(default_factory=list)
    key_insights: List[str] = field(default_factory=list)
    confidence_score: float = 0.5
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "ai_generator"
    validation_status: str = "pending"

@dataclass
class StrategyLearningOutcome:
    """Learning outcome from strategy performance"""
    strategy_id: str
    outcome_type: str  # success, failure, mixed
    key_lesson: str
    supporting_evidence: Dict[str, Any]
    applicable_conditions: Dict[str, Any]
    confidence: float
    impact_score: float  # How important this learning is

class StrategyRAGEnhancedGenerator:
    """
    🤖 RAG-Enhanced Strategy Generation System
    """
    
    def __init__(self, rag_system: AdvancedMemoryRAGSystem):
        self.rag_system = rag_system
        self.strategy_patterns = defaultdict(list)
        self.learning_cache = {}
        self.generation_history = deque(maxlen=1000)
        
        # Strategy knowledge categories
        self.knowledge_categories = {
            "successful_patterns": [],
            "failure_patterns": [],
            "market_insights": [],
            "optimization_lessons": [],
            "risk_lessons": []
        }
        
        # Pattern recognition thresholds
        self.pattern_confidence_threshold = 0.7
        self.minimum_pattern_occurrences = 3
        
        logger.info("🤖 RAG-Enhanced Strategy Generator initialized")
    
    async def generate_strategy_with_rag(self, 
                                       objectives: List[StrategyObjective],
                                       market_regime: MarketRegime,
                                       symbols: List[str] = None,
                                       use_historical_insights: bool = True) -> StrategyDNA:
        """Generate strategy enhanced with RAG knowledge"""
        
        try:
            # Query RAG for relevant insights
            insights = await self._query_strategy_insights(objectives, market_regime, symbols)
            
            # Extract actionable patterns from RAG
            patterns = await self._extract_actionable_patterns(insights, market_regime)
            
            # Generate base strategy with RAG enhancement
            enhanced_strategy = await self._generate_rag_enhanced_strategy(
                objectives, market_regime, patterns, symbols
            )
            
            # Apply learned optimizations
            if use_historical_insights:
                enhanced_strategy = await self._apply_historical_optimizations(
                    enhanced_strategy, insights
                )
            
            # Record generation event
            await self._record_strategy_generation_event(enhanced_strategy, insights, patterns)
            
            logger.info(f"🧠 Generated RAG-enhanced strategy: {enhanced_strategy.name}")
            
            return enhanced_strategy
            
        except Exception as e:
            logger.error(f"❌ RAG-enhanced strategy generation failed: {e}")
            raise
    
    async def _query_strategy_insights(self, 
                                     objectives: List[StrategyObjective],
                                     market_regime: MarketRegime,
                                     symbols: List[str] = None) -> RetrievalResult:
        """Query RAG system for relevant strategy insights"""
        
        try:
            # Build context-aware query
            query_parts = []
            
            # Add objectives context
            if objectives:
                obj_text = ", ".join([obj.value for obj in objectives])
                query_parts.append(f"strategies optimized for {obj_text}")
            
            # Add regime context
            query_parts.append(f"effective in {market_regime.value} markets")
            
            # Add symbols context
            if symbols:
                symbol_text = ", ".join(symbols[:3])  # Limit to avoid too long queries
                query_parts.append(f"trading {symbol_text}")
            
            # Construct query
            query = f"Successful trading strategies: {' and '.join(query_parts)}. " \
                   f"What patterns, parameters, and approaches work best?"
            
            # Query RAG system
            insights = await self.rag_system.query_trading_intelligence(
                query=query,
                query_type=QueryType.TRADING_STRATEGY,
                max_results=10,
                knowledge_types=[
                    KnowledgeType.TRADING_STRATEGY,
                    KnowledgeType.SUCCESS_PATTERN,
                    KnowledgeType.MARKET_ANALYSIS
                ]
            )
            
            logger.info(f"📚 Retrieved {len(insights.entries)} strategy insights from RAG")
            
            return insights
            
        except Exception as e:
            logger.error(f"❌ Error querying strategy insights: {e}")
            return RetrievalResult(entries=[], similarities=[], reasoning="Query failed")
    
    async def _extract_actionable_patterns(self, 
                                         insights: RetrievalResult,
                                         market_regime: MarketRegime) -> Dict[str, Any]:
        """Extract actionable patterns from RAG insights"""
        
        patterns = {
            "successful_indicators": [],
            "optimal_parameters": {},
            "risk_controls": [],
            "entry_conditions": [],
            "exit_conditions": [],
            "position_sizing_rules": [],
            "regime_adaptations": []
        }
        
        try:
            for i, entry in enumerate(insights.entries):
                content = entry.content.lower()
                similarity = insights.similarities[i] if i < len(insights.similarities) else 0.5
                
                # Only process high-confidence insights
                if similarity < 0.6:
                    continue
                
                # Extract indicator patterns
                if any(indicator in content for indicator in 
                      ['moving average', 'rsi', 'bollinger', 'macd', 'stochastic']):
                    patterns["successful_indicators"].append({
                        "content": entry.content,
                        "confidence": similarity,
                        "type": self._classify_indicator_type(content)
                    })
                
                # Extract parameter insights
                if any(param in content for param in ['period', 'threshold', 'window']):
                    param_insights = self._extract_parameter_insights(content)
                    if param_insights:
                        patterns["optimal_parameters"].update(param_insights)
                
                # Extract risk control patterns
                if any(risk_term in content for risk_term in 
                      ['stop loss', 'position size', 'drawdown', 'risk']):
                    patterns["risk_controls"].append({
                        "content": entry.content,
                        "confidence": similarity,
                        "regime": market_regime.value
                    })
                
                # Extract entry/exit patterns
                if 'entry' in content or 'signal' in content:
                    patterns["entry_conditions"].append({
                        "content": entry.content,
                        "confidence": similarity
                    })
                
                if 'exit' in content or 'close' in content:
                    patterns["exit_conditions"].append({
                        "content": entry.content,
                        "confidence": similarity
                    })
            
            logger.info(f"🔍 Extracted {sum(len(v) if isinstance(v, list) else 1 for v in patterns.values())} actionable patterns")
            
            return patterns
            
        except Exception as e:
            logger.error(f"❌ Error extracting actionable patterns: {e}")
            return patterns
    
    def _classify_indicator_type(self, content: str) -> str:
        """Classify the type of trading indicator"""
        
        if any(word in content for word in ['moving average', 'ma', 'sma', 'ema']):
            return "trend_following"
        elif any(word in content for word in ['rsi', 'stochastic', 'oscillator']):
            return "momentum"
        elif any(word in content for word in ['bollinger', 'bands', 'std']):
            return "volatility"
        elif any(word in content for word in ['volume', 'vwap']):
            return "volume"
        else:
            return "other"
    
    def _extract_parameter_insights(self, content: str) -> Dict[str, Any]:
        """Extract parameter optimization insights from content"""
        
        parameters = {}
        
        # Simple pattern matching for common parameters
        patterns = {
            r'period\s*(?:of\s*)?(\d+)': 'period',
            r'threshold\s*(?:of\s*)?(\d*\.?\d+)': 'threshold',
            r'window\s*(?:of\s*)?(\d+)': 'window',
            r'(\d+)\s*day': 'lookback_days'
        }
        
        import re
        
        for pattern, param_name in patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                try:
                    value = float(matches[0])
                    parameters[param_name] = value
                except ValueError:
                    continue
        
        return parameters
    
    async def _generate_rag_enhanced_strategy(self, 
                                            objectives: List[StrategyObjective],
                                            market_regime: MarketRegime,
                                            patterns: Dict[str, Any],
                                            symbols: List[str] = None) -> StrategyDNA:
        """Generate strategy enhanced with RAG patterns"""
        
        try:
            # Create base strategy structure
            strategy_id = f"rag_enhanced_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            strategy_name = f"RAG Enhanced {market_regime.value.title()} Strategy"
            
            # Determine strategy type from patterns
            strategy_type = self._infer_strategy_type_from_patterns(patterns, objectives)
            
            # Build indicators from successful patterns
            indicators = self._build_indicators_from_patterns(patterns)
            
            # Build entry conditions from patterns
            entry_conditions = self._build_entry_conditions_from_patterns(patterns)
            
            # Build exit conditions from patterns
            exit_conditions = self._build_exit_conditions_from_patterns(patterns)
            
            # Build position sizing from patterns
            position_sizing = self._build_position_sizing_from_patterns(patterns)
            
            # Build risk controls from patterns
            stop_loss_config = self._build_stop_loss_from_patterns(patterns)
            take_profit_config = self._build_take_profit_from_patterns(patterns)
            
            # Regime sensitivity based on patterns
            regime_sensitivity = self._build_regime_sensitivity_from_patterns(patterns, market_regime)
            
            # Create enhanced strategy DNA
            enhanced_strategy = StrategyDNA(
                strategy_id=strategy_id,
                name=strategy_name,
                strategy_type=strategy_type,
                indicators=indicators,
                entry_conditions=entry_conditions,
                exit_conditions=exit_conditions,
                position_sizing=position_sizing,
                stop_loss_config=stop_loss_config,
                take_profit_config=take_profit_config,
                regime_sensitivity=regime_sensitivity,
                
                # RAG-enhanced metadata
                generation_method="rag_enhanced",
                parent_strategies=[],
                confidence_score=self._calculate_generation_confidence(patterns),
                
                # Enhanced with RAG insights
                validation_results={
                    "rag_patterns_used": len([p for p in patterns.values() if isinstance(p, list) and p]),
                    "insight_confidence": np.mean([
                        p.get("confidence", 0.5) for pattern_list in patterns.values() 
                        if isinstance(pattern_list, list) 
                        for p in pattern_list if isinstance(p, dict)
                    ]) if any(isinstance(p, list) and p for p in patterns.values()) else 0.5
                }
            )
            
            return enhanced_strategy
            
        except Exception as e:
            logger.error(f"❌ Error generating RAG-enhanced strategy: {e}")
            raise
    
    def _infer_strategy_type_from_patterns(self, 
                                         patterns: Dict[str, Any],
                                         objectives: List[StrategyObjective]) -> StrategyType:
        """Infer strategy type from patterns and objectives"""
        
        # Analyze indicator types
        indicator_types = []
        for indicator in patterns.get("successful_indicators", []):
            indicator_types.append(indicator.get("type", "other"))
        
        # Count indicator type frequency
        type_counts = defaultdict(int)
        for itype in indicator_types:
            type_counts[itype] += 1
        
        # Determine strategy type
        if type_counts.get("trend_following", 0) >= 2:
            return StrategyType.TREND_FOLLOWING
        elif type_counts.get("momentum", 0) >= 2:
            return StrategyType.MOMENTUM
        elif type_counts.get("volatility", 0) >= 1 and type_counts.get("momentum", 0) >= 1:
            return StrategyType.VOLATILITY_TRADING
        elif any(obj == StrategyObjective.HIGH_SHARPE_RATIO for obj in objectives):
            return StrategyType.STATISTICAL_ARBITRAGE
        else:
            return StrategyType.HYBRID_AI
    
    def _build_indicators_from_patterns(self, patterns: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Build technical indicators configuration from patterns"""
        
        indicators = {}
        
        # Process successful indicators
        for indicator_info in patterns.get("successful_indicators", []):
            content = indicator_info.get("content", "").lower()
            confidence = indicator_info.get("confidence", 0.5)
            
            # Only include high-confidence indicators
            if confidence < 0.6:
                continue
            
            # Moving averages
            if "moving average" in content or "ma" in content:
                if "moving_averages" not in indicators:
                    indicators["moving_averages"] = {
                        "fast_period": patterns.get("optimal_parameters", {}).get("period", 12),
                        "slow_period": patterns.get("optimal_parameters", {}).get("period", 26) * 2
                    }
            
            # RSI
            if "rsi" in content:
                indicators["oscillators"] = indicators.get("oscillators", {})
                indicators["oscillators"]["rsi_period"] = patterns.get("optimal_parameters", {}).get("period", 14)
                indicators["oscillators"]["rsi_threshold"] = patterns.get("optimal_parameters", {}).get("threshold", 0.7)
            
            # Bollinger Bands
            if "bollinger" in content:
                indicators["volatility"] = indicators.get("volatility", {})
                indicators["volatility"]["bb_period"] = patterns.get("optimal_parameters", {}).get("window", 20)
                indicators["volatility"]["bb_std"] = 2.0
        
        # Default indicators if none found
        if not indicators:
            indicators = {
                "moving_averages": {"fast_period": 12, "slow_period": 26},
                "oscillators": {"rsi_period": 14, "rsi_threshold": 0.7}
            }
        
        return indicators
    
    def _build_entry_conditions_from_patterns(self, patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build entry conditions from patterns"""
        
        entry_conditions = []
        
        # Process entry condition patterns
        for entry_info in patterns.get("entry_conditions", []):
            content = entry_info.get("content", "").lower()
            confidence = entry_info.get("confidence", 0.5)
            
            if confidence < 0.6:
                continue
            
            # Moving average crossover
            if "crossover" in content or "cross" in content:
                entry_conditions.append({
                    "indicator": "moving_averages",
                    "operator": ">",
                    "threshold": 0.01,
                    "description": "Fast MA crosses above slow MA"
                })
            
            # RSI oversold/overbought
            if "rsi" in content and ("oversold" in content or "overbought" in content):
                if "oversold" in content:
                    entry_conditions.append({
                        "indicator": "rsi",
                        "operator": "<",
                        "threshold": 0.3,
                        "description": "RSI oversold condition"
                    })
                else:
                    entry_conditions.append({
                        "indicator": "rsi",
                        "operator": ">",
                        "threshold": 0.7,
                        "description": "RSI overbought condition"
                    })
            
            # Volume confirmation
            if "volume" in content:
                entry_conditions.append({
                    "indicator": "volume",
                    "operator": ">",
                    "threshold": 1.2,
                    "description": "Volume above average"
                })
        
        # Default entry conditions if none found
        if not entry_conditions:
            entry_conditions = [
                {
                    "indicator": "moving_averages",
                    "operator": ">",
                    "threshold": 0.02,
                    "description": "Trend confirmation"
                }
            ]
        
        return entry_conditions
    
    def _build_exit_conditions_from_patterns(self, patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build exit conditions from patterns"""
        
        exit_conditions = []
        
        # Process exit condition patterns
        for exit_info in patterns.get("exit_conditions", []):
            content = exit_info.get("content", "").lower()
            confidence = exit_info.get("confidence", 0.5)
            
            if confidence < 0.6:
                continue
            
            # Profit target
            if "profit" in content or "target" in content:
                threshold = patterns.get("optimal_parameters", {}).get("threshold", 0.03)
                exit_conditions.append({
                    "type": "profit_target",
                    "parameter": threshold,
                    "description": "Take profit at target"
                })
            
            # Time-based exit
            if "time" in content or "hold" in content:
                hold_period = patterns.get("optimal_parameters", {}).get("lookback_days", 5)
                exit_conditions.append({
                    "type": "time_based",
                    "parameter": hold_period,
                    "description": f"Exit after {hold_period} days"
                })
            
            # Trend reversal
            if "reversal" in content or "reverse" in content:
                exit_conditions.append({
                    "type": "trend_reversal",
                    "parameter": 0.02,
                    "description": "Exit on trend reversal"
                })
        
        # Default exit conditions if none found
        if not exit_conditions:
            exit_conditions = [
                {
                    "type": "profit_target",
                    "parameter": 0.03,
                    "description": "Default profit target"
                }
            ]
        
        return exit_conditions
    
    def _build_position_sizing_from_patterns(self, patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Build position sizing configuration from patterns"""
        
        # Analyze position sizing insights from risk controls
        base_size = 0.02  # Default 2%
        
        for risk_info in patterns.get("risk_controls", []):
            content = risk_info.get("content", "").lower()
            confidence = risk_info.get("confidence", 0.5)
            
            if confidence < 0.6:
                continue
            
            # Extract position sizing hints
            if "position size" in content:
                if "small" in content or "conservative" in content:
                    base_size = min(base_size, 0.01)  # 1%
                elif "aggressive" in content or "large" in content:
                    base_size = max(base_size, 0.03)  # 3%
            
            # Risk-adjusted sizing
            if "volatility" in content and "adjust" in content:
                return {
                    "method": "volatility_adjusted",
                    "base_size": base_size,
                    "volatility_lookback": 20,
                    "target_volatility": 0.15
                }
        
        return {
            "method": "fixed",
            "base_size": base_size,
            "max_size": base_size * 2
        }
    
    def _build_stop_loss_from_patterns(self, patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Build stop loss configuration from patterns"""
        
        default_stop = 0.02  # Default 2%
        
        for risk_info in patterns.get("risk_controls", []):
            content = risk_info.get("content", "").lower()
            confidence = risk_info.get("confidence", 0.5)
            
            if confidence < 0.6:
                continue
            
            if "stop loss" in content or "stop" in content:
                if "tight" in content or "close" in content:
                    default_stop = 0.01  # 1%
                elif "wide" in content or "loose" in content:
                    default_stop = 0.03  # 3%
        
        return {
            "type": "fixed",
            "threshold": default_stop,
            "trail": False
        }
    
    def _build_take_profit_from_patterns(self, patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Build take profit configuration from patterns"""
        
        default_tp = 0.03  # Default 3%
        
        for exit_info in patterns.get("exit_conditions", []):
            content = exit_info.get("content", "").lower()
            confidence = exit_info.get("confidence", 0.5)
            
            if confidence < 0.6:
                continue
            
            if "take profit" in content or "profit target" in content:
                threshold = patterns.get("optimal_parameters", {}).get("threshold", default_tp)
                default_tp = threshold
        
        return {
            "type": "fixed",
            "threshold": default_tp,
            "partial": False
        }
    
    def _build_regime_sensitivity_from_patterns(self, 
                                              patterns: Dict[str, Any],
                                              current_regime: MarketRegime) -> Dict[MarketRegime, float]:
        """Build regime sensitivity from patterns"""
        
        # Default sensitivity
        regime_sensitivity = {regime: 0.5 for regime in MarketRegime}
        
        # Boost sensitivity for current regime
        regime_sensitivity[current_regime] = 0.8
        
        # Analyze regime-specific patterns
        for risk_info in patterns.get("risk_controls", []):
            regime = risk_info.get("regime", "")
            confidence = risk_info.get("confidence", 0.5)
            
            if regime and confidence > 0.7:
                try:
                    regime_enum = MarketRegime(regime)
                    regime_sensitivity[regime_enum] = max(
                        regime_sensitivity[regime_enum], confidence
                    )
                except ValueError:
                    continue
        
        return regime_sensitivity
    
    def _calculate_generation_confidence(self, patterns: Dict[str, Any]) -> float:
        """Calculate confidence score for generated strategy"""
        
        total_confidence = 0.0
        total_weight = 0.0
        
        # Weight different pattern types
        weights = {
            "successful_indicators": 0.3,
            "optimal_parameters": 0.2,
            "risk_controls": 0.2,
            "entry_conditions": 0.15,
            "exit_conditions": 0.15
        }
        
        for pattern_type, weight in weights.items():
            pattern_list = patterns.get(pattern_type, [])
            
            if isinstance(pattern_list, list) and pattern_list:
                avg_confidence = np.mean([
                    p.get("confidence", 0.5) for p in pattern_list 
                    if isinstance(p, dict)
                ])
                total_confidence += avg_confidence * weight
                total_weight += weight
        
        return total_confidence / total_weight if total_weight > 0 else 0.5
    
    async def _apply_historical_optimizations(self, 
                                            strategy: StrategyDNA,
                                            insights: RetrievalResult) -> StrategyDNA:
        """Apply historical optimizations learned from RAG"""
        
        try:
            # Query for optimization lessons
            optimization_query = f"Parameter optimization lessons for {strategy.strategy_type.value} strategies"
            
            optimization_insights = await self.rag_system.query_trading_intelligence(
                query=optimization_query,
                query_type=QueryType.OPTIMIZATION,
                knowledge_types=[KnowledgeType.SUCCESS_PATTERN, KnowledgeType.OPTIMIZATION]
            )
            
            # Apply optimization insights
            optimized_strategy = strategy
            
            for insight in optimization_insights.entries:
                content = insight.content.lower()
                
                # Parameter optimizations
                if "period" in content and "optimal" in content:
                    # Extract and apply period optimizations
                    pass
                
                if "threshold" in content and "better" in content:
                    # Extract and apply threshold optimizations
                    pass
                
                if "risk" in content and "reduce" in content:
                    # Apply risk reduction optimizations
                    if "stop_loss_config" in optimized_strategy.__dict__:
                        current_stop = optimized_strategy.stop_loss_config.get("threshold", 0.02)
                        optimized_strategy.stop_loss_config["threshold"] = current_stop * 0.9  # Reduce by 10%
            
            return optimized_strategy
            
        except Exception as e:
            logger.warning(f"⚠️ Could not apply historical optimizations: {e}")
            return strategy
    
    async def _record_strategy_generation_event(self, 
                                               strategy: StrategyDNA,
                                               insights: RetrievalResult,
                                               patterns: Dict[str, Any]):
        """Record strategy generation event for learning"""
        
        try:
            # Create knowledge entry for this generation
            generation_content = f"""
            Generated strategy: {strategy.name}
            Strategy type: {strategy.strategy_type.value}
            Generation method: RAG-enhanced
            
            RAG insights used: {len(insights.entries)}
            Patterns extracted: {sum(len(v) if isinstance(v, list) else 1 for v in patterns.values())}
            Confidence: {strategy.confidence_score:.2f}
            
            Key patterns applied:
            - Indicators: {len(patterns.get('successful_indicators', []))}
            - Entry conditions: {len(patterns.get('entry_conditions', []))}
            - Exit conditions: {len(patterns.get('exit_conditions', []))}
            - Risk controls: {len(patterns.get('risk_controls', []))}
            """
            
            await self.rag_system.add_trading_knowledge(
                content=generation_content,
                knowledge_type=KnowledgeType.TRADING_STRATEGY,
                source="ai_strategy_generator",
                context={
                    "strategy_id": strategy.strategy_id,
                    "generation_timestamp": datetime.now().isoformat(),
                    "patterns_used": patterns,
                    "rag_insights_count": len(insights.entries)
                },
                tags=["ai_generated", "rag_enhanced", strategy.strategy_type.value]
            )
            
            # Store in generation history
            self.generation_history.append({
                "strategy_id": strategy.strategy_id,
                "timestamp": datetime.now(),
                "patterns_used": patterns,
                "insights_count": len(insights.entries),
                "confidence": strategy.confidence_score
            })
            
        except Exception as e:
            logger.error(f"❌ Failed to record generation event: {e}")

class StrategyLearningEngine:
    """
    📚 Strategy Performance Learning Engine
    """
    
    def __init__(self, rag_system: AdvancedMemoryRAGSystem):
        self.rag_system = rag_system
        self.learning_outcomes = deque(maxlen=1000)
        self.pattern_recognition = {}
        self.performance_patterns = defaultdict(list)
        
        logger.info("📚 Strategy Learning Engine initialized")
    
    async def learn_from_strategy_performance(self, 
                                            strategy: StrategyDNA,
                                            performance: StrategyPerformance,
                                            validation_result: Optional[ValidationResult] = None,
                                            market_context: Dict[str, Any] = None) -> StrategyLearningOutcome:
        """Learn from strategy performance and update knowledge base"""
        
        try:
            # Analyze performance outcome
            outcome_type = self._classify_performance_outcome(performance)
            
            # Extract key lessons
            key_lesson = await self._extract_key_lesson(strategy, performance, outcome_type, market_context)
            
            # Generate supporting evidence
            supporting_evidence = self._generate_supporting_evidence(performance, validation_result)
            
            # Determine applicable conditions
            applicable_conditions = self._determine_applicable_conditions(strategy, market_context)
            
            # Calculate confidence and impact
            confidence = self._calculate_lesson_confidence(performance, validation_result)
            impact_score = self._calculate_lesson_impact(performance, outcome_type)
            
            # Create learning outcome
            learning_outcome = StrategyLearningOutcome(
                strategy_id=strategy.strategy_id,
                outcome_type=outcome_type,
                key_lesson=key_lesson,
                supporting_evidence=supporting_evidence,
                applicable_conditions=applicable_conditions,
                confidence=confidence,
                impact_score=impact_score
            )
            
            # Store learning in RAG system
            await self._store_learning_outcome(learning_outcome, strategy)
            
            # Update pattern recognition
            await self._update_pattern_recognition(learning_outcome, strategy)
            
            # Store in learning history
            self.learning_outcomes.append(learning_outcome)
            
            logger.info(f"📚 Learned from strategy {strategy.name}: {outcome_type} - {key_lesson[:50]}...")
            
            return learning_outcome
            
        except Exception as e:
            logger.error(f"❌ Strategy learning failed: {e}")
            raise
    
    def _classify_performance_outcome(self, performance: StrategyPerformance) -> str:
        """Classify the performance outcome"""
        
        # Multiple criteria for classification
        sharpe_good = performance.sharpe_ratio > 1.0
        return_good = performance.total_return > 0.1
        drawdown_good = performance.max_drawdown < 0.15
        win_rate_good = performance.win_rate > 0.5
        
        good_criteria = sum([sharpe_good, return_good, drawdown_good, win_rate_good])
        
        if good_criteria >= 3:
            return "success"
        elif good_criteria >= 2:
            return "mixed"
        else:
            return "failure"
    
    async def _extract_key_lesson(self, 
                                strategy: StrategyDNA,
                                performance: StrategyPerformance,
                                outcome_type: str,
                                market_context: Dict[str, Any] = None) -> str:
        """Extract key lesson from performance"""
        
        lessons = []
        
        if outcome_type == "success":
            # Success lessons
            if performance.sharpe_ratio > 1.5:
                lessons.append(f"High Sharpe ratio ({performance.sharpe_ratio:.2f}) achieved with {strategy.strategy_type.value} approach")
            
            if performance.max_drawdown < 0.10:
                lessons.append(f"Low drawdown ({performance.max_drawdown:.1%}) maintained through effective risk controls")
            
            if performance.win_rate > 0.6:
                lessons.append(f"High win rate ({performance.win_rate:.1%}) indicates good signal quality")
            
            # Analyze successful components
            if strategy.indicators:
                lessons.append(f"Successful indicators combination: {list(strategy.indicators.keys())}")
        
        elif outcome_type == "failure":
            # Failure lessons
            if performance.sharpe_ratio < 0.0:
                lessons.append(f"Negative Sharpe ratio ({performance.sharpe_ratio:.2f}) indicates poor risk-adjusted returns")
            
            if performance.max_drawdown > 0.25:
                lessons.append(f"Excessive drawdown ({performance.max_drawdown:.1%}) suggests inadequate risk management")
            
            if performance.win_rate < 0.4:
                lessons.append(f"Low win rate ({performance.win_rate:.1%}) indicates poor signal quality")
            
        else:  # mixed
            lessons.append(f"Mixed results: Strong in some areas but needs improvement in others")
        
        # Market context lessons
        if market_context:
            regime = market_context.get("market_regime", "unknown")
            lessons.append(f"Performance in {regime} market conditions")
        
        return " | ".join(lessons[:3])  # Top 3 lessons
    
    def _generate_supporting_evidence(self, 
                                    performance: StrategyPerformance,
                                    validation_result: Optional[ValidationResult] = None) -> Dict[str, Any]:
        """Generate supporting evidence for the lesson"""
        
        evidence = {
            "performance_metrics": {
                "sharpe_ratio": performance.sharpe_ratio,
                "total_return": performance.total_return,
                "max_drawdown": performance.max_drawdown,
                "win_rate": performance.win_rate,
                "profit_factor": performance.profit_factor,
                "total_trades": performance.total_trades
            }
        }
        
        if validation_result:
            evidence["validation_results"] = {
                "overall_status": validation_result.overall_status.value,
                "overall_score": validation_result.overall_score,
                "confidence_level": validation_result.confidence_level
            }
            
            if validation_result.stress_test_results:
                evidence["stress_test_resilience"] = validation_result.stress_test_results.get("overall_score", 0.0)
        
        return evidence
    
    def _determine_applicable_conditions(self, 
                                       strategy: StrategyDNA,
                                       market_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Determine when this lesson applies"""
        
        conditions = {
            "strategy_type": strategy.strategy_type.value,
            "indicators_used": list(strategy.indicators.keys()) if strategy.indicators else [],
            "position_sizing_method": strategy.position_sizing.get("method", "unknown")
        }
        
        if market_context:
            conditions.update({
                "market_regime": market_context.get("market_regime", "unknown"),
                "volatility_environment": market_context.get("volatility_level", "unknown"),
                "correlation_environment": market_context.get("correlation_level", "unknown")
            })
        
        # Add regime sensitivity
        if strategy.regime_sensitivity:
            best_regime = max(strategy.regime_sensitivity.items(), key=lambda x: x[1])
            conditions["best_regime"] = best_regime[0].value
            conditions["regime_sensitivity"] = best_regime[1]
        
        return conditions
    
    def _calculate_lesson_confidence(self, 
                                   performance: StrategyPerformance,
                                   validation_result: Optional[ValidationResult] = None) -> float:
        """Calculate confidence in the lesson"""
        
        confidence_factors = []
        
        # Trade count confidence
        if performance.total_trades > 100:
            confidence_factors.append(0.9)
        elif performance.total_trades > 50:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.5)
        
        # Performance consistency
        if abs(performance.sharpe_ratio) > 1.0:  # Strong signal either way
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.6)
        
        # Validation confidence
        if validation_result:
            confidence_factors.append(validation_result.confidence_level)
        
        return np.mean(confidence_factors)
    
    def _calculate_lesson_impact(self, performance: StrategyPerformance, outcome_type: str) -> float:
        """Calculate the impact/importance of this lesson"""
        
        # Base impact on outcome magnitude
        if outcome_type == "success":
            # Higher impact for exceptional success
            impact = min(1.0, (performance.sharpe_ratio + 1.0) / 3.0)
        elif outcome_type == "failure":
            # Higher impact for spectacular failure (more to learn)
            impact = min(1.0, abs(performance.sharpe_ratio) / 2.0)
        else:  # mixed
            impact = 0.5
        
        # Boost impact if many trades (more statistical significance)
        if performance.total_trades > 100:
            impact *= 1.2
        
        return min(1.0, impact)
    
    async def _store_learning_outcome(self, 
                                    learning_outcome: StrategyLearningOutcome,
                                    strategy: StrategyDNA):
        """Store learning outcome in RAG system"""
        
        try:
            # Determine knowledge type
            if learning_outcome.outcome_type == "success":
                knowledge_type = KnowledgeType.SUCCESS_PATTERN
            else:
                knowledge_type = KnowledgeType.ERROR_PATTERN
            
            # Create comprehensive learning content
            learning_content = f"""
            Strategy Learning Outcome:
            
            Strategy: {strategy.name} ({strategy.strategy_id})
            Outcome: {learning_outcome.outcome_type.upper()}
            
            Key Lesson: {learning_outcome.key_lesson}
            
            Performance Evidence:
            - Sharpe Ratio: {learning_outcome.supporting_evidence['performance_metrics']['sharpe_ratio']:.2f}
            - Total Return: {learning_outcome.supporting_evidence['performance_metrics']['total_return']:.2%}
            - Max Drawdown: {learning_outcome.supporting_evidence['performance_metrics']['max_drawdown']:.2%}
            - Win Rate: {learning_outcome.supporting_evidence['performance_metrics']['win_rate']:.1%}
            - Total Trades: {learning_outcome.supporting_evidence['performance_metrics']['total_trades']}
            
            Applicable Conditions:
            - Strategy Type: {learning_outcome.applicable_conditions.get('strategy_type', 'Unknown')}
            - Market Regime: {learning_outcome.applicable_conditions.get('market_regime', 'Unknown')}
            - Best Regime: {learning_outcome.applicable_conditions.get('best_regime', 'Unknown')}
            
            Confidence: {learning_outcome.confidence:.2f}
            Impact Score: {learning_outcome.impact_score:.2f}
            """
            
            # Store in RAG system
            await self.rag_system.add_trading_knowledge(
                content=learning_content,
                knowledge_type=knowledge_type,
                source="strategy_learning_engine",
                context={
                    "strategy_id": strategy.strategy_id,
                    "outcome_type": learning_outcome.outcome_type,
                    "confidence": learning_outcome.confidence,
                    "impact_score": learning_outcome.impact_score,
                    "learning_timestamp": datetime.now().isoformat()
                },
                tags=[
                    "strategy_learning",
                    learning_outcome.outcome_type,
                    strategy.strategy_type.value,
                    f"confidence_{int(learning_outcome.confidence * 10)}"
                ]
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to store learning outcome: {e}")
    
    async def _update_pattern_recognition(self, 
                                        learning_outcome: StrategyLearningOutcome,
                                        strategy: StrategyDNA):
        """Update pattern recognition based on learning"""
        
        try:
            # Extract pattern key
            pattern_key = f"{strategy.strategy_type.value}_{learning_outcome.outcome_type}"
            
            # Store performance pattern
            pattern_data = {
                "strategy_id": strategy.strategy_id,
                "outcome": learning_outcome.outcome_type,
                "confidence": learning_outcome.confidence,
                "impact": learning_outcome.impact_score,
                "conditions": learning_outcome.applicable_conditions,
                "lesson": learning_outcome.key_lesson,
                "timestamp": datetime.now()
            }
            
            self.performance_patterns[pattern_key].append(pattern_data)
            
            # Update pattern recognition metrics
            self.pattern_recognition[pattern_key] = {
                "total_instances": len(self.performance_patterns[pattern_key]),
                "success_rate": len([p for p in self.performance_patterns[pattern_key] if p["outcome"] == "success"]) / len(self.performance_patterns[pattern_key]),
                "avg_confidence": np.mean([p["confidence"] for p in self.performance_patterns[pattern_key]]),
                "avg_impact": np.mean([p["impact"] for p in self.performance_patterns[pattern_key]]),
                "last_updated": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to update pattern recognition: {e}")
    
    def get_learning_insights(self, strategy_type: Optional[StrategyType] = None,
                            outcome_type: Optional[str] = None) -> Dict[str, Any]:
        """Get learning insights and patterns"""
        
        try:
            insights = {
                "total_learning_outcomes": len(self.learning_outcomes),
                "pattern_recognition_stats": dict(self.pattern_recognition),
                "recent_lessons": []
            }
            
            # Filter recent lessons
            recent_outcomes = list(self.learning_outcomes)[-10:]  # Last 10
            
            for outcome in recent_outcomes:
                if strategy_type and outcome.strategy_id not in [s.strategy_id for s in [] if s.strategy_type == strategy_type]:
                    continue
                
                if outcome_type and outcome.outcome_type != outcome_type:
                    continue
                
                insights["recent_lessons"].append({
                    "strategy_id": outcome.strategy_id,
                    "outcome_type": outcome.outcome_type,
                    "key_lesson": outcome.key_lesson[:100] + "..." if len(outcome.key_lesson) > 100 else outcome.key_lesson,
                    "confidence": outcome.confidence,
                    "impact_score": outcome.impact_score
                })
            
            # Pattern summary
            if self.performance_patterns:
                insights["pattern_summary"] = {}
                for pattern_key, patterns in self.performance_patterns.items():
                    insights["pattern_summary"][pattern_key] = {
                        "count": len(patterns),
                        "success_rate": len([p for p in patterns if p["outcome"] == "success"]) / len(patterns),
                        "avg_confidence": np.mean([p["confidence"] for p in patterns])
                    }
            
            return insights
            
        except Exception as e:
            logger.error(f"❌ Error getting learning insights: {e}")
            return {}

class AIStrategyRAGIntegration:
    """
    🧠 MAIN AI STRATEGY + RAG INTEGRATION SYSTEM
    Orchestrates the complete integration between AI Strategy Generator and RAG system
    """
    
    def __init__(self):
        self.rag_system: Optional[AdvancedMemoryRAGSystem] = None
        self.rag_enhanced_generator: Optional[StrategyRAGEnhancedGenerator] = None
        self.learning_engine: Optional[StrategyLearningEngine] = None
        
        # Integration statistics
        self.integration_stats = {
            "strategies_generated_with_rag": 0,
            "lessons_learned": 0,
            "knowledge_entries_created": 0,
            "pattern_recognitions": 0,
            "last_learning_session": None,
            "system_initialization": datetime.now()
        }
        
    async def initialize(self):
        """Initialize the RAG integration system"""
        
        try:
            # Initialize RAG system
            self.rag_system = AdvancedMemoryRAGSystem()
            await self.rag_system.initialize()
            
            # Initialize RAG-enhanced generator
            self.rag_enhanced_generator = StrategyRAGEnhancedGenerator(self.rag_system)
            
            # Initialize learning engine
            self.learning_engine = StrategyLearningEngine(self.rag_system)
            
            logger.info("🧠 AI Strategy RAG Integration fully initialized")
            
            # Seed initial knowledge if needed
            await self._seed_initial_knowledge()
            
        except Exception as e:
            logger.error(f"❌ RAG integration initialization failed: {e}")
            raise
    
    async def _seed_initial_knowledge(self):
        """Seed the RAG system with initial strategy knowledge"""
        
        try:
            # Basic trading strategy knowledge
            initial_knowledge = [
                {
                    "content": "Moving average crossover strategies work well in trending markets. Fast MA (12-period) crossing above slow MA (26-period) generates buy signals. Best performance in bull markets with confirmation from volume.",
                    "type": KnowledgeType.TRADING_STRATEGY,
                    "tags": ["moving_average", "trend_following", "crossover"]
                },
                {
                    "content": "RSI oversold/overbought strategy: Buy when RSI < 30, sell when RSI > 70. Works best in ranging markets. Use 14-period RSI with 0.7 threshold for better signals.",
                    "type": KnowledgeType.TRADING_STRATEGY,
                    "tags": ["rsi", "oscillator", "mean_reversion"]
                },
                {
                    "content": "Risk management lesson: Stop losses should be 1-2% for low volatility assets, 2-3% for medium volatility, and 3-5% for high volatility. Adjust based on 20-day realized volatility.",
                    "type": KnowledgeType.SUCCESS_PATTERN,
                    "tags": ["risk_management", "stop_loss", "volatility_adjustment"]
                },
                {
                    "content": "Position sizing optimization: Use 2% risk per trade as baseline. Scale down to 1% during high volatility periods. Scale up to 3% only for high-confidence signals with strong trend confirmation.",
                    "type": KnowledgeType.OPTIMIZATION,
                    "tags": ["position_sizing", "risk_per_trade", "volatility_adjustment"]
                }
            ]
            
            for knowledge in initial_knowledge:
                await self.rag_system.add_trading_knowledge(
                    content=knowledge["content"],
                    knowledge_type=knowledge["type"],
                    source="initial_seed",
                    tags=knowledge["tags"]
                )
            
            self.integration_stats["knowledge_entries_created"] += len(initial_knowledge)
            
            logger.info(f"🌱 Seeded {len(initial_knowledge)} initial knowledge entries")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to seed initial knowledge: {e}")
    
    async def generate_enhanced_strategy(self, 
                                       objectives: List[StrategyObjective],
                                       market_regime: MarketRegime,
                                       symbols: List[str] = None) -> StrategyDNA:
        """Generate strategy enhanced with RAG knowledge"""
        
        if not self.rag_enhanced_generator:
            raise ValueError("RAG integration not initialized")
        
        strategy = await self.rag_enhanced_generator.generate_strategy_with_rag(
            objectives, market_regime, symbols
        )
        
        self.integration_stats["strategies_generated_with_rag"] += 1
        
        return strategy
    
    async def learn_from_performance(self, 
                                   strategy: StrategyDNA,
                                   performance: StrategyPerformance,
                                   validation_result: Optional[ValidationResult] = None,
                                   market_context: Dict[str, Any] = None) -> StrategyLearningOutcome:
        """Learn from strategy performance"""
        
        if not self.learning_engine:
            raise ValueError("RAG integration not initialized")
        
        learning_outcome = await self.learning_engine.learn_from_strategy_performance(
            strategy, performance, validation_result, market_context
        )
        
        self.integration_stats["lessons_learned"] += 1
        self.integration_stats["last_learning_session"] = datetime.now()
        
        return learning_outcome
    
    async def get_strategy_recommendations(self, 
                                         current_market_context: Dict[str, Any],
                                         performance_objectives: List[StrategyObjective]) -> Dict[str, Any]:
        """Get strategy recommendations based on learned knowledge"""
        
        try:
            if not self.rag_system:
                return {"error": "RAG system not initialized"}
            
            # Build context-aware query
            regime = current_market_context.get("market_regime", "unknown")
            volatility = current_market_context.get("volatility_level", "unknown")
            
            query = f"""
            Given current market conditions:
            - Market regime: {regime}
            - Volatility level: {volatility}
            - Performance objectives: {', '.join([obj.value for obj in performance_objectives])}
            
            What are the most effective trading strategies and approaches?
            What lessons have been learned from similar market conditions?
            What parameters and risk controls work best?
            """
            
            # Query RAG system
            recommendations = await self.rag_system.query_trading_intelligence(
                query=query,
                query_type=QueryType.DECISION_SUPPORT,
                max_results=10,
                knowledge_types=[
                    KnowledgeType.TRADING_STRATEGY,
                    KnowledgeType.SUCCESS_PATTERN,
                    KnowledgeType.OPTIMIZATION
                ]
            )
            
            # Extract actionable recommendations
            actionable_recommendations = {
                "recommended_strategies": [],
                "optimal_parameters": {},
                "risk_controls": [],
                "market_specific_insights": [],
                "confidence_score": 0.0
            }
            
            for i, entry in enumerate(recommendations.entries):
                similarity = recommendations.similarities[i] if i < len(recommendations.similarities) else 0.5
                
                if similarity > 0.6:  # High relevance threshold
                    actionable_recommendations["recommended_strategies"].append({
                        "description": entry.content[:200] + "...",
                        "confidence": similarity,
                        "source": entry.metadata.get("source", "unknown")
                    })
            
            # Calculate overall confidence
            if recommendations.similarities:
                actionable_recommendations["confidence_score"] = np.mean([
                    s for s in recommendations.similarities if s > 0.6
                ])
            
            return actionable_recommendations
            
        except Exception as e:
            logger.error(f"❌ Error getting strategy recommendations: {e}")
            return {"error": str(e)}
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get integration system status and statistics"""
        
        try:
            status = {
                "system_status": "active" if self.rag_system else "inactive",
                "components_initialized": {
                    "rag_system": self.rag_system is not None,
                    "rag_enhanced_generator": self.rag_enhanced_generator is not None,
                    "learning_engine": self.learning_engine is not None
                },
                "integration_statistics": self.integration_stats.copy(),
                "current_timestamp": datetime.now()
            }
            
            # Add RAG system statistics if available
            if self.rag_system:
                status["rag_system_stats"] = {
                    "knowledge_entries": len(self.rag_system.knowledge_cache),
                    "queries_served": self.rag_system.stats.get("queries_served", 0),
                    "cache_hit_rate": self.rag_system.stats.get("cache_hit_rate", 0.0)
                }
            
            # Add learning engine statistics if available
            if self.learning_engine:
                status["learning_engine_stats"] = {
                    "total_lessons": len(self.learning_engine.learning_outcomes),
                    "pattern_types": len(self.learning_engine.pattern_recognition),
                    "recent_learning_activity": len([
                        outcome for outcome in self.learning_engine.learning_outcomes
                        if (datetime.now() - datetime.fromisoformat(
                            outcome.supporting_evidence.get("learning_timestamp", "2024-01-01T00:00:00")
                        )).days <= 7
                    ]) if self.learning_engine.learning_outcomes else 0
                }
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Error getting integration status: {e}")
            return {"error": str(e)}
    
    async def export_learned_knowledge(self) -> Dict[str, Any]:
        """Export all learned knowledge for analysis"""
        
        try:
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "integration_stats": self.integration_stats,
                "learned_patterns": {},
                "knowledge_summary": {}
            }
            
            # Export learning engine patterns
            if self.learning_engine:
                export_data["learned_patterns"] = {
                    pattern_key: {
                        "instances": len(patterns),
                        "success_rate": len([p for p in patterns if p["outcome"] == "success"]) / len(patterns),
                        "recent_lessons": [p["lesson"] for p in patterns[-5:]]  # Last 5 lessons
                    }
                    for pattern_key, patterns in self.learning_engine.performance_patterns.items()
                }
                
                export_data["knowledge_summary"] = self.learning_engine.get_learning_insights()
            
            # Export RAG system knowledge stats
            if self.rag_system:
                export_data["rag_knowledge_stats"] = {
                    "total_entries": len(self.rag_system.knowledge_cache),
                    "knowledge_types": {},
                    "recent_additions": 0
                }
            
            return export_data
            
        except Exception as e:
            logger.error(f"❌ Error exporting learned knowledge: {e}")
            return {"error": str(e)}

# Global integration instance
_rag_integration: Optional[AIStrategyRAGIntegration] = None

async def get_rag_integration() -> AIStrategyRAGIntegration:
    """Get global RAG integration instance"""
    global _rag_integration
    
    if _rag_integration is None:
        _rag_integration = AIStrategyRAGIntegration()
        await _rag_integration.initialize()
    
    return _rag_integration

# Integration functions for main AI Strategy Generator

async def generate_strategy_with_rag_enhancement(objectives: List[StrategyObjective],
                                               market_regime: MarketRegime,
                                               symbols: List[str] = None) -> StrategyDNA:
    """Generate strategy with RAG knowledge enhancement"""
    
    integration = await get_rag_integration()
    return await integration.generate_enhanced_strategy(objectives, market_regime, symbols)

async def learn_from_strategy_deployment(strategy_id: str,
                                       performance_data: Dict[str, Any],
                                       market_context: Dict[str, Any]) -> StrategyLearningOutcome:
    """Learn from deployed strategy performance"""
    
    try:
        integration = await get_rag_integration()
        
        # Convert performance data to StrategyPerformance object
        performance = StrategyPerformance(
            strategy_id=strategy_id,
            **performance_data
        )
        
        # Create mock strategy DNA (in real implementation, would load from library)
        strategy_dna = StrategyDNA(
            strategy_id=strategy_id,
            name=f"Strategy_{strategy_id}",
            strategy_type=StrategyType.HYBRID_AI
        )
        
        return await integration.learn_from_performance(
            strategy_dna, performance, None, market_context
        )
        
    except Exception as e:
        logger.error(f"❌ Error learning from strategy deployment: {e}")
        raise

async def get_rag_strategy_insights(market_context: Dict[str, Any],
                                  objectives: List[StrategyObjective]) -> Dict[str, Any]:
    """Get strategy insights from RAG knowledge base"""
    
    integration = await get_rag_integration()
    return await integration.get_strategy_recommendations(market_context, objectives)

def get_rag_integration_status() -> Dict[str, Any]:
    """Get RAG integration system status"""
    
    if _rag_integration:
        return _rag_integration.get_integration_status()
    else:
        return {"system_status": "not_initialized"}

if __name__ == "__main__":
    # Example usage and testing
    async def test_rag_integration():
        """Test the RAG integration system"""
        
        try:
            # Initialize integration
            integration = await get_rag_integration()
            
            # Test strategy generation with RAG
            objectives = [StrategyObjective.HIGH_SHARPE_RATIO, StrategyObjective.LOW_DRAWDOWN]
            strategy = await integration.generate_enhanced_strategy(
                objectives, MarketRegime.BULL_TRENDING, ["BTC/USD", "ETH/USD"]
            )
            
            print(f"Generated RAG-enhanced strategy: {strategy.name}")
            print(f"Confidence: {strategy.confidence_score:.2f}")
            
            # Test learning from performance
            mock_performance = StrategyPerformance(
                strategy_id=strategy.strategy_id,
                total_return=0.15,
                sharpe_ratio=1.2,
                max_drawdown=0.08,
                win_rate=0.6,
                total_trades=50
            )
            
            learning_outcome = await integration.learn_from_performance(
                strategy, mock_performance, None, {"market_regime": "bull_trending"}
            )
            
            print(f"Learning outcome: {learning_outcome.outcome_type}")
            print(f"Key lesson: {learning_outcome.key_lesson[:100]}...")
            
            # Test recommendations
            recommendations = await integration.get_strategy_recommendations(
                {"market_regime": "bull_trending", "volatility_level": "medium"},
                objectives
            )
            
            print(f"Recommendations: {len(recommendations.get('recommended_strategies', []))}")
            
            # Get system status
            status = integration.get_integration_status()
            print(f"Integration status: {status['system_status']}")
            print(f"Stats: {status['integration_statistics']}")
            
            return integration
            
        except Exception as e:
            print(f"Test error: {e}")
            raise
    
    # Run test
    asyncio.run(test_rag_integration())