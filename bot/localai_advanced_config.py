#!/usr/bin/env python3
"""
🏗️ LOCALAI ADVANCED CONFIGURATION SYSTEM
Enterprise-grade configuration management with load balancing and failover
- Dynamic Configuration Management
- Intelligent Load Balancing
- Automatic Failover Systems
- Multi-Endpoint Management
- Real-time Configuration Updates
- Performance-based Routing
"""
import os
import json
import asyncio
import aiohttp
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict, field
from loguru import logger
from pathlib import Path
import hashlib
import yaml
from concurrent.futures import ThreadPoolExecutor
import requests

@dataclass
class EndpointConfig:
    """Configuration for individual endpoints"""
    endpoint_id: str
    url: str
    port: int
    model_type: str
    priority: int  # 1-10, higher = preferred
    max_concurrent: int
    timeout: float
    retry_attempts: int
    health_check_interval: float
    weight: float  # Load balancing weight
    status: str = "unknown"  # unknown, healthy, degraded, failed
    current_load: int = 0
    avg_response_time: float = 0.0
    success_rate: float = 1.0
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0

@dataclass
class LoadBalancerConfig:
    """Load balancer configuration"""
    algorithm: str  # round_robin, weighted, least_connections, response_time
    sticky_sessions: bool
    session_timeout: float
    health_check_threshold: int
    failover_enabled: bool
    backup_endpoints: List[str]
    circuit_breaker_threshold: int
    circuit_breaker_timeout: float

@dataclass
class PerformanceTarget:
    """Performance targets for auto-scaling"""
    max_response_time: float  # seconds
    min_success_rate: float   # 0.0-1.0
    max_queue_size: int
    target_cpu_usage: float   # 0.0-1.0
    target_memory_usage: float # 0.0-1.0

@dataclass
class ConfigurationProfile:
    """Complete configuration profile for different scenarios"""
    profile_name: str
    description: str
    endpoints: List[EndpointConfig]
    load_balancer: LoadBalancerConfig
    performance_targets: PerformanceTarget
    scaling_enabled: bool
    monitoring_enabled: bool
    backup_strategy: str
    created_at: datetime = field(default_factory=datetime.now)

