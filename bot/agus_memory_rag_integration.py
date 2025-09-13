#!/usr/bin/env python3
"""
🔗 AGUS 2.0 + ADVANCED MEMORY RAG INTEGRATION
Seamless integration layer between AGUS 2.0 Hybrid System and Advanced Memory RAG
- Enhanced AI responses with trading knowledge context
- Automatic knowledge capture from all trading decisions  
- RAG-powered intelligent routing and response generation
- Trading memory persistence and retrieval
- Context-aware query enhancement
"""
import os
import json
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from loguru import logger
import threading
from pathlib import Path

# Import AGUS 2.0 components
try:
    from .agus_2_hybrid_system import (
        AGUS2HybridSystem, AIProvider, QueryContext, AIResponse, 
        ContextualMemoryManager, QueryComplexity, ReasoningMode,
        IntelligentRoutingEngine, AdvancedReasoningEngine
    )
    AGUS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AGUS 2.0 not available: {e}")
    AGUS_AVAILABLE = False

# Import Advanced Memory RAG components  
try:
    from .advanced_memory_rag_system import (
        AdvancedMemoryRAGSystem, VectorKnowledgeBase, PersonalizedRAGEngine,
        ContinualLearningSystem, KnowledgeType, QueryType, RAGResponse
    )
    RAG_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Advanced Memory RAG not available: {e}")
    RAG_AVAILABLE = False

class IntegrationType(Enum):
    """Types of integration between AGUS and RAG systems"""
    KNOWLEDGE_ENHANCED = "knowledge_enhanced"    # RAG enhances AGUS responses
    DUAL_RESPONSE = "dual_response"             # Both systems respond
    RAG_FALLBACK = "rag_fallback"               # RAG as fallback for AGUS
    AGUS_FALLBACK = "agus_fallback"             # AGUS as fallback for RAG
    HYBRID_FUSION = "hybrid_fusion"             # Deep integration and fusion

class ResponseMode(Enum):
    """Response generation modes"""
    RAG_PRIMARY = "rag_primary"                 # RAG generates primary response
    AGUS_PRIMARY = "agus_primary"               # AGUS generates primary response  
    FUSION = "fusion"                           # Combine both responses
    CONTEXT_INJECTED = "context_injected"       # Inject RAG context into AGUS
    SELECTIVE = "selective"                     # Choose best system per query

@dataclass
class IntegratedResponse:
    """Combined response from both systems"""
    primary_content: str
    rag_content: Optional[str] = None
    agus_content: Optional[str] = None
    knowledge_context: List[Any] = None
    confidence: float = 0.0
    reasoning_steps: List[str] = None
    sources: List[str] = None
    recommendations: List[str] = None
    integration_type: IntegrationType = IntegrationType.KNOWLEDGE_ENHANCED
    response_mode: ResponseMode = ResponseMode.CONTEXT_INJECTED
    response_time: float = 0.0
    metadata: Dict[str, Any] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.knowledge_context is None:
            self.knowledge_context = []
        if self.reasoning_steps is None:
            self.reasoning_steps = []
        if self.sources is None:
            self.sources = []
        if self.recommendations is None:
            self.recommendations = []
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()

