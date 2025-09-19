#!/usr/bin/env python3
"""
⚡ LocalAI Performance Optimizer
Advanced performance optimization system for LocalAI institutional deployments
"""
import os
import time
import psutil
import threading
import statistics
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import deque, defaultdict
from loguru import logger
import json
from pathlib import Path

class OptimizationMode(Enum):
    """Performance optimization modes"""
    LATENCY_OPTIMIZED = "latency_optimized"
    THROUGHPUT_OPTIMIZED = "throughput_optimized"
    BALANCED = "balanced"
    MEMORY_CONSERVING = "memory_conserving"
    GPU_OPTIMIZED = "gpu_optimized"

class ResourceType(Enum):
    """System resource types"""
    CPU = "cpu"
    MEMORY = "memory"
    GPU = "gpu"
    DISK = "disk"
    NETWORK = "network"

@dataclass
class SystemResources:
    """Current system resource metrics"""
    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    disk_usage_percent: float
    gpu_memory_percent: float = 0.0
    gpu_utilization_percent: float = 0.0
    network_io_mb_s: float = 0.0
    temperature_celsius: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class PerformanceProfile:
    """Performance profile for optimization"""
    mode: OptimizationMode
    max_concurrent_requests: int
    context_length: int
    batch_size: int
    threads: int
    gpu_layers: int
    temperature: float
    memory_limit_gb: float
    cache_enabled: bool = True
    compression_enabled: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceMetrics:
    """Performance metrics tracking"""
    requests_per_second: float
    average_latency_ms: float
    p95_latency_ms: float
    error_rate_percent: float
    throughput_tokens_per_second: float
    memory_efficiency_percent: float
    cpu_efficiency_percent: float
    cache_hit_rate_percent: float
    timestamp: datetime = field(default_factory=datetime.now)

