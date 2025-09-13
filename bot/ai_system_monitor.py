"""
🔍 AI SYSTEM MONITOR - SISTEMA DE MONITOREO Y LOGGING AVANZADO
Sistema completo de logging, caching, error handling y monitoreo para el sistema AI Hybrid
Proporciona visibilidad completa y robustez operacional
"""

import asyncio
import json
import time
import threading
import traceback
import sqlite3
import pickle
import gzip
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict, deque
import logging
from logging.handlers import RotatingFileHandler
import hashlib
import psutil
import gc

from .util import logger
from .config import settings

@dataclass
class SystemEvent:
    """Evento del sistema para logging y monitoreo"""
    timestamp: datetime
    event_type: str  # "info", "warning", "error", "critical"
    component: str   # "news_engine", "sentiment_analyzer", "price_predictor", etc.
    event_id: str
    message: str
    data: Dict = None
    exception: str = None
    stack_trace: str = None
    performance_metrics: Dict = None

@dataclass
class PerformanceMetrics:
    """Métricas de rendimiento del sistema"""
    component: str
    operation: str
    duration_ms: float
    memory_usage_mb: float
    cpu_usage_pct: float
    timestamp: datetime
    success: bool
    error_message: str = None

class AdvancedCache:
    """
    🗄️ Sistema de cache avanzado con TTL, compresión y persistencia
    """
    
    def __init__(self, cache_dir: str = "data_cache/ai_cache", 
                 max_memory_mb: int = 500, compression: bool = True):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_memory_mb = max_memory_mb
        self.compression = compression
        
        # Cache en memoria
        self.memory_cache = {}
        self.cache_metadata = {}  # TTL, timestamps, access counts
        self.access_count = defaultdict(int)
        
        # Lock para thread safety
        self.lock = threading.RLock()
        
        # Cache de disco para persistencia
        self.disk_cache_file = self.cache_dir / "persistent_cache.pkl.gz"
        
        # Configuración
        self.default_ttl = 3600  # 1 hora
        self.cleanup_interval = 300  # 5 minutos
        self.max_items_memory = 1000
        
        # Estadísticas
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "disk_loads": 0,
            "disk_saves": 0
        }
        
        # Cargar cache persistente
        self._load_persistent_cache()
        
        # Iniciar cleanup automático
        self._start_cleanup_thread()
        
        logger.info(f"🗄️ Advanced Cache inicializado: {cache_dir}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtiene valor del cache con TTL check"""
        with self.lock:
            # Verificar cache en memoria
            if key in self.memory_cache:
                metadata = self.cache_metadata.get(key, {})
                
                # Verificar TTL
                if self._is_expired(metadata):
                    self._remove_from_memory(key)
                    self.stats["misses"] += 1
                    return self._check_disk_cache(key, default)
                
                # Cache hit
                self.access_count[key] += 1
                metadata["last_access"] = time.time()
                self.stats["hits"] += 1
                
                return self.memory_cache[key]
            
            # Cache miss - verificar disco
            self.stats["misses"] += 1
            return self._check_disk_cache(key, default)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Almacena valor en cache con TTL"""
        with self.lock:
            try:
                ttl = ttl or self.default_ttl
                current_time = time.time()
                
                # Metadata
                metadata = {
                    "created": current_time,
                    "last_access": current_time,
                    "ttl": ttl,
                    "size_bytes": self._estimate_size(value)
                }
                
                # Verificar límites de memoria
                if len(self.memory_cache) >= self.max_items_memory:
                    self._evict_lru()
                
                current_memory = self._get_cache_memory_usage()
                if current_memory > self.max_memory_mb:
                    self._evict_by_memory()
                
                # Almacenar en memoria
                self.memory_cache[key] = value
                self.cache_metadata[key] = metadata
                self.access_count[key] = 1
                
                # Almacenar en disco si es importante
                if ttl > 3600:  # Persistir si TTL > 1 hora
                    self._save_to_disk(key, value, metadata)
                
                return True
                
            except Exception as e:
                logger.error(f"Error guardando en cache {key}: {e}")
                return False
    
    def _check_disk_cache(self, key: str, default: Any) -> Any:
        """Verifica cache en disco"""
        try:
            disk_file = self.cache_dir / f"{hashlib.md5(key.encode()).hexdigest()}.cache"
            
            if disk_file.exists():
                if self.compression:
                    with gzip.open(disk_file, 'rb') as f:
                        data = pickle.load(f)
                else:
                    with open(disk_file, 'rb') as f:
                        data = pickle.load(f)
                
                # Verificar TTL
                if not self._is_expired(data["metadata"]):
                    # Cargar a memoria
                    self.memory_cache[key] = data["value"]
                    self.cache_metadata[key] = data["metadata"]
                    self.cache_metadata[key]["last_access"] = time.time()
                    
                    self.stats["disk_loads"] += 1
                    return data["value"]
                else:
                    # Eliminar archivo expirado
                    disk_file.unlink()
            
        except Exception as e:
            logger.debug(f"Error cargando desde disco {key}: {e}")
        
        return default
    
    def _save_to_disk(self, key: str, value: Any, metadata: Dict):
        """Guarda en disco para persistencia"""
        try:
            disk_file = self.cache_dir / f"{hashlib.md5(key.encode()).hexdigest()}.cache"
            
            data = {"value": value, "metadata": metadata}
            
            if self.compression:
                with gzip.open(disk_file, 'wb') as f:
                    pickle.dump(data, f)
            else:
                with open(disk_file, 'wb') as f:
                    pickle.dump(data, f)
            
            self.stats["disk_saves"] += 1
            
        except Exception as e:
            logger.debug(f"Error guardando a disco {key}: {e}")
    
    def _is_expired(self, metadata: Dict) -> bool:
        """Verifica si un item ha expirado"""
        if not metadata:
            return True
        
        created = metadata.get("created", 0)
        ttl = metadata.get("ttl", self.default_ttl)
        
        return time.time() - created > ttl
    
    def _evict_lru(self):
        """Elimina el item menos recientemente usado"""
        if not self.cache_metadata:
            return
        
        # Encontrar el menos recientemente accedido
        lru_key = min(
            self.cache_metadata.keys(),
            key=lambda k: self.cache_metadata[k].get("last_access", 0)
        )
        
        self._remove_from_memory(lru_key)
        self.stats["evictions"] += 1
    
    def _evict_by_memory(self):
        """Elimina items para liberar memoria"""
        # Ordenar por access count (menor primero)
        sorted_keys = sorted(
            self.memory_cache.keys(),
            key=lambda k: self.access_count[k]
        )
        
        # Eliminar 25% de los items menos usados
        items_to_remove = max(1, len(sorted_keys) // 4)
        
        for key in sorted_keys[:items_to_remove]:
            self._remove_from_memory(key)
            self.stats["evictions"] += 1
        
        # Forzar garbage collection
        gc.collect()
    
    def _remove_from_memory(self, key: str):
        """Elimina item de memoria"""
        self.memory_cache.pop(key, None)
        self.cache_metadata.pop(key, None)
        self.access_count.pop(key, None)
    
    def _get_cache_memory_usage(self) -> float:
        """Estima uso de memoria del cache"""
        total_size = 0
        for metadata in self.cache_metadata.values():
            total_size += metadata.get("size_bytes", 0)
        
        return total_size / (1024 * 1024)  # MB
    
    def _estimate_size(self, obj: Any) -> int:
        """Estima tamaño de un objeto"""
        try:
            return len(pickle.dumps(obj))
        except:
            return 1024  # Estimación por defecto
    
    def _load_persistent_cache(self):
        """Carga cache persistente al inicio"""
        try:
            if self.disk_cache_file.exists():
                if self.compression:
                    with gzip.open(self.disk_cache_file, 'rb') as f:
                        persistent_data = pickle.load(f)
                else:
                    with open(self.disk_cache_file, 'rb') as f:
                        persistent_data = pickle.load(f)
                
                # Cargar items no expirados
                current_time = time.time()
                for key, data in persistent_data.items():
                    if not self._is_expired(data.get("metadata", {})):
                        self.memory_cache[key] = data["value"]
                        self.cache_metadata[key] = data["metadata"]
                
                logger.info(f"📂 Cache persistente cargado: {len(self.memory_cache)} items")
        
        except Exception as e:
            logger.warning(f"Error cargando cache persistente: {e}")
    
    def _start_cleanup_thread(self):
        """Inicia thread de limpieza automática"""
        def cleanup_loop():
            while True:
                try:
                    time.sleep(self.cleanup_interval)
                    self.cleanup_expired()
                except Exception as e:
                    logger.error(f"Error en cleanup automático: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
    
    def cleanup_expired(self):
        """Limpia items expirados"""
        with self.lock:
            expired_keys = []
            
            for key, metadata in self.cache_metadata.items():
                if self._is_expired(metadata):
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_from_memory(key)
            
            if expired_keys:
                logger.debug(f"🧹 Cache cleanup: {len(expired_keys)} items expirados")
    
    def get_stats(self) -> Dict:
        """Estadísticas del cache"""
        with self.lock:
            hit_rate = (self.stats["hits"] / (self.stats["hits"] + self.stats["misses"])) if (self.stats["hits"] + self.stats["misses"]) > 0 else 0
            
            return {
                **self.stats,
                "hit_rate": hit_rate,
                "memory_items": len(self.memory_cache),
                "memory_usage_mb": self._get_cache_memory_usage(),
                "access_counts": dict(self.access_count)
            }

class AISystemLogger:
    """
    📝 Sistema de logging avanzado para componentes AI
    """
    
    def __init__(self, log_dir: str = "logs/ai_system"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Base de datos para eventos
        self.events_db = self.log_dir / "system_events.db"
        self._init_events_database()
        
        # Configurar loggers por componente
        self.loggers = {}
        self._setup_component_loggers()
        
        # Buffer de eventos en memoria
        self.event_buffer = deque(maxlen=1000)
        self.performance_buffer = deque(maxlen=5000)
        
        # Lock para thread safety
        self.lock = threading.Lock()
        
        logger.info(f"📝 AI System Logger inicializado: {log_dir}")
    
    def _init_events_database(self):
        """Inicializa base de datos de eventos"""
        with sqlite3.connect(self.events_db) as conn:
            cursor = conn.cursor()
            
            # Tabla de eventos del sistema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    event_type TEXT NOT NULL,
                    component TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    data TEXT,
                    exception TEXT,
                    stack_trace TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de métricas de rendimiento
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    component TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    memory_usage_mb REAL,
                    cpu_usage_pct REAL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Índices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON system_events(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_component ON system_events(component)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON performance_metrics(timestamp)")
            
            conn.commit()
    
    def _setup_component_loggers(self):
        """Configura loggers por componente"""
        components = [
            "news_engine", "sentiment_analyzer", "price_predictor", 
            "trading_integration", "dashboard", "system_monitor"
        ]
        
        for component in components:
            # Logger específico del componente
            component_logger = logging.getLogger(f"ai_system.{component}")
            component_logger.setLevel(logging.DEBUG)
            
            # Handler con rotación
            log_file = self.log_dir / f"{component}.log"
            handler = RotatingFileHandler(
                log_file, maxBytes=10*1024*1024, backupCount=5  # 10MB por archivo
            )
            
            # Formato detallado
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            
            component_logger.addHandler(handler)
            self.loggers[component] = component_logger
    
    def log_event(self, event: SystemEvent):
        """Registra evento del sistema"""
        with self.lock:
            # Agregar a buffer
            self.event_buffer.append(event)
            
            # Log al archivo correspondiente
            component_logger = self.loggers.get(event.component, logger)
            
            log_msg = f"{event.event_id} | {event.message}"
            if event.data:
                log_msg += f" | Data: {json.dumps(event.data, default=str)}"
            
            if event.event_type == "critical":
                component_logger.critical(log_msg)
            elif event.event_type == "error":
                component_logger.error(log_msg)
                if event.exception:
                    component_logger.error(f"Exception: {event.exception}")
                if event.stack_trace:
                    component_logger.error(f"Stack trace: {event.stack_trace}")
            elif event.event_type == "warning":
                component_logger.warning(log_msg)
            else:
                component_logger.info(log_msg)
            
            # Guardar en base de datos (asíncrono)
            self._save_event_to_db(event)
    
    def log_performance(self, metrics: PerformanceMetrics):
        """Registra métricas de rendimiento"""
        with self.lock:
            self.performance_buffer.append(metrics)
            
            # Log performance crítico
            if metrics.duration_ms > 10000:  # > 10 segundos
                self.log_event(SystemEvent(
                    timestamp=datetime.now(),
                    event_type="warning",
                    component=metrics.component,
                    event_id="SLOW_OPERATION",
                    message=f"Operation {metrics.operation} took {metrics.duration_ms:.0f}ms",
                    data=asdict(metrics)
                ))
            
            # Guardar en base de datos
            self._save_performance_to_db(metrics)
    
    def _save_event_to_db(self, event: SystemEvent):
        """Guarda evento en base de datos"""
        try:
            with sqlite3.connect(self.events_db) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO system_events 
                    (timestamp, event_type, component, event_id, message, data, exception, stack_trace)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.timestamp,
                    event.event_type,
                    event.component,
                    event.event_id,
                    event.message,
                    json.dumps(event.data, default=str) if event.data else None,
                    event.exception,
                    event.stack_trace
                ))
                
                conn.commit()
        
        except Exception as e:
            logger.error(f"Error guardando evento en DB: {e}")
    
    def _save_performance_to_db(self, metrics: PerformanceMetrics):
        """Guarda métricas en base de datos"""
        try:
            with sqlite3.connect(self.events_db) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO performance_metrics 
                    (timestamp, component, operation, duration_ms, memory_usage_mb, 
                     cpu_usage_pct, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.timestamp,
                    metrics.component,
                    metrics.operation,
                    metrics.duration_ms,
                    metrics.memory_usage_mb,
                    metrics.cpu_usage_pct,
                    metrics.success,
                    metrics.error_message
                ))
                
                conn.commit()
        
        except Exception as e:
            logger.error(f"Error guardando métricas en DB: {e}")
    
    def get_recent_events(self, component: str = None, 
                         event_type: str = None, 
                         limit: int = 100) -> List[SystemEvent]:
        """Obtiene eventos recientes"""
        try:
            with sqlite3.connect(self.events_db) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM system_events WHERE 1=1"
                params = []
                
                if component:
                    query += " AND component = ?"
                    params.append(component)
                
                if event_type:
                    query += " AND event_type = ?"
                    params.append(event_type)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                events = []
                for row in rows:
                    event = SystemEvent(
                        timestamp=datetime.fromisoformat(row[1]),
                        event_type=row[2],
                        component=row[3],
                        event_id=row[4],
                        message=row[5],
                        data=json.loads(row[6]) if row[6] else None,
                        exception=row[7],
                        stack_trace=row[8]
                    )
                    events.append(event)
                
                return events
        
        except Exception as e:
            logger.error(f"Error obteniendo eventos: {e}")
            return []
    
    def get_performance_stats(self, component: str = None,
                            hours_back: int = 24) -> Dict:
        """Obtiene estadísticas de rendimiento"""
        try:
            with sqlite3.connect(self.events_db) as conn:
                cursor = conn.cursor()
                
                cutoff_time = datetime.now() - timedelta(hours=hours_back)
                
                query = """
                    SELECT component, operation, 
                           AVG(duration_ms) as avg_duration,
                           MAX(duration_ms) as max_duration,
                           MIN(duration_ms) as min_duration,
                           COUNT(*) as total_operations,
                           SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_operations
                    FROM performance_metrics 
                    WHERE timestamp >= ?
                """
                params = [cutoff_time]
                
                if component:
                    query += " AND component = ?"
                    params.append(component)
                
                query += " GROUP BY component, operation"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                stats = {}
                for row in rows:
                    comp = row[0]
                    op = row[1]
                    
                    if comp not in stats:
                        stats[comp] = {}
                    
                    stats[comp][op] = {
                        "avg_duration_ms": row[2],
                        "max_duration_ms": row[3],
                        "min_duration_ms": row[4],
                        "total_operations": row[5],
                        "successful_operations": row[6],
                        "success_rate": row[6] / row[5] if row[5] > 0 else 0
                    }
                
                return stats
        
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}

class ErrorHandler:
    """
    🚨 Manejador de errores avanzado con recovery automático
    """
    
    def __init__(self, system_logger: AISystemLogger):
        self.system_logger = system_logger
        self.error_counts = defaultdict(int)
        self.circuit_breakers = {}
        self.recovery_strategies = {}
        
        # Configuración de circuit breakers
        self.circuit_breaker_config = {
            "error_threshold": 5,
            "time_window": 300,  # 5 minutos
            "recovery_timeout": 600  # 10 minutos
        }
        
        logger.info("🚨 Error Handler inicializado")
    
    def handle_error(self, component: str, operation: str, 
                    exception: Exception, recovery_func: Callable = None) -> bool:
        """
        Maneja error con logging y recovery automático
        Returns: True si se recuperó exitosamente, False si no
        """
        error_key = f"{component}:{operation}"
        
        # Incrementar contador
        self.error_counts[error_key] += 1
        
        # Crear evento de error
        event = SystemEvent(
            timestamp=datetime.now(),
            event_type="error",
            component=component,
            event_id=f"ERROR_{operation.upper()}",
            message=f"Error in {operation}: {str(exception)}",
            exception=str(exception),
            stack_trace=traceback.format_exc(),
            data={"error_count": self.error_counts[error_key]}
        )
        
        self.system_logger.log_event(event)
        
        # Verificar circuit breaker
        if self._should_trip_circuit_breaker(error_key):
            self._trip_circuit_breaker(error_key, component, operation)
            return False
        
        # Intentar recovery si se proporciona
        if recovery_func:
            try:
                logger.info(f"🔄 Intentando recovery para {component}:{operation}")
                recovery_result = recovery_func()
                
                if recovery_result:
                    # Recovery exitoso
                    self.error_counts[error_key] = 0  # Reset contador
                    
                    recovery_event = SystemEvent(
                        timestamp=datetime.now(),
                        event_type="info",
                        component=component,
                        event_id=f"RECOVERY_{operation.upper()}",
                        message=f"Successful recovery for {operation}",
                        data={"previous_errors": self.error_counts[error_key]}
                    )
                    self.system_logger.log_event(recovery_event)
                    
                    return True
            
            except Exception as recovery_error:
                # Recovery falló
                recovery_event = SystemEvent(
                    timestamp=datetime.now(),
                    event_type="error",
                    component=component,
                    event_id=f"RECOVERY_FAILED_{operation.upper()}",
                    message=f"Recovery failed for {operation}: {str(recovery_error)}",
                    exception=str(recovery_error),
                    stack_trace=traceback.format_exc()
                )
                self.system_logger.log_event(recovery_event)
        
        return False
    
    def _should_trip_circuit_breaker(self, error_key: str) -> bool:
        """Verifica si debe activar circuit breaker"""
        error_count = self.error_counts[error_key]
        threshold = self.circuit_breaker_config["error_threshold"]
        
        return error_count >= threshold
    
    def _trip_circuit_breaker(self, error_key: str, component: str, operation: str):
        """Activa circuit breaker"""
        circuit_breaker = {
            "tripped_at": datetime.now(),
            "error_count": self.error_counts[error_key],
            "component": component,
            "operation": operation
        }
        
        self.circuit_breakers[error_key] = circuit_breaker
        
        # Log critical event
        event = SystemEvent(
            timestamp=datetime.now(),
            event_type="critical",
            component=component,
            event_id=f"CIRCUIT_BREAKER_{operation.upper()}",
            message=f"Circuit breaker activated for {component}:{operation} after {self.error_counts[error_key]} errors",
            data=circuit_breaker
        )
        
        self.system_logger.log_event(event)
        
        logger.critical(f"🔴 Circuit breaker activado: {component}:{operation}")
    
    def is_circuit_open(self, component: str, operation: str) -> bool:
        """Verifica si circuit breaker está abierto"""
        error_key = f"{component}:{operation}"
        
        if error_key not in self.circuit_breakers:
            return False
        
        breaker = self.circuit_breakers[error_key]
        tripped_at = breaker["tripped_at"]
        recovery_timeout = self.circuit_breaker_config["recovery_timeout"]
        
        # Verificar si ha pasado el timeout de recovery
        if datetime.now() - tripped_at > timedelta(seconds=recovery_timeout):
            # Intentar recovery automático
            del self.circuit_breakers[error_key]
            self.error_counts[error_key] = 0
            
            logger.info(f"🟡 Circuit breaker reset automático: {component}:{operation}")
            return False
        
        return True
    
    def get_error_summary(self) -> Dict:
        """Resumen de errores y circuit breakers"""
        return {
            "error_counts": dict(self.error_counts),
            "active_circuit_breakers": len(self.circuit_breakers),
            "circuit_breakers": {
                key: {
                    **breaker,
                    "tripped_at": breaker["tripped_at"].isoformat()
                }
                for key, breaker in self.circuit_breakers.items()
            }
        }

class PerformanceMonitor:
    """
    📊 Monitor de rendimiento con métricas detalladas
    """
    
    def __init__(self, system_logger: AISystemLogger):
        self.system_logger = system_logger
        self.active_operations = {}
        self.lock = threading.Lock()
        
        logger.info("📊 Performance Monitor inicializado")
    
    def start_operation(self, component: str, operation: str) -> str:
        """Inicia monitoreo de una operación"""
        operation_id = f"{component}_{operation}_{time.time()}"
        
        with self.lock:
            self.active_operations[operation_id] = {
                "component": component,
                "operation": operation,
                "start_time": time.time(),
                "start_memory": self._get_memory_usage(),
                "start_cpu": psutil.cpu_percent()
            }
        
        return operation_id
    
    def end_operation(self, operation_id: str, success: bool = True, 
                     error_message: str = None):
        """Finaliza monitoreo y registra métricas"""
        with self.lock:
            if operation_id not in self.active_operations:
                return
            
            op_data = self.active_operations[operation_id]
            
            # Calcular métricas
            end_time = time.time()
            duration_ms = (end_time - op_data["start_time"]) * 1000
            
            memory_usage = self._get_memory_usage()
            cpu_usage = psutil.cpu_percent()
            
            # Crear métricas
            metrics = PerformanceMetrics(
                component=op_data["component"],
                operation=op_data["operation"],
                duration_ms=duration_ms,
                memory_usage_mb=memory_usage,
                cpu_usage_pct=cpu_usage,
                timestamp=datetime.now(),
                success=success,
                error_message=error_message
            )
            
            # Registrar métricas
            self.system_logger.log_performance(metrics)
            
            # Limpiar operación activa
            del self.active_operations[operation_id]
    
    def _get_memory_usage(self) -> float:
        """Obtiene uso de memoria actual en MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except:
            return 0.0
    
    def operation_context(self, component: str, operation: str):
        """Context manager para monitoreo automático"""
        class OperationContext:
            def __init__(self, monitor, comp, op):
                self.monitor = monitor
                self.component = comp
                self.operation = op
                self.operation_id = None
            
            def __enter__(self):
                self.operation_id = self.monitor.start_operation(self.component, self.operation)
                return self.operation_id
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                success = exc_type is None
                error_msg = str(exc_val) if exc_val else None
                self.monitor.end_operation(self.operation_id, success, error_msg)
        
        return OperationContext(self, component, operation)

# Instancias globales del sistema de monitoreo
ai_cache = AdvancedCache()
ai_logger = AISystemLogger()
error_handler = ErrorHandler(ai_logger)
performance_monitor = PerformanceMonitor(ai_logger)

# Decorador para logging automático
def monitored_operation(component: str, operation: str = None):
    """Decorador para monitoreo automático de operaciones"""
    def decorator(func):
        op_name = operation or func.__name__
        
        def wrapper(*args, **kwargs):
            with performance_monitor.operation_context(component, op_name):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_handler.handle_error(component, op_name, e)
                    raise
        
        return wrapper
    return decorator

# Funciones de conveniencia
def log_ai_event(component: str, event_type: str, message: str, 
                 data: Dict = None, event_id: str = None):
    """Función de conveniencia para logging"""
    event = SystemEvent(
        timestamp=datetime.now(),
        event_type=event_type,
        component=component,
        event_id=event_id or f"{event_type.upper()}_{int(time.time())}",
        message=message,
        data=data
    )
    ai_logger.log_event(event)

def get_system_health() -> Dict:
    """Estado de salud del sistema AI"""
    return {
        "cache_stats": ai_cache.get_stats(),
        "error_summary": error_handler.get_error_summary(),
        "performance_stats": ai_logger.get_performance_stats(),
        "recent_events": [
            asdict(event) for event in ai_logger.get_recent_events(limit=10)
        ]
    }

if __name__ == "__main__":
    # Test del sistema de monitoreo
    import asyncio
    
    async def test_monitoring_system():
        logger.info("🧪 Testing AI System Monitor...")
        
        # Test de cache
        ai_cache.set("test_key", {"data": "test_value"}, ttl=60)
        cached_value = ai_cache.get("test_key")
        print(f"Cache test: {cached_value}")
        
        # Test de logging
        log_ai_event("test_component", "info", "Test message", {"key": "value"})
        
        # Test de performance monitoring
        with performance_monitor.operation_context("test", "operation"):
            await asyncio.sleep(0.1)  # Simular trabajo
        
        # Test de error handling
        try:
            raise ValueError("Test error")
        except Exception as e:
            error_handler.handle_error("test", "error_test", e)
        
        # Obtener estado del sistema
        health = get_system_health()
        print(f"System health: {json.dumps(health, indent=2, default=str)}")
    
    asyncio.run(test_monitoring_system())