class AGUSMemoryRAGIntegration:
    """
    🎭 AGUS 2.0 + Advanced Memory RAG Integration Engine
    Seamless integration of hybrid AI with trading knowledge
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        
        # Initialize systems if available
        self.agus_system = None
        self.rag_system = None
        
        if AGUS_AVAILABLE:
            try:
                self.agus_system = AGUS2HybridSystem()
                logger.info("✅ AGUS 2.0 System initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize AGUS 2.0: {e}")
        
        if RAG_AVAILABLE:
            try:
                self.rag_system = AdvancedMemoryRAGSystem()
                self.rag_system.initialize_with_base_knowledge()
                logger.info("✅ Advanced Memory RAG System initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize RAG System: {e}")
        
        # Integration configuration
        self.integration_config = {
            "default_integration_type": IntegrationType.KNOWLEDGE_ENHANCED,
            "default_response_mode": ResponseMode.CONTEXT_INJECTED,
            "knowledge_threshold": 0.3,  # Minimum similarity for knowledge injection
            "max_knowledge_entries": 5,   # Max knowledge entries to inject
            "response_timeout": 30.0,     # Maximum response time
            "enable_learning": True,      # Enable automatic learning from responses
            "context_enhancement": True,  # Enable context enhancement
            "citation_generation": True,  # Generate citations from knowledge
        }
        
        # Performance tracking
        self.integration_stats = {
            "total_queries": 0,
            "knowledge_enhanced_responses": 0,
            "rag_fallbacks": 0,
            "agus_fallbacks": 0,
            "fusion_responses": 0,
            "avg_response_time": 0.0,
            "knowledge_injection_rate": 0.0,
        }
        
        # Query routing logic
        self.query_router = self._initialize_query_router()
        
        # Response fusion engine
        self.fusion_engine = ResponseFusionEngine()
        
        logger.info("🔗 AGUS-RAG Integration initialized successfully")
    
    def _initialize_query_router(self) -> Dict[str, Any]:
        """Initialize intelligent query routing"""
        return {
            "trading_keywords": [
                "strategy", "trade", "position", "risk", "market", "analysis",
                "volatility", "correlation", "sentiment", "pattern", "signal"
            ],
            "knowledge_keywords": [
                "remember", "what", "how", "why", "explain", "analyze", 
                "compare", "recommend", "suggest", "history", "pattern"
            ],
            "routing_rules": {
                QueryComplexity.TRIVIAL: ResponseMode.RAG_PRIMARY,
                QueryComplexity.SIMPLE: ResponseMode.CONTEXT_INJECTED,
                QueryComplexity.MODERATE: ResponseMode.FUSION,
                QueryComplexity.COMPLEX: ResponseMode.FUSION,
                QueryComplexity.CRITICAL: ResponseMode.FUSION,
            }
        }
    
    async def process_query(self, query: str, user_id: str = "default",
                           session_id: str = "default", 
                           context: Dict[str, Any] = None,
                           integration_type: Optional[IntegrationType] = None,
                           response_mode: Optional[ResponseMode] = None) -> IntegratedResponse:
        """
        Main entry point for processing queries with integrated intelligence
        """
        start_time = time.time()
        self.integration_stats["total_queries"] += 1
        
        try:
            # Determine integration approach
            int_type = integration_type or self.integration_config["default_integration_type"]
            resp_mode = response_mode or self._route_response_mode(query, context)
            
            # Prepare context
            enhanced_context = await self._enhance_query_context(query, user_id, context)
            
            # Generate integrated response based on mode
            if resp_mode == ResponseMode.RAG_PRIMARY:
                response = await self._rag_primary_response(query, enhanced_context)
            elif resp_mode == ResponseMode.AGUS_PRIMARY:
                response = await self._agus_primary_response(query, enhanced_context)
            elif resp_mode == ResponseMode.FUSION:
                response = await self._fusion_response(query, enhanced_context)
            elif resp_mode == ResponseMode.CONTEXT_INJECTED:
                response = await self._context_injected_response(query, enhanced_context)
            else:  # SELECTIVE
                response = await self._selective_response(query, enhanced_context)
            
            response.response_time = time.time() - start_time
            response.integration_type = int_type
            response.response_mode = resp_mode
            
            # Update statistics
            self._update_stats(response)
            
            # Optional: Learn from this interaction
            if self.integration_config["enable_learning"]:
                await self._learn_from_interaction(query, response, enhanced_context)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error processing integrated query: {e}")
            return self._create_fallback_response(query, start_time)
    
    def _route_response_mode(self, query: str, context: Dict[str, Any] = None) -> ResponseMode:
        """Intelligently route query to appropriate response mode"""
        query_lower = query.lower()
        context = context or {}
        
        # Check if query has trading-specific terms
        trading_score = sum(1 for keyword in self.query_router["trading_keywords"] 
                           if keyword in query_lower)
        
        # Check if query asks for knowledge/memory
        knowledge_score = sum(1 for keyword in self.query_router["knowledge_keywords"] 
                             if keyword in query_lower)
        
        # Determine complexity
        query_complexity = self._estimate_query_complexity(query)
        
        # Apply routing rules
        if knowledge_score > trading_score and self.rag_system:
            return ResponseMode.RAG_PRIMARY
        elif trading_score > 3 and query_complexity >= QueryComplexity.MODERATE:
            return ResponseMode.FUSION
        elif query_complexity in self.query_router["routing_rules"]:
            return self.query_router["routing_rules"][query_complexity]
        else:
            return ResponseMode.CONTEXT_INJECTED
    
    def _estimate_query_complexity(self, query: str) -> QueryComplexity:
        """Estimate query complexity for routing"""
        query_lower = query.lower()
        word_count = len(query.split())
        
        # Complexity indicators
        complex_words = ["analyze", "compare", "optimize", "predict", "strategy", "risk"]
        critical_words = ["emergency", "critical", "urgent", "fix", "error", "problem"]
        
        complex_score = sum(1 for word in complex_words if word in query_lower)
        critical_score = sum(1 for word in critical_words if word in query_lower)
        
        if critical_score > 0:
            return QueryComplexity.CRITICAL
        elif complex_score > 2 or word_count > 50:
            return QueryComplexity.COMPLEX
        elif complex_score > 1 or word_count > 20:
            return QueryComplexity.MODERATE
        elif word_count > 10:
            return QueryComplexity.SIMPLE
        else:
            return QueryComplexity.TRIVIAL
    
    async def _enhance_query_context(self, query: str, user_id: str, 
                                   context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Enhance query context with trading and user information"""
        enhanced = context.copy() if context else {}
        
        # Add user context from AGUS system
        if self.agus_system and hasattr(self.agus_system, 'memory_manager'):
            try:
                user_prefs = self.agus_system.memory_manager.extract_user_preferences(user_id)
                enhanced["user_preferences"] = user_prefs
            except Exception as e:
                logger.debug(f"Could not get user preferences: {e}")
        
        # Add relevant trading knowledge
        if self.rag_system and self.integration_config["context_enhancement"]:
            try:
                rag_response = self.rag_system.query_trading_intelligence(
                    query=query,
                    query_type=self._map_to_query_type(query),
                    user_context=enhanced.get("user_preferences", {}),
                    trading_context=enhanced.get("trading_context", {})
                )
                
                enhanced["relevant_knowledge"] = {
                    "entries": [asdict(entry) for entry in rag_response.knowledge_context[:3]],
                    "insights": rag_response.generated_insights,
                    "confidence": rag_response.confidence
                }
            except Exception as e:
                logger.debug(f"Could not enhance with RAG context: {e}")
        
        # Add system status
        enhanced["system_status"] = {
            "agus_available": self.agus_system is not None,
            "rag_available": self.rag_system is not None,
            "timestamp": datetime.now().isoformat()
        }
        
        return enhanced
    
    def _map_to_query_type(self, query: str) -> QueryType:
        """Map natural language query to QueryType"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["strategy", "recommend", "suggest"]):
            return QueryType.STRATEGY_RECOMMENDATION
        elif any(word in query_lower for word in ["market", "analysis", "condition"]):
            return QueryType.MARKET_CONTEXT
        elif any(word in query_lower for word in ["risk", "danger", "safe"]):
            return QueryType.RISK_GUIDANCE
        elif any(word in query_lower for word in ["pattern", "similar", "like"]):
            return QueryType.PATTERN_MATCHING
        elif any(word in query_lower for word in ["decision", "should", "choose"]):
            return QueryType.DECISION_SUPPORT
        elif any(word in query_lower for word in ["performance", "result", "outcome"]):
            return QueryType.PERFORMANCE_ANALYSIS
        elif any(word in query_lower for word in ["error", "problem", "fix", "help"]):
            return QueryType.TROUBLESHOOTING
        else:
            return QueryType.GENERAL_INQUIRY
    
    async def _rag_primary_response(self, query: str, context: Dict[str, Any]) -> IntegratedResponse:
        """Generate response with RAG as primary system"""
        if not self.rag_system:
            return self._create_fallback_response(query, time.time())
        
        try:
            rag_response = self.rag_system.query_trading_intelligence(
                query=query,
                query_type=self._map_to_query_type(query),
                user_context=context.get("user_preferences", {}),
                trading_context=context.get("trading_context", {})
            )
            
            return IntegratedResponse(
                primary_content=rag_response.content,
                rag_content=rag_response.content,
                knowledge_context=rag_response.knowledge_context,
                confidence=rag_response.confidence,
                reasoning_steps=rag_response.reasoning_steps,
                sources=rag_response.citations,
                recommendations=rag_response.recommendations,
                metadata={"rag_response": asdict(rag_response)}
            )
            
        except Exception as e:
            logger.error(f"❌ Error in RAG primary response: {e}")
            return self._create_fallback_response(query, time.time())
    
    async def _agus_primary_response(self, query: str, context: Dict[str, Any]) -> IntegratedResponse:
        """Generate response with AGUS as primary system"""
        if not self.agus_system:
            return await self._rag_primary_response(query, context)
        
        try:
            # Create QueryContext for AGUS
            query_context = QueryContext(
                query=query,
                user_id=context.get("user_id", "default"),
                session_id=context.get("session_id", "default"),
                query_type="trading",
                complexity=self._estimate_query_complexity(query),
                reasoning_mode=ReasoningMode.CHAIN_OF_THOUGHT,
                priority=5,
                max_response_time=30.0,
                cost_budget=0.10,
                timestamp=datetime.now(),
                metadata=context
            )
            
            agus_response = await self.agus_system.process_query(query_context)
            
            return IntegratedResponse(
                primary_content=agus_response.content,
                agus_content=agus_response.content,
                confidence=agus_response.confidence,
                reasoning_steps=agus_response.reasoning_steps,
                metadata={
                    "agus_response": asdict(agus_response),
                    "provider": agus_response.provider.value
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Error in AGUS primary response: {e}")
            return await self._rag_primary_response(query, context)
    
    async def _fusion_response(self, query: str, context: Dict[str, Any]) -> IntegratedResponse:
        """Generate fused response from both systems"""
        try:
            # Get responses from both systems in parallel
            tasks = []
            
            if self.rag_system:
                tasks.append(self._rag_primary_response(query, context))
            
            if self.agus_system:
                tasks.append(self._agus_primary_response(query, context))
            
            if not tasks:
                return self._create_fallback_response(query, time.time())
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter successful responses
            valid_responses = [r for r in responses if isinstance(r, IntegratedResponse)]
            
            if not valid_responses:
                return self._create_fallback_response(query, time.time())
            
            # Fuse responses
            fused = await self.fusion_engine.fuse_responses(valid_responses, query, context)
            
            self.integration_stats["fusion_responses"] += 1
            return fused
            
        except Exception as e:
            logger.error(f"❌ Error in fusion response: {e}")
            return self._create_fallback_response(query, time.time())
    
    async def _context_injected_response(self, query: str, context: Dict[str, Any]) -> IntegratedResponse:
        """Generate AGUS response enhanced with RAG context"""
        try:
            # First get relevant knowledge from RAG
            knowledge_context = []
            if self.rag_system:
                try:
                    rag_response = self.rag_system.query_trading_intelligence(
                        query=query,
                        query_type=self._map_to_query_type(query),
                        user_context=context.get("user_preferences", {}),
                        trading_context=context.get("trading_context", {}),
                    )
                    
                    if rag_response.knowledge_context:
                        knowledge_context = rag_response.knowledge_context[:self.integration_config["max_knowledge_entries"]]
                        
                        # Inject knowledge into query context
                        knowledge_summary = "\n".join([
                            f"Relevant Knowledge: {entry.content[:200]}..."
                            for entry in knowledge_context
                        ])
                        
                        enhanced_query = f"{query}\n\nRelevant Context:\n{knowledge_summary}"
                        
                        # Update context
                        context["knowledge_injected"] = True
                        context["knowledge_entries"] = len(knowledge_context)
                        
                        query = enhanced_query
                        
                        self.integration_stats["knowledge_enhanced_responses"] += 1
                
                except Exception as e:
                    logger.debug(f"Knowledge injection failed: {e}")
            
            # Now get AGUS response with enhanced context
            agus_response = await self._agus_primary_response(query, context)
            
            # Enhance the response with knowledge context
            agus_response.knowledge_context = knowledge_context
            if knowledge_context:
                agus_response.sources.extend([
                    f"Knowledge: {entry.knowledge_type.value} (confidence: {entry.confidence:.2f})"
                    for entry in knowledge_context
                ])
            
            return agus_response
            
        except Exception as e:
            logger.error(f"❌ Error in context-injected response: {e}")
            return self._create_fallback_response(query, time.time())
    
    async def _selective_response(self, query: str, context: Dict[str, Any]) -> IntegratedResponse:
        """Intelligently select best system for the query"""
        query_lower = query.lower()
        
        # Knowledge-heavy queries go to RAG
        if any(word in query_lower for word in ["remember", "history", "pattern", "similar", "before"]):
            return await self._rag_primary_response(query, context)
        
        # Complex analysis goes to fusion
        elif any(word in query_lower for word in ["analyze", "compare", "strategy", "optimize"]):
            return await self._fusion_response(query, context)
        
        # Simple questions go to enhanced AGUS
        else:
            return await self._context_injected_response(query, context)
    
    async def _learn_from_interaction(self, query: str, response: IntegratedResponse, 
                                    context: Dict[str, Any]):
        """Learn from the interaction for system improvement"""
        if not self.rag_system or not self.integration_config["enable_learning"]:
            return
        
        try:
            # Extract learning signals
            decision_data = {
                "query": query,
                "response_mode": response.response_mode.value,
                "confidence": response.confidence,
                "knowledge_used": len(response.knowledge_context) if response.knowledge_context else 0,
                "response_length": len(response.primary_content),
                "sources_count": len(response.sources) if response.sources else 0,
            }
            
            # Track this as a decision for learning
            decision_id = f"integration_{int(time.time())}_{hash(query) % 10000}"
            
            self.rag_system.learn_from_decision(
                decision_id=decision_id,
                decision_type="query_response",
                context=context,
                prediction=response.primary_content[:200],
                symbol=context.get("symbol", ""),
                strategy=context.get("strategy", "integrated_response")
            )
            
        except Exception as e:
            logger.debug(f"Learning from interaction failed: {e}")
    
    def _update_stats(self, response: IntegratedResponse):
        """Update integration statistics"""
        total = self.integration_stats["total_queries"]
        
        # Update average response time
        self.integration_stats["avg_response_time"] = (
            (self.integration_stats["avg_response_time"] * (total - 1) + response.response_time) / total
        )
        
        # Update knowledge injection rate
        if response.knowledge_context:
            self.integration_stats["knowledge_injection_rate"] = (
                (self.integration_stats["knowledge_injection_rate"] * (total - 1) + 1) / total
            )
        else:
            self.integration_stats["knowledge_injection_rate"] = (
                self.integration_stats["knowledge_injection_rate"] * (total - 1) / total
            )
    
    def _create_fallback_response(self, query: str, start_time: float) -> IntegratedResponse:
        """Create fallback response when systems fail"""
        return IntegratedResponse(
            primary_content=f"I encountered an issue processing your query: '{query}'. "
                           "Please try rephrasing your question or check system availability.",
            confidence=0.1,
            reasoning_steps=["System fallback activated due to processing error"],
            response_time=time.time() - start_time,
            metadata={"fallback_reason": "system_error"}
        )
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get comprehensive integration status"""
        return {
            "systems_status": {
                "agus_available": self.agus_system is not None,
                "rag_available": self.rag_system is not None,
                "integration_active": (self.agus_system is not None) or (self.rag_system is not None)
            },
            "integration_stats": self.integration_stats,
            "configuration": self.integration_config,
            "agus_status": self.agus_system.get_system_status() if self.agus_system else None,
            "rag_status": self.rag_system.get_system_status() if self.rag_system else None
        }

