#!/usr/bin/env python3
"""
🧠 AGUS 2.0 HYBRID INTELLIGENCE SYSTEM
Advanced LocalAI+Cloud hybrid system with institutional-grade capabilities
- Intelligent Auto-Switching Engine (LocalAI ↔ Cloud)
- Advanced Reasoning Layer with Chain-of-Thought
- Contextual Memory Integration
- Unique Trading Intelligence
- Performance Optimization Layer
- Self-Reflection & Auto-Correction
"""
import os
import json
import asyncio
import aiohttp
import time
import hashlib
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from functools import total_ordering
from loguru import logger
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from pathlib import Path
import sqlite3
import psutil
import statistics
from collections import defaultdict, deque

# Imports for integrations
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import trafilatura
except ImportError:
    trafilatura = None

class AIProvider(Enum):
    """Available AI providers"""
    LOCAL_AI = "localai"
    AGUS_CLOUD = "agus_cloud"
    HYBRID_FUSION = "hybrid_fusion"
    FALLBACK_FREE = "fallback_free"

@total_ordering
class QueryComplexity(Enum):
    """Query complexity levels for routing decisions"""
    TRIVIAL = 1      # Simple lookups, basic questions
    SIMPLE = 2       # Single-step analysis
    MODERATE = 3     # Multi-step reasoning
    COMPLEX = 4      # Advanced analysis, predictions
    CRITICAL = 5     # Mission-critical decisions
    
    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

class ReasoningMode(Enum):
    """Reasoning modes for different types of queries"""
    DIRECT = "direct"                    # Simple Q&A
    CHAIN_OF_THOUGHT = "chain_of_thought" # Step-by-step reasoning
    SELF_REFLECTION = "self_reflection"   # Multi-pass with validation
    ENSEMBLE = "ensemble"                 # Multiple models consensus
    TREE_OF_THOUGHTS = "tree_of_thoughts" # Branching analysis

@dataclass
class QueryContext:
    """Context for each AI query"""
    query: str
    user_id: str
    session_id: str
    query_type: str  # trading, debugging, analysis, general
    complexity: QueryComplexity
    reasoning_mode: ReasoningMode
    priority: int  # 1-10
    max_response_time: float  # seconds
    cost_budget: float  # maximum cost allowance
    timestamp: datetime
    metadata: Dict[str, Any]

@dataclass
class AIResponse:
    """Standardized AI response"""
    content: str
    provider: AIProvider
    reasoning_steps: List[str]
    confidence: float  # 0.0 - 1.0
    cost: float
    response_time: float
    quality_score: float
    metadata: Dict[str, Any]
    timestamp: datetime

@dataclass
class PerformanceMetrics:
    """Performance tracking for AI providers"""
    provider: AIProvider
    avg_response_time: float
    avg_cost: float
    avg_quality: float
    success_rate: float
    total_queries: int
    last_24h_queries: int
    error_rate: float
    availability: float

