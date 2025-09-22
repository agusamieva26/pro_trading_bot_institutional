#!/usr/bin/env python3
"""
🧠 ADVANCED MEMORY SYSTEM WITH RAG - INSTITUTIONAL GRADE
Comprehensive vector-based knowledge system for trading intelligence
- Vector Knowledge Base with Semantic Embeddings
- Personalized RAG Engine for Trading Context
- Continual Learning Memory System
- Advanced Query Processing with Natural Language
- Knowledge Graph Construction & Relationship Mapping
- Integration with AGUS 2.0 Hybrid Intelligence System
"""
import os
import json
import asyncio
import sqlite3
import hashlib
import pickle
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from collections import defaultdict, deque
import numpy as np
import pandas as pd
from loguru import logger
import httpx

# Vector embeddings and search (conditional imports to avoid Keras 3 compatibility issues)
# Reemplazado por API
EMBEDDINGS_API_BASE_URL = os.environ.get("QWEN_API_BASE_URL", "https://api.together.xyz/v1")
EMBEDDINGS_API_KEY = os.environ.get("QWEN_API_KEY")
EMBEDDINGS_MODEL_NAME = os.environ.get("EMBEDDINGS_MODEL_NAME", "togethercomputer/m2-bert-80M-8k-retrieval")

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("faiss not available")

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None
    Settings = None
    logger.warning("chromadb not available")

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    tiktoken = None
    logger.warning("tiktoken not available")

# Advanced ML and processing
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Integration imports
try:
    from .agus_2_hybrid_system import (
        AIProvider, QueryContext, AIResponse, ContextualMemoryManager,
        QueryComplexity, ReasoningMode
    )
except ImportError:
    logger.warning("AGUS 2.0 system not available for integration")
    AIProvider = None

class KnowledgeType(Enum):
    """Types of trading knowledge stored in the vector database"""
    TRADING_STRATEGY = "trading_strategy"
    MARKET_ANALYSIS = "market_analysis" 
    RISK_ASSESSMENT = "risk_assessment"
    TRADING_DECISION = "trading_decision"
    MARKET_PATTERN = "market_pattern"
    PERFORMANCE_INSIGHT = "performance_insight"
    NEWS_SENTIMENT = "news_sentiment"
    TECHNICAL_INDICATOR = "technical_indicator"
    VOLATILITY_ANALYSIS = "volatility_analysis"
    CORRELATION_INSIGHT = "correlation_insight"
    ERROR_PATTERN = "error_pattern"
    SUCCESS_PATTERN = "success_pattern"

class QueryType(Enum):
    """Types of queries for knowledge retrieval"""
    STRATEGY_RECOMMENDATION = "strategy_recommendation"
    MARKET_CONTEXT = "market_context"
    RISK_GUIDANCE = "risk_guidance"
    PATTERN_MATCHING = "pattern_matching"
    DECISION_SUPPORT = "decision_support"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    TROUBLESHOOTING = "troubleshooting"
    GENERAL_INQUIRY = "general_inquiry"

class EmbeddingModel(Enum):
    """Available embedding models for different purposes"""
    FINANCIAL_BERT = "ProsusAI/finbert"
    SENTENCE_TRANSFORMER = "sentence-transformers/all-MiniLM-L6-v2"
    TRADING_CUSTOM = "trading-custom-model"
    MULTI_QA = "sentence-transformers/multi-qa-MiniLM-L6-cos-v1"

@dataclass
class KnowledgeEntry:
    """Single knowledge entry in the vector database"""
    id: str
    content: str
    knowledge_type: KnowledgeType
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0
    tags: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    validation_score: float = 0.0
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    effectiveness_score: float = 0.0

@dataclass
class RetrievalResult:
    """Result from vector knowledge retrieval"""
    entries: List[KnowledgeEntry]
    similarities: List[float]
    query_embedding: np.ndarray
    retrieval_time: float
    total_candidates: int
    filters_applied: List[str]
    reranked: bool = False
    reasoning: str = ""
    context_enhancement: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RAGResponse:
    """Complete RAG-enhanced response"""
    content: str
    knowledge_context: List[KnowledgeEntry]
    confidence: float
    reasoning_steps: List[str]
    citations: List[str]
    generated_insights: List[str]
    knowledge_gaps: List[str]
    recommendations: List[str]
    response_time: float
    timestamp: datetime = field(default_factory=datetime.now)

