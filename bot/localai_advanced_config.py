#!/usr/bin/env python3
"""
🔧 LocalAI Advanced Configuration System
Professional configuration management for LocalAI institutional deployments
"""
import os
import json
import yaml
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from loguru import logger

class LoadBalancingStrategy(Enum):
    """Load balancing strategies for multi-endpoint setups"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_RESPONSE_TIME = "weighted_response_time"
    RESOURCE_BASED = "resource_based"
    PERFORMANCE_BASED = "performance_based"

class EndpointHealth(Enum):
    """Health status of endpoints"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class EndpointConfig:
    """Configuration for individual LocalAI endpoints"""
    name: str
    url: str
    port: int
    model_name: str
    weight: float = 1.0
    max_connections: int = 10
    timeout_seconds: float = 30.0
    health_check_interval: int = 30
    enabled: bool = True
    gpu_enabled: bool = False
    context_length: int = 4096
    temperature: float = 0.7
    max_tokens: int = 1024
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LoadBalancerConfig:
    """Load balancer configuration"""
    strategy: LoadBalancingStrategy
    health_check_enabled: bool = True
    failover_enabled: bool = True
    retry_attempts: int = 3
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    metrics_enabled: bool = True
    logging_enabled: bool = True

@dataclass
class SecurityConfig:
    """Security configuration for LocalAI"""
    api_key_required: bool = False
    rate_limiting_enabled: bool = True
    max_requests_per_minute: int = 100
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    ssl_enabled: bool = False
    cert_path: Optional[str] = None
    key_path: Optional[str] = None

class LocalAIAdvancedConfig:
    """
    🏛️ Advanced Configuration System for LocalAI
    Professional-grade configuration management with load balancing,
    health monitoring, and performance optimization
    """
    
    def __init__(self, config_dir: str = "bot/localai_configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.endpoints: Dict[str, EndpointConfig] = {}
        self.load_balancer = LoadBalancerConfig(
            strategy=LoadBalancingStrategy.PERFORMANCE_BASED
        )
        self.security = SecurityConfig()
        
        self._load_configuration()
        
        logger.info("🔧 LocalAI Advanced Configuration initialized")
    
    def add_endpoint(self, config: EndpointConfig) -> bool:
        """Add new endpoint configuration"""
        try:
            self.endpoints[config.name] = config
            self._save_configuration()
            logger.info(f"✅ Added endpoint: {config.name} ({config.url}:{config.port})")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to add endpoint {config.name}: {e}")
            return False
    
    def remove_endpoint(self, name: str) -> bool:
        """Remove endpoint configuration"""
        if name in self.endpoints:
            del self.endpoints[name]
            self._save_configuration()
            logger.info(f"🗑️ Removed endpoint: {name}")
            return True
        return False
    
    def get_active_endpoints(self) -> List[EndpointConfig]:
        """Get list of active endpoints"""
        return [ep for ep in self.endpoints.values() if ep.enabled]
    
    def get_endpoint_by_name(self, name: str) -> Optional[EndpointConfig]:
        """Get endpoint configuration by name"""
        return self.endpoints.get(name)
    
    def update_load_balancer_config(self, config: LoadBalancerConfig) -> None:
        """Update load balancer configuration"""
        self.load_balancer = config
        self._save_configuration()
        logger.info(f"🔄 Updated load balancer: {config.strategy.value}")
    
    def get_optimal_endpoint(self, prefer_gpu: bool = False) -> Optional[EndpointConfig]:
        """Get optimal endpoint based on configuration"""
        active_endpoints = self.get_active_endpoints()
        
        if not active_endpoints:
            return None
        
        if prefer_gpu:
            gpu_endpoints = [ep for ep in active_endpoints if ep.gpu_enabled]
            if gpu_endpoints:
                active_endpoints = gpu_endpoints
        
        # Simple selection based on weight for now
        return max(active_endpoints, key=lambda ep: ep.weight)
    
    def generate_yaml_config(self, endpoint: EndpointConfig) -> str:
        """Generate YAML configuration for LocalAI"""
        config = {
            "name": endpoint.model_name,
            "parameters": {
                "model": endpoint.model_name,
                "context_size": endpoint.context_length,
                "threads": 4,
                "f16": True,
                "low_vram": not endpoint.gpu_enabled,
                "gpu_layers": 35 if endpoint.gpu_enabled else 0,
                "temperature": endpoint.temperature,
                "top_k": 40,
                "top_p": 0.95,
                "max_tokens": endpoint.max_tokens,
                "batch_size": 8,
                "rope_freq_base": 10000,
                "rope_freq_scale": 1.0,
                "disable_no_action": True
            }
        }
        
        return yaml.dump(config, default_flow_style=False)
    
    def _load_configuration(self) -> None:
        """Load configuration from disk"""
        config_file = self.config_dir / "advanced_config.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                
                # Load endpoints
                for ep_data in data.get("endpoints", []):
                    endpoint = EndpointConfig(**ep_data)
                    self.endpoints[endpoint.name] = endpoint
                
                # Load load balancer config
                if "load_balancer" in data:
                    lb_data = data["load_balancer"]
                    lb_data["strategy"] = LoadBalancingStrategy(lb_data["strategy"])
                    self.load_balancer = LoadBalancerConfig(**lb_data)
                
                # Load security config
                if "security" in data:
                    self.security = SecurityConfig(**data["security"])
                
                logger.info(f"📁 Loaded configuration with {len(self.endpoints)} endpoints")
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to load configuration: {e}")
                self._create_default_configuration()
        else:
            self._create_default_configuration()
    
    def _save_configuration(self) -> None:
        """Save configuration to disk"""
        try:
            config_file = self.config_dir / "advanced_config.json"
            
            data = {
                "endpoints": [asdict(ep) for ep in self.endpoints.values()],
                "load_balancer": asdict(self.load_balancer),
                "security": asdict(self.security)
            }
            
            # Convert enums to strings
            data["load_balancer"]["strategy"] = data["load_balancer"]["strategy"].value
            
            with open(config_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Failed to save configuration: {e}")
    
    def _create_default_configuration(self) -> None:
        """Create default configuration"""
        # Add default local endpoint
        default_endpoint = EndpointConfig(
            name="local_default",
            url="localhost",
            port=8080,
            model_name="phi-4",
            weight=1.0,
            enabled=True
        )
        
        self.endpoints["local_default"] = default_endpoint
        self._save_configuration()
        
        logger.info("🔧 Created default LocalAI configuration")
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get summary of current configuration"""
        active_endpoints = self.get_active_endpoints()
        
        return {
            "total_endpoints": len(self.endpoints),
            "active_endpoints": len(active_endpoints),
            "gpu_endpoints": len([ep for ep in active_endpoints if ep.gpu_enabled]),
            "load_balancer_strategy": self.load_balancer.strategy.value,
            "security_enabled": self.security.api_key_required,
            "endpoints": [
                {
                    "name": ep.name,
                    "url": f"{ep.url}:{ep.port}",
                    "model": ep.model_name,
                    "gpu": ep.gpu_enabled,
                    "weight": ep.weight,
                    "enabled": ep.enabled
                }
                for ep in self.endpoints.values()
            ]
        }