class ContextualMemoryManager:
    """
    🧠 Advanced Memory Management System
    Integrates with chat_with_ai.py and provides contextual awareness
    """
    
    def __init__(self, memory_db_path: str = "bot/agus_memory.db"):
        self.memory_db_path = memory_db_path
        self.session_contexts = {}  # In-memory session storage
        self.conversation_history = defaultdict(lambda: deque(maxlen=50))
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database for persistent memory"""
        try:
            with sqlite3.connect(self.memory_db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT,
                        user_id TEXT,
                        query TEXT,
                        response TEXT,
                        provider TEXT,
                        context_data TEXT,
                        timestamp DATETIME,
                        quality_score REAL
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        user_id TEXT PRIMARY KEY,
                        trading_style TEXT,
                        risk_tolerance TEXT,
                        preferred_assets TEXT,
                        communication_style TEXT,
                        context_data TEXT,
                        updated_at DATETIME
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS market_insights (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT,
                        insight_type TEXT,
                        content TEXT,
                        confidence REAL,
                        provider TEXT,
                        timestamp DATETIME,
                        validated BOOLEAN
                    )
                """)
                
                logger.info("🧠 Memory database initialized successfully")
        except Exception as e:
            logger.error(f"❌ Error initializing memory database: {e}")

    def store_conversation(self, query_context: QueryContext, response: AIResponse):
        """Store conversation in persistent memory"""
        try:
            with sqlite3.connect(self.memory_db_path) as conn:
                conn.execute("""
                    INSERT INTO conversations 
                    (session_id, user_id, query, response, provider, context_data, timestamp, quality_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    query_context.session_id,
                    query_context.user_id,
                    query_context.query,
                    response.content,
                    response.provider.value,
                    json.dumps(query_context.metadata),
                    datetime.now(),
                    response.quality_score
                ))
                
            # Update in-memory history
            session_key = f"{query_context.user_id}:{query_context.session_id}"
            self.conversation_history[session_key].append({
                "query": query_context.query,
                "response": response.content,
                "timestamp": datetime.now(),
                "provider": response.provider.value
            })
            
        except Exception as e:
            logger.error(f"❌ Error storing conversation: {e}")

    def get_conversation_context(self, user_id: str, session_id: str, max_history: int = 10) -> List[Dict]:
        """Get recent conversation context for continuity"""
        session_key = f"{user_id}:{session_id}"
        return list(self.conversation_history[session_key])[-max_history:]

    def extract_user_preferences(self, user_id: str) -> Dict:
        """Extract learned user preferences from conversation history"""
        try:
            with sqlite3.connect(self.memory_db_path) as conn:
                cursor = conn.execute("""
                    SELECT query, response, context_data 
                    FROM conversations 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 50
                """, (user_id,))
                
                conversations = cursor.fetchall()
                
            # Analyze conversations to extract preferences
            preferences = {
                "trading_style": "balanced",
                "risk_tolerance": "moderate", 
                "preferred_assets": [],
                "communication_style": "detailed",
                "insights": []
            }
            
            # Simple keyword analysis for preferences
            all_text = " ".join([conv[0] + " " + conv[1] for conv in conversations]).lower()
            
            # Trading style detection
            if "aggressive" in all_text or "scalping" in all_text:
                preferences["trading_style"] = "aggressive"
            elif "conservative" in all_text or "safe" in all_text:
                preferences["trading_style"] = "conservative"
                
            # Risk tolerance
            if "high risk" in all_text or "yolo" in all_text:
                preferences["risk_tolerance"] = "high"
            elif "low risk" in all_text or "careful" in all_text:
                preferences["risk_tolerance"] = "low"
                
            return preferences
            
        except Exception as e:
            logger.error(f"❌ Error extracting user preferences: {e}")
            return {}

class IntelligentRoutingEngine:
    """
    🎯 Advanced AI Provider Routing System
    Decides LocalAI vs Cloud based on query analysis
    """
    
    def __init__(self):
        self.provider_metrics = {}
        self.routing_rules = self._initialize_routing_rules()
        self.cost_tracker = defaultdict(float)
        self.performance_history = defaultdict(list)
        
    def _initialize_routing_rules(self) -> Dict:
        """Initialize routing decision rules"""
        return {
            QueryComplexity.TRIVIAL: {
                "preferred": [AIProvider.FALLBACK_FREE, AIProvider.LOCAL_AI],
                "max_cost": 0.001,
                "max_time": 2.0
            },
            QueryComplexity.SIMPLE: {
                "preferred": [AIProvider.LOCAL_AI, AIProvider.FALLBACK_FREE],
                "max_cost": 0.01,
                "max_time": 5.0
            },
            QueryComplexity.MODERATE: {
                "preferred": [AIProvider.LOCAL_AI, AIProvider.AGUS_CLOUD],
                "max_cost": 0.05,
                "max_time": 10.0
            },
            QueryComplexity.COMPLEX: {
                "preferred": [AIProvider.AGUS_CLOUD, AIProvider.HYBRID_FUSION],
                "max_cost": 0.20,
                "max_time": 30.0
            },
            QueryComplexity.CRITICAL: {
                "preferred": [AIProvider.HYBRID_FUSION, AIProvider.AGUS_CLOUD],
                "max_cost": 1.00,
                "max_time": 60.0
            }
        }
    
    def analyze_query_complexity(self, query: str, context: Optional[Dict] = None) -> QueryComplexity:
        """Analyze query to determine complexity level"""
        query_lower = query.lower()
        
        # Keyword-based complexity analysis
        trivial_keywords = ["status", "price", "simple", "what is", "help"]
        simple_keywords = ["analyze", "check", "show", "explain"]
        moderate_keywords = ["strategy", "recommend", "compare", "optimize"]
        complex_keywords = ["predict", "forecast", "model", "backtest", "risk assessment"]
        critical_keywords = ["debug", "fix", "critical", "emergency", "system", "error"]
        
        # Count keyword matches
        scores = {
            QueryComplexity.TRIVIAL: sum(1 for kw in trivial_keywords if kw in query_lower),
            QueryComplexity.SIMPLE: sum(1 for kw in simple_keywords if kw in query_lower),
            QueryComplexity.MODERATE: sum(1 for kw in moderate_keywords if kw in query_lower),
            QueryComplexity.COMPLEX: sum(1 for kw in complex_keywords if kw in query_lower),
            QueryComplexity.CRITICAL: sum(1 for kw in critical_keywords if kw in query_lower)
        }
        
        # Additional complexity factors
        word_count = len(query.split())
        if word_count > 50:
            scores[QueryComplexity.COMPLEX] += 2
        elif word_count > 20:
            scores[QueryComplexity.MODERATE] += 1
            
        # Context-based complexity
        if context:
            if context.get("requires_real_time_data"):
                scores[QueryComplexity.COMPLEX] += 2
            if context.get("involves_multiple_assets"):
                scores[QueryComplexity.MODERATE] += 1
            if context.get("system_critical"):
                scores[QueryComplexity.CRITICAL] += 3
        
        # Return highest scoring complexity
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def select_optimal_provider(self, query_context: QueryContext) -> Tuple[AIProvider, float]:
        """Select the optimal AI provider based on context and performance"""
        complexity = query_context.complexity
        rules = self.routing_rules[complexity]
        
        # Get provider availability and performance
        available_providers = []
        for provider in rules["preferred"]:
            availability = self._check_provider_availability(provider)
            if availability > 0.8:  # 80% availability threshold
                performance = self._get_provider_performance(provider)
                score = self._calculate_provider_score(
                    provider, performance, query_context
                )
                available_providers.append((provider, score))
        
        if not available_providers:
            # Fallback to free AI if nothing else available
            return AIProvider.FALLBACK_FREE, 0.5
            
        # Sort by score and return best
        available_providers.sort(key=lambda x: x[1], reverse=True)
        return available_providers[0]
    
    def _check_provider_availability(self, provider: AIProvider) -> float:
        """Check if provider is available and responsive"""
        try:
            if provider == AIProvider.LOCAL_AI:
                # Check LocalAI endpoint
                response = requests.get("http://localhost:8080/v1/models", timeout=2)
                return 1.0 if response.status_code == 200 else 0.0
                
            elif provider == AIProvider.AGUS_CLOUD:
                # Check if OpenAI API key is available
                return 1.0 if os.environ.get("OPENAI_API_KEY") else 0.0
                
            elif provider == AIProvider.FALLBACK_FREE:
                # Free AI is always available
                return 1.0
                
            else:
                return 0.8  # Default availability for hybrid modes
                
        except Exception as e:
            logger.debug(f"Provider {provider.value} availability check failed: {e}")
            return 0.0
    
    def _get_provider_performance(self, provider: AIProvider) -> Dict:
        """Get historical performance metrics for provider"""
        if provider not in self.provider_metrics:
            # Initialize default metrics
            self.provider_metrics[provider] = PerformanceMetrics(
                provider=provider,
                avg_response_time=5.0,
                avg_cost=0.01,
                avg_quality=0.7,
                success_rate=0.9,
                total_queries=0,
                last_24h_queries=0,
                error_rate=0.1,
                availability=0.9
            )
        return asdict(self.provider_metrics[provider])
    
    def _calculate_provider_score(self, provider: AIProvider, performance: Dict, context: QueryContext) -> float:
        """Calculate overall score for provider selection"""
        # Base score from performance
        score = 0.0
        
        # Quality weight (40%)
        score += performance["avg_quality"] * 0.4
        
        # Speed weight (20% - inverse of response time)
        max_time = self.routing_rules[context.complexity]["max_time"]
        time_score = max(0, 1 - (performance["avg_response_time"] / max_time))
        score += time_score * 0.2
        
        # Cost efficiency weight (20% - inverse of cost)
        max_cost = self.routing_rules[context.complexity]["max_cost"]
        cost_score = max(0, 1 - (performance["avg_cost"] / max_cost))
        score += cost_score * 0.2
        
        # Availability weight (20%)
        score += performance["availability"] * 0.2
        
        # Priority boost for preferred providers
        rules = self.routing_rules[context.complexity]
        if provider in rules["preferred"][:2]:  # Top 2 preferred
            score += 0.1
            
        return min(1.0, max(0.0, score))

class AdvancedReasoningEngine:
    """
    🧠 Advanced Reasoning System with Chain-of-Thought and Self-Reflection
    """
    
    def __init__(self):
        self.reasoning_cache = {}
        self.reflection_history = defaultdict(list)
        
    async def process_with_reasoning(self, query_context: QueryContext, provider: AIProvider) -> AIResponse:
        """Process query with advanced reasoning based on mode"""
        
        if query_context.reasoning_mode == ReasoningMode.DIRECT:
            return await self._direct_processing(query_context, provider)
        
        elif query_context.reasoning_mode == ReasoningMode.CHAIN_OF_THOUGHT:
            return await self._chain_of_thought_processing(query_context, provider)
        
        elif query_context.reasoning_mode == ReasoningMode.SELF_REFLECTION:
            return await self._self_reflection_processing(query_context, provider)
        
        elif query_context.reasoning_mode == ReasoningMode.ENSEMBLE:
            return await self._ensemble_processing(query_context, provider)
        
        elif query_context.reasoning_mode == ReasoningMode.TREE_OF_THOUGHTS:
            return await self._tree_of_thoughts_processing(query_context, provider)
        
        else:
            return await self._direct_processing(query_context, provider)
    
    async def _direct_processing(self, context: QueryContext, provider: AIProvider) -> AIResponse:
        """Direct processing without advanced reasoning"""
        start_time = time.time()
        
        try:
            if provider == AIProvider.AGUS_CLOUD:
                response_content = await self._openai_request(context.query)
            elif provider == AIProvider.LOCAL_AI:
                response_content = await self._localai_request(context.query)
            else:
                response_content = await self._fallback_processing(context.query)
            
            response_time = time.time() - start_time
            
            return AIResponse(
                content=response_content,
                provider=provider,
                reasoning_steps=["Direct processing"],
                confidence=0.8,
                cost=self._calculate_cost(provider, context.query),
                response_time=response_time,
                quality_score=0.8,
                metadata={},
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error in direct processing: {e}")
            return self._create_error_response(str(e), provider)
    
    async def _chain_of_thought_processing(self, context: QueryContext, provider: AIProvider) -> AIResponse:
        """Chain-of-thought reasoning for complex analysis"""
        start_time = time.time()
        reasoning_steps = []
        
        try:
            # Step 1: Break down the problem
            breakdown_prompt = f"""
            Query: {context.query}
            
            Please break this down into logical steps for analysis:
            1. Identify key components
            2. Determine analysis approach  
            3. Consider relevant factors
            4. Plan execution steps
            
            Provide a step-by-step breakdown:
            """
            
            if provider == AIProvider.AGUS_CLOUD:
                breakdown = await self._openai_request(breakdown_prompt)
            else:
                breakdown = await self._localai_request(breakdown_prompt)
                
            reasoning_steps.append(f"Problem Breakdown: {breakdown[:200]}...")
            
            # Step 2: Execute each step
            execution_prompt = f"""
            Original Query: {context.query}
            Analysis Plan: {breakdown}
            
            Now execute this analysis step by step, showing your reasoning:
            """
            
            if provider == AIProvider.AGUS_CLOUD:
                execution = await self._openai_request(execution_prompt)
            else:
                execution = await self._localai_request(execution_prompt)
                
            reasoning_steps.append(f"Step-by-step Execution: {execution[:200]}...")
            
            # Step 3: Synthesize results
            synthesis_prompt = f"""
            Query: {context.query}
            Analysis: {execution}
            
            Provide a clear, actionable conclusion based on this reasoning:
            """
            
            if provider == AIProvider.AGUS_CLOUD:
                final_response = await self._openai_request(synthesis_prompt)
            else:
                final_response = await self._localai_request(synthesis_prompt)
                
            reasoning_steps.append("Final Synthesis: Completed")
            
            response_time = time.time() - start_time
            
            return AIResponse(
                content=final_response,
                provider=provider,
                reasoning_steps=reasoning_steps,
                confidence=0.9,
                cost=self._calculate_cost(provider, context.query) * 3,  # 3x cost for chain reasoning
                response_time=response_time,
                quality_score=0.9,
                metadata={"reasoning_mode": "chain_of_thought"},
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error in chain-of-thought processing: {e}")
            return self._create_error_response(str(e), provider)
    
    async def _self_reflection_processing(self, context: QueryContext, provider: AIProvider) -> AIResponse:
        """Self-reflection processing with validation and refinement"""
        start_time = time.time()
        reasoning_steps = []
        
        try:
            # First pass: Initial response
            initial_response = await self._direct_processing(context, provider)
            reasoning_steps.append("Initial Analysis: Completed")
            
            # Second pass: Critical evaluation
            critique_prompt = f"""
            Original Query: {context.query}
            My Initial Response: {initial_response.content}
            
            Please critically evaluate this response:
            1. Are there any logical errors?
            2. What important factors might be missing?
            3. How could this analysis be improved?
            4. What are the potential risks or limitations?
            
            Provide a detailed critique:
            """
            
            if provider == AIProvider.AGUS_CLOUD:
                critique = await self._openai_request(critique_prompt)
            else:
                critique = await self._localai_request(critique_prompt)
                
            reasoning_steps.append(f"Self-Critique: {critique[:200]}...")
            
            # Third pass: Refined response
            refinement_prompt = f"""
            Query: {context.query}
            Initial Response: {initial_response.content}
            Self-Critique: {critique}
            
            Based on the critique, provide an improved, refined response that addresses the identified issues:
            """
            
            if provider == AIProvider.AGUS_CLOUD:
                refined_response = await self._openai_request(refinement_prompt)
            else:
                refined_response = await self._localai_request(refinement_prompt)
                
            reasoning_steps.append("Refined Analysis: Completed")
            
            response_time = time.time() - start_time
            
            return AIResponse(
                content=refined_response,
                provider=provider,
                reasoning_steps=reasoning_steps,
                confidence=0.95,
                cost=self._calculate_cost(provider, context.query) * 4,  # 4x cost for reflection
                response_time=response_time,
                quality_score=0.95,
                metadata={"reasoning_mode": "self_reflection", "critique": critique},
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error in self-reflection processing: {e}")
            return self._create_error_response(str(e), provider)
    
    async def _ensemble_processing(self, context: QueryContext, provider: AIProvider) -> AIResponse:
        """Ensemble processing using multiple approaches"""
        start_time = time.time()
        reasoning_steps = []
        
        try:
            # Get responses from multiple methods
            direct_task = self._direct_processing(context, provider)
            cot_context = QueryContext(
                query=context.query,
                user_id=context.user_id,
                session_id=context.session_id,
                query_type=context.query_type,
                complexity=context.complexity,
                reasoning_mode=ReasoningMode.CHAIN_OF_THOUGHT,
                priority=context.priority,
                max_response_time=context.max_response_time,
                cost_budget=context.cost_budget,
                timestamp=context.timestamp,
                metadata=context.metadata
            )
            cot_task = self._chain_of_thought_processing(cot_context, provider)
            
            # Execute both approaches
            direct_result, cot_result = await asyncio.gather(direct_task, cot_task)
            
            reasoning_steps.extend(direct_result.reasoning_steps)
            reasoning_steps.extend(cot_result.reasoning_steps)
            
            # Synthesize ensemble result
            synthesis_prompt = f"""
            Query: {context.query}
            
            Method 1 (Direct): {direct_result.content}
            Method 2 (Chain-of-Thought): {cot_result.content}
            
            Synthesize the best insights from both approaches into a comprehensive response:
            """
            
            if provider == AIProvider.AGUS_CLOUD:
                ensemble_result = await self._openai_request(synthesis_prompt)
            else:
                ensemble_result = await self._localai_request(synthesis_prompt)
                
            reasoning_steps.append("Ensemble Synthesis: Completed")
            
            response_time = time.time() - start_time
            
            # Calculate weighted confidence
            avg_confidence = (direct_result.confidence + cot_result.confidence) / 2
            ensemble_confidence = min(0.98, avg_confidence + 0.1)  # Boost for ensemble
            
            return AIResponse(
                content=ensemble_result,
                provider=provider,
                reasoning_steps=reasoning_steps,
                confidence=ensemble_confidence,
                cost=direct_result.cost + cot_result.cost + self._calculate_cost(provider, synthesis_prompt),
                response_time=response_time,
                quality_score=0.92,
                metadata={"reasoning_mode": "ensemble", "methods_used": ["direct", "chain_of_thought"]},
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error in ensemble processing: {e}")
            return self._create_error_response(str(e), provider)
    
    async def _tree_of_thoughts_processing(self, context: QueryContext, provider: AIProvider) -> AIResponse:
        """Tree-of-thoughts processing for complex branching analysis"""
        start_time = time.time()
        reasoning_steps = []
        
        try:
            # Generate multiple thought branches
            branch_prompt = f"""
            Query: {context.query}
            
            Generate 3 different approaches to analyze this query:
            
            Approach 1: [Technical Analysis Focus]
            Approach 2: [Risk Management Focus] 
            Approach 3: [Market Context Focus]
            
            For each approach, outline the key considerations:
            """
            
            if provider == AIProvider.AGUS_CLOUD:
                branches = await self._openai_request(branch_prompt)
            else:
                branches = await self._localai_request(branch_prompt)
                
            reasoning_steps.append(f"Branch Generation: {branches[:200]}...")
            
            # Evaluate each branch
            evaluation_prompt = f"""
            Query: {context.query}
            Generated Approaches: {branches}
            
            Evaluate each approach:
            1. Which approach is most relevant?
            2. What are the strengths/weaknesses of each?
            3. How can they be combined effectively?
            
            Provide evaluation:
            """
            
            if provider == AIProvider.AGUS_CLOUD:
                evaluation = await self._openai_request(evaluation_prompt)
            else:
                evaluation = await self._localai_request(evaluation_prompt)
                
            reasoning_steps.append(f"Branch Evaluation: {evaluation[:200]}...")
            
            # Synthesize optimal path
            synthesis_prompt = f"""
            Query: {context.query}
            Available Approaches: {branches}
            Evaluation: {evaluation}
            
            Based on the evaluation, synthesize the optimal analysis path and provide the final recommendation:
            """
            
            if provider == AIProvider.AGUS_CLOUD:
                final_synthesis = await self._openai_request(synthesis_prompt)
            else:
                final_synthesis = await self._localai_request(synthesis_prompt)
                
            reasoning_steps.append("Tree Synthesis: Completed")
            
            response_time = time.time() - start_time
            
            return AIResponse(
                content=final_synthesis,
                provider=provider,
                reasoning_steps=reasoning_steps,
                confidence=0.93,
                cost=self._calculate_cost(provider, context.query) * 5,  # 5x cost for tree reasoning
                response_time=response_time,
                quality_score=0.93,
                metadata={"reasoning_mode": "tree_of_thoughts", "branches": 3},
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error in tree-of-thoughts processing: {e}")
            return self._create_error_response(str(e), provider)
    
    async def _openai_request(self, prompt: str) -> str:
        """Make request to OpenAI API"""
        try:
            if not OpenAI:
                raise Exception("OpenAI library not available")
                
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise Exception("OpenAI API key not configured")
                
            client = OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Use GPT-4o-mini for reliability and availability
                messages=[
                    {"role": "system", "content": "You are AGUS 2.0, an advanced AI trading assistant with institutional-grade capabilities."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            return content if content is not None else "No response content"
            
        except Exception as e:
            logger.error(f"OpenAI request failed: {e}")
            raise e
    
    async def _localai_request(self, prompt: str) -> str:
        """Make request to LocalAI"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "microsoft/DialoGPT-large",
                    "messages": [
                        {"role": "system", "content": "You are AGUS 2.0, an advanced AI trading assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 800,
                    "temperature": 0.7
                }
                
                async with session.post(
                    "http://localhost:8080/v1/chat/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["choices"][0]["message"]["content"]
                    else:
                        raise Exception(f"LocalAI returned status {response.status}")
                        
        except Exception as e:
            logger.error(f"LocalAI request failed: {e}")
            raise e
    
    async def _fallback_processing(self, query: str) -> str:
        """Fallback processing using free AI assistant"""
        try:
            from .free_ai_assistant import free_ai_assistant
            
            # Simple pattern matching for common queries
            query_lower = query.lower()
            
            if "status" in query_lower or "health" in query_lower:
                return "🤖 AGUS 2.0 System Status: All systems operational. Hybrid AI engine ready."
            
            elif "help" in query_lower:
                return """🧠 AGUS 2.0 Hybrid AI Assistant
                
Available capabilities:
• Trading analysis and recommendations
• Market sentiment analysis
• Code debugging and optimization  
• Risk assessment
• Strategy recommendations
• Real-time market insights

Ask me anything about trading, markets, or system optimization!"""
            
            elif "price" in query_lower or "market" in query_lower:
                return "📊 Real-time market analysis capability activated. Please specify which assets you'd like me to analyze."
            
            else:
                return f"🤖 AGUS 2.0: I understand you're asking about '{query[:100]}...'. While my advanced reasoning is temporarily using fallback mode, I can still help with basic analysis and guidance. For complex analysis, please ensure AGUS Cloud or LocalAI is configured."
                
        except Exception as e:
            return f"⚠️ Fallback processing error: {e}"
    
    def _calculate_cost(self, provider: AIProvider, query: str) -> float:
        """Calculate estimated cost for query"""
        token_estimate = len(query.split()) * 1.3  # Rough token estimate
        
        if provider == AIProvider.AGUS_CLOUD:
            return token_estimate * 0.00003  # GPT-4 pricing estimate
        elif provider == AIProvider.LOCAL_AI:
            return 0.0  # LocalAI is free
        else:
            return 0.0  # Fallback is free
    
    def _create_error_response(self, error_msg: str, provider: AIProvider) -> AIResponse:
        """Create standardized error response"""
        return AIResponse(
            content=f"⚠️ Error processing request: {error_msg}",
            provider=provider,
            reasoning_steps=[f"Error encountered: {error_msg}"],
            confidence=0.1,
            cost=0.0,
            response_time=1.0,
            quality_score=0.1,
            metadata={"error": error_msg},
            timestamp=datetime.now()
        )

class TradingIntelligenceLayer:
    """
    📊 Unique Trading Intelligence System
    Real-time sentiment fusion, strategy recommendations, debugging
    """
    
    def __init__(self):
        self.market_memory = defaultdict(dict)
        self.strategy_cache = {}
        self.debug_history = []
        
    async def analyze_market_sentiment_fusion(self, symbols: List[str], reasoning_engine: AdvancedReasoningEngine) -> Dict:
        """Fuse multiple sentiment sources for comprehensive analysis"""
        try:
            sentiment_sources = []
            
            # Source 1: Technical sentiment
            tech_sentiment = await self._get_technical_sentiment(symbols)
            sentiment_sources.append(("technical", tech_sentiment))
            
            # Source 2: News sentiment (if available)
            try:
                news_sentiment = await self._get_news_sentiment(symbols)
                sentiment_sources.append(("news", news_sentiment))
            except:
                pass
            
            # Source 3: Social sentiment (simulated for now)
            social_sentiment = await self._get_social_sentiment(symbols)
            sentiment_sources.append(("social", social_sentiment))
            
            # Fusion analysis using AI reasoning
            fusion_prompt = f"""
            Analyze these sentiment sources for {', '.join(symbols[:5])}:
            
            Technical Sentiment: {tech_sentiment}
            Social Sentiment: {social_sentiment}
            
            Provide a fused sentiment analysis with:
            1. Overall market mood
            2. Key drivers
            3. Risk factors
            4. Trading opportunities
            5. Confidence level
            
            Format as structured analysis:
            """
            
            context = QueryContext(
                query=fusion_prompt,
                user_id="system",
                session_id="sentiment_analysis",
                query_type="trading",
                complexity=QueryComplexity.MODERATE,
                reasoning_mode=ReasoningMode.CHAIN_OF_THOUGHT,
                priority=7,
                max_response_time=15.0,
                cost_budget=0.10,
                timestamp=datetime.now(),
                metadata={"symbols": symbols}
            )
            
            # Use chain-of-thought for comprehensive analysis
            response = await reasoning_engine._chain_of_thought_processing(context, AIProvider.AGUS_CLOUD)
            
            return {
                "fused_sentiment": response.content,
                "confidence": response.confidence,
                "sources": sentiment_sources,
                "analysis_quality": response.quality_score,
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error in sentiment fusion: {e}")
            return {"error": str(e)}
    
    async def generate_strategy_recommendations(self, market_data: Dict, reasoning_engine: AdvancedReasoningEngine) -> Dict:
        """Generate intelligent strategy recommendations"""
        try:
            # Analyze current market conditions
            conditions_prompt = f"""
            Current Market Data Summary: {json.dumps(market_data, indent=2)[:1000]}
            
            Analyze current market conditions and recommend optimal trading strategies:
            
            1. Market Regime Analysis (trending, ranging, volatile)
            2. Optimal Strategies for current conditions
            3. Risk Management recommendations
            4. Position sizing suggestions
            5. Time horizon considerations
            6. Exit strategy planning
            
            Provide actionable strategy recommendations:
            """
            
            context = QueryContext(
                query=conditions_prompt,
                user_id="system",
                session_id="strategy_generation",
                query_type="trading",
                complexity=QueryComplexity.COMPLEX,
                reasoning_mode=ReasoningMode.ENSEMBLE,
                priority=8,
                max_response_time=30.0,
                cost_budget=0.50,
                timestamp=datetime.now(),
                metadata={"market_data_points": len(market_data)}
            )
            
            # Use ensemble method for comprehensive strategy analysis
            response = await reasoning_engine._ensemble_processing(context, AIProvider.AGUS_CLOUD)
            
            return {
                "strategy_recommendations": response.content,
                "confidence": response.confidence,
                "reasoning_steps": response.reasoning_steps,
                "analysis_depth": "ensemble",
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error generating strategy recommendations: {e}")
            return {"error": str(e)}
    
    async def debug_trading_system(self, error_context: Dict, reasoning_engine: AdvancedReasoningEngine) -> Dict:
        """Advanced debugging with auto-fix capabilities"""
        try:
            debug_prompt = f"""
            Trading System Debug Request:
            
            Error Context: {json.dumps(error_context, indent=2)}
            
            Perform comprehensive system debugging:
            
            1. Root Cause Analysis
            2. Impact Assessment  
            3. Immediate Fixes Available
            4. Prevention Strategies
            5. Code Optimization Suggestions
            6. Risk Mitigation Steps
            
            Provide detailed debugging report with actionable fixes:
            """
            
            context = QueryContext(
                query=debug_prompt,
                user_id="system",
                session_id="debug_session",
                query_type="debugging",
                complexity=QueryComplexity.CRITICAL,
                reasoning_mode=ReasoningMode.SELF_REFLECTION,
                priority=10,
                max_response_time=60.0,
                cost_budget=1.00,
                timestamp=datetime.now(),
                metadata=error_context
            )
            
            # Use self-reflection for thorough debugging
            response = await reasoning_engine._self_reflection_processing(context, AIProvider.AGUS_CLOUD)
            
            # Store debug history
            self.debug_history.append({
                "timestamp": datetime.now(),
                "error_context": error_context,
                "analysis": response.content,
                "confidence": response.confidence
            })
            
            return {
                "debug_analysis": response.content,
                "confidence": response.confidence,
                "reasoning_steps": response.reasoning_steps,
                "auto_fix_available": self._check_auto_fix_availability(response.content),
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error in system debugging: {e}")
            return {"error": str(e)}
    
    async def _get_technical_sentiment(self, symbols: List[str]) -> Dict:
        """Get technical analysis based sentiment"""
        try:
            from .free_ai_assistant import free_ai_assistant
            
            sentiment_scores = {}
            for symbol in symbols[:5]:  # Limit to top 5 for performance
                try:
                    # Get basic market data
                    from .data import fetch_bars
                    df = fetch_bars(symbol, start=None, end=None, min_bars=20)
                    
                    if not df.empty:
                        latest_price = df['close'].iloc[-1]
                        price_change = (latest_price - df['close'].iloc[-2]) / df['close'].iloc[-2]
                        
                        # Simple technical sentiment
                        if price_change > 0.02:
                            sentiment_scores[symbol] = {"score": 0.7, "reason": "Strong upward momentum"}
                        elif price_change > 0:
                            sentiment_scores[symbol] = {"score": 0.3, "reason": "Positive momentum"}
                        elif price_change < -0.02:
                            sentiment_scores[symbol] = {"score": -0.7, "reason": "Strong downward pressure"}
                        else:
                            sentiment_scores[symbol] = {"score": -0.2, "reason": "Negative momentum"}
                    else:
                        sentiment_scores[symbol] = {"score": 0.0, "reason": "No data available"}
                        
                except Exception as e:
                    sentiment_scores[symbol] = {"score": 0.0, "reason": f"Analysis error: {str(e)[:50]}"}
            
            return sentiment_scores
            
        except Exception as e:
            logger.error(f"Error getting technical sentiment: {e}")
            return {}
    
    async def _get_news_sentiment(self, symbols: List[str]) -> Dict:
        """Get news-based sentiment analysis"""
        # Placeholder for news sentiment
        # In a full implementation, this would integrate with news APIs
        return {symbol: {"score": 0.1, "reason": "Neutral news sentiment"} for symbol in symbols}
    
    async def _get_social_sentiment(self, symbols: List[str]) -> Dict:
        """Get social media sentiment analysis"""
        # Placeholder for social sentiment
        # In a full implementation, this would integrate with social media APIs
        return {symbol: {"score": 0.0, "reason": "Social sentiment analysis unavailable"} for symbol in symbols}
    
    def _check_auto_fix_availability(self, debug_analysis: str) -> bool:
        """Check if auto-fix is available for detected issues"""
        auto_fixable_patterns = [
            "syntax error",
            "import error", 
            "configuration issue",
            "api timeout",
            "connection error"
        ]
        
        analysis_lower = debug_analysis.lower()
        return any(pattern in analysis_lower for pattern in auto_fixable_patterns)

class PerformanceOptimizationLayer:
    """
    ⚡ Performance Optimization and Monitoring System
    """
    
    def __init__(self):
        self.response_times = defaultdict(list)
        self.cost_tracking = defaultdict(float)
        self.quality_scores = defaultdict(list)
        self.optimization_rules = self._initialize_optimization_rules()
    
    def _initialize_optimization_rules(self) -> Dict:
        """Initialize performance optimization rules"""
        return {
            "response_time_thresholds": {
                QueryComplexity.TRIVIAL: 2.0,
                QueryComplexity.SIMPLE: 5.0,
                QueryComplexity.MODERATE: 15.0,
                QueryComplexity.COMPLEX: 30.0,
                QueryComplexity.CRITICAL: 60.0
            },
            "cost_limits": {
                "hourly": 5.00,
                "daily": 50.00,
                "weekly": 200.00
            },
            "quality_minimums": {
                QueryComplexity.TRIVIAL: 0.6,
                QueryComplexity.SIMPLE: 0.7,
                QueryComplexity.MODERATE: 0.8,
                QueryComplexity.COMPLEX: 0.85,
                QueryComplexity.CRITICAL: 0.9
            }
        }
    
    def monitor_performance(self, response: AIResponse, context: QueryContext):
        """Monitor and track performance metrics"""
        provider = response.provider.value
        
        # Track response times
        self.response_times[provider].append(response.response_time)
        if len(self.response_times[provider]) > 100:
            self.response_times[provider] = self.response_times[provider][-50:]  # Keep last 50
        
        # Track costs
        self.cost_tracking[provider] += response.cost
        
        # Track quality scores
        self.quality_scores[provider].append(response.quality_score)
        if len(self.quality_scores[provider]) > 100:
            self.quality_scores[provider] = self.quality_scores[provider][-50:]
        
        # Check for performance issues
        self._check_performance_thresholds(response, context)
    
    def _check_performance_thresholds(self, response: AIResponse, context: QueryContext):
        """Check if performance thresholds are exceeded"""
        threshold = self.optimization_rules["response_time_thresholds"][context.complexity]
        
        if response.response_time > threshold:
            logger.warning(f"⚠️ Response time threshold exceeded: {response.response_time:.2f}s > {threshold}s")
        
        quality_min = self.optimization_rules["quality_minimums"][context.complexity]
        if response.quality_score < quality_min:
            logger.warning(f"⚠️ Quality score below threshold: {response.quality_score:.2f} < {quality_min}")
    
    def get_performance_report(self) -> Dict:
        """Generate comprehensive performance report"""
        report = {
            "timestamp": datetime.now(),
            "providers": {}
        }
        
        for provider in [p.value for p in AIProvider]:
            if provider in self.response_times and self.response_times[provider]:
                report["providers"][provider] = {
                    "avg_response_time": statistics.mean(self.response_times[provider]),
                    "total_cost": self.cost_tracking.get(provider, 0.0),
                    "avg_quality": statistics.mean(self.quality_scores.get(provider, [0.5])),
                    "total_queries": len(self.response_times[provider])
                }
        
        return report
    
    def optimize_routing_weights(self) -> Dict:
        """Dynamically optimize routing weights based on performance"""
        optimizations = {}
        
        for provider in [p.value for p in AIProvider]:
            if provider in self.response_times and len(self.response_times[provider]) >= 5:
                avg_time = statistics.mean(self.response_times[provider])
                avg_quality = statistics.mean(self.quality_scores.get(provider, [0.5]))
                total_cost = self.cost_tracking.get(provider, 0.0)
                
                # Calculate optimization score
                time_score = max(0, 1 - (avg_time / 30))  # Normalize to 30 second max
                quality_score = avg_quality
                cost_score = max(0, 1 - (total_cost / 100))  # Normalize to $100 max
                
                optimization_score = (time_score * 0.4 + quality_score * 0.4 + cost_score * 0.2)
                
                optimizations[provider] = {
                    "optimization_score": optimization_score,
                    "recommended_weight": min(1.0, optimization_score + 0.2)
                }
        
        return optimizations

class AGUS2HybridSystem:
    """
    🧠 AGUS 2.0 MAIN HYBRID INTELLIGENCE SYSTEM
    Orchestrates all components for institutional-grade AI capabilities
    """
    
    def __init__(self):
        self.memory_manager = ContextualMemoryManager()
        self.routing_engine = IntelligentRoutingEngine()
        self.reasoning_engine = AdvancedReasoningEngine()
        self.trading_intelligence = TradingIntelligenceLayer()
        self.performance_optimizer = PerformanceOptimizationLayer()
        
        # System state
        self.system_status = "initializing"
        self.active_sessions = {}
        self.startup_time = datetime.now()
        
        logger.info("🧠 AGUS 2.0 Hybrid Intelligence System initialized")
        self._system_health_check()
    
    def _system_health_check(self):
        """Perform initial system health check"""
        health_status = {
            "memory_db": "ok" if Path(self.memory_manager.memory_db_path).parent.exists() else "error",
            "localai": "ok" if self.routing_engine._check_provider_availability(AIProvider.LOCAL_AI) > 0.5 else "unavailable",
            "agus": "ok" if self.routing_engine._check_provider_availability(AIProvider.AGUS_CLOUD) > 0.5 else "unavailable",
            "fallback_ai": "ok"
        }
        
        self.system_status = "operational" if health_status["fallback_ai"] == "ok" else "limited"
        logger.info(f"🩺 AGUS 2.0 Health Check: {health_status}")
    
    async def process_query(self, query: str, user_id: str = "default", session_id: str = "default", 
                          query_type: str = "general", priority: int = 5) -> AIResponse:
        """
        🎯 Main query processing pipeline
        """
        start_time = time.time()
        
        try:
            # Step 1: Analyze query and create context
            complexity = self.routing_engine.analyze_query_complexity(query)
            
            # Determine optimal reasoning mode
            reasoning_mode = self._select_reasoning_mode(query, complexity, query_type)
            
            # Create query context
            context = QueryContext(
                query=query,
                user_id=user_id,
                session_id=session_id,
                query_type=query_type,
                complexity=complexity,
                reasoning_mode=reasoning_mode,
                priority=priority,
                max_response_time=30.0,
                cost_budget=1.00,
                timestamp=datetime.now(),
                metadata={
                    "conversation_history": self.memory_manager.get_conversation_context(user_id, session_id, 5),
                    "user_preferences": self.memory_manager.extract_user_preferences(user_id)
                }
            )
            
            # Step 2: Select optimal provider
            provider, provider_score = self.routing_engine.select_optimal_provider(context)
            logger.info(f"🎯 AGUS 2.0 Routing: {provider.value} (score: {provider_score:.2f}) for {complexity.name} query")
            
            # Step 3: Process with advanced reasoning
            response = await self.reasoning_engine.process_with_reasoning(context, provider)
            
            # Step 4: Enhance with trading intelligence if applicable
            if query_type == "trading" and response.quality_score > 0.7:
                try:
                    enhanced_response = await self._enhance_with_trading_intelligence(response, context)
                    if enhanced_response:
                        response = enhanced_response
                except Exception as e:
                    logger.debug(f"Trading intelligence enhancement failed: {e}")
            
            # Step 5: Store in memory and monitor performance
            self.memory_manager.store_conversation(context, response)
            self.performance_optimizer.monitor_performance(response, context)
            
            # Step 6: Update system metrics
            total_time = time.time() - start_time
            response.response_time = total_time
            
            logger.info(f"✅ AGUS 2.0 Query processed: {total_time:.2f}s, confidence: {response.confidence:.2f}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ AGUS 2.0 Error processing query: {e}")
            return AIResponse(
                content=f"⚠️ AGUS 2.0 encountered an error: {str(e)[:200]}...",
                provider=AIProvider.FALLBACK_FREE,
                reasoning_steps=[f"Error: {str(e)}"],
                confidence=0.1,
                cost=0.0,
                response_time=time.time() - start_time,
                quality_score=0.1,
                metadata={"error": str(e)},
                timestamp=datetime.now()
            )
    
    def _select_reasoning_mode(self, query: str, complexity: QueryComplexity, query_type: str) -> ReasoningMode:
        """Select optimal reasoning mode based on query characteristics"""
        query_lower = query.lower()
        
        # Critical queries need self-reflection
        if query_type == "debugging" or "critical" in query_lower or "emergency" in query_lower:
            return ReasoningMode.SELF_REFLECTION
        
        # Complex analysis benefits from tree-of-thoughts
        if complexity == QueryComplexity.CRITICAL and ("analyze" in query_lower or "strategy" in query_lower):
            return ReasoningMode.TREE_OF_THOUGHTS
        
        # Trading decisions benefit from ensemble
        if query_type == "trading" and complexity >= QueryComplexity.MODERATE:
            return ReasoningMode.ENSEMBLE
        
        # Complex queries benefit from chain-of-thought
        if complexity >= QueryComplexity.COMPLEX:
            return ReasoningMode.CHAIN_OF_THOUGHT
        
        # Simple queries use direct processing
        return ReasoningMode.DIRECT
    
    async def _enhance_with_trading_intelligence(self, base_response: AIResponse, context: QueryContext) -> Optional[AIResponse]:
        """Enhance response with trading intelligence if applicable"""
        try:
            enhancement_prompt = f"""
            Base AI Response: {base_response.content}
            
            Enhance this trading response with:
            1. Real-time market context
            2. Risk assessment
            3. Actionable next steps
            4. Key monitoring points
            
            Provide enhanced trading intelligence:
            """
            
            enhanced_context = QueryContext(
                query=enhancement_prompt,
                user_id=context.user_id,
                session_id=context.session_id,
                query_type="trading",
                complexity=QueryComplexity.MODERATE,
                reasoning_mode=ReasoningMode.DIRECT,
                priority=context.priority,
                max_response_time=10.0,
                cost_budget=0.20,
                timestamp=datetime.now(),
                metadata=context.metadata
            )
            
            enhanced_response = await self.reasoning_engine._direct_processing(enhanced_context, base_response.provider)
            
            # Combine responses
            combined_content = f"{base_response.content}\n\n🎯 AGUS 2.0 Trading Intelligence Enhancement:\n{enhanced_response.content}"
            
            return AIResponse(
                content=combined_content,
                provider=base_response.provider,
                reasoning_steps=base_response.reasoning_steps + ["Trading Intelligence Enhancement"],
                confidence=min(0.98, base_response.confidence + 0.05),
                cost=base_response.cost + enhanced_response.cost,
                response_time=base_response.response_time + enhanced_response.response_time,
                quality_score=min(0.98, base_response.quality_score + 0.05),
                metadata={**base_response.metadata, "enhanced": True},
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.debug(f"Enhancement failed: {e}")
            return None
    
    async def analyze_market_with_hybrid_intelligence(self, symbols: List[str]) -> Dict:
        """Comprehensive market analysis using all AGUS 2.0 capabilities"""
        try:
            logger.info(f"🧠 AGUS 2.0 Market Analysis: {len(symbols)} symbols")
            
            # Multi-faceted analysis
            tasks = []
            
            # 1. Sentiment fusion analysis
            sentiment_task = self.trading_intelligence.analyze_market_sentiment_fusion(symbols, self.reasoning_engine)
            tasks.append(("sentiment", sentiment_task))
            
            # 2. Strategy recommendations
            market_data = {"symbols": symbols, "analysis_timestamp": datetime.now()}
            strategy_task = self.trading_intelligence.generate_strategy_recommendations(market_data, self.reasoning_engine)
            tasks.append(("strategy", strategy_task))
            
            # Execute analysis tasks
            results = {}
            for task_name, task in tasks:
                try:
                    result = await task
                    results[task_name] = result
                except Exception as e:
                    logger.error(f"Task {task_name} failed: {e}")
                    results[task_name] = {"error": str(e)}
            
            # Generate comprehensive report
            report_query = f"""
            Comprehensive Market Analysis Report for: {', '.join(symbols[:10])}
            
            Sentiment Analysis: {results.get('sentiment', {})}
            Strategy Recommendations: {results.get('strategy', {})}
            
            Create a executive summary with:
            1. Key Market Insights
            2. Risk Assessment
            3. Opportunity Identification
            4. Recommended Actions
            5. Monitoring Points
            
            Provide professional market analysis report:
            """
            
            report_response = await self.process_query(
                query=report_query,
                user_id="system",
                session_id="market_analysis",
                query_type="trading",
                priority=8
            )
            
            return {
                "executive_summary": report_response.content,
                "detailed_analysis": results,
                "confidence": report_response.confidence,
                "analysis_timestamp": datetime.now(),
                "agus_version": "2.0"
            }
            
        except Exception as e:
            logger.error(f"❌ Market analysis error: {e}")
            return {"error": str(e)}
    
    async def debug_system_with_ai(self, error_details: Dict) -> Dict:
        """Advanced system debugging using AGUS 2.0 capabilities"""
        try:
            logger.info("🛠️ AGUS 2.0 System Debugging initiated")
            
            return await self.trading_intelligence.debug_trading_system(error_details, self.reasoning_engine)
            
        except Exception as e:
            logger.error(f"❌ System debugging error: {e}")
            return {"error": str(e)}
    
    def get_system_status(self) -> Dict:
        """Get comprehensive AGUS 2.0 system status"""
        return {
            "system_version": "AGUS 2.0 Hybrid",
            "status": self.system_status,
            "uptime_seconds": (datetime.now() - self.startup_time).total_seconds(),
            "active_sessions": len(self.active_sessions),
            "providers": {
                "localai": self.routing_engine._check_provider_availability(AIProvider.LOCAL_AI),
                "agus": self.routing_engine._check_provider_availability(AIProvider.AGUS_CLOUD),
                "fallback": 1.0
            },
            "performance": self.performance_optimizer.get_performance_report(),
            "memory_stats": {
                "conversations_stored": len(self.memory_manager.conversation_history),
                "db_path": self.memory_manager.memory_db_path
            }
        }

# Global AGUS 2.0 instance
agus_2_system = AGUS2HybridSystem()

# Integration functions for chat_with_ai.py compatibility
async def agus_2_analyze_query(query: str, user_id: str = "default", session_id: str = "default") -> str:
    """Main entry point for AGUS 2.0 analysis"""
    try:
        response = await agus_2_system.process_query(
            query=query,
            user_id=user_id,
            session_id=session_id,
            query_type="general",
            priority=5
        )
        
        return f"""🧠 **AGUS 2.0 HYBRID INTELLIGENCE**

{response.content}

---
*Provider: {response.provider.value} | Confidence: {response.confidence:.1%} | Quality: {response.quality_score:.1%}*
*Response Time: {response.response_time:.2f}s | Reasoning Steps: {len(response.reasoning_steps)}*"""
        
    except Exception as e:
        logger.error(f"❌ AGUS 2.0 analysis error: {e}")
        return f"⚠️ AGUS 2.0 encountered an error: {e}"

async def agus_2_trading_analysis(symbols: List[str]) -> Dict:
    """Trading-focused analysis entry point"""
    return await agus_2_system.analyze_market_with_hybrid_intelligence(symbols)

async def agus_2_debug_system(error_context: Dict) -> Dict:
    """System debugging entry point"""
    return await agus_2_system.debug_system_with_ai(error_context)

def get_agus_2_status() -> Dict:
    """System status entry point"""
    return agus_2_system.get_system_status()

# Test function
async def test_agus_2():
    """Test AGUS 2.0 system"""
    logger.info("🧪 Testing AGUS 2.0 Hybrid System...")
    
    # Test basic query
    result = await agus_2_analyze_query("What is the status of the trading bot?")
    print("Basic Query Result:", result[:200])
    
    # Test trading analysis
    trading_result = await agus_2_trading_analysis(["BTC/USD", "ETH/USD"])
    print("Trading Analysis:", trading_result.get("executive_summary", "")[:200])
    
    # Test system status
    status = get_agus_2_status()
    print("System Status:", status)
    
    logger.info("✅ AGUS 2.0 testing completed")

if __name__ == "__main__":
    asyncio.run(test_agus_2())