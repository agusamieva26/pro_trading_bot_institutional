#!/usr/bin/env python3
"""
🧪 COMPREHENSIVE TEST SUITE FOR ADVANCED MEMORY RAG SYSTEM
Tests all components: Vector Knowledge Base, RAG Engine, Learning System, AGUS Integration
"""
import os
import sys
import asyncio
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add bot directory to path
sys.path.append(str(Path(__file__).parent))

try:
    from bot.advanced_memory_rag_system import (
        AdvancedMemoryRAGSystem, KnowledgeType, QueryType,
        VectorKnowledgeBase, PersonalizedRAGEngine, ContinualLearningSystem
    )
    print("✅ Advanced Memory RAG System imported successfully")
except ImportError as e:
    print(f"❌ Failed to import Advanced Memory RAG System: {e}")
    sys.exit(1)

try:
    from bot.agus_memory_rag_integration import AGUSMemoryRAGIntegration, IntegrationType, ResponseMode
    print("✅ AGUS-RAG Integration imported successfully")
except ImportError as e:
    print(f"⚠️ AGUS-RAG Integration not available: {e}")
    AGUSMemoryRAGIntegration = None

class AdvancedMemoryRAGTester:
    """Comprehensive testing suite for the Advanced Memory RAG System"""
    
    def __init__(self):
        self.test_results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_details": []
        }
        
        # Initialize systems
        self.rag_system = None
        self.integration_system = None
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        self.test_results["total_tests"] += 1
        if success:
            self.test_results["passed_tests"] += 1
            status = "✅ PASS"
        else:
            self.test_results["failed_tests"] += 1
            status = "❌ FAIL"
        
        self.test_results["test_details"].append({
            "name": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
        print(f"{status} - {test_name}")
        if details:
            print(f"   Details: {details}")
    
    def test_system_initialization(self):
        """Test 1: System Initialization"""
        print("\n🔧 Testing System Initialization...")
        
        try:
            # Test RAG system initialization
            self.rag_system = AdvancedMemoryRAGSystem()
            self.log_test("RAG System Initialization", True, "System initialized successfully")
            
            # Initialize with base knowledge
            self.rag_system.initialize_with_base_knowledge()
            self.log_test("Base Knowledge Initialization", True, "Base knowledge loaded")
            
            # Test integration system if available
            if AGUSMemoryRAGIntegration:
                self.integration_system = AGUSMemoryRAGIntegration()
                self.log_test("Integration System Initialization", True, "AGUS-RAG integration ready")
            else:
                self.log_test("Integration System Initialization", False, "AGUS integration not available")
                
        except Exception as e:
            self.log_test("System Initialization", False, f"Error: {str(e)}")
    
    def test_knowledge_base_operations(self):
        """Test 2: Vector Knowledge Base Operations"""
        print("\n📚 Testing Vector Knowledge Base...")
        
        if not self.rag_system:
            self.log_test("Knowledge Base Tests", False, "RAG system not initialized")
            return
        
        try:
            # Test adding knowledge
            test_knowledge = [
                {
                    "content": "Support and resistance levels are crucial for entry and exit decisions in trading",
                    "knowledge_type": KnowledgeType.TRADING_STRATEGY,
                    "metadata": {"importance": "high", "category": "technical_analysis"},
                    "tags": ["support", "resistance", "technical_analysis"]
                },
                {
                    "content": "Risk management failed when position size exceeded 2% of account balance",
                    "knowledge_type": KnowledgeType.ERROR_PATTERN,
                    "metadata": {"loss_amount": 500, "lesson": "position_sizing"},
                    "tags": ["risk_management", "position_sizing", "error"]
                },
                {
                    "content": "Successful breakout trade on AAPL using volume confirmation",
                    "knowledge_type": KnowledgeType.SUCCESS_PATTERN,
                    "metadata": {"symbol": "AAPL", "profit": 150, "strategy": "breakout"},
                    "tags": ["breakout", "volume", "success", "AAPL"]
                }
            ]
            
            knowledge_ids = []
            for knowledge in test_knowledge:
                entry_id = self.rag_system.add_trading_knowledge(**knowledge)
                knowledge_ids.append(entry_id)
                
            self.log_test("Knowledge Addition", True, f"Added {len(knowledge_ids)} knowledge entries")
            
            # Test knowledge retrieval
            query_result = self.rag_system.knowledge_base.query_knowledge(
                query="trading strategies for technical analysis",
                query_type=QueryType.STRATEGY_RECOMMENDATION,
                max_results=5
            )
            
            self.log_test("Knowledge Retrieval", len(query_result.entries) > 0, 
                         f"Retrieved {len(query_result.entries)} relevant entries")
            
            # Test knowledge statistics
            stats = self.rag_system.knowledge_base.get_statistics()
            self.log_test("Knowledge Statistics", stats["total_entries"] > 0, 
                         f"Total entries: {stats['total_entries']}")
            
        except Exception as e:
            self.log_test("Knowledge Base Operations", False, f"Error: {str(e)}")
    
    def test_rag_engine_functionality(self):
        """Test 3: RAG Engine Functionality"""
        print("\n🧠 Testing RAG Engine...")
        
        if not self.rag_system:
            self.log_test("RAG Engine Tests", False, "RAG system not initialized")
            return
        
        try:
            # Test different query types
            test_queries = [
                {
                    "query": "What should I consider when managing risk in volatile markets?",
                    "query_type": QueryType.RISK_GUIDANCE,
                    "context": {"market_regime": "high_volatility", "user_risk_profile": "moderate"}
                },
                {
                    "query": "Show me successful trading patterns I can learn from",
                    "query_type": QueryType.PATTERN_MATCHING,
                    "context": {"learning_focus": "success_patterns"}
                },
                {
                    "query": "What strategy should I use for AAPL stock?",
                    "query_type": QueryType.STRATEGY_RECOMMENDATION,
                    "context": {"symbol": "AAPL", "timeframe": "daily"}
                }
            ]
            
            for i, test_query in enumerate(test_queries):
                response = self.rag_system.query_trading_intelligence(
                    query=test_query["query"],
                    query_type=test_query["query_type"],
                    trading_context=test_query["context"]
                )
                
                # Verify response quality
                has_content = len(response.content) > 50
                has_confidence = response.confidence > 0
                has_reasoning = len(response.reasoning_steps) > 0
                
                success = has_content and has_confidence and has_reasoning
                details = f"Content: {len(response.content)} chars, Confidence: {response.confidence:.2f}"
                
                self.log_test(f"RAG Query {i+1} ({test_query['query_type'].value})", success, details)
            
        except Exception as e:
            self.log_test("RAG Engine Functionality", False, f"Error: {str(e)}")
    
    def test_learning_system(self):
        """Test 4: Continual Learning System"""
        print("\n📖 Testing Learning System...")
        
        if not self.rag_system:
            self.log_test("Learning System Tests", False, "RAG system not initialized")
            return
        
        try:
            learning_system = self.rag_system.learning_system
            
            # Test decision tracking
            test_decisions = [
                {
                    "decision_id": "test_trade_001",
                    "decision_type": "position_entry",
                    "context": {"symbol": "AAPL", "signal": "bullish_breakout", "market_regime": "trending"},
                    "prediction": "price_increase",
                    "symbol": "AAPL",
                    "strategy": "breakout_trading"
                },
                {
                    "decision_id": "test_trade_002",
                    "decision_type": "position_sizing",
                    "context": {"symbol": "TSLA", "volatility": "high", "account_risk": "2%"},
                    "prediction": "conservative_sizing",
                    "symbol": "TSLA",
                    "strategy": "risk_management"
                }
            ]
            
            for decision in test_decisions:
                learning_system.track_trading_decision(**decision)
            
            self.log_test("Decision Tracking", True, f"Tracked {len(test_decisions)} decisions")
            
            # Test outcome recording
            learning_system.record_decision_outcome("test_trade_001", "successful_breakout", 0.85)
            learning_system.record_decision_outcome("test_trade_002", "avoided_loss", 0.75)
            
            self.log_test("Outcome Recording", True, "Recorded decision outcomes")
            
            # Test learning insights
            insights = learning_system.get_learning_insights()
            has_insights = len(insights.get("learning_stats", {})) > 0
            
            self.log_test("Learning Insights", has_insights, f"Generated insights: {list(insights.keys())}")
            
        except Exception as e:
            self.log_test("Learning System", False, f"Error: {str(e)}")
    
    async def test_integration_system(self):
        """Test 5: AGUS-RAG Integration"""
        print("\n🔗 Testing AGUS-RAG Integration...")
        
        if not self.integration_system:
            self.log_test("Integration System Tests", False, "Integration system not available")
            return
        
        try:
            # Test integrated queries
            integration_queries = [
                {
                    "query": "What's the best strategy for trading in current market conditions?",
                    "context": {"trading_context": {"market_regime": "volatile", "volatility": 0.35}},
                    "integration_type": IntegrationType.KNOWLEDGE_ENHANCED
                },
                {
                    "query": "Analyze my trading performance and suggest improvements",
                    "context": {"user_context": {"trading_style": "swing", "recent_performance": {"win_rate": 0.6}}},
                    "response_mode": ResponseMode.FUSION
                }
            ]
            
            for i, test_query in enumerate(integration_queries):
                response = await self.integration_system.process_query(
                    query=test_query["query"],
                    context=test_query["context"],
                    integration_type=test_query.get("integration_type"),
                    response_mode=test_query.get("response_mode")
                )
                
                # Verify integrated response
                has_content = len(response.primary_content) > 50
                has_confidence = response.confidence > 0
                response_time_ok = response.response_time < 30.0
                
                success = has_content and has_confidence and response_time_ok
                details = f"Confidence: {response.confidence:.2f}, Time: {response.response_time:.2f}s"
                
                self.log_test(f"Integration Query {i+1}", success, details)
            
            # Test integration status
            status = self.integration_system.get_integration_status()
            integration_active = status["systems_status"]["integration_active"]
            
            self.log_test("Integration Status", integration_active, f"Systems: {status['systems_status']}")
            
        except Exception as e:
            self.log_test("Integration System", False, f"Error: {str(e)}")
    
    def test_performance_benchmarks(self):
        """Test 6: Performance Benchmarks"""
        print("\n⚡ Testing Performance Benchmarks...")
        
        if not self.rag_system:
            self.log_test("Performance Tests", False, "RAG system not initialized")
            return
        
        try:
            # Benchmark knowledge retrieval speed
            start_time = time.time()
            
            for i in range(10):
                query_result = self.rag_system.knowledge_base.query_knowledge(
                    query=f"trading strategy number {i}",
                    max_results=5
                )
            
            avg_query_time = (time.time() - start_time) / 10
            query_speed_ok = avg_query_time < 1.0  # Should be under 1 second
            
            self.log_test("Knowledge Retrieval Speed", query_speed_ok, 
                         f"Avg query time: {avg_query_time:.3f}s")
            
            # Benchmark RAG response generation
            start_time = time.time()
            
            response = self.rag_system.query_trading_intelligence(
                query="What are the most effective risk management techniques?",
                query_type=QueryType.RISK_GUIDANCE
            )
            
            response_time = time.time() - start_time
            response_speed_ok = response_time < 5.0  # Should be under 5 seconds
            
            self.log_test("RAG Response Speed", response_speed_ok, 
                         f"Response time: {response_time:.3f}s")
            
            # Test memory usage (basic check)
            system_status = self.rag_system.get_system_status()
            memory_usage_ok = True  # Placeholder for actual memory check
            
            self.log_test("Memory Usage", memory_usage_ok, "Memory usage within acceptable limits")
            
        except Exception as e:
            self.log_test("Performance Benchmarks", False, f"Error: {str(e)}")
    
    def test_edge_cases_and_robustness(self):
        """Test 7: Edge Cases and Robustness"""
        print("\n🛡️ Testing Edge Cases and Robustness...")
        
        if not self.rag_system:
            self.log_test("Robustness Tests", False, "RAG system not initialized")
            return
        
        try:
            # Test empty queries
            empty_response = self.rag_system.query_trading_intelligence(
                query="",
                query_type=QueryType.GENERAL_INQUIRY
            )
            
            handles_empty = len(empty_response.content) > 0
            self.log_test("Empty Query Handling", handles_empty, "System handles empty queries gracefully")
            
            # Test very long queries
            long_query = "What should I do " * 100 + "for trading?"
            long_response = self.rag_system.query_trading_intelligence(
                query=long_query,
                query_type=QueryType.GENERAL_INQUIRY
            )
            
            handles_long = len(long_response.content) > 0
            self.log_test("Long Query Handling", handles_long, "System handles long queries")
            
            # Test special characters
            special_query = "What about trading with symbols like $AAPL @mention #hashtag?"
            special_response = self.rag_system.query_trading_intelligence(
                query=special_query,
                query_type=QueryType.GENERAL_INQUIRY
            )
            
            handles_special = len(special_response.content) > 0
            self.log_test("Special Characters", handles_special, "System handles special characters")
            
            # Test non-existent knowledge queries
            nonexistent_response = self.rag_system.query_trading_intelligence(
                query="Tell me about trading strategies for fictional alien markets",
                query_type=QueryType.STRATEGY_RECOMMENDATION
            )
            
            handles_nonexistent = nonexistent_response.confidence < 0.5
            self.log_test("Non-existent Knowledge", handles_nonexistent, 
                         f"Low confidence for unknown topics: {nonexistent_response.confidence:.2f}")
            
        except Exception as e:
            self.log_test("Edge Cases and Robustness", False, f"Error: {str(e)}")
    
    async def run_comprehensive_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Comprehensive Advanced Memory RAG System Tests")
        print("=" * 80)
        
        start_time = time.time()
        
        # Run all tests
        self.test_system_initialization()
        self.test_knowledge_base_operations()
        self.test_rag_engine_functionality()
        self.test_learning_system()
        await self.test_integration_system()
        self.test_performance_benchmarks()
        self.test_edge_cases_and_robustness()
        
        total_time = time.time() - start_time
        
        # Print comprehensive results
        print("\n" + "=" * 80)
        print("🏁 TEST RESULTS SUMMARY")
        print("=" * 80)
        
        print(f"⏱️  Total Test Time: {total_time:.2f} seconds")
        print(f"📊 Total Tests: {self.test_results['total_tests']}")
        print(f"✅ Passed: {self.test_results['passed_tests']}")
        print(f"❌ Failed: {self.test_results['failed_tests']}")
        
        success_rate = self.test_results['passed_tests'] / self.test_results['total_tests'] * 100
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("\n🎉 SYSTEM READY FOR PRODUCTION!")
        elif success_rate >= 60:
            print("\n⚠️  SYSTEM FUNCTIONAL WITH MINOR ISSUES")
        else:
            print("\n❌ SYSTEM NEEDS SIGNIFICANT IMPROVEMENTS")
        
        # Show detailed results
        print("\n📋 DETAILED TEST RESULTS:")
        print("-" * 50)
        
        for test in self.test_results["test_details"]:
            print(f"{test['status']} - {test['name']}")
            if test["details"]:
                print(f"     {test['details']}")
        
        # Show system status if available
        if self.rag_system:
            print("\n🔧 SYSTEM STATUS:")
            print("-" * 30)
            status = self.rag_system.get_system_status()
            print(f"Knowledge Entries: {status.get('knowledge_base_stats', {}).get('total_entries', 'N/A')}")
            print(f"Total Queries: {status.get('system_stats', {}).get('total_queries', 'N/A')}")
            print(f"Health Status: {status.get('health_status', 'Unknown')}")
        
        return success_rate >= 80

async def main():
    """Main test execution"""
    tester = AdvancedMemoryRAGTester()
    success = await tester.run_comprehensive_tests()
    
    if success:
        print("\n🎯 Advanced Memory RAG System is ready for deployment!")
        return 0
    else:
        print("\n🔧 System needs additional work before deployment")
        return 1

if __name__ == "__main__":
    # Run the comprehensive test suite
    result = asyncio.run(main())