class LocalAIAdvancedConfig:
    """
    🏗️ Advanced Configuration System for LocalAI
    Manages complex multi-endpoint configurations with enterprise features
    """
    
    def __init__(self, config_dir: str = "bot/localai_configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        self.profiles: Dict[str, ConfigurationProfile] = {}
        self.active_profile: Optional[str] = None
        self.endpoint_pools: Dict[str, List[EndpointConfig]] = {}
        
        # Load balancing state
        self.current_endpoint_index: Dict[str, int] = {}
        self.session_mapping: Dict[str, str] = {}  # session_id -> endpoint_id
        self.circuit_breakers: Dict[str, Dict] = {}
        
        # Performance monitoring
        self.performance_history: Dict[str, List[Dict]] = {}
        self.scaling_actions: List[Dict] = []
        
        logger.info("🏗️ Advanced Configuration System initialized")
    
    def create_trading_profiles(self):
        """Create predefined trading-specific configuration profiles"""
        
        # 1. HIGH FREQUENCY TRADING PROFILE
        hft_endpoints = [
            EndpointConfig(
                endpoint_id="hft_sentiment_primary",
                url="http://localhost:8081",
                port=8081,
                model_type="sentiment",
                priority=10,
                max_concurrent=50,
                timeout=0.5,  # Ultra-fast for HFT
                retry_attempts=1,
                health_check_interval=5.0,
                weight=1.0
            ),
            EndpointConfig(
                endpoint_id="hft_sentiment_backup",
                url="http://localhost:8091",
                port=8091,
                model_type="sentiment",
                priority=8,
                max_concurrent=30,
                timeout=1.0,
                retry_attempts=2,
                health_check_interval=10.0,
                weight=0.5
            ),
            EndpointConfig(
                endpoint_id="hft_prediction_primary",
                url="http://localhost:8082",
                port=8082,
                model_type="prediction",
                priority=10,
                max_concurrent=40,
                timeout=1.0,
                retry_attempts=1,
                health_check_interval=5.0,
                weight=1.0
            )
        ]
        
        hft_lb_config = LoadBalancerConfig(
            algorithm="response_time",  # Fastest response wins
            sticky_sessions=False,  # No stickiness for speed
            session_timeout=30.0,
            health_check_threshold=3,
            failover_enabled=True,
            backup_endpoints=["hft_sentiment_backup"],
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=30.0
        )
        
        hft_performance = PerformanceTarget(
            max_response_time=1.0,  # 1 second max
            min_success_rate=0.98,  # 98% success rate
            max_queue_size=100,
            target_cpu_usage=0.7,
            target_memory_usage=0.8
        )
        
        self.profiles["hft_trading"] = ConfigurationProfile(
            profile_name="High Frequency Trading",
            description="Ultra-low latency configuration for HFT operations",
            endpoints=hft_endpoints,
            load_balancer=hft_lb_config,
            performance_targets=hft_performance,
            scaling_enabled=True,
            monitoring_enabled=True,
            backup_strategy="immediate_failover"
        )
        
        # 2. INSTITUTIONAL ANALYSIS PROFILE
        institutional_endpoints = [
            EndpointConfig(
                endpoint_id="inst_analysis_gpu",
                url="http://localhost:8083",
                port=8083,
                model_type="analysis",
                priority=10,
                max_concurrent=20,
                timeout=10.0,  # Longer timeout for complex analysis
                retry_attempts=3,
                health_check_interval=30.0,
                weight=1.0
            ),
            EndpointConfig(
                endpoint_id="inst_risk_primary",
                url="http://localhost:8084",
                port=8084,
                model_type="risk",
                priority=9,
                max_concurrent=25,
                timeout=5.0,
                retry_attempts=2,
                health_check_interval=15.0,
                weight=0.8
            ),
            EndpointConfig(
                endpoint_id="inst_news_processor",
                url="http://localhost:8085",
                port=8085,
                model_type="news",
                priority=8,
                max_concurrent=30,
                timeout=7.0,
                retry_attempts=3,
                health_check_interval=20.0,
                weight=0.6
            )
        ]
        
        institutional_lb_config = LoadBalancerConfig(
            algorithm="weighted",  # Weighted round robin
            sticky_sessions=True,   # Session affinity for complex analysis
            session_timeout=300.0,  # 5 minutes
            health_check_threshold=2,
            failover_enabled=True,
            backup_endpoints=["inst_risk_primary"],
            circuit_breaker_threshold=10,
            circuit_breaker_timeout=60.0
        )
        
        institutional_performance = PerformanceTarget(
            max_response_time=10.0,
            min_success_rate=0.95,
            max_queue_size=50,
            target_cpu_usage=0.8,
            target_memory_usage=0.85
        )
        
        self.profiles["institutional"] = ConfigurationProfile(
            profile_name="Institutional Analysis",
            description="High-capacity configuration for institutional trading analysis",
            endpoints=institutional_endpoints,
            load_balancer=institutional_lb_config,
            performance_targets=institutional_performance,
            scaling_enabled=True,
            monitoring_enabled=True,
            backup_strategy="graceful_degradation"
        )
        
        # 3. DEVELOPMENT & TESTING PROFILE
        dev_endpoints = [
            EndpointConfig(
                endpoint_id="dev_all_in_one",
                url="http://localhost:8080",
                port=8080,
                model_type="general",
                priority=5,
                max_concurrent=10,
                timeout=15.0,
                retry_attempts=1,
                health_check_interval=60.0,
                weight=1.0
            )
        ]
        
        dev_lb_config = LoadBalancerConfig(
            algorithm="round_robin",
            sticky_sessions=False,
            session_timeout=60.0,
            health_check_threshold=1,
            failover_enabled=False,
            backup_endpoints=[],
            circuit_breaker_threshold=20,
            circuit_breaker_timeout=120.0
        )
        
        dev_performance = PerformanceTarget(
            max_response_time=20.0,
            min_success_rate=0.85,
            max_queue_size=20,
            target_cpu_usage=0.9,
            target_memory_usage=0.9
        )
        
        self.profiles["development"] = ConfigurationProfile(
            profile_name="Development & Testing",
            description="Relaxed configuration for development and testing",
            endpoints=dev_endpoints,
            load_balancer=dev_lb_config,
            performance_targets=dev_performance,
            scaling_enabled=False,
            monitoring_enabled=True,
            backup_strategy="none"
        )
        
        logger.info(f"✅ Created {len(self.profiles)} configuration profiles")
    
    def activate_profile(self, profile_name: str) -> bool:
        """Activate a specific configuration profile"""
        if profile_name not in self.profiles:
            logger.error(f"❌ Profile '{profile_name}' not found")
            return False
        
        self.active_profile = profile_name
        profile = self.profiles[profile_name]
        
        # Initialize endpoint pools by model type
        self.endpoint_pools.clear()
        for endpoint in profile.endpoints:
            if endpoint.model_type not in self.endpoint_pools:
                self.endpoint_pools[endpoint.model_type] = []
            self.endpoint_pools[endpoint.model_type].append(endpoint)
        
        # Sort endpoints by priority within each pool
        for model_type in self.endpoint_pools:
            self.endpoint_pools[model_type].sort(key=lambda x: x.priority, reverse=True)
        
        # Initialize load balancing state
        for model_type in self.endpoint_pools:
            self.current_endpoint_index[model_type] = 0
            
        # Initialize circuit breakers
        for endpoint in profile.endpoints:
            self.circuit_breakers[endpoint.endpoint_id] = {
                "state": "closed",  # closed, open, half_open
                "failure_count": 0,
                "last_failure": None,
                "next_attempt": None
            }
        
        logger.info(f"✅ Activated profile: {profile.profile_name}")
        logger.info(f"📊 Endpoints by type: {dict((k, len(v)) for k, v in self.endpoint_pools.items())}")
        
        return True
    
    async def get_optimal_endpoint(self, model_type: str, session_id: Optional[str] = None) -> Optional[EndpointConfig]:
        """
        Get the optimal endpoint based on load balancing algorithm
        """
        if not self.active_profile or model_type not in self.endpoint_pools:
            logger.warning(f"⚠️ No active profile or endpoints for model type: {model_type}")
            return None
        
        profile = self.profiles[self.active_profile]
        endpoints = self.endpoint_pools[model_type]
        available_endpoints = [ep for ep in endpoints if self._is_endpoint_available(ep)]
        
        if not available_endpoints:
            logger.error(f"❌ No available endpoints for {model_type}")
            return None
        
        # Handle sticky sessions
        if profile.load_balancer.sticky_sessions and session_id:
            if session_id in self.session_mapping:
                mapped_endpoint_id = self.session_mapping[session_id]
                mapped_endpoint = next((ep for ep in available_endpoints if ep.endpoint_id == mapped_endpoint_id), None)
                if mapped_endpoint:
                    return mapped_endpoint
        
        # Select endpoint based on algorithm
        algorithm = profile.load_balancer.algorithm
        
        if algorithm == "round_robin":
            selected = self._round_robin_selection(model_type, available_endpoints)
        elif algorithm == "weighted":
            selected = self._weighted_selection(available_endpoints)
        elif algorithm == "least_connections":
            selected = self._least_connections_selection(available_endpoints)
        elif algorithm == "response_time":
            selected = self._response_time_selection(available_endpoints)
        else:
            selected = available_endpoints[0]  # Fallback to first available
        
        # Update session mapping if needed
        if profile.load_balancer.sticky_sessions and session_id and selected:
            self.session_mapping[session_id] = selected.endpoint_id
        
        return selected
    
    def _is_endpoint_available(self, endpoint: EndpointConfig) -> bool:
        """Check if endpoint is available (not in circuit breaker open state)"""
        cb_state = self.circuit_breakers.get(endpoint.endpoint_id, {})
        
        if cb_state.get("state") == "open":
            # Check if circuit breaker timeout has passed
            next_attempt = cb_state.get("next_attempt")
            if next_attempt and datetime.now() >= next_attempt:
                # Move to half-open state
                self.circuit_breakers[endpoint.endpoint_id]["state"] = "half_open"
                logger.info(f"🔄 Circuit breaker half-open for {endpoint.endpoint_id}")
                return True
            return False
        
        return endpoint.status in ["healthy", "unknown", "degraded"]
    
    def _round_robin_selection(self, model_type: str, endpoints: List[EndpointConfig]) -> EndpointConfig:
        """Round robin load balancing"""
        current_index = self.current_endpoint_index[model_type]
        selected = endpoints[current_index % len(endpoints)]
        self.current_endpoint_index[model_type] = (current_index + 1) % len(endpoints)
        return selected
    
    def _weighted_selection(self, endpoints: List[EndpointConfig]) -> EndpointConfig:
        """Weighted random selection based on endpoint weights"""
        weights = [ep.weight for ep in endpoints]
        total_weight = sum(weights)
        
        if total_weight == 0:
            return endpoints[0]
        
        r = random.uniform(0, total_weight)
        current_weight = 0
        
        for i, endpoint in enumerate(endpoints):
            current_weight += weights[i]
            if r <= current_weight:
                return endpoint
        
        return endpoints[-1]  # Fallback
    
    def _least_connections_selection(self, endpoints: List[EndpointConfig]) -> EndpointConfig:
        """Select endpoint with least current connections"""
        return min(endpoints, key=lambda ep: ep.current_load)
    
    def _response_time_selection(self, endpoints: List[EndpointConfig]) -> EndpointConfig:
        """Select endpoint with best average response time"""
        return min(endpoints, key=lambda ep: ep.avg_response_time or float('inf'))
    
    async def update_endpoint_metrics(self, endpoint_id: str, response_time: float, success: bool):
        """Update endpoint metrics after a request"""
        # Find endpoint
        endpoint = None
        for pool in self.endpoint_pools.values():
            for ep in pool:
                if ep.endpoint_id == endpoint_id:
                    endpoint = ep
                    break
            if endpoint:
                break
        
        if not endpoint:
            return
        
        # Update metrics
        if success:
            # Update average response time (exponential moving average)
            alpha = 0.3  # Smoothing factor
            if endpoint.avg_response_time == 0:
                endpoint.avg_response_time = response_time
            else:
                endpoint.avg_response_time = (alpha * response_time + 
                                            (1 - alpha) * endpoint.avg_response_time)
            
            # Reset circuit breaker if in half-open state
            cb_state = self.circuit_breakers.get(endpoint_id, {})
            if cb_state.get("state") == "half_open":
                self.circuit_breakers[endpoint_id]["state"] = "closed"
                self.circuit_breakers[endpoint_id]["failure_count"] = 0
                logger.info(f"✅ Circuit breaker closed for {endpoint_id}")
        else:
            # Handle failure
            await self._handle_endpoint_failure(endpoint_id)
    
    async def _handle_endpoint_failure(self, endpoint_id: str):
        """Handle endpoint failure and circuit breaker logic"""
        cb_state = self.circuit_breakers.get(endpoint_id, {})
        profile = self.profiles[self.active_profile]
        
        cb_state["failure_count"] = cb_state.get("failure_count", 0) + 1
        cb_state["last_failure"] = datetime.now()
        
        # Check if circuit breaker should open
        if cb_state["failure_count"] >= profile.load_balancer.circuit_breaker_threshold:
            cb_state["state"] = "open"
            cb_state["next_attempt"] = (datetime.now() + 
                                      timedelta(seconds=profile.load_balancer.circuit_breaker_timeout))
            
            logger.warning(f"🔴 Circuit breaker OPEN for {endpoint_id} "
                         f"(failures: {cb_state['failure_count']})")
        
        self.circuit_breakers[endpoint_id] = cb_state
    
    async def perform_health_checks(self):
        """Perform health checks on all endpoints"""
        if not self.active_profile:
            return
        
        profile = self.profiles[self.active_profile]
        
        for endpoint in profile.endpoints:
            await self._health_check_endpoint(endpoint)
    
    async def _health_check_endpoint(self, endpoint: EndpointConfig):
        """Perform health check on a single endpoint"""
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{endpoint.url}/v1/models",
                    timeout=aiohttp.ClientTimeout(total=endpoint.timeout)
                ) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        endpoint.status = "healthy"
                        endpoint.last_health_check = datetime.now()
                        endpoint.consecutive_failures = 0
                        
                        # Update response time
                        if endpoint.avg_response_time == 0:
                            endpoint.avg_response_time = response_time
                        else:
                            endpoint.avg_response_time = (0.2 * response_time + 
                                                        0.8 * endpoint.avg_response_time)
                    else:
                        await self._mark_endpoint_unhealthy(endpoint, f"HTTP {response.status}")
        
        except Exception as e:
            await self._mark_endpoint_unhealthy(endpoint, str(e))
    
    async def _mark_endpoint_unhealthy(self, endpoint: EndpointConfig, error: str):
        """Mark endpoint as unhealthy"""
        endpoint.consecutive_failures += 1
        endpoint.last_health_check = datetime.now()
        
        if endpoint.consecutive_failures >= 3:
            endpoint.status = "failed"
            logger.error(f"❌ Endpoint {endpoint.endpoint_id} marked as failed: {error}")
        else:
            endpoint.status = "degraded"
            logger.warning(f"⚠️ Endpoint {endpoint.endpoint_id} degraded: {error}")
    
    def save_configuration(self, filename: str = "advanced_config.json"):
        """Save current configuration to file"""
        config_data = {
            "profiles": {name: asdict(profile) for name, profile in self.profiles.items()},
            "active_profile": self.active_profile,
            "circuit_breakers": self.circuit_breakers,
            "created_at": datetime.now().isoformat()
        }
        
        config_file = self.config_dir / filename
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2, default=str)
        
        logger.info(f"💾 Configuration saved to {config_file}")
    
    def load_configuration(self, filename: str = "advanced_config.json") -> bool:
        """Load configuration from file"""
        config_file = self.config_dir / filename
        
        if not config_file.exists():
            logger.warning(f"⚠️ Configuration file not found: {config_file}")
            return False
        
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Reconstruct profiles
            self.profiles.clear()
            for name, profile_data in config_data.get("profiles", {}).items():
                # Convert datetime strings back to datetime objects
                if "created_at" in profile_data:
                    profile_data["created_at"] = datetime.fromisoformat(profile_data["created_at"])
                
                # Reconstruct dataclass objects
                endpoints = [EndpointConfig(**ep) for ep in profile_data["endpoints"]]
                lb_config = LoadBalancerConfig(**profile_data["load_balancer"])
                perf_targets = PerformanceTarget(**profile_data["performance_targets"])
                
                profile = ConfigurationProfile(
                    profile_name=profile_data["profile_name"],
                    description=profile_data["description"],
                    endpoints=endpoints,
                    load_balancer=lb_config,
                    performance_targets=perf_targets,
                    scaling_enabled=profile_data["scaling_enabled"],
                    monitoring_enabled=profile_data["monitoring_enabled"],
                    backup_strategy=profile_data["backup_strategy"],
                    created_at=profile_data.get("created_at", datetime.now())
                )
                
                self.profiles[name] = profile
            
            # Restore other state
            self.active_profile = config_data.get("active_profile")
            self.circuit_breakers = config_data.get("circuit_breakers", {})
            
            logger.info(f"✅ Configuration loaded from {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        if not self.active_profile:
            return {"status": "no_active_profile"}
        
        profile = self.profiles[self.active_profile]
        
        status = {
            "active_profile": profile.profile_name,
            "total_endpoints": len(profile.endpoints),
            "healthy_endpoints": len([ep for ep in profile.endpoints if ep.status == "healthy"]),
            "failed_endpoints": len([ep for ep in profile.endpoints if ep.status == "failed"]),
            "circuit_breakers_open": len([cb for cb in self.circuit_breakers.values() if cb.get("state") == "open"]),
            "endpoint_details": {},
            "load_balancer_algorithm": profile.load_balancer.algorithm,
            "performance_targets": asdict(profile.performance_targets)
        }
        
        for endpoint in profile.endpoints:
            status["endpoint_details"][endpoint.endpoint_id] = {
                "status": endpoint.status,
                "current_load": endpoint.current_load,
                "avg_response_time": endpoint.avg_response_time,
                "success_rate": endpoint.success_rate,
                "consecutive_failures": endpoint.consecutive_failures
            }
        
        return status

# Initialize global advanced configuration manager
advanced_config = LocalAIAdvancedConfig()

async def initialize_advanced_config() -> bool:
    """Initialize the advanced configuration system"""
    logger.info("🏗️ Initializing Advanced Configuration System...")
    
    # Create predefined profiles
    advanced_config.create_trading_profiles()
    
    # Try to load existing configuration
    if not advanced_config.load_configuration():
        logger.info("📋 No existing configuration found, using defaults")
    
    # Default to development profile for safety
    if not advanced_config.active_profile:
        success = advanced_config.activate_profile("development")
        if success:
            logger.info("✅ Activated default development profile")
        else:
            logger.error("❌ Failed to activate default profile")
            return False
    
    # Save configuration
    advanced_config.save_configuration()
    
    return True

if __name__ == "__main__":
    asyncio.run(initialize_advanced_config())