class ResponseFusionEngine:
    """
    🔀 Response Fusion Engine
    Intelligently combines responses from multiple AI systems
    """
    
    def __init__(self):
        self.fusion_strategies = {
            "confidence_weighted": self._confidence_weighted_fusion,
            "knowledge_prioritized": self._knowledge_prioritized_fusion,
            "length_balanced": self._length_balanced_fusion,
            "source_diverse": self._source_diverse_fusion,
        }
        
        self.default_strategy = "knowledge_prioritized"
    
    async def fuse_responses(self, responses: List[IntegratedResponse], 
                           query: str, context: Dict[str, Any]) -> IntegratedResponse:
        """Fuse multiple responses into a single comprehensive response"""
        if not responses:
            return IntegratedResponse(primary_content="No responses available for fusion")
        
        if len(responses) == 1:
            return responses[0]
        
        try:
            # Choose fusion strategy based on responses
            strategy = self._choose_fusion_strategy(responses, query, context)
            
            # Apply fusion strategy
            fused = await self.fusion_strategies[strategy](responses, query, context)
            
            # Enhance fused response
            fused = self._enhance_fused_response(fused, responses)
            
            return fused
            
        except Exception as e:
            logger.error(f"❌ Error fusing responses: {e}")
            # Return best single response as fallback
            return max(responses, key=lambda r: r.confidence)
    
    def _choose_fusion_strategy(self, responses: List[IntegratedResponse], 
                               query: str, context: Dict[str, Any]) -> str:
        """Choose the best fusion strategy for the given responses"""
        # If one response has significantly more knowledge context, prioritize it
        knowledge_counts = [len(r.knowledge_context) if r.knowledge_context else 0 
                           for r in responses]
        
        if max(knowledge_counts) > 2 * (sum(knowledge_counts) / len(knowledge_counts)):
            return "knowledge_prioritized"
        
        # If confidence varies significantly, use confidence weighting
        confidences = [r.confidence for r in responses]
        if max(confidences) - min(confidences) > 0.3:
            return "confidence_weighted"
        
        # If responses have very different lengths, balance them
        lengths = [len(r.primary_content) for r in responses]
        if max(lengths) > 2 * min(lengths):
            return "length_balanced"
        
        # Default to knowledge prioritized
        return self.default_strategy
    
    async def _confidence_weighted_fusion(self, responses: List[IntegratedResponse], 
                                        query: str, context: Dict[str, Any]) -> IntegratedResponse:
        """Fuse responses weighted by confidence scores"""
        # Sort by confidence
        sorted_responses = sorted(responses, key=lambda r: r.confidence, reverse=True)
        
        primary = sorted_responses[0]
        secondary = sorted_responses[1:] if len(sorted_responses) > 1 else []
        
        # Start with highest confidence response
        fused_content = [f"**Primary Analysis (Confidence: {primary.confidence:.1%}):**"]
        fused_content.append(primary.primary_content)
        
        # Add insights from secondary responses if they're confident enough
        for i, response in enumerate(secondary):
            if response.confidence > 0.6:  # Only include confident secondary responses
                fused_content.append(f"\n**Additional Perspective (Confidence: {response.confidence:.1%}):**")
                fused_content.append(response.primary_content[:300] + "..." 
                                   if len(response.primary_content) > 300 
                                   else response.primary_content)
        
        return IntegratedResponse(
            primary_content="\n".join(fused_content),
            confidence=primary.confidence,
            reasoning_steps=primary.reasoning_steps + [f"Fused with {len(secondary)} additional responses"],
            sources=primary.sources + [s for r in secondary for s in (r.sources or [])],
            recommendations=primary.recommendations + [r for resp in secondary for r in (resp.recommendations or [])],
            knowledge_context=primary.knowledge_context + [k for r in secondary for k in (r.knowledge_context or [])]
        )
    
    async def _knowledge_prioritized_fusion(self, responses: List[IntegratedResponse], 
                                          query: str, context: Dict[str, Any]) -> IntegratedResponse:
        """Fuse responses prioritizing those with more knowledge context"""
        # Sort by knowledge context richness
        sorted_responses = sorted(responses, 
                                key=lambda r: len(r.knowledge_context) if r.knowledge_context else 0, 
                                reverse=True)
        
        primary = sorted_responses[0]
        secondary = sorted_responses[1:]
        
        fused_content = []
        
        # Start with knowledge-rich response
        if primary.knowledge_context:
            fused_content.append(f"**Knowledge-Enhanced Analysis (Based on {len(primary.knowledge_context)} sources):**")
        else:
            fused_content.append("**Primary Analysis:**")
        
        fused_content.append(primary.primary_content)
        
        # Add complementary insights from other responses
        for response in secondary:
            if response.primary_content and response.primary_content != primary.primary_content:
                # Extract unique insights
                unique_insights = self._extract_unique_insights(
                    response.primary_content, primary.primary_content
                )
                
                if unique_insights:
                    fused_content.append("\n**Additional Insights:**")
                    fused_content.append(unique_insights)
        
        # Combine all knowledge contexts
        all_knowledge = primary.knowledge_context or []
        for response in secondary:
            if response.knowledge_context:
                all_knowledge.extend(response.knowledge_context)
        
        # Remove duplicates based on content
        unique_knowledge = []
        seen_content = set()
        for knowledge in all_knowledge:
            content_hash = hash(knowledge.content)
            if content_hash not in seen_content:
                unique_knowledge.append(knowledge)
                seen_content.add(content_hash)
        
        return IntegratedResponse(
            primary_content="\n".join(fused_content),
            confidence=max(r.confidence for r in responses),
            reasoning_steps=primary.reasoning_steps + ["Enhanced with knowledge from multiple sources"],
            sources=list(set([s for r in responses for s in (r.sources or [])])),
            recommendations=list(set([rec for r in responses for rec in (r.recommendations or [])])),
            knowledge_context=unique_knowledge[:10]  # Limit to top 10
        )
    
    async def _length_balanced_fusion(self, responses: List[IntegratedResponse], 
                                    query: str, context: Dict[str, Any]) -> IntegratedResponse:
        """Fuse responses balancing content length"""
        # Sort by content length
        sorted_responses = sorted(responses, key=lambda r: len(r.primary_content), reverse=True)
        
        target_length = sum(len(r.primary_content) for r in responses) // len(responses)
        
        fused_content = []
        current_length = 0
        
        for i, response in enumerate(sorted_responses):
            if i == 0:  # Always include the first (longest) response
                fused_content.append(f"**Comprehensive Analysis:**")
                content_to_add = response.primary_content
                if len(content_to_add) > target_length:
                    content_to_add = content_to_add[:target_length] + "..."
                fused_content.append(content_to_add)
                current_length += len(content_to_add)
            else:
                # Add complementary content from other responses
                remaining_length = target_length - current_length
                if remaining_length > 100:  # Only if we have reasonable space
                    unique_content = self._extract_unique_insights(
                        response.primary_content, fused_content[-1]
                    )
                    
                    if unique_content:
                        content_to_add = unique_content[:remaining_length]
                        fused_content.append(f"\n**Additional Perspective:**")
                        fused_content.append(content_to_add)
                        current_length += len(content_to_add)
        
        best_response = max(responses, key=lambda r: r.confidence)
        
        return IntegratedResponse(
            primary_content="\n".join(fused_content),
            confidence=best_response.confidence,
            reasoning_steps=best_response.reasoning_steps + ["Balanced fusion of multiple responses"],
            sources=[s for r in responses for s in (r.sources or [])],
            recommendations=[rec for r in responses for rec in (r.recommendations or [])],
            knowledge_context=best_response.knowledge_context
        )
    
    async def _source_diverse_fusion(self, responses: List[IntegratedResponse], 
                                   query: str, context: Dict[str, Any]) -> IntegratedResponse:
        """Fuse responses maximizing source diversity"""
        all_sources = set()
        for response in responses:
            if response.sources:
                all_sources.update(response.sources)
        
        # Prioritize responses with unique sources
        source_scores = {}
        for i, response in enumerate(responses):
            unique_sources = set(response.sources or []) - {s for j, r in enumerate(responses) 
                                                           if j != i for s in (r.sources or [])}
            source_scores[i] = len(unique_sources)
        
        # Sort by source diversity
        sorted_indices = sorted(source_scores.keys(), key=lambda i: source_scores[i], reverse=True)
        sorted_responses = [responses[i] for i in sorted_indices]
        
        return await self._confidence_weighted_fusion(sorted_responses, query, context)
    
    def _extract_unique_insights(self, content: str, reference_content: str) -> str:
        """Extract insights from content that are unique compared to reference"""
        # Simple approach: extract sentences that don't appear in reference
        content_sentences = [s.strip() for s in content.split('.') if s.strip()]
        reference_sentences = [s.strip() for s in reference_content.split('.') if s.strip()]
        
        unique_sentences = []
        for sentence in content_sentences:
            # Check if sentence is sufficiently different from reference
            is_unique = True
            for ref_sentence in reference_sentences:
                # Simple similarity check
                common_words = set(sentence.lower().split()) & set(ref_sentence.lower().split())
                if len(common_words) > len(sentence.split()) * 0.6:  # 60% word overlap
                    is_unique = False
                    break
            
            if is_unique and len(sentence) > 20:  # Minimum meaningful length
                unique_sentences.append(sentence)
        
        return '. '.join(unique_sentences[:3]) + '.' if unique_sentences else ""
    
    def _enhance_fused_response(self, fused: IntegratedResponse, 
                               original_responses: List[IntegratedResponse]) -> IntegratedResponse:
        """Enhance the fused response with metadata from originals"""
        # Aggregate metadata
        all_metadata = {}
        for response in original_responses:
            if response.metadata:
                all_metadata.update(response.metadata)
        
        # Add fusion metadata
        all_metadata["fusion_info"] = {
            "source_responses": len(original_responses),
            "fusion_timestamp": datetime.now().isoformat(),
            "confidence_range": [min(r.confidence for r in original_responses),
                               max(r.confidence for r in original_responses)]
        }
        
        fused.metadata = all_metadata
        return fused