class AdvancedEmbeddingEngine:
    """
    🎯 Advanced Embedding Generation Engine
    Specialized for trading and financial content
    """
    
    def __init__(self, cache_dir: str = "data_cache/embeddings"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.api_available = bool(EMBEDDINGS_API_KEY)
        self.dimension = 768 # Dimensión para m2-bert-80M-8k-retrieval
        
        # Embedding cache
        self.embedding_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
    
    def preprocess_text(self, text: str, knowledge_type: KnowledgeType) -> str:
        """Preprocess text for better embeddings"""
        # Basic cleaning
        text = text.strip()
        
        # Trading-specific enhancement
        if knowledge_type == KnowledgeType.TRADING_DECISION:
            text = f"[DECISION] {text}"
            
        elif knowledge_type == KnowledgeType.ERROR_PATTERN:
            text = f"[ERROR_PATTERN] {text}"
            
        elif knowledge_type == KnowledgeType.SUCCESS_PATTERN:
            text = f"[SUCCESS_PATTERN] {text}"
        
        return text
    
    def generate_embedding(self, text: str, knowledge_type: KnowledgeType, 
                          model: EmbeddingModel = EmbeddingModel.SENTENCE_TRANSFORMER) -> np.ndarray:
        """Generate embedding for text content"""
        if not self.api_available:
            # Return a simple hash-based embedding as fallback
            text_hash = hashlib.md5(text.encode()).hexdigest()
            embedding = np.array([int(text_hash[i:i+2], 16) / 255.0 for i in range(0, min(len(text_hash), 192), 2)] + [0.0] * (self.dimension - 96))
            return embedding[:self.dimension]
        
        # Check cache first
        cache_key = hashlib.md5(f"{text}:{knowledge_type.value}:{model.value}".encode()).hexdigest()
        
        if cache_key in self.embedding_cache:
            self.cache_hits += 1
            return self.embedding_cache[cache_key]
        
        self.cache_misses += 1
        
        try:
            # Preprocess text
            processed_text = self.preprocess_text(text, knowledge_type)
            
            headers = {
                "Authorization": f"Bearer {EMBEDDINGS_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": EMBEDDINGS_MODEL_NAME,
                "input": [processed_text]
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(f"{EMBEDDINGS_API_BASE_URL}/embeddings", headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()
            
            embedding = np.array(result['data'][0]['embedding'])
            
            # Cache result
            self.embedding_cache[cache_key] = embedding
            
            return embedding
        except Exception as e:
            logger.error(f"❌ Error generating embedding: {e}")
            # Return zero vector as fallback
            return np.zeros(self.dimension)
    
    def batch_generate_embeddings(self, texts: List[str], knowledge_types: List[KnowledgeType],
                                 model: EmbeddingModel = EmbeddingModel.SENTENCE_TRANSFORMER) -> List[np.ndarray]:
        """Generate embeddings in batch for efficiency"""
        try:
            # Preprocess all texts
            processed_texts = [
                self.preprocess_text(text, ktype) 
                for text, ktype in zip(texts, knowledge_types)
            ]
            
            headers = {
                "Authorization": f"Bearer {EMBEDDINGS_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": EMBEDDINGS_MODEL_NAME,
                "input": processed_texts
            }
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(f"{EMBEDDINGS_API_BASE_URL}/embeddings", headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()
            
            embeddings = [np.array(item['embedding']) for item in result['data']]
            
            # Cache results
            for i, (text, ktype) in enumerate(zip(texts, knowledge_types)):
                cache_key = hashlib.md5(f"{text}:{ktype.value}:{model.value}".encode()).hexdigest()
                self.embedding_cache[cache_key] = embeddings[i]
            
            return embeddings
            
        except Exception as e:
            logger.error(f"❌ Error in batch embedding generation: {e}")
            return [np.zeros(self.dimension) for _ in texts]
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between embeddings"""
        try:
            return float(cosine_similarity([embedding1], [embedding2])[0][0])
        except Exception as e:
            logger.error(f"❌ Error computing similarity: {e}")
            return 0.0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get embedding cache statistics"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0
        
        return {
            "cache_size": len(self.embedding_cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": hit_rate
        }

class VectorKnowledgeBase:
    """
    📚 Advanced Vector Knowledge Base
    Stores and retrieves trading knowledge using vector embeddings
    """
    
    def __init__(self, db_path: str = "data_cache/vector_knowledge"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize embedding engine
        self.embedding_engine = AdvancedEmbeddingEngine()
        
        # Initialize ChromaDB for vector storage
        if CHROMADB_AVAILABLE and chromadb is not None and Settings is not None:
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.db_path / "chroma_db"),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        else:
            logger.warning("⚠️ ChromaDB not available - using simple in-memory storage")
            self.chroma_client = None
        
        # Create collections for different knowledge types
        self.collections = {}
        self._initialize_collections()
        
        # FAISS indices for fast similarity search
        self.faiss_indices = {}
        self.faiss_metadata = {}
        
        # SQLite for metadata and relationships
        self.metadata_db = self.db_path / "metadata.db"
        self._initialize_metadata_db()
        
        # In-memory caches
        self.knowledge_cache = {}
        self.query_cache = {}
        
        # Statistics
        self.stats = {
            "total_entries": 0,
            "queries_served": 0,
            "cache_hits": 0,
            "last_updated": datetime.now()
        }
        
        # Lock for thread safety
        self.lock = threading.RLock()
    
    def _initialize_collections(self):
        """Initialize ChromaDB collections for each knowledge type"""
        if not self.chroma_client:
            logger.warning("⚠️ ChromaDB client not available - skipping collection initialization")
            return
            
        try:
            for knowledge_type in KnowledgeType:
                collection_name = f"knowledge_{knowledge_type.value}"
                
                try:
                    # Try to get existing collection
                    collection = self.chroma_client.get_collection(collection_name)
                except:
                    # Create new collection
                    collection = self.chroma_client.create_collection(
                        name=collection_name,
                        metadata={
                            "description": f"Knowledge base for {knowledge_type.value}",
                            "created": datetime.now().isoformat()
                        }
                    )
                
                self.collections[knowledge_type] = collection
                
            logger.info(f"✅ Initialized {len(self.collections)} knowledge collections")
            
        except Exception as e:
            logger.error(f"❌ Error initializing collections: {e}")
    
    def _initialize_metadata_db(self):
        """Initialize SQLite database for metadata"""
        try:
            with sqlite3.connect(self.metadata_db) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_entries (
                        id TEXT PRIMARY KEY,
                        content TEXT,
                        knowledge_type TEXT,
                        metadata TEXT,
                        timestamp DATETIME,
                        confidence REAL,
                        tags TEXT,
                        context TEXT,
                        source TEXT,
                        validation_score REAL,
                        access_count INTEGER DEFAULT 0,
                        last_accessed DATETIME,
                        effectiveness_score REAL DEFAULT 0.0
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_relationships (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        from_entry TEXT,
                        to_entry TEXT,
                        relationship_type TEXT,
                        strength REAL,
                        created_at DATETIME
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS query_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query_text TEXT,
                        query_type TEXT,
                        results_count INTEGER,
                        response_time REAL,
                        timestamp DATETIME,
                        user_feedback REAL
                    )
                """)
                
                # Create indices
                conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge_entries(knowledge_type)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON knowledge_entries(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_effectiveness ON knowledge_entries(effectiveness_score)")
                
            logger.info("✅ Metadata database initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing metadata database: {e}")
    
    def add_knowledge(self, content: str, knowledge_type: KnowledgeType,
                     metadata: Optional[Dict[str, Any]] = None, tags: Optional[List[str]] = None,
                     context: Optional[Dict[str, Any]] = None, source: str = "system",
                     confidence: float = 1.0) -> str:
        """Add new knowledge entry to the vector database"""
        with self.lock:
            try:
                # Generate unique ID
                entry_id = str(uuid.uuid4())
                
                # Generate embedding
                embedding = self.embedding_engine.generate_embedding(content, knowledge_type)
                
                # Create knowledge entry
                entry = KnowledgeEntry(
                    id=entry_id,
                    content=content,
                    knowledge_type=knowledge_type,
                    metadata=metadata or {},
                    embedding=embedding,
                    confidence=confidence,
                    tags=tags or [],
                    context=context or {},
                    source=source
                )
                
                # Store in ChromaDB
                collection = self.collections[knowledge_type]
                collection.add(
                    ids=[entry_id],
                    embeddings=[embedding.tolist()],
                    documents=[content],
                    metadatas=[{
                        "knowledge_type": knowledge_type.value,
                        "source": source,
                        "confidence": confidence,
                        "tags": json.dumps(tags or []),
                        "timestamp": entry.timestamp.isoformat()
                    }]
                )
                
                # Store metadata in SQLite
                with sqlite3.connect(self.metadata_db) as conn:
                    conn.execute("""
                        INSERT INTO knowledge_entries 
                        (id, content, knowledge_type, metadata, timestamp, confidence, 
                         tags, context, source, validation_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entry_id, content, knowledge_type.value, 
                        json.dumps(metadata or {}), entry.timestamp,
                        confidence, json.dumps(tags or []), 
                        json.dumps(context or {}), source, 0.0
                    ))
                
                # Cache entry
                self.knowledge_cache[entry_id] = entry
                
                # Update statistics
                self.stats["total_entries"] += 1
                self.stats["last_updated"] = datetime.now()
                
                logger.info(f"✅ Added knowledge entry: {entry_id} ({knowledge_type.value})")
                return entry_id
                
            except Exception as e:
                logger.error(f"❌ Error adding knowledge: {e}")
                return ""
    
    def query_knowledge(self, query: str, query_type: QueryType = QueryType.GENERAL_INQUIRY,
                       knowledge_types: Optional[List[KnowledgeType]] = None,
                       max_results: int = 10, min_similarity: float = 0.3,
                       include_context: bool = True) -> RetrievalResult:
        """Query the knowledge base using semantic search"""
        with self.lock:
            start_time = time.time()
            
            try:
                # Generate query embedding
                query_embedding = self.embedding_engine.generate_embedding(
                    query, 
                    KnowledgeType.MARKET_ANALYSIS,  # Default for queries
                    EmbeddingModel.MULTI_QA  # Better for questions
                )
                
                all_results = []
                total_candidates = 0
                
                # Search in relevant collections
                search_types = knowledge_types or list(KnowledgeType)
                
                for knowledge_type in search_types:
                    if knowledge_type not in self.collections:
                        continue
                    
                    collection = self.collections[knowledge_type]
                    
                    try:
                        # Query ChromaDB
                        results = collection.query(
                            query_embeddings=[query_embedding.tolist()],
                            n_results=min(max_results, 100),  # Limit per collection
                            include=["documents", "metadatas", "distances", "embeddings"]
                        )
                        
                        if results and results["ids"][0]:
                            for i, (doc_id, document, metadata, distance) in enumerate(zip(
                                results["ids"][0],
                                results["documents"][0], 
                                results["metadatas"][0],
                                results["distances"][0]
                            )):
                                # Convert distance to similarity
                                similarity = 1.0 - distance
                                
                                if similarity >= min_similarity:
                                    # Load full entry from cache or create
                                    if doc_id in self.knowledge_cache:
                                        entry = self.knowledge_cache[doc_id]
                                    else:
                                        entry = self._load_knowledge_entry(doc_id)
                                    
                                    if entry:
                                        all_results.append((entry, similarity))
                        
                        total_candidates += len(results["ids"][0]) if results["ids"] else 0
                        
                    except Exception as e:
                        logger.debug(f"Error querying {knowledge_type.value}: {e}")
                
                # Sort by similarity and take top results
                all_results.sort(key=lambda x: x[1], reverse=True)
                top_results = all_results[:max_results]
                
                # Extract entries and similarities
                entries = [result[0] for result in top_results]
                similarities = [result[1] for result in top_results]
                
                # Update access statistics
                for entry in entries:
                    entry.access_count += 1
                    entry.last_accessed = datetime.now()
                    self._update_entry_stats(entry)
                
                response_time = time.time() - start_time
                
                # Create retrieval result
                result = RetrievalResult(
                    entries=entries,
                    similarities=similarities,
                    query_embedding=query_embedding,
                    retrieval_time=response_time,
                    total_candidates=total_candidates,
                    filters_applied=[f"knowledge_types: {len(search_types)}", f"min_similarity: {min_similarity}"],
                    reasoning=f"Retrieved {len(entries)} relevant entries from {len(search_types)} knowledge categories"
                )
                
                # Update statistics
                self.stats["queries_served"] += 1
                
                # Log query for analysis
                self._log_query(query, query_type, len(entries), response_time)
                
                return result
                
            except Exception as e:
                logger.error(f"❌ Error querying knowledge: {e}")
                return RetrievalResult(
                    entries=[],
                    similarities=[],
                    query_embedding=np.array([]),
                    retrieval_time=time.time() - start_time,
                    total_candidates=0,
                    filters_applied=[],
                    reasoning=f"Query failed: {str(e)}"
                )
    
    def _load_knowledge_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Load knowledge entry from database"""
        try:
            with sqlite3.connect(self.metadata_db) as conn:
                cursor = conn.execute("""
                    SELECT * FROM knowledge_entries WHERE id = ?
                """, (entry_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                entry = KnowledgeEntry(
                    id=row[0],
                    content=row[1],
                    knowledge_type=KnowledgeType(row[2]),
                    metadata=json.loads(row[3]),
                    timestamp=datetime.fromisoformat(row[4]),
                    confidence=row[5],
                    tags=json.loads(row[6]),
                    context=json.loads(row[7]),
                    source=row[8],
                    validation_score=row[9],
                    access_count=row[10],
                    last_accessed=datetime.fromisoformat(row[11]) if row[11] else None,
                    effectiveness_score=row[12]
                )
                
                # Cache the entry
                self.knowledge_cache[entry_id] = entry
                return entry
                
        except Exception as e:
            logger.error(f"❌ Error loading knowledge entry {entry_id}: {e}")
            return None
    
    def _update_entry_stats(self, entry: KnowledgeEntry):
        """Update entry statistics in database"""
        try:
            with sqlite3.connect(self.metadata_db) as conn:
                conn.execute("""
                    UPDATE knowledge_entries 
                    SET access_count = ?, last_accessed = ?
                    WHERE id = ?
                """, (entry.access_count, entry.last_accessed, entry.id))
        except Exception as e:
            logger.debug(f"Error updating entry stats: {e}")
    
    def _log_query(self, query: str, query_type: QueryType, results_count: int, response_time: float):
        """Log query for analysis and improvement"""
        try:
            with sqlite3.connect(self.metadata_db) as conn:
                conn.execute("""
                    INSERT INTO query_history 
                    (query_text, query_type, results_count, response_time, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (query, query_type.value, results_count, response_time, datetime.now()))
        except Exception as e:
            logger.debug(f"Error logging query: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        try:
            with sqlite3.connect(self.metadata_db) as conn:
                # Count entries by type
                cursor = conn.execute("""
                    SELECT knowledge_type, COUNT(*) 
                    FROM knowledge_entries 
                    GROUP BY knowledge_type
                """)
                type_counts = dict(cursor.fetchall())
                
                # Recent activity
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM query_history 
                    WHERE timestamp > datetime('now', '-24 hours')
                """)
                recent_queries = cursor.fetchone()[0]
                
                # Top performing entries
                cursor = conn.execute("""
                    SELECT knowledge_type, COUNT(*) 
                    FROM knowledge_entries 
                    WHERE effectiveness_score > 0.7
                    GROUP BY knowledge_type
                """)
                high_performing = dict(cursor.fetchall())
            
            stats = {
                **self.stats,
                "entries_by_type": type_counts,
                "recent_queries_24h": recent_queries,
                "high_performing_entries": high_performing,
                "embedding_stats": self.embedding_engine.get_cache_stats(),
                "collections_count": len(self.collections)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting statistics: {e}")
            return self.stats

class PersonalizedRAGEngine:
    """
    🎭 Personalized RAG Engine for Trading Intelligence
    Retrieval-Augmented Generation specifically tuned for trading context
    """
    
    def __init__(self, knowledge_base: VectorKnowledgeBase):
        self.knowledge_base = knowledge_base
        
        # RAG configuration
        self.max_context_tokens = 4000
        self.max_retrieved_entries = 15
        self.similarity_threshold = 0.4
        self.context_window = 8192
        
        # Initialize tokenizer for context management
        if TIKTOKEN_AVAILABLE and tiktoken is not None:
            try:
                self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
            except Exception:
                # Fallback tokenizer
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
        else:
            logger.warning("⚠️ tiktoken not available - using simple token counting")
            self.tokenizer = None
        
        # Response templates for different query types
        self.response_templates = {
            QueryType.STRATEGY_RECOMMENDATION: """
Based on the trading knowledge and historical patterns, here's my analysis:

**Strategy Recommendation:**
{strategy_content}

**Supporting Evidence:**
{evidence}

**Risk Considerations:**
{risks}

**Historical Context:**
{historical_context}
            """,
            
            QueryType.MARKET_CONTEXT: """
**Current Market Analysis:**
{market_analysis}

**Relevant Patterns:**
{patterns}

**Key Insights:**
{insights}
            """,
            
            QueryType.DECISION_SUPPORT: """
**Decision Analysis:**
{decision_analysis}

**Recommended Action:**
{recommendation}

**Confidence Level:** {confidence}%

**Supporting Evidence:**
{evidence}

**Potential Risks:**
{risks}
            """
        }
        
        # Context enhancement strategies
        self.context_enhancers = {
            "market_regime": self._enhance_market_regime_context,
            "volatility": self._enhance_volatility_context, 
            "correlation": self._enhance_correlation_context,
            "sentiment": self._enhance_sentiment_context
        }
        
        # Performance tracking
        self.rag_stats = {
            "queries_processed": 0,
            "avg_response_time": 0.0,
            "context_utilization": 0.0,
            "user_satisfaction": 0.0
        }
    
    def generate_rag_response(self, query: str, query_type: QueryType = QueryType.GENERAL_INQUIRY,
                             user_context: Optional[Dict[str, Any]] = None,
                             trading_context: Optional[Dict[str, Any]] = None) -> RAGResponse:
        """Generate RAG-enhanced response for trading queries"""
        start_time = time.time()
        
        try:
            # Step 1: Retrieve relevant knowledge
            retrieval_result = self.knowledge_base.query_knowledge(
                query=query,
                query_type=query_type,
                max_results=self.max_retrieved_entries,
                min_similarity=self.similarity_threshold
            )
            
            if not retrieval_result.entries:
                return self._generate_fallback_response(query, query_type, start_time)
            
            # Step 2: Enhance context with trading-specific information
            enhanced_context = self._enhance_trading_context(
                retrieval_result.entries, 
                user_context or {},
                trading_context or {}
            )
            
            # Step 3: Build contextual prompt
            context_prompt = self._build_context_prompt(
                query, query_type, retrieval_result.entries, enhanced_context
            )
            
            # Step 4: Generate reasoning and insights
            reasoning_steps = self._generate_reasoning_steps(
                query, retrieval_result.entries, query_type
            )
            
            # Step 5: Create comprehensive response
            response_content = self._generate_response_content(
                query, query_type, retrieval_result.entries, enhanced_context, reasoning_steps
            )
            
            # Step 6: Extract citations and recommendations
            citations = self._extract_citations(retrieval_result.entries)
            recommendations = self._generate_recommendations(
                query, query_type, retrieval_result.entries, enhanced_context
            )
            
            # Step 7: Identify knowledge gaps
            knowledge_gaps = self._identify_knowledge_gaps(
                query, retrieval_result.entries, query_type
            )
            
            response_time = time.time() - start_time
            
            # Create RAG response
            rag_response = RAGResponse(
                content=response_content,
                knowledge_context=retrieval_result.entries,
                confidence=self._calculate_response_confidence(retrieval_result),
                reasoning_steps=reasoning_steps,
                citations=citations,
                generated_insights=self._generate_insights(retrieval_result.entries),
                knowledge_gaps=knowledge_gaps,
                recommendations=recommendations,
                response_time=response_time
            )
            
            # Update statistics
            self.rag_stats["queries_processed"] += 1
            self.rag_stats["avg_response_time"] = (
                (self.rag_stats["avg_response_time"] * (self.rag_stats["queries_processed"] - 1) + response_time) /
                self.rag_stats["queries_processed"]
            )
            
            return rag_response
            
        except Exception as e:
            logger.error(f"❌ Error generating RAG response: {e}")
            return self._generate_fallback_response(query, query_type, start_time)
    
    def _enhance_trading_context(self, entries: List[KnowledgeEntry], 
                               user_context: Dict[str, Any], 
                               trading_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance context with trading-specific information"""
        enhanced = {
            "market_regime": trading_context.get("market_regime", "unknown"),
            "volatility_regime": trading_context.get("volatility", "moderate"),
            "user_risk_profile": user_context.get("risk_tolerance", "moderate"),
            "preferred_assets": user_context.get("preferred_assets", []),
            "trading_style": user_context.get("trading_style", "balanced"),
            "recent_performance": user_context.get("recent_performance", {}),
            "knowledge_clusters": self._cluster_knowledge_entries(entries),
            "temporal_patterns": self._extract_temporal_patterns(entries),
            "confidence_distribution": self._analyze_confidence_distribution(entries)
        }
        
        # Apply context enhancers
        for enhancer_name, enhancer_func in self.context_enhancers.items():
            try:
                enhancement = enhancer_func(entries, trading_context)
                enhanced[f"enhanced_{enhancer_name}"] = enhancement
            except Exception as e:
                logger.debug(f"Context enhancer {enhancer_name} failed: {e}")
        
        return enhanced
    
    def _cluster_knowledge_entries(self, entries: List[KnowledgeEntry]) -> List[Dict[str, Any]]:
        """Cluster knowledge entries by similarity"""
        if len(entries) < 2:
            return []
        
        try:
            embeddings = np.array([entry.embedding for entry in entries if entry.embedding is not None])
            
            if len(embeddings) < 2:
                return []
            
            # Use KMeans clustering
            n_clusters = min(3, len(embeddings))
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            clusters = kmeans.fit_predict(embeddings)
            
            # Group entries by cluster
            clustered = defaultdict(list)
            for i, cluster_id in enumerate(clusters):
                if i < len(entries):
                    clustered[int(cluster_id)].append(entries[i])
            
            return [
                {
                    "cluster_id": cluster_id,
                    "entries": cluster_entries,
                    "dominant_type": max(
                        [entry.knowledge_type for entry in cluster_entries],
                        key=lambda x: sum(1 for e in cluster_entries if e.knowledge_type == x)
                    ).value,
                    "avg_confidence": np.mean([entry.confidence for entry in cluster_entries])
                }
                for cluster_id, cluster_entries in clustered.items()
            ]
            
        except Exception as e:
            logger.debug(f"Error clustering entries: {e}")
            return []
    
    def _extract_temporal_patterns(self, entries: List[KnowledgeEntry]) -> Dict[str, Any]:
        """Extract temporal patterns from knowledge entries"""
        if not entries:
            return {}
        
        timestamps = [entry.timestamp for entry in entries]
        
        return {
            "time_span_days": (max(timestamps) - min(timestamps)).days,
            "recent_entries_pct": sum(
                1 for ts in timestamps 
                if (datetime.now() - ts).days <= 30
            ) / len(timestamps),
            "knowledge_recency_score": np.mean([
                max(0, 1 - (datetime.now() - entry.timestamp).days / 365)
                for entry in entries
            ])
        }
    
    def _analyze_confidence_distribution(self, entries: List[KnowledgeEntry]) -> Dict[str, Any]:
        """Analyze confidence distribution of retrieved entries"""
        if not entries:
            return {}
        
        confidences = [entry.confidence for entry in entries]
        
        return {
            "avg_confidence": np.mean(confidences),
            "min_confidence": min(confidences),
            "max_confidence": max(confidences),
            "confidence_std": np.std(confidences),
            "high_confidence_ratio": sum(1 for c in confidences if c >= 0.8) / len(confidences)
        }
    
    def _enhance_market_regime_context(self, entries: List[KnowledgeEntry], 
                                     trading_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance context with market regime information"""
        market_regime = trading_context.get("market_regime", "unknown")
        
        # Find entries relevant to current market regime
        regime_relevant = [
            entry for entry in entries
            if market_regime.lower() in entry.content.lower() or
               any(market_regime.lower() in tag.lower() for tag in entry.tags)
        ]
        
        return {
            "current_regime": market_regime,
            "regime_relevant_entries": len(regime_relevant),
            "regime_insights": [
                entry.content[:200] + "..." if len(entry.content) > 200 else entry.content
                for entry in regime_relevant[:3]
            ]
        }
    
    def _enhance_volatility_context(self, entries: List[KnowledgeEntry], 
                                   trading_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance context with volatility information"""
        volatility = trading_context.get("volatility", "moderate")
        
        volatility_entries = [
            entry for entry in entries
            if "volatility" in entry.content.lower() or
               entry.knowledge_type == KnowledgeType.VOLATILITY_ANALYSIS
        ]
        
        return {
            "current_volatility": volatility,
            "volatility_relevant_count": len(volatility_entries),
            "volatility_insights": [
                entry.metadata.get("volatility_insight", "")
                for entry in volatility_entries[:3]
            ]
        }
    
    def _enhance_correlation_context(self, entries: List[KnowledgeEntry], 
                                    trading_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance context with correlation insights"""
        correlation_entries = [
            entry for entry in entries
            if entry.knowledge_type == KnowledgeType.CORRELATION_INSIGHT or
               "correlation" in entry.content.lower()
        ]
        
        return {
            "correlation_entries_count": len(correlation_entries),
            "correlation_insights": [
                entry.metadata.get("correlation_data", {})
                for entry in correlation_entries[:3]
            ]
        }
    
    def _enhance_sentiment_context(self, entries: List[KnowledgeEntry], 
                                  trading_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance context with sentiment analysis"""
        sentiment_entries = [
            entry for entry in entries
            if entry.knowledge_type == KnowledgeType.NEWS_SENTIMENT
        ]
        
        sentiments = []
        for entry in sentiment_entries:
            sentiment_data = entry.metadata.get("sentiment", {})
            if sentiment_data:
                sentiments.append(sentiment_data)
        
        if sentiments:
            avg_sentiment = np.mean([s.get("score", 0) for s in sentiments])
            sentiment_label = "bullish" if avg_sentiment > 0.1 else "bearish" if avg_sentiment < -0.1 else "neutral"
        else:
            avg_sentiment = 0.0
            sentiment_label = "neutral"
        
        return {
            "sentiment_entries_count": len(sentiment_entries),
            "avg_sentiment_score": avg_sentiment,
            "sentiment_label": sentiment_label,
            "sentiment_insights": sentiments[:3]
        }
    
    def _build_context_prompt(self, query: str, query_type: QueryType, 
                             entries: List[KnowledgeEntry], 
                             enhanced_context: Dict[str, Any]) -> str:
        """Build context prompt for RAG generation"""
        context_parts = [
            f"Query: {query}",
            f"Query Type: {query_type.value}",
            "",
            "Relevant Knowledge Context:",
        ]
        
        # Add knowledge entries
        for i, entry in enumerate(entries[:8]):  # Limit context size
            context_parts.append(f"""
Entry {i+1} ({entry.knowledge_type.value}):
Content: {entry.content[:300]}...
Confidence: {entry.confidence:.2f}
Tags: {', '.join(entry.tags[:3])}
---""")
        
        # Add enhanced context
        if enhanced_context.get("market_regime") != "unknown":
            context_parts.append(f"\nCurrent Market Regime: {enhanced_context['market_regime']}")
        
        if enhanced_context.get("volatility_regime"):
            context_parts.append(f"Volatility Environment: {enhanced_context['volatility_regime']}")
        
        # Add clustering insights
        clusters = enhanced_context.get("knowledge_clusters", [])
        if clusters:
            context_parts.append("\nKnowledge Clusters:")
            for cluster in clusters[:2]:
                context_parts.append(f"- {cluster['dominant_type']}: {len(cluster['entries'])} entries")
        
        return "\n".join(context_parts)
    
    def _generate_reasoning_steps(self, query: str, entries: List[KnowledgeEntry], 
                                query_type: QueryType) -> List[str]:
        """Generate reasoning steps for the response"""
        steps = []
        
        # Analysis step
        steps.append(f"Analyzed {len(entries)} relevant knowledge entries from trading database")
        
        # Knowledge type analysis
        knowledge_types = [entry.knowledge_type.value for entry in entries]
        type_counts = {kt: knowledge_types.count(kt) for kt in set(knowledge_types)}
        dominant_type = max(type_counts.items(), key=lambda x: x[1])
        steps.append(f"Primary knowledge focus: {dominant_type[0]} ({dominant_type[1]} entries)")
        
        # Confidence analysis
        avg_confidence = np.mean([entry.confidence for entry in entries])
        steps.append(f"Average confidence of retrieved knowledge: {avg_confidence:.2f}")
        
        # Recency analysis
        recent_entries = sum(1 for entry in entries if (datetime.now() - entry.timestamp).days <= 30)
        steps.append(f"Knowledge recency: {recent_entries}/{len(entries)} entries from last 30 days")
        
        # Query-specific reasoning
        if query_type == QueryType.STRATEGY_RECOMMENDATION:
            strategy_entries = [e for e in entries if e.knowledge_type == KnowledgeType.TRADING_STRATEGY]
            if strategy_entries:
                steps.append(f"Found {len(strategy_entries)} specific strategy recommendations")
        
        elif query_type == QueryType.RISK_GUIDANCE:
            risk_entries = [e for e in entries if e.knowledge_type == KnowledgeType.RISK_ASSESSMENT]
            if risk_entries:
                steps.append(f"Incorporated {len(risk_entries)} risk assessment insights")
        
        return steps
    
    def _generate_response_content(self, query: str, query_type: QueryType, 
                                 entries: List[KnowledgeEntry], 
                                 enhanced_context: Dict[str, Any], 
                                 reasoning_steps: List[str]) -> str:
        """Generate comprehensive response content"""
        
        # Start with contextual introduction
        response_parts = []
        
        if query_type == QueryType.STRATEGY_RECOMMENDATION:
            response_parts.append("**Trading Strategy Analysis:**")
            
            # Extract strategy-related content
            strategy_entries = [e for e in entries if e.knowledge_type == KnowledgeType.TRADING_STRATEGY]
            if strategy_entries:
                best_strategy = max(strategy_entries, key=lambda x: x.confidence)
                response_parts.append(f"Based on historical analysis, the recommended approach is: {best_strategy.content[:200]}...")
            
            # Add market context
            market_regime = enhanced_context.get("market_regime")
            if market_regime and market_regime != "unknown":
                response_parts.append(f"\nGiven the current {market_regime} market environment:")
                regime_entries = [e for e in entries if market_regime.lower() in e.content.lower()]
                if regime_entries:
                    response_parts.append(f"- {regime_entries[0].content[:150]}...")
        
        elif query_type == QueryType.MARKET_CONTEXT:
            response_parts.append("**Market Context Analysis:**")
            
            # Group entries by type
            analysis_entries = [e for e in entries if e.knowledge_type == KnowledgeType.MARKET_ANALYSIS]
            pattern_entries = [e for e in entries if e.knowledge_type == KnowledgeType.MARKET_PATTERN]
            
            if analysis_entries:
                response_parts.append("**Current Market Analysis:**")
                for entry in analysis_entries[:2]:
                    response_parts.append(f"- {entry.content[:150]}...")
            
            if pattern_entries:
                response_parts.append("\n**Relevant Patterns:**")
                for entry in pattern_entries[:2]:
                    response_parts.append(f"- {entry.content[:150]}...")
        
        elif query_type == QueryType.DECISION_SUPPORT:
            response_parts.append("**Decision Support Analysis:**")
            
            # Find decision-related entries
            decision_entries = [e for e in entries if e.knowledge_type == KnowledgeType.TRADING_DECISION]
            success_entries = [e for e in entries if e.knowledge_type == KnowledgeType.SUCCESS_PATTERN]
            error_entries = [e for e in entries if e.knowledge_type == KnowledgeType.ERROR_PATTERN]
            
            if success_entries:
                response_parts.append("**Success Patterns:**")
                for entry in success_entries[:2]:
                    response_parts.append(f"✅ {entry.content[:150]}...")
            
            if error_entries:
                response_parts.append("\n**Risk Considerations (from past errors):**")
                for entry in error_entries[:2]:
                    response_parts.append(f"⚠️ {entry.content[:150]}...")
        
        else:  # General inquiry
            response_parts.append("**Trading Intelligence Analysis:**")
            
            # Organize by knowledge type
            knowledge_summary = {}
            for entry in entries[:5]:  # Top 5 most relevant
                kt = entry.knowledge_type.value
                if kt not in knowledge_summary:
                    knowledge_summary[kt] = []
                knowledge_summary[kt].append(entry.content[:120] + "...")
            
            for knowledge_type, contents in knowledge_summary.items():
                response_parts.append(f"\n**{knowledge_type.replace('_', ' ').title()}:**")
                for content in contents[:2]:  # Max 2 per type
                    response_parts.append(f"• {content}")
        
        # Add confidence and recency information
        avg_confidence = np.mean([entry.confidence for entry in entries])
        response_parts.append(f"\n**Analysis Confidence:** {avg_confidence:.1%}")
        
        recent_count = sum(1 for entry in entries if (datetime.now() - entry.timestamp).days <= 7)
        if recent_count > 0:
            response_parts.append(f"**Recent Insights:** {recent_count} entries from the last 7 days")
        
        return "\n".join(response_parts)
    
    def _extract_citations(self, entries: List[KnowledgeEntry]) -> List[str]:
        """Extract citations from knowledge entries"""
        citations = []
        
        for i, entry in enumerate(entries[:5]):  # Top 5 for citations
            citation = f"[{i+1}] {entry.knowledge_type.value} - " \
                      f"Confidence: {entry.confidence:.2f}, " \
                      f"Source: {entry.source}, " \
                      f"Date: {entry.timestamp.strftime('%Y-%m-%d')}"
            citations.append(citation)
        
        return citations
    
    def _generate_recommendations(self, query: str, query_type: QueryType, 
                                entries: List[KnowledgeEntry], 
                                enhanced_context: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Base recommendations from knowledge
        success_entries = [e for e in entries if e.knowledge_type == KnowledgeType.SUCCESS_PATTERN]
        for entry in success_entries[:2]:
            rec = f"Apply proven pattern: {entry.content[:100]}..."
            recommendations.append(rec)
        
        # Risk-based recommendations
        error_entries = [e for e in entries if e.knowledge_type == KnowledgeType.ERROR_PATTERN]
        for entry in error_entries[:2]:
            rec = f"Avoid known pitfall: {entry.content[:100]}..."
            recommendations.append(rec)
        
        # Context-specific recommendations
        market_regime = enhanced_context.get("market_regime")
        if market_regime == "high_volatility":
            recommendations.append("Consider reducing position sizes due to high volatility environment")
        elif market_regime == "low_volatility":
            recommendations.append("Current low volatility may allow for slightly larger position sizes")
        
        # User-specific recommendations
        risk_profile = enhanced_context.get("user_risk_profile", "moderate")
        if risk_profile == "conservative":
            recommendations.append("Focus on lower-risk strategies given your conservative profile")
        elif risk_profile == "aggressive":
            recommendations.append("Higher-risk strategies may align with your aggressive profile")
        
        return recommendations[:5]  # Limit to 5 recommendations
    
    def _identify_knowledge_gaps(self, query: str, entries: List[KnowledgeEntry], 
                               query_type: QueryType) -> List[str]:
        """Identify gaps in knowledge that could improve responses"""
        gaps = []
        
        # Check for missing knowledge types
        present_types = set(entry.knowledge_type for entry in entries)
        
        if query_type == QueryType.STRATEGY_RECOMMENDATION:
            if KnowledgeType.RISK_ASSESSMENT not in present_types:
                gaps.append("Risk assessment data for recommended strategies")
            if KnowledgeType.PERFORMANCE_INSIGHT not in present_types:
                gaps.append("Historical performance data for strategy validation")
        
        elif query_type == QueryType.MARKET_CONTEXT:
            if KnowledgeType.NEWS_SENTIMENT not in present_types:
                gaps.append("Current news sentiment analysis")
            if KnowledgeType.CORRELATION_INSIGHT not in present_types:
                gaps.append("Asset correlation analysis")
        
        # Check for low confidence
        low_confidence_entries = sum(1 for entry in entries if entry.confidence < 0.6)
        if low_confidence_entries > len(entries) / 2:
            gaps.append("Higher confidence knowledge sources needed")
        
        # Check for recency
        old_entries = sum(1 for entry in entries if (datetime.now() - entry.timestamp).days > 90)
        if old_entries > len(entries) / 2:
            gaps.append("More recent market data and insights")
        
        return gaps
    
    def _generate_insights(self, entries: List[KnowledgeEntry]) -> List[str]:
        """Generate novel insights from retrieved knowledge"""
        insights = []
        
        # Pattern insights
        knowledge_types = [entry.knowledge_type for entry in entries]
        type_diversity = len(set(knowledge_types)) / len(KnowledgeType)
        if type_diversity > 0.5:
            insights.append(f"High knowledge diversity suggests complex market dynamics")
        
        # Temporal insights
        timestamps = [entry.timestamp for entry in entries]
        if timestamps:
            time_span = (max(timestamps) - min(timestamps)).days
            if time_span > 180:
                insights.append(f"Long-term perspective available: {time_span} days of historical context")
        
        # Confidence insights
        confidences = [entry.confidence for entry in entries]
        high_conf_ratio = sum(1 for c in confidences if c > 0.8) / len(confidences)
        if high_conf_ratio > 0.7:
            insights.append("High confidence knowledge base supports reliable recommendations")
        
        # Content insights
        combined_content = " ".join([entry.content for entry in entries[:5]])
        if "risk" in combined_content.lower():
            risk_mentions = combined_content.lower().count("risk")
            insights.append(f"Risk considerations feature prominently ({risk_mentions} mentions)")
        
        return insights[:3]  # Limit to 3 insights
    
    def _calculate_response_confidence(self, retrieval_result: RetrievalResult) -> float:
        """Calculate overall confidence in the response"""
        if not retrieval_result.entries:
            return 0.0
        
        # Factors for confidence calculation
        similarity_score = np.mean(retrieval_result.similarities) if retrieval_result.similarities else 0.0
        knowledge_confidence = np.mean([entry.confidence for entry in retrieval_result.entries])
        coverage_score = min(1.0, len(retrieval_result.entries) / 10)  # 10 entries = full coverage
        
        # Recency factor
        recent_entries = sum(1 for entry in retrieval_result.entries 
                           if (datetime.now() - entry.timestamp).days <= 30)
        recency_score = recent_entries / len(retrieval_result.entries)
        
        # Weighted combination
        confidence = float(
            similarity_score * 0.3 +
            knowledge_confidence * 0.3 +
            coverage_score * 0.2 +
            recency_score * 0.2
        )
        
        return min(1.0, max(0.0, confidence))
    
    def _generate_fallback_response(self, query: str, query_type: QueryType, start_time: float) -> RAGResponse:
        """Generate fallback response when no knowledge is retrieved"""
        return RAGResponse(
            content=f"I don't have sufficient knowledge to provide a comprehensive answer about '{query}'. "
                   "This suggests we need to build more knowledge in this area.",
            knowledge_context=[],
            confidence=0.1,
            reasoning_steps=["No relevant knowledge found in database", "Fallback response generated"],
            citations=[],
            generated_insights=[],
            knowledge_gaps=[f"Missing knowledge for query type: {query_type.value}"],
            recommendations=["Consider adding more knowledge entries for this topic"],
            response_time=time.time() - start_time
        )
    
    def get_rag_statistics(self) -> Dict[str, Any]:
        """Get RAG engine performance statistics"""
        return {
            **self.rag_stats,
            "knowledge_base_stats": self.knowledge_base.get_statistics(),
            "context_window_size": self.context_window,
            "max_retrieved_entries": self.max_retrieved_entries,
            "similarity_threshold": self.similarity_threshold
        }

class ContinualLearningSystem:
    """
    📚 Continual Learning System for Trading Knowledge
    Automatically learns from trading decisions and outcomes
    """
    
    def __init__(self, knowledge_base: VectorKnowledgeBase, learning_db_path: str = "data_cache/learning_system"):
        self.knowledge_base = knowledge_base
        self.learning_db_path = Path(learning_db_path)
        self.learning_db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize learning database
        self.learning_db = self.learning_db_path / "learning.db"
        self._initialize_learning_db()
        
        # Learning configuration
        self.learning_config = {
            "min_outcome_samples": 5,  # Minimum samples before learning
            "success_threshold": 0.7,  # Threshold for successful outcomes
            "confidence_update_rate": 0.1,  # Rate of confidence updates
            "pattern_similarity_threshold": 0.8,  # Similarity for pattern matching
            "learning_decay_rate": 0.95,  # Decay rate for old learnings
        }
        
        # Pattern recognition
        self.pattern_cache = {}
        self.outcome_history = deque(maxlen=1000)
        
        # Learning statistics
        self.learning_stats = {
            "decisions_tracked": 0,
            "patterns_learned": 0,
            "knowledge_updates": 0,
            "success_rate_improvements": 0,
        }
    
    def _initialize_learning_db(self):
        """Initialize learning database"""
        try:
            with sqlite3.connect(self.learning_db) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS trading_decisions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        decision_id TEXT UNIQUE,
                        decision_type TEXT,
                        context TEXT,
                        prediction TEXT,
                        actual_outcome TEXT,
                        success_score REAL,
                        timestamp DATETIME,
                        symbol TEXT,
                        strategy TEXT,
                        market_conditions TEXT,
                        confidence REAL
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS learned_patterns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pattern_id TEXT UNIQUE,
                        pattern_type TEXT,
                        pattern_data TEXT,
                        success_rate REAL,
                        sample_count INTEGER,
                        last_updated DATETIME,
                        confidence REAL,
                        validation_score REAL
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_evolution (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        knowledge_id TEXT,
                        update_type TEXT,
                        old_confidence REAL,
                        new_confidence REAL,
                        reason TEXT,
                        timestamp DATETIME
                    )
                """)
                
                # Create indices
                conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_symbol ON trading_decisions(symbol)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON trading_decisions(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_type ON learned_patterns(pattern_type)")
                
            logger.info("✅ Learning database initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing learning database: {e}")
    
    def track_trading_decision(self, decision_id: str, decision_type: str, 
                             context: Dict[str, Any], prediction: str,
                             symbol: str = "", strategy: str = "", 
                             market_conditions: Optional[Dict[str, Any]] = None,
                             confidence: float = 1.0):
        """Track a trading decision for later learning"""
        try:
            with sqlite3.connect(self.learning_db) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO trading_decisions 
                    (decision_id, decision_type, context, prediction, symbol, 
                     strategy, market_conditions, confidence, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    decision_id, decision_type, json.dumps(context), prediction,
                    symbol, strategy, json.dumps(market_conditions or {}),
                    confidence, datetime.now()
                ))
            
            self.learning_stats["decisions_tracked"] += 1
            logger.debug(f"✅ Tracked decision: {decision_id}")
            
        except Exception as e:
            logger.error(f"❌ Error tracking decision: {e}")
    
    def record_decision_outcome(self, decision_id: str, actual_outcome: str, 
                              success_score: float):
        """Record the actual outcome of a tracked decision"""
        try:
            with sqlite3.connect(self.learning_db) as conn:
                # Update the decision with outcome
                conn.execute("""
                    UPDATE trading_decisions 
                    SET actual_outcome = ?, success_score = ?
                    WHERE decision_id = ?
                """, (actual_outcome, success_score, decision_id))
                
                # Get the decision details
                cursor = conn.execute("""
                    SELECT * FROM trading_decisions WHERE decision_id = ?
                """, (decision_id,))
                
                decision_row = cursor.fetchone()
                
            if decision_row:
                # Add to outcome history
                self.outcome_history.append({
                    "decision_id": decision_id,
                    "success_score": success_score,
                    "decision_type": decision_row[2],
                    "timestamp": datetime.now()
                })
                
                # Trigger learning process
                self._process_decision_outcome(decision_row, success_score)
                
                logger.debug(f"✅ Recorded outcome for decision: {decision_id}")
            
        except Exception as e:
            logger.error(f"❌ Error recording outcome: {e}")
    
    def _process_decision_outcome(self, decision_row: Tuple, success_score: float):
        """Process a decision outcome for learning"""
        try:
            decision_type = decision_row[2]
            context = json.loads(decision_row[3]) if decision_row[3] else {}
            prediction = decision_row[4]
            actual_outcome = decision_row[5]
            symbol = decision_row[8]
            strategy = decision_row[9]
            
            # Extract patterns from successful decisions
            if success_score >= self.learning_config["success_threshold"]:
                self._extract_success_pattern(decision_type, context, prediction, symbol, strategy)
            
            # Extract patterns from failed decisions
            if success_score < 0.3:  # Failed decision threshold
                self._extract_failure_pattern(decision_type, context, prediction, symbol, strategy)
            
            # Update related knowledge entries
            self._update_knowledge_confidence(context, success_score)
            
        except Exception as e:
            logger.error(f"❌ Error processing decision outcome: {e}")
    
    def _extract_success_pattern(self, decision_type: str, context: Dict[str, Any], 
                                prediction: str, symbol: str, strategy: str):
        """Extract pattern from successful decision"""
        try:
            pattern_data = {
                "decision_type": decision_type,
                "context_features": {
                    key: value for key, value in context.items()
                    if isinstance(value, (str, int, float, bool))
                },
                "prediction": prediction,
                "symbol": symbol,
                "strategy": strategy
            }
            
            # Generate pattern ID
            pattern_string = json.dumps(pattern_data, sort_keys=True)
            pattern_id = hashlib.md5(pattern_string.encode()).hexdigest()[:16]
            
            # Check if similar pattern exists
            similar_pattern = self._find_similar_pattern(pattern_data, "success")
            
            if similar_pattern:
                # Update existing pattern
                self._update_pattern_statistics(similar_pattern["pattern_id"], True)
            else:
                # Create new pattern
                self._create_new_pattern(pattern_id, "success", pattern_data)
            
            # Add to knowledge base as success pattern
            success_content = f"Successful {decision_type} decision: {prediction}. "
            success_content += f"Context: {json.dumps(pattern_data['context_features'])}"
            
            self.knowledge_base.add_knowledge(
                content=success_content,
                knowledge_type=KnowledgeType.SUCCESS_PATTERN,
                metadata={
                    "pattern_id": pattern_id,
                    "decision_type": decision_type,
                    "symbol": symbol,
                    "strategy": strategy,
                    "learned_from": "continual_learning"
                },
                tags=["success", decision_type, symbol, strategy],
                source="learning_system",
                confidence=0.8
            )
            
            self.learning_stats["patterns_learned"] += 1
            
        except Exception as e:
            logger.error(f"❌ Error extracting success pattern: {e}")
    
    def _extract_failure_pattern(self, decision_type: str, context: Dict[str, Any], 
                                prediction: str, symbol: str, strategy: str):
        """Extract pattern from failed decision"""
        try:
            pattern_data = {
                "decision_type": decision_type,
                "context_features": {
                    key: value for key, value in context.items()
                    if isinstance(value, (str, int, float, bool))
                },
                "prediction": prediction,
                "symbol": symbol,
                "strategy": strategy
            }
            
            # Generate pattern ID
            pattern_string = json.dumps(pattern_data, sort_keys=True)
            pattern_id = hashlib.md5(pattern_string.encode()).hexdigest()[:16]
            
            # Check if similar pattern exists
            similar_pattern = self._find_similar_pattern(pattern_data, "failure")
            
            if similar_pattern:
                # Update existing pattern
                self._update_pattern_statistics(similar_pattern["pattern_id"], False)
            else:
                # Create new pattern
                self._create_new_pattern(pattern_id, "failure", pattern_data)
            
            # Add to knowledge base as error pattern
            error_content = f"Failed {decision_type} decision to avoid: {prediction}. "
            error_content += f"Context that led to failure: {json.dumps(pattern_data['context_features'])}"
            
            self.knowledge_base.add_knowledge(
                content=error_content,
                knowledge_type=KnowledgeType.ERROR_PATTERN,
                metadata={
                    "pattern_id": pattern_id,
                    "decision_type": decision_type,
                    "symbol": symbol,
                    "strategy": strategy,
                    "learned_from": "continual_learning"
                },
                tags=["error", decision_type, symbol, strategy],
                source="learning_system",
                confidence=0.8
            )
            
            self.learning_stats["patterns_learned"] += 1
            
        except Exception as e:
            logger.error(f"❌ Error extracting failure pattern: {e}")
    
    def _find_similar_pattern(self, pattern_data: Dict[str, Any], pattern_type: str) -> Optional[Dict]:
        """Find similar existing pattern"""
        try:
            with sqlite3.connect(self.learning_db) as conn:
                cursor = conn.execute("""
                    SELECT pattern_id, pattern_data, success_rate, sample_count 
                    FROM learned_patterns 
                    WHERE pattern_type = ?
                """, (pattern_type,))
                
                existing_patterns = cursor.fetchall()
            
            for pattern_row in existing_patterns:
                existing_data = json.loads(pattern_row[1])
                similarity = self._calculate_pattern_similarity(pattern_data, existing_data)
                
                if similarity >= self.learning_config["pattern_similarity_threshold"]:
                    return {
                        "pattern_id": pattern_row[0],
                        "pattern_data": existing_data,
                        "success_rate": pattern_row[2],
                        "sample_count": pattern_row[3],
                        "similarity": similarity
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error finding similar pattern: {e}")
            return None
    
    def _calculate_pattern_similarity(self, pattern1: Dict[str, Any], pattern2: Dict[str, Any]) -> float:
        """Calculate similarity between two patterns"""
        try:
            # Simple similarity based on matching features
            matching_features = 0
            total_features = 0
            
            # Compare context features
            context1 = pattern1.get("context_features", {})
            context2 = pattern2.get("context_features", {})
            
            all_keys = set(context1.keys()) | set(context2.keys())
            total_features += len(all_keys)
            
            for key in all_keys:
                if key in context1 and key in context2:
                    if context1[key] == context2[key]:
                        matching_features += 1
                    elif isinstance(context1[key], (int, float)) and isinstance(context2[key], (int, float)):
                        # Numerical similarity
                        diff = abs(context1[key] - context2[key])
                        max_val = max(abs(context1[key]), abs(context2[key]), 1)
                        similarity = 1 - (diff / max_val)
                        matching_features += max(0, similarity)
            
            # Compare other features
            for feature in ["decision_type", "symbol", "strategy"]:
                total_features += 1
                if pattern1.get(feature) == pattern2.get(feature):
                    matching_features += 1
            
            return matching_features / total_features if total_features > 0 else 0.0
            
        except Exception as e:
            logger.error(f"❌ Error calculating pattern similarity: {e}")
            return 0.0
    
    def _create_new_pattern(self, pattern_id: str, pattern_type: str, pattern_data: Dict[str, Any]):
        """Create new learned pattern"""
        try:
            with sqlite3.connect(self.learning_db) as conn:
                conn.execute("""
                    INSERT INTO learned_patterns 
                    (pattern_id, pattern_type, pattern_data, success_rate, 
                     sample_count, last_updated, confidence, validation_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern_id, pattern_type, json.dumps(pattern_data),
                    1.0 if pattern_type == "success" else 0.0,
                    1, datetime.now(), 0.5, 0.0
                ))
                
        except Exception as e:
            logger.error(f"❌ Error creating new pattern: {e}")
    
    def _update_pattern_statistics(self, pattern_id: str, was_successful: bool):
        """Update statistics for existing pattern"""
        try:
            with sqlite3.connect(self.learning_db) as conn:
                # Get current statistics
                cursor = conn.execute("""
                    SELECT success_rate, sample_count FROM learned_patterns 
                    WHERE pattern_id = ?
                """, (pattern_id,))
                
                row = cursor.fetchone()
                if not row:
                    return
                
                current_success_rate, sample_count = row
                
                # Update statistics
                new_sample_count = sample_count + 1
                new_success_rate = (
                    (current_success_rate * sample_count + (1.0 if was_successful else 0.0)) /
                    new_sample_count
                )
                
                # Update database
                conn.execute("""
                    UPDATE learned_patterns 
                    SET success_rate = ?, sample_count = ?, last_updated = ?
                    WHERE pattern_id = ?
                """, (new_success_rate, new_sample_count, datetime.now(), pattern_id))
                
        except Exception as e:
            logger.error(f"❌ Error updating pattern statistics: {e}")
    
    def _update_knowledge_confidence(self, context: Dict[str, Any], success_score: float):
        """Update confidence of related knowledge entries based on outcomes"""
        try:
            # Find potentially related knowledge entries
            related_queries = [
                context.get("strategy", ""),
                context.get("symbol", ""),
                context.get("decision_reason", ""),
            ]
            
            for query in related_queries:
                if not query:
                    continue
                
                # Query for related knowledge
                retrieval_result = self.knowledge_base.query_knowledge(
                    query=query,
                    max_results=5,
                    min_similarity=0.6
                )
                
                for entry in retrieval_result.entries:
                    # Calculate confidence adjustment
                    confidence_adjustment = (success_score - 0.5) * self.learning_config["confidence_update_rate"]
                    new_confidence = max(0.1, min(1.0, entry.confidence + confidence_adjustment))
                    
                    if abs(confidence_adjustment) > 0.01:  # Only update if significant change
                        # Log the knowledge evolution
                        with sqlite3.connect(self.learning_db) as conn:
                            conn.execute("""
                                INSERT INTO knowledge_evolution 
                                (knowledge_id, update_type, old_confidence, new_confidence, reason, timestamp)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (
                                entry.id, "outcome_learning", entry.confidence, new_confidence,
                                f"Updated based on success_score: {success_score}", datetime.now()
                            ))
                        
                        # Update the entry (this would need to be implemented in knowledge base)
                        entry.confidence = new_confidence
                        self.learning_stats["knowledge_updates"] += 1
                
        except Exception as e:
            logger.error(f"❌ Error updating knowledge confidence: {e}")
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights from the learning system"""
        try:
            with sqlite3.connect(self.learning_db) as conn:
                # Success rate by decision type
                cursor = conn.execute("""
                    SELECT decision_type, AVG(success_score), COUNT(*)
                    FROM trading_decisions 
                    WHERE actual_outcome IS NOT NULL
                    GROUP BY decision_type
                """)
                success_by_type = {row[0]: {"avg_success": row[1], "count": row[2]} 
                                  for row in cursor.fetchall()}
                
                # Success rate by symbol
                cursor = conn.execute("""
                    SELECT symbol, AVG(success_score), COUNT(*)
                    FROM trading_decisions 
                    WHERE actual_outcome IS NOT NULL AND symbol != ''
                    GROUP BY symbol
                    ORDER BY COUNT(*) DESC
                    LIMIT 10
                """)
                success_by_symbol = {row[0]: {"avg_success": row[1], "count": row[2]} 
                                    for row in cursor.fetchall()}
                
                # Top patterns
                cursor = conn.execute("""
                    SELECT pattern_type, AVG(success_rate), COUNT(*)
                    FROM learned_patterns
                    GROUP BY pattern_type
                """)
                pattern_stats = {row[0]: {"avg_success_rate": row[1], "count": row[2]} 
                               for row in cursor.fetchall()}
                
                # Recent performance trend
                cursor = conn.execute("""
                    SELECT DATE(timestamp), AVG(success_score)
                    FROM trading_decisions 
                    WHERE actual_outcome IS NOT NULL 
                      AND timestamp > datetime('now', '-30 days')
                    GROUP BY DATE(timestamp)
                    ORDER BY DATE(timestamp)
                """)
                recent_trend = [(row[0], row[1]) for row in cursor.fetchall()]
            
            return {
                "learning_stats": self.learning_stats,
                "success_by_decision_type": success_by_type,
                "success_by_symbol": success_by_symbol,
                "pattern_statistics": pattern_stats,
                "recent_performance_trend": recent_trend,
                "outcome_history_size": len(self.outcome_history)
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting learning insights: {e}")
            return {"learning_stats": self.learning_stats}

class AdvancedMemoryRAGSystem:
    """
    🌟 ADVANCED MEMORY RAG SYSTEM - MAIN ORCHESTRATOR
    Complete integration of Vector Knowledge Base, RAG Engine, and Continual Learning
    """
    
    def __init__(self, base_path: str = "data_cache/advanced_memory"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize core components
        logger.info("🚀 Initializing Advanced Memory RAG System...")
        
        self.knowledge_base = VectorKnowledgeBase(str(self.base_path / "knowledge"))
        self.rag_engine = PersonalizedRAGEngine(self.knowledge_base)
        self.learning_system = ContinualLearningSystem(self.knowledge_base, str(self.base_path / "learning"))
        
        # Integration with AGUS 2.0 (if available)
        self.agus_integration = None
        if AIProvider:
            try:
                # This would integrate with existing AGUS system
                logger.info("✅ AGUS 2.0 integration available")
            except Exception as e:
                logger.warning(f"AGUS 2.0 integration failed: {e}")
        
        # System statistics
        self.system_stats = {
            "initialized_at": datetime.now(),
            "total_queries": 0,
            "total_knowledge_entries": 0,
            "total_learning_decisions": 0,
            "uptime_hours": 0.0
        }
        
        logger.info("✅ Advanced Memory RAG System initialized successfully!")
    
    def add_trading_knowledge(self, content: str, knowledge_type: KnowledgeType, 
                             metadata: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """Add trading knowledge to the system"""
        return self.knowledge_base.add_knowledge(
            content=content,
            knowledge_type=knowledge_type,
            metadata=metadata,
            **kwargs
        )
    
    def query_trading_intelligence(self, query: str, query_type: QueryType = QueryType.GENERAL_INQUIRY,
                                  user_context: Optional[Dict[str, Any]] = None,
                                  trading_context: Optional[Dict[str, Any]] = None) -> RAGResponse:
        """Main interface for querying trading intelligence"""
        self.system_stats["total_queries"] += 1
        
        # Generate RAG response
        response = self.rag_engine.generate_rag_response(
            query=query,
            query_type=query_type,
            user_context=user_context,
            trading_context=trading_context
        )
        
        return response
    
    def learn_from_decision(self, decision_id: str, decision_type: str,
                           context: Dict[str, Any], prediction: str,
                           **kwargs):
        """Track a trading decision for learning"""
        self.learning_system.track_trading_decision(
            decision_id=decision_id,
            decision_type=decision_type,
            context=context,
            prediction=prediction,
            **kwargs
        )
        
        self.system_stats["total_learning_decisions"] += 1
    
    def record_decision_outcome(self, decision_id: str, actual_outcome: str, success_score: float):
        """Record the outcome of a decision for learning"""
        self.learning_system.record_decision_outcome(decision_id, actual_outcome, success_score)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        uptime = (datetime.now() - self.system_stats["initialized_at"]).total_seconds() / 3600
        self.system_stats["uptime_hours"] = uptime
        
        return {
            "system_stats": self.system_stats,
            "knowledge_base_stats": self.knowledge_base.get_statistics(),
            "rag_engine_stats": self.rag_engine.get_rag_statistics(),
            "learning_insights": self.learning_system.get_learning_insights(),
            "health_status": "operational"
        }
    
    def initialize_with_base_knowledge(self):
        """Initialize system with base trading knowledge"""
        base_knowledge = [
            {
                "content": "Risk management is the cornerstone of successful trading. Never risk more than 1-2% of your account on a single trade.",
                "knowledge_type": KnowledgeType.RISK_ASSESSMENT,
                "metadata": {"importance": "critical", "category": "risk_management"},
                "tags": ["risk", "position_sizing", "money_management"]
            },
            {
                "content": "Trend following strategies work best in trending markets. Look for higher highs and higher lows in uptrends.",
                "knowledge_type": KnowledgeType.TRADING_STRATEGY,
                "metadata": {"strategy_type": "trend_following", "market_condition": "trending"},
                "tags": ["trend", "strategy", "market_structure"]
            },
            {
                "content": "High volatility environments require reduced position sizes and wider stop losses to avoid premature exits.",
                "knowledge_type": KnowledgeType.VOLATILITY_ANALYSIS,
                "metadata": {"volatility_regime": "high", "adjustment": "position_sizing"},
                "tags": ["volatility", "position_sizing", "stop_loss"]
            },
            {
                "content": "Market correlations break down during crisis periods. Diversification may not provide protection when it's needed most.",
                "knowledge_type": KnowledgeType.CORRELATION_INSIGHT,
                "metadata": {"market_condition": "crisis", "diversification": "limited"},
                "tags": ["correlation", "crisis", "diversification"]
            },
            {
                "content": "Successful trading requires maintaining detailed records of all trades including entry/exit reasons and market conditions.",
                "knowledge_type": KnowledgeType.PERFORMANCE_INSIGHT,
                "metadata": {"category": "record_keeping", "importance": "high"},
                "tags": ["record_keeping", "analysis", "improvement"]
            }
        ]
        
        for knowledge in base_knowledge:
            self.add_trading_knowledge(**knowledge)
        
        logger.info(f"✅ Initialized system with {len(base_knowledge)} base knowledge entries")

# Example usage and integration
if __name__ == "__main__":
    # Initialize the Advanced Memory RAG System
    memory_system = AdvancedMemoryRAGSystem()
    
    # Initialize with base knowledge
    memory_system.initialize_with_base_knowledge()
    
    # Example query
    response = memory_system.query_trading_intelligence(
        query="What should I consider when trading in a high volatility market?",
        query_type=QueryType.RISK_GUIDANCE,
        trading_context={"market_regime": "high_volatility", "volatility": 0.35}
    )
    
    print("RAG Response:")
    print(response.content)
    print("\nConfidence:", f"{response.confidence:.2%}")
    print("\nRecommendations:")
    for rec in response.recommendations:
        print(f"• {rec}")
    
    # Example learning
    memory_system.learn_from_decision(
        decision_id="trade_001",
        decision_type="position_entry",
        context={"symbol": "AAPL", "market_regime": "trending", "volatility": 0.25},
        prediction="bullish_breakout"
    )
    
    # Simulate outcome
    memory_system.record_decision_outcome(
        decision_id="trade_001",
        actual_outcome="successful_breakout",
        success_score=0.85
    )
    
    # Get system status
    status = memory_system.get_system_status()
    print(f"\nSystem Status: {status['health_status']}")
    print(f"Total Queries: {status['system_stats']['total_queries']}")
    print(f"Knowledge Entries: {status['knowledge_base_stats']['total_entries']}")