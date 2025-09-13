#!/usr/bin/env python3
"""
🔄 ORCHESTRATOR INTEGRATION LAYER
Seamless integration between Multi-Model Orchestrator and LocalAI Infrastructure
- LocalAI Model Registry Integration
- AGUS 2.0 Hybrid System Integration
- Trading Bot Integration Layer
- Performance Monitoring Bridge
- Real-time Data Pipeline Integration
"""
import os
import json
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from loguru import logger
from pathlib import Path
import threading

# Import orchestrator components
from .multi_model_orchestrator import (
    MultiModelOrchestrator, 
    OrchestrationTask, 
    EnsemblePrediction,
    ModelRole,
    ConsensusType,
    get_orchestrator,
    orchestrate_trading_analysis
)

# Import existing LocalAI components
from .localai_institutional_manager import LocalAIInstitutionalManager, ModelConfig
from .localai_trading_models import (
    FinancialSentimentModel, 
    TechnicalAnalysisModel,
    TradingModelOutput
)
from .agus_2_hybrid_system import AGUS2HybridSystem, AIProvider, QueryComplexity

# Import trading system components
try:
    from .strategy import TradingStrategy
    from .data import DataProvider
    from .risk import RiskManager
    from .execution import ExecutionManager
except ImportError:
    logger.warning("⚠️ Some trading components not available - running in standalone mode")
    TradingStrategy = None
    DataProvider = None
    RiskManager = None
    ExecutionManager = None

@dataclass
class IntegrationConfig:
    """Configuration for orchestrator integration"""
    enable_localai_models: bool = True
    enable_agus_integration: bool = True
    enable_trading_integration: bool = True
    model_startup_timeout: float = 60.0
    health_check_interval: int = 30
    max_concurrent_predictions: int = 10
    fallback_to_agus: bool = True
    performance_tracking: bool = True

class LocalAIModelWrapper:
    """
    🎯 Wrapper to integrate LocalAI models with the orchestrator
    """
    
    def __init__(self, model_instance: Any, model_name: str, model_role: ModelRole):
        self.model_instance = model_instance
        self.model_name = model_name
        self.model_role = model_role
        self.last_prediction = None
        self.performance_history = []
        
    async def predict(self, query: str, symbol: str, context: Dict[str, Any]) -> TradingModelOutput:
        """Make prediction using the wrapped LocalAI model"""
        try:
            start_time = time.time()
            
            # Call the appropriate method based on model type
            if hasattr(self.model_instance, 'analyze_sentiment'):
                result = await self.model_instance.analyze_sentiment(query, symbol)
            elif hasattr(self.model_instance, 'predict_price_movement'):
                # Get market data for technical analysis
                market_data = context.get('market_data', {})
                result = await self.model_instance.predict_price_movement(symbol, market_data)
            elif hasattr(self.model_instance, 'assess_risk'):
                portfolio_data = context.get('portfolio_data', {})
                result = await self.model_instance.assess_risk(symbol, portfolio_data)
            elif callable(self.model_instance):
                # Generic callable model
                result = await self.model_instance(query, symbol, context)
            else:
                # Fallback - create basic prediction
                result = TradingModelOutput(
                    model_name=self.model_name,
                    symbol=symbol,
                    prediction=0.0,
                    confidence=0.5,
                    reasoning=f"Fallback prediction from {self.model_name}",
                    features_used=["fallback"]
                )
            
            execution_time = time.time() - start_time
            
            # Track performance
            self.performance_history.append({
                "timestamp": datetime.now(),
                "execution_time": execution_time,
                "confidence": result.confidence
            })
            
            # Keep only last 100 predictions
            if len(self.performance_history) > 100:
                self.performance_history = self.performance_history[-100:]
            
            self.last_prediction = result
            return result
            
        except Exception as e:
            logger.error(f"❌ LocalAI model {self.model_name} prediction failed: {e}")
            
            # Return error prediction
            return TradingModelOutput(
                model_name=self.model_name,
                symbol=symbol,
                prediction=0.0,
                confidence=0.0,
                reasoning=f"Model error: {str(e)}",
                features_used=["error"]
            )

