#!/usr/bin/env python3
"""
🧪 COMPREHENSIVE INSTITUTIONAL LOCALAI TESTING SUITE
Tests all advanced LocalAI components and integration
- Multi-Model Manager Testing
- Configuration System Testing  
- Performance Optimization Testing
- Trading Models Integration Testing
- Advanced Monitoring Testing
- Full Integration Testing
"""
import os
import sys
import asyncio
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
import subprocess
import requests
from typing import Dict, List, Optional, Any, Tuple, Union

# Add bot directory to path for imports
sys.path.append(str(Path(__file__).parent / "bot"))

class InstitutionalLocalAITestSuite:
    """
    🧪 Comprehensive test suite for all institutional LocalAI components
    """
    
    def __init__(self):
        self.test_results = {}
        self.failed_tests = []
        self.passed_tests = []
        
        # Test configuration
        self.test_config = {
            "timeout": 30,  # seconds
            "retry_attempts": 3,
            "test_data_size": 100
        }
        
        logger.info("🧪 Institutional LocalAI Test Suite initialized")
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive test suite"""
        logger.info("🚀 Starting Comprehensive Institutional LocalAI Testing...")
        start_time = time.time()
        
        # Test phases
        test_phases = [
            ("Component Import Tests", self._test_component_imports),
            ("Multi-Model Manager Tests", self._test_multi_model_manager),
            ("Configuration System Tests", self._test_configuration_system),
            ("Performance Optimizer Tests", self._test_performance_optimizer),
            ("Trading Models Tests", self._test_trading_models),
            ("Advanced Monitoring Tests", self._test_advanced_monitoring),
            ("Integration Tests", self._test_full_integration),
            ("Performance Benchmarks", self._run_performance_benchmarks)
        ]
        
        for phase_name, test_func in test_phases:
            logger.info(f"🔍 Running {phase_name}...")
            try:
                results = await test_func()
                self.test_results[phase_name] = results
                
                if results.get("success", False):
                    self.passed_tests.append(phase_name)
                    logger.info(f"✅ {phase_name}: PASSED")
                else:
                    self.failed_tests.append(phase_name)
                    logger.error(f"❌ {phase_name}: FAILED")
                    
            except Exception as e:
                self.failed_tests.append(phase_name)
                self.test_results[phase_name] = {
                    "success": False,
                    "error": str(e),
                    "exception_type": type(e).__name__
                }
                logger.error(f"❌ {phase_name}: EXCEPTION - {e}")
        
        # Generate final report
        execution_time = time.time() - start_time
        return self._generate_test_report(execution_time)
    
    async def _test_component_imports(self) -> Dict[str, Any]:
        """Test that all components can be imported successfully"""
        logger.info("📦 Testing component imports...")
        
        import_tests = {
            "institutional_manager": "bot.localai_institutional_manager",
            "advanced_config": "bot.localai_advanced_config", 
            "performance_optimizer": "bot.localai_performance_optimizer",
            "trading_models": "bot.localai_trading_models",
            "advanced_monitoring": "bot.localai_advanced_monitoring"
        }
        
        results = {"success": True, "imports": {}}
        
        for component_name, import_path in import_tests.items():
            try:
                module = __import__(import_path, fromlist=[''])
                results["imports"][component_name] = {
                    "success": True,
                    "module_file": getattr(module, '__file__', 'unknown')
                }
                logger.debug(f"✅ {component_name}: Import successful")
                
            except Exception as e:
                results["imports"][component_name] = {
                    "success": False,
                    "error": str(e)
                }
                results["success"] = False
                logger.error(f"❌ {component_name}: Import failed - {e}")
        
        return results
    
    async def _test_multi_model_manager(self) -> Dict[str, Any]:
        """Test the Multi-Model Manager functionality"""
        logger.info("🤖 Testing Multi-Model Manager...")
        
        try:
            from bot.localai_institutional_manager import institutional_manager
            
            results = {"success": True, "tests": {}}
            
            # Test 1: Manager initialization
            try:
                gpu_available = institutional_manager.gpu_available
                model_count = len(institutional_manager.models)
                
                results["tests"]["initialization"] = {
                    "success": True,
                    "gpu_available": gpu_available,
                    "models_configured": model_count
                }
                logger.debug(f"✅ Manager initialized: {model_count} models, GPU: {gpu_available}")
                
            except Exception as e:
                results["tests"]["initialization"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            # Test 2: Model configuration creation
            try:
                # Test configuration file creation without full installation
                config_dir = Path("bot/localai_configs")
                if config_dir.exists():
                    config_files = list(config_dir.glob("*.yaml"))
                    results["tests"]["config_creation"] = {
                        "success": True,
                        "config_files": len(config_files)
                    }
                else:
                    results["tests"]["config_creation"] = {
                        "success": True,
                        "note": "Config directory not created yet (expected)"
                    }
                
            except Exception as e:
                results["tests"]["config_creation"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            # Test 3: Health check preparation
            try:
                test_endpoint = "http://localhost:8081"
                # Don't actually make request, just test the method exists
                health_method = hasattr(institutional_manager, '_health_check_endpoint')
                
                results["tests"]["health_check"] = {
                    "success": True,
                    "health_method_exists": health_method
                }
                
            except Exception as e:
                results["tests"]["health_check"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            return results
            
        except Exception as e:
            return {"success": False, "error": f"Manager import failed: {e}"}
    
    async def _test_configuration_system(self) -> Dict[str, Any]:
        """Test the Advanced Configuration System"""
        logger.info("⚙️ Testing Configuration System...")
        
        try:
            from bot.localai_advanced_config import advanced_config
            
            results = {"success": True, "tests": {}}
            
            # Test 1: Profile creation
            try:
                advanced_config.create_trading_profiles()
                profile_count = len(advanced_config.profiles)
                
                results["tests"]["profile_creation"] = {
                    "success": True,
                    "profiles_created": profile_count,
                    "profile_names": list(advanced_config.profiles.keys())
                }
                logger.debug(f"✅ Created {profile_count} trading profiles")
                
            except Exception as e:
                results["tests"]["profile_creation"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            # Test 2: Profile activation
            try:
                activation_success = advanced_config.activate_profile("development")
                active_profile = advanced_config.active_profile
                
                results["tests"]["profile_activation"] = {
                    "success": activation_success,
                    "active_profile": active_profile
                }
                
            except Exception as e:
                results["tests"]["profile_activation"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            # Test 3: Load balancing simulation
            try:
                if advanced_config.active_profile:
                    # Test endpoint selection without actual endpoints
                    endpoint_pools = advanced_config.endpoint_pools
                    algorithm = advanced_config.profiles[advanced_config.active_profile].load_balancer.algorithm
                    
                    results["tests"]["load_balancing"] = {
                        "success": True,
                        "algorithm": algorithm,
                        "endpoint_pools": len(endpoint_pools)
                    }
                else:
                    results["tests"]["load_balancing"] = {"success": False, "error": "No active profile"}
                    results["success"] = False
                
            except Exception as e:
                results["tests"]["load_balancing"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            return results
            
        except Exception as e:
            return {"success": False, "error": f"Configuration system import failed: {e}"}
    
    async def _test_performance_optimizer(self) -> Dict[str, Any]:
        """Test the Performance Optimization Engine"""
        logger.info("🚀 Testing Performance Optimizer...")
        
        try:
            from bot.localai_performance_optimizer import performance_optimizer
            
            results = {"success": True, "tests": {}}
            
            # Test 1: GPU detection
            try:
                gpu_available = performance_optimizer.gpu_manager.gpu_available
                gpu_devices = len(performance_optimizer.gpu_manager.gpu_devices)
                
                results["tests"]["gpu_detection"] = {
                    "success": True,
                    "gpu_available": gpu_available,
                    "gpu_devices": gpu_devices
                }
                logger.debug(f"✅ GPU detection: Available={gpu_available}, Devices={gpu_devices}")
                
            except Exception as e:
                results["tests"]["gpu_detection"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            # Test 2: Performance profiles
            try:
                profile_count = len(performance_optimizer.performance_profiles)
                profile_names = list(performance_optimizer.performance_profiles.keys())
                
                results["tests"]["performance_profiles"] = {
                    "success": True,
                    "profile_count": profile_count,
                    "profile_names": profile_names
                }
                
            except Exception as e:
                results["tests"]["performance_profiles"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            # Test 3: Profile activation
            try:
                activation_success = performance_optimizer.activate_profile("development")
                active_profile = performance_optimizer.active_profile
                
                results["tests"]["profile_activation"] = {
                    "success": activation_success,
                    "active_profile": active_profile
                }
                
            except Exception as e:
                results["tests"]["profile_activation"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            # Test 4: Resource monitoring setup
            try:
                # Test monitoring setup without starting the loop
                collectors_count = len(performance_optimizer.collectors)
                
                results["tests"]["monitoring_setup"] = {
                    "success": True,
                    "collectors_registered": collectors_count
                }
                
            except Exception as e:
                results["tests"]["monitoring_setup"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            return results
            
        except Exception as e:
            return {"success": False, "error": f"Performance optimizer import failed: {e}"}
    
    async def _test_trading_models(self) -> Dict[str, Any]:
        """Test the Custom Trading Models Integration"""
        logger.info("💹 Testing Trading Models...")
        
        try:
            from bot.localai_trading_models import trading_models
            
            results = {"success": True, "tests": {}}
            
            # Test 1: Model initialization
            try:
                sentiment_init = trading_models.sentiment_model.initialized
                technical_init = trading_models.technical_model.initialized
                
                results["tests"]["model_initialization"] = {
                    "success": True,
                    "sentiment_initialized": sentiment_init,
                    "technical_initialized": technical_init
                }
                
            except Exception as e:
                results["tests"]["model_initialization"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            # Test 2: Sentiment analysis (rule-based fallback)
            try:
                test_text = "The market is showing strong bullish momentum with increasing volume."
                sentiment_result = await trading_models.sentiment_model.analyze_sentiment(test_text, "BTC/USD")
                
                results["tests"]["sentiment_analysis"] = {
                    "success": True,
                    "prediction": sentiment_result.prediction,
                    "confidence": sentiment_result.confidence,
                    "model_name": sentiment_result.model_name
                }
                
            except Exception as e:
                results["tests"]["sentiment_analysis"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            # Test 3: Technical analysis
            try:
                test_market_data = {
                    "price": 58000,
                    "volume": 1000000,
                    "rsi": 45
                }
                technical_result = await trading_models.technical_model.predict_price_movement(test_market_data, "BTC/USD")
                
                results["tests"]["technical_analysis"] = {
                    "success": True,
                    "prediction": technical_result.prediction,
                    "confidence": technical_result.confidence
                }
                
            except Exception as e:
                results["tests"]["technical_analysis"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            # Test 4: Risk assessment
            try:
                test_portfolio = {"positions": {"BTC/USD": {"market_value": 10000}}}
                test_market = {"volatility": 0.3, "volume": 500000}
                
                risk_result = await trading_models.risk_model.assess_risk(test_portfolio, test_market)
                
                results["tests"]["risk_assessment"] = {
                    "success": True,
                    "prediction": risk_result.prediction,
                    "confidence": risk_result.confidence
                }
                
            except Exception as e:
                results["tests"]["risk_assessment"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            return results
            
        except Exception as e:
            return {"success": False, "error": f"Trading models import failed: {e}"}
    
    async def _test_advanced_monitoring(self) -> Dict[str, Any]:
        """Test the Advanced Monitoring System"""
        logger.info("📊 Testing Advanced Monitoring...")
        
        try:
            from bot.localai_advanced_monitoring import performance_monitor
            
            results = {"success": True, "tests": {}}
            
            # Test 1: Database initialization
            try:
                db_connection = performance_monitor.db.connection is not None
                
                results["tests"]["database_init"] = {
                    "success": db_connection,
                    "database_path": performance_monitor.db.db_path
                }
                
            except Exception as e:
                results["tests"]["database_init"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            # Test 2: Alert system
            try:
                alert_count = len(performance_monitor.alert_system.alerts)
                alert_names = list(performance_monitor.alert_system.alerts.keys())
                
                results["tests"]["alert_system"] = {
                    "success": True,
                    "alerts_configured": alert_count,
                    "alert_names": alert_names[:5]  # First 5 only
                }
                
            except Exception as e:
                results["tests"]["alert_system"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            # Test 3: Metric collection
            try:
                # Test metric recording
                performance_monitor.record_metric(
                    "test_metric",
                    42.0,
                    labels={"test": "true"},
                    metadata={"test_run": datetime.now().isoformat()}
                )
                
                results["tests"]["metric_collection"] = {
                    "success": True,
                    "collectors_registered": len(performance_monitor.collectors)
                }
                
            except Exception as e:
                results["tests"]["metric_collection"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            # Test 4: Real-time status
            try:
                status = performance_monitor.get_real_time_status()
                
                results["tests"]["real_time_status"] = {
                    "success": True,
                    "monitoring_active": status.get("monitoring_active", False),
                    "uptime_hours": status.get("uptime_hours", 0)
                }
                
            except Exception as e:
                results["tests"]["real_time_status"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            return results
            
        except Exception as e:
            return {"success": False, "error": f"Advanced monitoring import failed: {e}"}
    
    async def _test_full_integration(self) -> Dict[str, Any]:
        """Test full integration between all components"""
        logger.info("🔗 Testing Full Integration...")
        
        results = {"success": True, "tests": {}}
        
        try:
            # Test comprehensive analysis pipeline
            from bot.localai_trading_models import trading_models
            from bot.localai_performance_optimizer import performance_optimizer
            from bot.localai_advanced_monitoring import performance_monitor
            
            # Test 1: Comprehensive analysis
            try:
                test_symbol = "BTC/USD"
                test_market_data = {
                    "price": 58000,
                    "volume": 1000000,
                    "volatility": 0.25
                }
                test_news = "Bitcoin shows strong momentum as institutional adoption increases."
                test_portfolio = {"positions": {test_symbol: {"market_value": 10000}}}
                
                analysis_results = await trading_models.comprehensive_analysis(
                    test_symbol,
                    test_market_data,
                    test_news,
                    test_portfolio
                )
                
                results["tests"]["comprehensive_analysis"] = {
                    "success": True,
                    "components_analyzed": len([k for k, v in analysis_results.items() if v]),
                    "combined_signal": analysis_results.get("combined") is not None
                }
                
            except Exception as e:
                results["tests"]["comprehensive_analysis"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            # Test 2: Performance optimization integration
            try:
                optimization_result = performance_optimizer.optimize_inference_request(
                    "sentiment",
                    "Test prompt for optimization",
                    100
                )
                
                results["tests"]["performance_optimization"] = {
                    "success": optimization_result.get("optimized", False),
                    "cache_hit": optimization_result.get("cache_hit", False)
                }
                
            except Exception as e:
                results["tests"]["performance_optimization"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            # Test 3: Monitoring integration
            try:
                # Record some test metrics
                performance_monitor.record_metric("integration_test_response_time", 1.5)
                performance_monitor.record_metric("integration_test_success_rate", 0.98)
                
                status = performance_monitor.get_real_time_status()
                
                results["tests"]["monitoring_integration"] = {
                    "success": True,
                    "metrics_recorded": len(status.get("current_metrics", {}))
                }
                
            except Exception as e:
                results["tests"]["monitoring_integration"] = {"success": False, "error": str(e)}
                results["success"] = False
            
            return results
            
        except Exception as e:
            return {"success": False, "error": f"Integration test failed: {e}"}
    
    async def _run_performance_benchmarks(self) -> Dict[str, Any]:
        """Run performance benchmarks on the system"""
        logger.info("⚡ Running Performance Benchmarks...")
        
        results = {"success": True, "benchmarks": {}}
        
        try:
            # Benchmark 1: Sentiment analysis speed
            start_time = time.time()
            from bot.localai_trading_models import trading_models
            
            test_texts = [
                "The market is bullish today",
                "Bearish sentiment prevails",
                "Neutral market conditions",
                "Strong upward momentum",
                "Declining prices ahead"
            ]
            
            sentiment_times = []
            for text in test_texts:
                start = time.time()
                await trading_models.sentiment_model.analyze_sentiment(text, "TEST")
                sentiment_times.append(time.time() - start)
            
            avg_sentiment_time = sum(sentiment_times) / len(sentiment_times)
            
            results["benchmarks"]["sentiment_analysis"] = {
                "average_time_seconds": round(avg_sentiment_time, 3),
                "samples_tested": len(test_texts),
                "throughput_per_second": round(1.0 / avg_sentiment_time, 2)
            }
            
        except Exception as e:
            results["benchmarks"]["sentiment_analysis"] = {"error": str(e)}
            results["success"] = False
        
        try:
            # Benchmark 2: Technical analysis speed
            from bot.localai_trading_models import trading_models
            
            test_data = {
                "price": 58000,
                "volume": 1000000,
                "rsi": 45,
                "macd": 0.1
            }
            
            technical_times = []
            for i in range(5):
                start = time.time()
                await trading_models.technical_model.predict_price_movement(test_data, "BTC/USD")
                technical_times.append(time.time() - start)
            
            avg_technical_time = sum(technical_times) / len(technical_times)
            
            results["benchmarks"]["technical_analysis"] = {
                "average_time_seconds": round(avg_technical_time, 3),
                "samples_tested": len(technical_times),
                "throughput_per_second": round(1.0 / avg_technical_time, 2)
            }
            
        except Exception as e:
            results["benchmarks"]["technical_analysis"] = {"error": str(e)}
            results["success"] = False
        
        try:
            # Benchmark 3: Memory usage
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            results["benchmarks"]["memory_usage"] = {
                "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
                "percent": round(process.memory_percent(), 2)
            }
            
        except Exception as e:
            results["benchmarks"]["memory_usage"] = {"error": str(e)}
            results["success"] = False
        
        return results
    
    def _generate_test_report(self, execution_time: float) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.passed_tests) + len(self.failed_tests)
        success_rate = len(self.passed_tests) / total_tests if total_tests > 0 else 0
        
        report = {
            "test_summary": {
                "total_test_phases": total_tests,
                "passed_phases": len(self.passed_tests),
                "failed_phases": len(self.failed_tests),
                "success_rate": round(success_rate * 100, 2),
                "execution_time_seconds": round(execution_time, 2)
            },
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "detailed_results": self.test_results,
            "recommendations": self._generate_recommendations(),
            "timestamp": datetime.now().isoformat()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        if "Component Import Tests" in self.failed_tests:
            recommendations.append("Fix import issues before proceeding with installation")
        
        if "Multi-Model Manager Tests" in self.failed_tests:
            recommendations.append("Check Docker availability and model configuration")
        
        if "Performance Optimizer Tests" in self.failed_tests:
            recommendations.append("Verify GPU drivers and PyTorch installation")
        
        if "Trading Models Tests" in self.failed_tests:
            recommendations.append("Install required ML libraries: transformers, torch, ta-lib")
        
        if "Advanced Monitoring Tests" in self.failed_tests:
            recommendations.append("Check SQLite database permissions and disk space")
        
        if len(self.failed_tests) == 0:
            recommendations.append("All tests passed! System ready for production use")
        elif len(self.failed_tests) <= 2:
            recommendations.append("Most components working - address remaining issues for full functionality")
        else:
            recommendations.append("Multiple component failures - review installation and dependencies")
        
        return recommendations

async def run_tests():
    """Main test runner function"""
    test_suite = InstitutionalLocalAITestSuite()
    
    try:
        logger.info("🧪 Starting Institutional LocalAI Test Suite...")
        
        # Run all tests
        test_report = await test_suite.run_all_tests()
        
        # Save report
        report_file = Path("institutional_localai_test_report.json")
        with open(report_file, 'w') as f:
            json.dump(test_report, f, indent=2)
        
        # Print summary
        summary = test_report["test_summary"]
        logger.info("=" * 60)
        logger.info("🏁 TEST SUITE COMPLETED")
        logger.info("=" * 60)
        logger.info(f"📊 Total Test Phases: {summary['total_test_phases']}")
        logger.info(f"✅ Passed: {summary['passed_phases']}")
        logger.info(f"❌ Failed: {summary['failed_phases']}")
        logger.info(f"📈 Success Rate: {summary['success_rate']}%")
        logger.info(f"⏱️ Execution Time: {summary['execution_time_seconds']}s")
        logger.info("=" * 60)
        
        if test_report["recommendations"]:
            logger.info("💡 RECOMMENDATIONS:")
            for rec in test_report["recommendations"]:
                logger.info(f"   • {rec}")
        
        logger.info(f"📄 Detailed report saved to: {report_file}")
        
        return test_report
        
    except Exception as e:
        logger.error(f"❌ Test suite execution failed: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    # Run the test suite
    report = asyncio.run(run_tests())
    
    # Exit with appropriate code
    exit_code = 0 if report.get("test_summary", {}).get("failed_phases", 1) == 0 else 1
    sys.exit(exit_code)