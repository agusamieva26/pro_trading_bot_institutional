#!/usr/bin/env python3
"""
🚀 LOCALAI PERFORMANCE OPTIMIZATION ENGINE
GPU acceleration and advanced performance monitoring for institutional trading
- GPU Resource Management & Optimization
- Dynamic Performance Scaling
- Real-time Resource Monitoring
- Intelligent Caching Systems
- Memory & CPU Optimization
- Latency Optimization for Trading
"""
import os
import json
import asyncio
import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from loguru import logger
from pathlib import Path
import subprocess
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import queue
import gc

@dataclass
class SystemResources:
    """Current system resource usage"""
    cpu_usage: float
    memory_usage: float
    memory_available: float
    gpu_usage: float
    gpu_memory_usage: float
    gpu_memory_available: float
    disk_io: Dict[str, float]
    network_io: Dict[str, float]
    temperature: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class PerformanceProfile:
    """Performance optimization profile"""
    name: str
    max_cpu_usage: float
    max_memory_usage: float
    max_gpu_usage: float
    target_latency: float  # milliseconds
    cache_size: int  # MB
    batch_size: int
    gpu_layers: int
    threading_mode: str  # single, multi, adaptive
    optimization_level: str  # conservative, balanced, aggressive
    priority_class: str  # low, normal, high, realtime

@dataclass
class OptimizationAction:
    """Performance optimization action"""
    action_type: str
    target: str
    old_value: Any
    new_value: Any
    impact_score: float
    timestamp: datetime = field(default_factory=datetime.now)
    applied: bool = False