class LocalAIPerformanceOptimizer:
    """
    ⚡ Advanced Performance Optimization System
    Intelligent performance tuning and resource management for LocalAI
    """
    
    def __init__(self, monitoring_interval: int = 10):
        self.monitoring_interval = monitoring_interval
        self.optimization_mode = OptimizationMode.BALANCED
        
        # Performance tracking
        self.metrics_history: deque = deque(maxlen=1000)
        self.resource_history: deque = deque(maxlen=1000)
        self.optimization_history: List[Dict] = []
        
        # Current profiles
        self.profiles: Dict[str, PerformanceProfile] = {}
        self.active_profile: Optional[str] = None
        
        # Monitoring
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        
        # Performance cache
        self.performance_cache: Dict[str, Any] = {}
        
        self._create_default_profiles()
        self._start_monitoring()
        
        logger.info("⚡ LocalAI Performance Optimizer initialized")
    
    def _create_default_profiles(self) -> None:
        """Create default optimization profiles"""
        self.profiles = {
            "latency_optimized": PerformanceProfile(
                mode=OptimizationMode.LATENCY_OPTIMIZED,
                max_concurrent_requests=2,
                context_length=2048,
                batch_size=1,
                threads=max(1, psutil.cpu_count() // 2),
                gpu_layers=35,
                temperature=0.3,
                memory_limit_gb=4.0,
                cache_enabled=True
            ),
            "throughput_optimized": PerformanceProfile(
                mode=OptimizationMode.THROUGHPUT_OPTIMIZED,
                max_concurrent_requests=8,
                context_length=4096,
                batch_size=8,
                threads=psutil.cpu_count(),
                gpu_layers=35,
                temperature=0.7,
                memory_limit_gb=8.0,
                cache_enabled=True
            ),
            "balanced": PerformanceProfile(
                mode=OptimizationMode.BALANCED,
                max_concurrent_requests=4,
                context_length=4096,
                batch_size=4,
                threads=max(2, psutil.cpu_count() // 2),
                gpu_layers=25,
                temperature=0.5,
                memory_limit_gb=6.0,
                cache_enabled=True
            ),
            "memory_conserving": PerformanceProfile(
                mode=OptimizationMode.MEMORY_CONSERVING,
                max_concurrent_requests=1,
                context_length=1024,
                batch_size=1,
                threads=2,
                gpu_layers=0,
                temperature=0.7,
                memory_limit_gb=2.0,
                cache_enabled=False
            )
        }
        
        self.active_profile = "balanced"
    
    def get_system_resources(self) -> SystemResources:
        """Get current system resource metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network (simplified)
            network_io = psutil.net_io_counters()
            network_mb_s = 0.0  # Simplified for now
            
            # GPU (if available)
            gpu_memory_percent = 0.0
            gpu_utilization = 0.0
            
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    gpu_memory_percent = (gpu.memoryUsed / gpu.memoryTotal) * 100
                    gpu_utilization = gpu.load * 100
            except:
                pass  # GPU monitoring optional
            
            return SystemResources(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_available_gb=memory.available / (1024**3),
                disk_usage_percent=disk.percent,
                gpu_memory_percent=gpu_memory_percent,
                gpu_utilization_percent=gpu_utilization,
                network_io_mb_s=network_mb_s
            )
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to get system resources: {e}")
            return SystemResources(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_available_gb=0.0,
                disk_usage_percent=0.0
            )
    
    def optimize_for_workload(self, workload_type: str = "general") -> PerformanceProfile:
        """Optimize performance profile for specific workload"""
        current_resources = self.get_system_resources()
        
        # Determine optimal profile based on resources and workload
        if current_resources.memory_available_gb < 4:
            optimal_profile = "memory_conserving"
        elif current_resources.cpu_percent > 80:
            optimal_profile = "latency_optimized"
        elif workload_type == "batch_processing":
            optimal_profile = "throughput_optimized"
        else:
            optimal_profile = "balanced"
        
        self.active_profile = optimal_profile
        profile = self.profiles[optimal_profile]
        
        logger.info(f"🎯 Optimized for {workload_type}: {optimal_profile}")
        
        # Log optimization decision
        self.optimization_history.append({
            "timestamp": datetime.now().isoformat(),
            "workload_type": workload_type,
            "selected_profile": optimal_profile,
            "system_resources": {
                "cpu_percent": current_resources.cpu_percent,
                "memory_available_gb": current_resources.memory_available_gb,
                "gpu_available": current_resources.gpu_utilization_percent > 0
            }
        })
        
        return profile
    
    def get_optimal_batch_size(self, available_memory_gb: float) -> int:
        """Calculate optimal batch size based on available memory"""
        if available_memory_gb >= 8:
            return 8
        elif available_memory_gb >= 4:
            return 4
        elif available_memory_gb >= 2:
            return 2
        else:
            return 1
    
    def get_optimal_context_length(self, task_complexity: str = "medium") -> int:
        """Get optimal context length based on task complexity"""
        complexity_map = {
            "simple": 1024,
            "medium": 2048,
            "complex": 4096,
            "very_complex": 8192
        }
        
        base_length = complexity_map.get(task_complexity, 2048)
        current_resources = self.get_system_resources()
        
        # Reduce context length if memory is constrained
        if current_resources.memory_available_gb < 4:
            base_length = min(base_length, 2048)
        elif current_resources.memory_available_gb < 2:
            base_length = min(base_length, 1024)
        
        return base_length
    
    def get_performance_recommendations(self) -> Dict[str, Any]:
        """Get performance optimization recommendations"""
        current_resources = self.get_system_resources()
        recommendations = []
        
        # Memory recommendations
        if current_resources.memory_available_gb < 2:
            recommendations.append({
                "type": "memory",
                "priority": "high",
                "message": "Low memory detected. Consider using memory_conserving profile.",
                "action": "switch_profile",
                "target": "memory_conserving"
            })
        
        # CPU recommendations
        if current_resources.cpu_percent > 90:
            recommendations.append({
                "type": "cpu",
                "priority": "high",
                "message": "High CPU usage. Consider reducing concurrent requests.",
                "action": "reduce_concurrency",
                "target": max(1, self.profiles[self.active_profile].max_concurrent_requests // 2)
            })
        
        # GPU recommendations
        if current_resources.gpu_utilization_percent == 0 and current_resources.gpu_memory_percent == 0:
            recommendations.append({
                "type": "gpu",
                "priority": "medium",
                "message": "No GPU utilization detected. Consider CPU-only optimization.",
                "action": "disable_gpu_layers",
                "target": 0
            })
        
        return {
            "current_resources": current_resources,
            "active_profile": self.active_profile,
            "recommendations": recommendations,
            "performance_score": self._calculate_performance_score(current_resources)
        }
    
    def _calculate_performance_score(self, resources: SystemResources) -> float:
        """Calculate overall performance score (0-100)"""
        # Inverse relationship for resource usage (lower is better)
        cpu_score = max(0, 100 - resources.cpu_percent)
        memory_score = max(0, 100 - resources.memory_percent)
        
        # GPU score (higher utilization is better if GPU is available)
        gpu_score = resources.gpu_utilization_percent if resources.gpu_utilization_percent > 0 else 50
        
        # Weighted average
        total_score = (cpu_score * 0.4 + memory_score * 0.4 + gpu_score * 0.2)
        return round(total_score, 2)
    
    def _start_monitoring(self) -> None:
        """Start resource monitoring thread"""
        if self._monitoring_thread is None or not self._monitoring_thread.is_alive():
            self._monitoring_thread = threading.Thread(target=self._monitor_resources, daemon=True)
            self._monitoring_thread.start()
    
    def _monitor_resources(self) -> None:
        """Monitor system resources continuously"""
        while not self._stop_monitoring.is_set():
            try:
                resources = self.get_system_resources()
                self.resource_history.append(resources)
                
                # Log warnings for high resource usage
                if resources.cpu_percent > 95:
                    logger.warning(f"🔥 High CPU usage: {resources.cpu_percent:.1f}%")
                
                if resources.memory_percent > 90:
                    logger.warning(f"🧠 High memory usage: {resources.memory_percent:.1f}%")
                
            except Exception as e:
                logger.debug(f"Monitoring error: {e}")
            
            time.sleep(self.monitoring_interval)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary with historical data"""
        if not self.resource_history:
            return {"error": "No performance data available"}
        
        recent_resources = list(self.resource_history)[-10:]  # Last 10 measurements
        
        avg_cpu = statistics.mean([r.cpu_percent for r in recent_resources])
        avg_memory = statistics.mean([r.memory_percent for r in recent_resources])
        avg_memory_available = statistics.mean([r.memory_available_gb for r in recent_resources])
        
        return {
            "current_profile": self.active_profile,
            "optimization_mode": self.optimization_mode.value,
            "average_metrics": {
                "cpu_percent": round(avg_cpu, 2),
                "memory_percent": round(avg_memory, 2),
                "memory_available_gb": round(avg_memory_available, 2)
            },
            "total_optimizations": len(self.optimization_history),
            "monitoring_active": self._monitoring_thread is not None and self._monitoring_thread.is_alive()
        }
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self._stop_monitoring.set()
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
        logger.info("⚡ Performance optimizer cleanup completed")