class AGUSIntegrationBridge:
    """
    🧠 Bridge between Multi-Model Orchestrator and AGUS 2.0 Hybrid System
    """
    
    def __init__(self, agus_system: Optional[AGUS2HybridSystem] = None):
        self.agus_system = agus_system
        self.fallback_queries = []
        self.integration_metrics = {
            "orchestrator_calls": 0,
            "agus_fallbacks": 0,
            "successful_predictions": 0,
            "failed_predictions": 0
        }
    
    async def enhanced_prediction(
        self, 
        symbol: str, 
        analysis_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> EnsemblePrediction:
        """Enhanced prediction using both orchestrator and AGUS when needed"""
        
        try:
            self.integration_metrics["orchestrator_calls"] += 1
            
            # First try orchestrator
            orchestrator_result = await orchestrate_trading_analysis(
                symbol=symbol,
                analysis_type=analysis_type,
                context=context or {}
            )
            
            # If confidence is high, use orchestrator result
            if orchestrator_result.confidence_score > 0.7:
                self.integration_metrics["successful_predictions"] += 1
                return orchestrator_result
            
            # If confidence is low and AGUS is available, enhance with AGUS
            if self.agus_system and orchestrator_result.confidence_score < 0.5:
                agus_enhancement = await self._get_agus_enhancement(
                    symbol, analysis_type, orchestrator_result, context
                )
                
                if agus_enhancement:
                    # Combine orchestrator and AGUS results
                    enhanced_result = self._combine_predictions(
                        orchestrator_result, agus_enhancement
                    )
                    self.integration_metrics["successful_predictions"] += 1
                    return enhanced_result
            
            # Return orchestrator result even if confidence is medium
            self.integration_metrics["successful_predictions"] += 1
            return orchestrator_result
            
        except Exception as e:
            logger.error(f"❌ Enhanced prediction failed: {e}")
            self.integration_metrics["failed_predictions"] += 1
            
            # Try AGUS fallback if available
            if self.agus_system:
                try:
                    agus_result = await self._agus_fallback(symbol, analysis_type, context)
                    self.integration_metrics["agus_fallbacks"] += 1
                    return agus_result
                except Exception as agus_error:
                    logger.error(f"❌ AGUS fallback also failed: {agus_error}")
            
            # Return empty prediction as last resort
            return EnsemblePrediction(
                prediction_value=0.0,
                confidence_score=0.0,
                consensus_strength=0.0,
                disagreement_score=1.0,
                models_used=[],
                model_weights={},
                individual_predictions={},
                execution_time=0.0,
                reasoning="All prediction methods failed",
                uncertainty_bounds=(0.0, 0.0)
            )
    
    async def _get_agus_enhancement(
        self, 
        symbol: str, 
        analysis_type: str, 
        orchestrator_result: EnsemblePrediction,
        context: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Get enhancement from AGUS system"""
        try:
            query = f"Enhance analysis for {symbol}: {analysis_type}. Current prediction: {orchestrator_result.prediction_value}, confidence: {orchestrator_result.confidence_score:.2f}"
            
            agus_response = await self.agus_system.process_query(
                query=query,
                user_id="orchestrator",
                query_type="trading_enhancement",
                complexity=QueryComplexity.COMPLEX,
                context=context
            )
            
            if agus_response and agus_response.success:
                return {
                    "prediction": agus_response.content.get("prediction", 0.0),
                    "confidence": agus_response.confidence,
                    "reasoning": agus_response.content.get("reasoning", "AGUS enhancement"),
                    "metadata": agus_response.metadata
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"AGUS enhancement error: {e}")
            return None
    
    def _combine_predictions(
        self, 
        orchestrator_result: EnsemblePrediction, 
        agus_result: Dict[str, Any]
    ) -> EnsemblePrediction:
        """Combine orchestrator and AGUS predictions intelligently"""
        
        # Weight based on original confidence
        orchestrator_weight = orchestrator_result.confidence_score
        agus_weight = agus_result.get("confidence", 0.5)
        
        total_weight = orchestrator_weight + agus_weight
        
        if total_weight > 0:
            # Weighted average of predictions
            combined_prediction = (
                orchestrator_result.prediction_value * orchestrator_weight +
                agus_result.get("prediction", 0.0) * agus_weight
            ) / total_weight
            
            # Combined confidence (not just average, but enhanced)
            combined_confidence = min(0.95, (orchestrator_weight + agus_weight) / 2 * 1.2)
        else:
            combined_prediction = orchestrator_result.prediction_value
            combined_confidence = 0.3
        
        # Enhanced reasoning
        combined_reasoning = f"Orchestrator: {orchestrator_result.reasoning} | AGUS Enhancement: {agus_result.get('reasoning', 'N/A')}"
        
        # Create enhanced result
        enhanced_result = EnsemblePrediction(
            prediction_value=combined_prediction,
            confidence_score=combined_confidence,
            consensus_strength=orchestrator_result.consensus_strength,
            disagreement_score=max(0.0, orchestrator_result.disagreement_score - 0.1),  # Reduce disagreement
            models_used=orchestrator_result.models_used + ["agus_enhancement"],
            model_weights=orchestrator_result.model_weights,
            individual_predictions=orchestrator_result.individual_predictions,
            execution_time=orchestrator_result.execution_time,
            reasoning=combined_reasoning,
            uncertainty_bounds=orchestrator_result.uncertainty_bounds,
            metadata={
                **orchestrator_result.metadata,
                "agus_enhanced": True,
                "agus_confidence": agus_weight
            }
        )
        
        return enhanced_result
    
    async def _agus_fallback(
        self, 
        symbol: str, 
        analysis_type: str, 
        context: Optional[Dict[str, Any]]
    ) -> EnsemblePrediction:
        """Complete fallback to AGUS system"""
        query = f"Complete trading analysis for {symbol}: {analysis_type}"
        
        agus_response = await self.agus_system.process_query(
            query=query,
            user_id="orchestrator_fallback",
            query_type="trading",
            complexity=QueryComplexity.COMPLEX,
            context=context
        )
        
        if agus_response and agus_response.success:
            return EnsemblePrediction(
                prediction_value=agus_response.content.get("prediction", 0.0),
                confidence_score=agus_response.confidence,
                consensus_strength=0.5,  # Single model, moderate consensus
                disagreement_score=0.0,  # Single model, no disagreement
                models_used=["agus_fallback"],
                model_weights={"agus_fallback": 1.0},
                individual_predictions={},
                execution_time=agus_response.processing_time,
                reasoning=f"AGUS fallback: {agus_response.content.get('reasoning', 'AGUS analysis')}",
                uncertainty_bounds=(0.0, 0.0),
                metadata={"fallback_mode": True, "agus_response": agus_response.metadata}
            )
        else:
            # Last resort empty prediction
            return EnsemblePrediction(
                prediction_value=0.0,
                confidence_score=0.0,
                consensus_strength=0.0,
                disagreement_score=1.0,
                models_used=[],
                model_weights={},
                individual_predictions={},
                execution_time=0.0,
                reasoning="AGUS fallback failed",
                uncertainty_bounds=(0.0, 0.0),
                metadata={"complete_failure": True}
            )

class TradingIntegrationLayer:
    """
    📈 Integration layer for trading bot components
    """
    
    def __init__(self, orchestrator: MultiModelOrchestrator):
        self.orchestrator = orchestrator
        self.trading_predictions = {}
        self.prediction_history = []
        
        # Trading component references
        self.strategy = None
        self.data_provider = None
        self.risk_manager = None
        self.execution_manager = None
        
    def initialize_trading_components(self) -> None:
        """Initialize trading system components if available"""
        try:
            if TradingStrategy:
                self.strategy = TradingStrategy()
                logger.info("✅ Trading strategy component initialized")
            
            if DataProvider:
                self.data_provider = DataProvider()
                logger.info("✅ Data provider component initialized")
            
            if RiskManager:
                self.risk_manager = RiskManager()
                logger.info("✅ Risk manager component initialized")
            
            if ExecutionManager:
                self.execution_manager = ExecutionManager()
                logger.info("✅ Execution manager component initialized")
                
        except Exception as e:
            logger.warning(f"⚠️ Trading components initialization error: {e}")
    
    async def get_trading_prediction(
        self, 
        symbol: str, 
        analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """Get comprehensive trading prediction with risk assessment"""
        
        try:
            # Gather market context
            context = await self._gather_market_context(symbol)
            
            # Get orchestrator prediction
            prediction = await orchestrate_trading_analysis(
                symbol=symbol,
                analysis_type=analysis_type,
                context=context
            )
            
            # Enhance with trading-specific analysis
            trading_analysis = await self._enhance_with_trading_analysis(
                symbol, prediction, context
            )
            
            # Store prediction
            self.trading_predictions[symbol] = {
                "prediction": prediction,
                "trading_analysis": trading_analysis,
                "timestamp": datetime.now(),
                "context": context
            }
            
            # Add to history
            self.prediction_history.append({
                "symbol": symbol,
                "prediction": prediction.prediction_value,
                "confidence": prediction.confidence_score,
                "timestamp": datetime.now()
            })
            
            # Keep only last 1000 predictions
            if len(self.prediction_history) > 1000:
                self.prediction_history = self.prediction_history[-1000:]
            
            return {
                "symbol": symbol,
                "prediction": prediction.prediction_value,
                "confidence": prediction.confidence_score,
                "consensus": prediction.consensus_strength,
                "models_used": prediction.models_used,
                "trading_signal": trading_analysis.get("signal", "HOLD"),
                "risk_score": trading_analysis.get("risk_score", 0.5),
                "position_size": trading_analysis.get("position_size", 0.0),
                "stop_loss": trading_analysis.get("stop_loss", 0.0),
                "take_profit": trading_analysis.get("take_profit", 0.0),
                "reasoning": prediction.reasoning
            }
            
        except Exception as e:
            logger.error(f"❌ Trading prediction failed for {symbol}: {e}")
            return {
                "symbol": symbol,
                "prediction": 0.0,
                "confidence": 0.0,
                "error": str(e)
            }
    
    async def _gather_market_context(self, symbol: str) -> Dict[str, Any]:
        """Gather comprehensive market context for prediction"""
        context = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Add market data if data provider is available
            if self.data_provider:
                market_data = await self._get_market_data(symbol)
                context["market_data"] = market_data
            
            # Add risk context if risk manager is available
            if self.risk_manager:
                risk_data = await self._get_risk_context(symbol)
                context["risk_data"] = risk_data
            
            # Add general market conditions
            context["market_conditions"] = await self._assess_market_conditions()
            
        except Exception as e:
            logger.debug(f"Context gathering error: {e}")
        
        return context
    
    async def _get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get market data for symbol"""
        try:
            # This would integrate with actual data provider
            return {
                "price": 0.0,
                "volume": 0.0,
                "volatility": 0.0,
                "trend": "NEUTRAL"
            }
        except Exception:
            return {}
    
    async def _get_risk_context(self, symbol: str) -> Dict[str, Any]:
        """Get risk context for symbol"""
        try:
            # This would integrate with actual risk manager
            return {
                "portfolio_exposure": 0.0,
                "var": 0.0,
                "correlation": 0.0
            }
        except Exception:
            return {}
    
    async def _assess_market_conditions(self) -> Dict[str, Any]:
        """Assess general market conditions"""
        return {
            "volatility_regime": "NORMAL",
            "trend_strength": "MODERATE", 
            "market_sentiment": "NEUTRAL"
        }
    
    async def _enhance_with_trading_analysis(
        self, 
        symbol: str, 
        prediction: EnsemblePrediction, 
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Enhance prediction with trading-specific analysis"""
        
        analysis = {
            "signal": "HOLD",
            "risk_score": 0.5,
            "position_size": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0
        }
        
        try:
            # Determine trading signal based on prediction and confidence
            if prediction.confidence_score > 0.7:
                if prediction.prediction_value > 0.1:
                    analysis["signal"] = "BUY"
                elif prediction.prediction_value < -0.1:
                    analysis["signal"] = "SELL"
                else:
                    analysis["signal"] = "HOLD"
            else:
                analysis["signal"] = "HOLD"  # Low confidence = no action
            
            # Calculate risk score
            analysis["risk_score"] = 1.0 - prediction.confidence_score
            
            # Calculate position size based on confidence and risk
            if analysis["signal"] in ["BUY", "SELL"]:
                base_size = 0.02  # 2% base position
                confidence_multiplier = prediction.confidence_score
                consensus_multiplier = prediction.consensus_strength
                
                analysis["position_size"] = base_size * confidence_multiplier * consensus_multiplier
            
            # Set stop loss and take profit
            if analysis["signal"] != "HOLD":
                price_target = abs(prediction.prediction_value)
                analysis["stop_loss"] = price_target * 0.5  # 50% of target as stop loss
                analysis["take_profit"] = price_target * 2.0  # 200% of target as take profit
            
        except Exception as e:
            logger.debug(f"Trading analysis enhancement error: {e}")
        
        return analysis

class OrchestratorIntegrationManager:
    """
    🎭 MAIN INTEGRATION MANAGER
    Coordinates all orchestrator integrations
    """
    
    def __init__(self, config: Optional[IntegrationConfig] = None):
        self.config = config or IntegrationConfig()
        self.orchestrator = get_orchestrator()
        
        # Integration components
        self.localai_manager = None
        self.agus_bridge = None
        self.trading_layer = None
        
        # Monitoring
        self.integration_status = {
            "orchestrator": False,
            "localai": False,
            "agus": False,
            "trading": False
        }
        
        # Performance tracking
        self.integration_metrics = {
            "total_predictions": 0,
            "successful_integrations": 0,
            "failed_integrations": 0,
            "avg_response_time": 0.0
        }
        
        self.initialized = False
    
    async def initialize_all_integrations(self):
        """Initialize all integration components"""
        logger.info("🚀 Initializing orchestrator integrations...")
        
        try:
            # 1. Initialize core orchestrator
            await self._initialize_orchestrator()
            
            # 2. Initialize LocalAI integration
            if self.config.enable_localai_models:
                await self._initialize_localai_integration()
            
            # 3. Initialize AGUS integration
            if self.config.enable_agus_integration:
                await self._initialize_agus_integration()
            
            # 4. Initialize trading integration
            if self.config.enable_trading_integration:
                await self._initialize_trading_integration()
            
            # 5. Register integrated models
            await self._register_integrated_models()
            
            # 6. Start monitoring
            await self._start_integration_monitoring()
            
            self.initialized = True
            logger.info("✅ All orchestrator integrations initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Integration initialization failed: {e}")
            raise
    
    async def _initialize_orchestrator(self):
        """Initialize core orchestrator"""
        try:
            # Orchestrator is already initialized via get_orchestrator()
            self.integration_status["orchestrator"] = True
            logger.info("✅ Core orchestrator initialized")
        except Exception as e:
            logger.error(f"❌ Orchestrator initialization failed: {e}")
            raise
    
    async def _initialize_localai_integration(self):
        """Initialize LocalAI integration"""
        try:
            self.localai_manager = LocalAIInstitutionalManager()
            
            # Install and configure LocalAI models if not already done
            installation_success = await self.localai_manager.install_and_configure_all()
            
            if installation_success:
                self.integration_status["localai"] = True
                logger.info("✅ LocalAI integration initialized")
            else:
                logger.warning("⚠️ LocalAI integration partially initialized")
                
        except Exception as e:
            logger.warning(f"⚠️ LocalAI integration failed: {e}")
            self.integration_status["localai"] = False
    
    async def _initialize_agus_integration(self):
        """Initialize AGUS integration"""
        try:
            # Initialize AGUS system if available
            agus_system = AGUS2HybridSystem() if 'AGUS2HybridSystem' in globals() else None
            
            if agus_system:
                await agus_system.initialize()
                self.agus_bridge = AGUSIntegrationBridge(agus_system)
                self.integration_status["agus"] = True
                logger.info("✅ AGUS integration initialized")
            else:
                logger.warning("⚠️ AGUS system not available")
                self.integration_status["agus"] = False
                
        except Exception as e:
            logger.warning(f"⚠️ AGUS integration failed: {e}")
            self.integration_status["agus"] = False
    
    async def _initialize_trading_integration(self):
        """Initialize trading system integration"""
        try:
            self.trading_layer = TradingIntegrationLayer(self.orchestrator)
            self.trading_layer.initialize_trading_components()
            self.integration_status["trading"] = True
            logger.info("✅ Trading integration initialized")
        except Exception as e:
            logger.warning(f"⚠️ Trading integration failed: {e}")
            self.integration_status["trading"] = False
    
    async def _register_integrated_models(self):
        """Register integrated models with orchestrator"""
        try:
            model_count = 0
            
            # Register LocalAI models if available
            if self.localai_manager and self.integration_status["localai"]:
                for model_name, model_config in self.localai_manager.models.items():
                    try:
                        # Create wrapper for LocalAI model
                        model_wrapper = LocalAIModelWrapper(
                            model_instance=None,  # Would be actual model instance
                            model_name=model_name,
                            model_role=self._map_use_case_to_role(model_config.use_case)
                        )
                        
                        # Register with orchestrator
                        self.orchestrator.register_model(
                            model_name=model_name,
                            model_instance=model_wrapper,
                            role=self._map_use_case_to_role(model_config.use_case),
                            capabilities=[model_config.use_case]
                        )
                        
                        model_count += 1
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to register model {model_name}: {e}")
            
            logger.info(f"✅ Registered {model_count} integrated models")
            
        except Exception as e:
            logger.error(f"❌ Model registration failed: {e}")
    
    def _map_use_case_to_role(self, use_case: str) -> ModelRole:
        """Map LocalAI use case to orchestrator role"""
        mapping = {
            "sentiment": ModelRole.SENTIMENT_ANALYZER,
            "prediction": ModelRole.TECHNICAL_PREDICTOR,
            "risk": ModelRole.RISK_ASSESSOR,
            "news": ModelRole.NEWS_ANALYZER,
            "analysis": ModelRole.MARKET_SCANNER
        }
        return mapping.get(use_case, ModelRole.MARKET_SCANNER)
    
    async def _start_integration_monitoring(self):
        """Start integration health monitoring"""
        try:
            # Start monitoring thread
            monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            monitoring_thread.start()
            logger.info("✅ Integration monitoring started")
        except Exception as e:
            logger.warning(f"⚠️ Monitoring start failed: {e}")
    
    def _monitoring_loop(self) -> None:
        """Continuous monitoring loop"""
        while True:
            try:
                time.sleep(self.config.health_check_interval)
                
                # Perform health checks
                self._perform_health_checks()
                
                # Log status
                active_integrations = sum(self.integration_status.values())
                logger.debug(f"🔍 Integration health: {active_integrations}/4 components active")
                
            except Exception as e:
                logger.debug(f"Monitoring error: {e}")
    
    def _perform_health_checks(self) -> None:
        """Perform health checks on all integrations"""
        try:
            # Check orchestrator
            status = self.orchestrator.get_orchestrator_status()
            self.integration_status["orchestrator"] = status.get("active_models", 0) > 0
            
            # Check LocalAI
            if self.localai_manager:
                # Would perform actual health check
                pass
            
            # Check AGUS
            if self.agus_bridge:
                # Would perform actual health check  
                pass
            
            # Check trading layer
            if self.trading_layer:
                # Would perform actual health check
                pass
                
        except Exception as e:
            logger.debug(f"Health check error: {e}")
    
    async def get_comprehensive_prediction(
        self, 
        symbol: str, 
        analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """Get comprehensive prediction using all available integrations"""
        
        if not self.initialized:
            raise RuntimeError("Integration manager not initialized")
        
        start_time = time.time()
        self.integration_metrics["total_predictions"] += 1
        
        try:
            # Use AGUS bridge if available for enhanced predictions
            if self.agus_bridge:
                prediction = await self.agus_bridge.enhanced_prediction(
                    symbol=symbol,
                    analysis_type=analysis_type
                )
            else:
                # Fallback to direct orchestrator
                prediction = await orchestrate_trading_analysis(
                    symbol=symbol,
                    analysis_type=analysis_type
                )
            
            # Enhance with trading analysis if available
            if self.trading_layer:
                trading_prediction = await self.trading_layer.get_trading_prediction(
                    symbol=symbol,
                    analysis_type=analysis_type
                )
                
                # Combine results
                comprehensive_result = {
                    **trading_prediction,
                    "orchestrator_prediction": prediction.prediction_value,
                    "orchestrator_confidence": prediction.confidence_score,
                    "consensus_strength": prediction.consensus_strength,
                    "disagreement_score": prediction.disagreement_score,
                    "models_used": prediction.models_used,
                    "execution_time": time.time() - start_time,
                    "integration_status": self.integration_status
                }
            else:
                # Basic prediction without trading enhancement
                comprehensive_result = {
                    "symbol": symbol,
                    "prediction": prediction.prediction_value,
                    "confidence": prediction.confidence_score,
                    "consensus": prediction.consensus_strength,
                    "disagreement": prediction.disagreement_score,
                    "models_used": prediction.models_used,
                    "reasoning": prediction.reasoning,
                    "execution_time": time.time() - start_time,
                    "integration_status": self.integration_status
                }
            
            self.integration_metrics["successful_integrations"] += 1
            
            # Update average response time
            total_predictions = self.integration_metrics["total_predictions"]
            current_avg = self.integration_metrics["avg_response_time"]
            new_time = time.time() - start_time
            
            self.integration_metrics["avg_response_time"] = (
                (current_avg * (total_predictions - 1) + new_time) / total_predictions
            )
            
            return comprehensive_result
            
        except Exception as e:
            logger.error(f"❌ Comprehensive prediction failed for {symbol}: {e}")
            self.integration_metrics["failed_integrations"] += 1
            
            return {
                "symbol": symbol,
                "error": str(e),
                "integration_status": self.integration_status,
                "execution_time": time.time() - start_time
            }
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get comprehensive integration status"""
        orchestrator_status = self.orchestrator.get_orchestrator_status()
        
        return {
            "integrations": self.integration_status,
            "metrics": self.integration_metrics,
            "orchestrator": orchestrator_status,
            "initialized": self.initialized,
            "config": {
                "localai_enabled": self.config.enable_localai_models,
                "agus_enabled": self.config.enable_agus_integration,
                "trading_enabled": self.config.enable_trading_integration
            }
        }

# Global integration manager
_integration_manager = None

def get_integration_manager() -> OrchestratorIntegrationManager:
    """Get global integration manager instance"""
    global _integration_manager
    if _integration_manager is None:
        _integration_manager = OrchestratorIntegrationManager()
    return _integration_manager

# High-level convenience functions
async def get_trading_prediction(symbol: str, analysis_type: str = "comprehensive") -> Dict[str, Any]:
    """High-level function to get comprehensive trading prediction"""
    manager = get_integration_manager()
    
    if not manager.initialized:
        await manager.initialize_all_integrations()
    
    return await manager.get_comprehensive_prediction(symbol, analysis_type)

async def initialize_complete_system():
    """Initialize the complete integrated system"""
    logger.info("🚀 Initializing complete orchestrator integration system...")
    
    manager = get_integration_manager()
    await manager.initialize_all_integrations()
    
    status = manager.get_integration_status()
    logger.info(f"✅ System initialized: {status}")
    
    return manager

if __name__ == "__main__":
    async def test_integration():
        """Test the complete integration system"""
        logger.info("🧪 Testing orchestrator integration system...")
        
        try:
            # Initialize system
            manager = await initialize_complete_system()
            
            # Test prediction
            result = await get_trading_prediction("BTC/USD", "comprehensive")
            
            print("\n🎭 INTEGRATION TEST RESULTS:")
            print(json.dumps(result, indent=2, default=str))
            
            # Test status
            status = manager.get_integration_status()
            print(f"\n📊 INTEGRATION STATUS:")
            print(json.dumps(status, indent=2, default=str))
            
            logger.info("✅ Integration testing completed")
            
        except Exception as e:
            logger.error(f"❌ Integration testing failed: {e}")
    
    asyncio.run(test_integration())