class GPUManager:
    """
    🎮 Advanced GPU Management System
    """
    
    def __init__(self):
        self.gpu_available = self._detect_gpu()
        self.gpu_devices = []
        self.gpu_memory_pools = {}
        self.current_allocations = {}
        
        if self.gpu_available:
            self._initialize_gpu_pools()
    
    def _detect_gpu(self) -> bool:
        """Detect and configure GPU availability"""
        try:
            # Try NVIDIA first
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                gpu_info = result.stdout.strip().split('\n')
                for i, info in enumerate(gpu_info):
                    name, memory = info.split(', ')
                    self.gpu_devices.append({
                        'id': i,
                        'name': name.strip(),
                        'memory': int(memory),
                        'vendor': 'nvidia'
                    })
                logger.info(f"🎮 Detected {len(self.gpu_devices)} NVIDIA GPU(s)")
                return True
        except FileNotFoundError:
            pass
        
        try:
            # Try AMD ROCm
            result = subprocess.run(['rocm-smi', '--showproductname', '--showmeminfo', 'vram'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                # Parse AMD GPU info (simplified)
                self.gpu_devices.append({
                    'id': 0,
                    'name': 'AMD GPU',
                    'memory': 8192,  # Default assumption
                    'vendor': 'amd'
                })
                logger.info("🎮 Detected AMD GPU")
                return True
        except FileNotFoundError:
            pass
        
        try:
            # Try Intel Arc
            import torch
            if torch.cuda.is_available():
                self.gpu_devices.append({
                    'id': 0,
                    'name': 'Intel Arc GPU',
                    'memory': 4096,  # Default assumption
                    'vendor': 'intel'
                })
                logger.info("🎮 Detected Intel GPU")
                return True
        except ImportError:
            pass
        
        logger.info("💻 No GPU detected - CPU-only mode")
        return False
    
    def _initialize_gpu_pools(self):
        """Initialize GPU memory pools for efficient allocation"""
        for device in self.gpu_devices:
            device_id = device['id']
            total_memory = device['memory']
            
            # Reserve memory pools
            self.gpu_memory_pools[device_id] = {
                'total': total_memory,
                'reserved': int(total_memory * 0.2),  # 20% reserved for system
                'model_cache': int(total_memory * 0.5),  # 50% for model cache
                'inference': int(total_memory * 0.3),  # 30% for inference
                'available': total_memory,
                'allocated': 0
            }
    
    def allocate_gpu_memory(self, model_id: str, required_memory: int) -> Optional[int]:
        """Allocate GPU memory for a model"""
        if not self.gpu_available:
            return None
        
        # Find best GPU for allocation
        best_gpu = None
        max_available = 0
        
        for device_id, pool in self.gpu_memory_pools.items():
            available = pool['available']
            if available >= required_memory and available > max_available:
                best_gpu = device_id
                max_available = available
        
        if best_gpu is not None:
            # Allocate memory
            self.gpu_memory_pools[best_gpu]['available'] -= required_memory
            self.gpu_memory_pools[best_gpu]['allocated'] += required_memory
            self.current_allocations[model_id] = {
                'gpu_id': best_gpu,
                'memory': required_memory,
                'allocated_at': datetime.now()
            }
            
            logger.info(f"🎮 Allocated {required_memory}MB on GPU {best_gpu} for {model_id}")
            return best_gpu
        
        return None
    
    def get_gpu_utilization(self) -> Dict[str, Any]:
        """Get current GPU utilization metrics"""
        if not self.gpu_available:
            return {'gpu_available': False}
        
        utilization = {'gpu_available': True, 'devices': []}
        
        try:
            if self.gpu_devices[0]['vendor'] == 'nvidia':
                result = subprocess.run([
                    'nvidia-smi', 
                    '--query-gpu=utilization.gpu,utilization.memory,temperature.gpu,memory.used,memory.total',
                    '--format=csv,noheader,nounits'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for i, line in enumerate(lines):
                        parts = line.split(', ')
                        if len(parts) >= 5:
                            utilization['devices'].append({
                                'id': i,
                                'gpu_util': float(parts[0]),
                                'memory_util': float(parts[1]),
                                'temperature': float(parts[2]),
                                'memory_used': int(parts[3]),
                                'memory_total': int(parts[4])
                            })
        except Exception as e:
            logger.debug(f"GPU utilization query failed: {e}")
        
        return utilization

class PerformanceOptimizer:
    """
    🚀 Advanced Performance Optimization Engine
    """
    
    def __init__(self):
        self.gpu_manager = GPUManager()
        self.monitoring_active = False
        self.optimization_thread = None
        self.resource_history: List[SystemResources] = []
        self.performance_profiles: Dict[str, PerformanceProfile] = {}
        self.active_profile: Optional[str] = None
        self.optimization_actions: List[OptimizationAction] = []
        
        # Performance cache
        self.response_cache = {}
        self.cache_max_size = 1000
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Initialize profiles
        self._create_performance_profiles()
        
        logger.info("🚀 Performance Optimization Engine initialized")
    
    def _create_performance_profiles(self):
        """Create predefined performance profiles"""
        
        # 1. HIGH FREQUENCY TRADING PROFILE
        self.performance_profiles["hft"] = PerformanceProfile(
            name="High Frequency Trading",
            max_cpu_usage=95.0,
            max_memory_usage=90.0,
            max_gpu_usage=95.0,
            target_latency=100.0,  # 100ms max
            cache_size=2048,  # 2GB cache
            batch_size=1,  # No batching for HFT
            gpu_layers=35,
            threading_mode="adaptive",
            optimization_level="aggressive",
            priority_class="realtime"
        )
        
        # 2. INSTITUTIONAL ANALYSIS PROFILE
        self.performance_profiles["institutional"] = PerformanceProfile(
            name="Institutional Analysis",
            max_cpu_usage=80.0,
            max_memory_usage=85.0,
            max_gpu_usage=90.0,
            target_latency=1000.0,  # 1 second
            cache_size=4096,  # 4GB cache
            batch_size=8,
            gpu_layers=40,
            threading_mode="multi",
            optimization_level="balanced",
            priority_class="high"
        )
        
        # 3. DEVELOPMENT PROFILE
        self.performance_profiles["development"] = PerformanceProfile(
            name="Development & Testing",
            max_cpu_usage=70.0,
            max_memory_usage=75.0,
            max_gpu_usage=80.0,
            target_latency=5000.0,  # 5 seconds
            cache_size=1024,  # 1GB cache
            batch_size=4,
            gpu_layers=20,
            threading_mode="single",
            optimization_level="conservative",
            priority_class="normal"
        )
        
        logger.info(f"✅ Created {len(self.performance_profiles)} performance profiles")
    
    def activate_profile(self, profile_name: str) -> bool:
        """Activate a performance profile"""
        if profile_name not in self.performance_profiles:
            logger.error(f"❌ Performance profile '{profile_name}' not found")
            return False
        
        self.active_profile = profile_name
        profile = self.performance_profiles[profile_name]
        
        # Apply profile settings
        self._apply_system_optimizations(profile)
        
        logger.info(f"✅ Activated performance profile: {profile.name}")
        return True
    
    def _apply_system_optimizations(self, profile: PerformanceProfile):
        """Apply system-level optimizations based on profile"""
        try:
            # Set process priority
            current_process = psutil.Process()
            
            if profile.priority_class == "realtime":
                # Highest priority (be careful!)
                current_process.nice(-10)
            elif profile.priority_class == "high":
                current_process.nice(-5)
            elif profile.priority_class == "normal":
                current_process.nice(0)
            else:  # low
                current_process.nice(5)
            
            # Configure garbage collection based on optimization level
            if profile.optimization_level == "aggressive":
                # Disable automatic GC for performance
                gc.disable()
                # Manual GC every 1000 operations
                self._setup_manual_gc(1000)
            elif profile.optimization_level == "balanced":
                # Tune GC thresholds
                gc.set_threshold(700, 10, 10)
            # Conservative keeps default GC settings
            
            logger.info(f"⚙️ Applied system optimizations for {profile.name}")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not apply all system optimizations: {e}")
    
    def _setup_manual_gc(self, operations_threshold: int):
        """Setup manual garbage collection for aggressive optimization"""
        self.gc_counter = 0
        self.gc_threshold = operations_threshold
    
    def trigger_gc_if_needed(self):
        """Trigger garbage collection if threshold reached"""
        if hasattr(self, 'gc_counter'):
            self.gc_counter += 1
            if self.gc_counter >= self.gc_threshold:
                gc.collect()
                self.gc_counter = 0
    
    async def start_monitoring(self, interval: float = 1.0):
        """Start performance monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.optimization_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self.optimization_thread.start()
        
        logger.info("📊 Performance monitoring started")
    
    def _monitoring_loop(self, interval: float):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                resources = self._collect_system_resources()
                self.resource_history.append(resources)
                
                # Keep only last 1000 measurements
                if len(self.resource_history) > 1000:
                    self.resource_history = self.resource_history[-1000:]
                
                # Check for optimization opportunities
                self._check_optimization_opportunities(resources)
                
                # Cleanup cache if needed
                self._cleanup_cache()
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"❌ Monitoring loop error: {e}")
                time.sleep(interval)
    
    def _collect_system_resources(self) -> SystemResources:
        """Collect current system resource metrics"""
        # CPU and Memory
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        # GPU metrics
        gpu_util = self.gpu_manager.get_gpu_utilization()
        gpu_usage = 0.0
        gpu_memory_usage = 0.0
        gpu_memory_available = 0.0
        
        if gpu_util['gpu_available'] and gpu_util['devices']:
            gpu_device = gpu_util['devices'][0]
            gpu_usage = gpu_device['gpu_util']
            gpu_memory_usage = (gpu_device['memory_used'] / gpu_device['memory_total']) * 100
            gpu_memory_available = gpu_device['memory_total'] - gpu_device['memory_used']
        
        # Disk I/O
        disk_io = psutil.disk_io_counters()
        disk_metrics = {
            'read_bytes': disk_io.read_bytes if disk_io else 0,
            'write_bytes': disk_io.write_bytes if disk_io else 0
        }
        
        # Network I/O
        net_io = psutil.net_io_counters()
        net_metrics = {
            'bytes_sent': net_io.bytes_sent if net_io else 0,
            'bytes_recv': net_io.bytes_recv if net_io else 0
        }
        
        # Temperature (if available)
        temperatures = {}
        try:
            sensors = psutil.sensors_temperatures()
            for name, entries in sensors.items():
                if entries:
                    temperatures[name] = entries[0].current
        except:
            pass
        
        return SystemResources(
            cpu_usage=cpu_usage,
            memory_usage=memory.percent,
            memory_available=memory.available / (1024**3),  # GB
            gpu_usage=gpu_usage,
            gpu_memory_usage=gpu_memory_usage,
            gpu_memory_available=gpu_memory_available,
            disk_io=disk_metrics,
            network_io=net_metrics,
            temperature=temperatures
        )
    
    def _check_optimization_opportunities(self, resources: SystemResources):
        """Check for performance optimization opportunities"""
        if not self.active_profile:
            return
        
        profile = self.performance_profiles[self.active_profile]
        
        # Check CPU usage
        if resources.cpu_usage > profile.max_cpu_usage:
            self._suggest_cpu_optimization(resources.cpu_usage, profile.max_cpu_usage)
        
        # Check memory usage
        if resources.memory_usage > profile.max_memory_usage:
            self._suggest_memory_optimization(resources.memory_usage, profile.max_memory_usage)
        
        # Check GPU usage
        if resources.gpu_usage > profile.max_gpu_usage:
            self._suggest_gpu_optimization(resources.gpu_usage, profile.max_gpu_usage)
        
        # Check for memory leaks (rising trend)
        if len(self.resource_history) >= 10:
            recent_memory = [r.memory_usage for r in self.resource_history[-10:]]
            if self._is_trending_up(recent_memory, threshold=5.0):
                self._suggest_memory_leak_check()
    
    def _is_trending_up(self, values: List[float], threshold: float) -> bool:
        """Check if values are trending upward"""
        if len(values) < 3:
            return False
        
        slope = (values[-1] - values[0]) / len(values)
        return slope > threshold
    
    def _suggest_cpu_optimization(self, current: float, target: float):
        """Suggest CPU optimization actions"""
        action = OptimizationAction(
            action_type="cpu_optimization",
            target="cpu_usage",
            old_value=current,
            new_value=target,
            impact_score=8.0
        )
        
        self.optimization_actions.append(action)
        logger.warning(f"🔥 High CPU usage detected: {current:.1f}% (target: {target:.1f}%)")
    
    def _suggest_memory_optimization(self, current: float, target: float):
        """Suggest memory optimization actions"""
        action = OptimizationAction(
            action_type="memory_optimization",
            target="memory_usage",
            old_value=current,
            new_value=target,
            impact_score=7.0
        )
        
        self.optimization_actions.append(action)
        logger.warning(f"💾 High memory usage detected: {current:.1f}% (target: {target:.1f}%)")
        
        # Trigger immediate garbage collection
        gc.collect()
    
    def _suggest_gpu_optimization(self, current: float, target: float):
        """Suggest GPU optimization actions"""
        action = OptimizationAction(
            action_type="gpu_optimization",
            target="gpu_usage",
            old_value=current,
            new_value=target,
            impact_score=9.0
        )
        
        self.optimization_actions.append(action)
        logger.warning(f"🎮 High GPU usage detected: {current:.1f}% (target: {target:.1f}%)")
    
    def _suggest_memory_leak_check(self):
        """Suggest memory leak investigation"""
        action = OptimizationAction(
            action_type="memory_leak_check",
            target="memory_trend",
            old_value="increasing",
            new_value="stable",
            impact_score=6.0
        )
        
        self.optimization_actions.append(action)
        logger.warning("📈 Potential memory leak detected - memory usage trending upward")
    
    def optimize_inference_request(self, model_type: str, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """Optimize an inference request based on current performance profile"""
        if not self.active_profile:
            return {"optimized": False, "reason": "No active profile"}
        
        profile = self.performance_profiles[self.active_profile]
        optimizations = []
        
        # Check cache first
        cache_key = self._generate_cache_key(model_type, prompt, max_tokens)
        if cache_key in self.response_cache:
            self.cache_hits += 1
            return {
                "optimized": True,
                "cache_hit": True,
                "response": self.response_cache[cache_key]["response"],
                "original_time": self.response_cache[cache_key]["response_time"]
            }
        
        self.cache_misses += 1
        
        # Optimize batch size
        optimized_batch_size = profile.batch_size
        if profile.optimization_level == "aggressive" and model_type == "sentiment":
            optimized_batch_size = 1  # No batching for real-time sentiment
        
        # Optimize token limits based on use case
        optimized_max_tokens = max_tokens
        if profile.optimization_level == "aggressive":
            if model_type == "sentiment":
                optimized_max_tokens = min(max_tokens, 50)  # Short responses
            elif model_type == "prediction":
                optimized_max_tokens = min(max_tokens, 200)  # Concise predictions
        
        # GPU optimization
        gpu_config = {}
        if self.gpu_manager.gpu_available:
            gpu_config = {
                "gpu_layers": profile.gpu_layers,
                "use_gpu": True,
                "memory_map": True
            }
        
        return {
            "optimized": True,
            "cache_hit": False,
            "batch_size": optimized_batch_size,
            "max_tokens": optimized_max_tokens,
            "gpu_config": gpu_config,
            "target_latency": profile.target_latency,
            "optimizations": optimizations
        }
    
    def cache_response(self, model_type: str, prompt: str, max_tokens: int, 
                      response: str, response_time: float):
        """Cache a response for future use"""
        cache_key = self._generate_cache_key(model_type, prompt, max_tokens)
        
        # Don't cache if cache is full and this is a low-value response
        if len(self.response_cache) >= self.cache_max_size:
            self._cleanup_cache()
        
        self.response_cache[cache_key] = {
            "response": response,
            "response_time": response_time,
            "cached_at": datetime.now(),
            "access_count": 1
        }
    
    def _generate_cache_key(self, model_type: str, prompt: str, max_tokens: int) -> str:
        """Generate a cache key for the request"""
        combined = f"{model_type}:{prompt}:{max_tokens}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    def _cleanup_cache(self):
        """Clean up old cache entries"""
        if len(self.response_cache) <= self.cache_max_size:
            return
        
        # Remove oldest entries first
        sorted_cache = sorted(
            self.response_cache.items(),
            key=lambda x: (x[1]["access_count"], x[1]["cached_at"])
        )
        
        # Remove 25% of cache
        remove_count = len(self.response_cache) // 4
        for i in range(remove_count):
            del self.response_cache[sorted_cache[i][0]]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        if not self.resource_history:
            return {"error": "No metrics available"}
        
        latest = self.resource_history[-1]
        
        # Calculate averages over last 60 measurements (1 minute if 1sec interval)
        recent_history = self.resource_history[-60:] if len(self.resource_history) >= 60 else self.resource_history
        
        avg_cpu = sum(r.cpu_usage for r in recent_history) / len(recent_history)
        avg_memory = sum(r.memory_usage for r in recent_history) / len(recent_history)
        avg_gpu = sum(r.gpu_usage for r in recent_history) / len(recent_history)
        
        cache_hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0.0
        
        return {
            "current": {
                "cpu_usage": latest.cpu_usage,
                "memory_usage": latest.memory_usage,
                "gpu_usage": latest.gpu_usage,
                "memory_available_gb": latest.memory_available,
                "temperature": latest.temperature
            },
            "averages": {
                "cpu_usage": avg_cpu,
                "memory_usage": avg_memory,
                "gpu_usage": avg_gpu
            },
            "cache": {
                "hit_rate": cache_hit_rate,
                "total_hits": self.cache_hits,
                "total_misses": self.cache_misses,
                "cache_size": len(self.response_cache)
            },
            "gpu": self.gpu_manager.get_gpu_utilization(),
            "active_profile": self.active_profile,
            "optimization_actions": len(self.optimization_actions),
            "monitoring_active": self.monitoring_active
        }
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        if self.optimization_thread:
            self.optimization_thread.join(timeout=5.0)
        logger.info("📊 Performance monitoring stopped")

# Initialize global performance optimizer
performance_optimizer = PerformanceOptimizer()

async def initialize_performance_optimization() -> bool:
    """Initialize the performance optimization system"""
    logger.info("🚀 Initializing Performance Optimization Engine...")
    
    # Start with development profile for safety
    if not performance_optimizer.activate_profile("development"):
        logger.error("❌ Failed to activate default performance profile")
        return False
    
    # Start monitoring
    await performance_optimizer.start_monitoring(interval=1.0)
    
    logger.info("✅ Performance Optimization Engine ready")
    return True

if __name__ == "__main__":
    asyncio.run(initialize_performance_optimization())