# Example usage and testing
async def test_integration():
    """Test the AGUS-RAG integration"""
    integration = AGUSMemoryRAGIntegration()
    
    # Test queries
    test_queries = [
        "What trading strategy should I use in a high volatility market?",
        "Analyze the risk of my current portfolio allocation",
        "What patterns have led to successful trades in the past?",
        "Should I buy AAPL stock right now?",
        "Explain the correlation between crypto and tech stocks"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        
        response = await integration.process_query(
            query=query,
            context={"trading_context": {"market_regime": "volatile", "volatility": 0.35}}
        )
        
        print(f"✅ Response (Confidence: {response.confidence:.1%}):")
        print(response.primary_content[:200] + "...")
        
        if response.knowledge_context:
            print(f"📚 Knowledge Sources: {len(response.knowledge_context)}")
        
        if response.recommendations:
            print(f"💡 Recommendations: {len(response.recommendations)}")
    
    # Print integration status
    status = integration.get_integration_status()
    print(f"\n📊 Integration Stats:")
    print(f"Total Queries: {status['integration_stats']['total_queries']}")
    print(f"Knowledge Enhanced: {status['integration_stats']['knowledge_enhanced_responses']}")
    print(f"Average Response Time: {status['integration_stats']['avg_response_time']:.2f}s")

if __name__ == "__main__":
    # Run the integration test
    asyncio.run(test_integration())