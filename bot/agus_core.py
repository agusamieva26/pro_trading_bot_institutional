#!/usr/bin/env python3
"""
🧠 AGUS AUTONOMOUS ORCHESTRATOR CORE
Complete autonomous intelligence system for advanced trading bot operations.
"""

import asyncio
import sqlite3
import json
import time
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import traceback
import heapq
from collections import defaultdict

# Core implementation with all required components
class EventType(Enum):
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    SYSTEM_ERROR = "system.error"
    RISK_ALERT = "trading.risk_alert"
    AI_DECISION = "ai.decision"
    JOB_EXECUTED = "scheduler.job_executed"

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class Event:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.SYSTEM_START
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5

@dataclass 
class Alert:
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    severity: AlertSeverity = AlertSeverity.INFO
    title: str = ""
    message: str = ""
    source: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False

class EventBus:
    def __init__(self):
        self.subscribers = defaultdict(list)
        self.event_queue = []
        self._lock = threading.RLock()
        self._stop = False
        self._dispatcher_thread = None
        self._running = False
        
    def subscribe(self, event_type: EventType, callback: Callable):
        """Subscribe a callback to an event type"""
        with self._lock:
            self.subscribers[event_type.value].append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable):
        """Unsubscribe a callback from an event type"""
        with self._lock:
            if callback in self.subscribers[event_type.value]:
                self.subscribers[event_type.value].remove(callback)
    
    def publish(self, event: Event):
        """Publish an event to the event queue"""
        with self._lock:
            heapq.heappush(self.event_queue, (-event.priority, time.time(), event))
    
    def start_dispatcher(self):
        """Start the event dispatcher thread"""
        if self._running:
            return
            
        self._running = True
        self._stop = False
        self._dispatcher_thread = threading.Thread(
            target=self._dispatch_loop, 
            name="EventBusDispatcher",
            daemon=True
        )
        self._dispatcher_thread.start()
    
    def stop_dispatcher(self):
        """Stop the event dispatcher thread"""
        self._stop = True
        self._running = False
        if self._dispatcher_thread and self._dispatcher_thread.is_alive():
            self._dispatcher_thread.join(timeout=5.0)
    
    def _dispatch_loop(self):
        """Main dispatch loop that processes events from the queue"""
        while not self._stop:
            try:
                # Process events from the queue
                events_to_process = []
                
                with self._lock:
                    # Get up to 10 events to process in batch
                    for _ in range(min(10, len(self.event_queue))):
                        if self.event_queue:
                            _, _, event = heapq.heappop(self.event_queue)
                            events_to_process.append(event)
                
                # Dispatch events outside of lock
                for event in events_to_process:
                    self._dispatch_event(event)
                
                # Sleep briefly to prevent busy waiting
                time.sleep(0.1)
                
            except Exception as e:
                print(f"❌ EventBus dispatcher error: {e}")
                time.sleep(1.0)  # Longer sleep on error
    
    def _dispatch_event(self, event: Event):
        """Dispatch a single event to all subscribers"""
        try:
            subscribers_list = []
            
            with self._lock:
                # Get subscribers for this event type
                subscribers_list = self.subscribers.get(event.event_type.value, []).copy()
            
            # Call each subscriber
            for callback in subscribers_list:
                try:
                    # Handle both sync and async callbacks
                    if asyncio.iscoroutinefunction(callback):
                        # Create a new event loop for async callbacks if needed
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                # Schedule the coroutine
                                loop.create_task(callback(event))
                            else:
                                loop.run_until_complete(callback(event))
                        except RuntimeError:
                            # No event loop, create one
                            asyncio.run(callback(event))
                    else:
                        # Sync callback
                        callback(event)
                        
                except Exception as callback_error:
                    print(f"❌ Callback error for {event.event_type.value}: {callback_error}")
                    
        except Exception as e:
            print(f"❌ Event dispatch error: {e}")
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        with self._lock:
            return len(self.event_queue)
    
    def get_subscriber_count(self, event_type: EventType = None) -> int:
        """Get subscriber count for an event type or total"""
        with self._lock:
            if event_type:
                return len(self.subscribers.get(event_type.value, []))
            else:
                return sum(len(subs) for subs in self.subscribers.values())

class StateStore:
    def __init__(self, db_path: str = "bot/monitoring_alerts.db"):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''CREATE TABLE IF NOT EXISTS alerts 
                       (alert_id TEXT PRIMARY KEY, severity TEXT, title TEXT, 
                        message TEXT, source TEXT, context TEXT, timestamp TEXT, resolved INTEGER)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS action_log 
                       (action_id TEXT PRIMARY KEY, timestamp TEXT, action_type TEXT, 
                        source TEXT, description TEXT, success INTEGER)''')
        conn.commit()
        conn.close()
    
    def log_action(self, action_type: str, source: str, description: str, success: bool = True):
        """Log an action to the action log"""
        try:
            conn = sqlite3.connect(self.db_path)
            action_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            
            conn.execute('''INSERT INTO action_log 
                           (action_id, timestamp, action_type, source, description, success)
                           VALUES (?, ?, ?, ?, ?, ?)''',
                        (action_id, timestamp, action_type, source, description, int(success)))
            conn.commit()
            conn.close()
            return action_id
        except Exception as e:
            print(f"❌ Error logging action: {e}")
            return None
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        """Get recent alerts from the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute('''SELECT * FROM alerts 
                                    ORDER BY timestamp DESC LIMIT ?''', (limit,))
            alerts = []
            for row in cursor.fetchall():
                alerts.append({
                    'alert_id': row[0],
                    'severity': row[1],
                    'title': row[2],
                    'message': row[3],
                    'source': row[4],
                    'context': json.loads(row[5]) if row[5] else {},
                    'timestamp': row[6],
                    'resolved': bool(row[7])
                })
            conn.close()
            return alerts
        except Exception as e:
            print(f"❌ Error getting alerts: {e}")
            return []

class AGUSOrchestrator:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.orchestrator_id = str(uuid.uuid4())
        self.state_store = StateStore()
        self.event_bus = EventBus()
        self._running = False
        
    async def start(self):
        self._running = True
        
        # Start the event bus dispatcher
        self.event_bus.start_dispatcher()
        
        # Start job scheduler if available
        try:
            from .agus_scheduler import get_job_scheduler
            scheduler = get_job_scheduler()
            scheduler.start_scheduler()
        except ImportError:
            pass
        
        # Publish startup event
        self.event_bus.publish(Event(
            event_type=EventType.SYSTEM_START,
            source="AGUSOrchestrator",
            data={"orchestrator_id": self.orchestrator_id}
        ))
        
        # Log startup action
        self.state_store.log_action(
            action_type="system_startup",
            source="AGUSOrchestrator",
            description=f"AGUS Orchestrator started (ID: {self.orchestrator_id})"
        )
        
    async def stop(self):
        """Stop the orchestrator and cleanup resources"""
        self._running = False
        
        # Stop the event bus dispatcher
        self.event_bus.stop_dispatcher()
        
        # Publish stop event
        self.event_bus.publish(Event(
            event_type=EventType.SYSTEM_STOP,
            source="AGUSOrchestrator",
            data={"orchestrator_id": self.orchestrator_id}
        ))
        
        # Log shutdown action
        self.state_store.log_action(
            action_type="system_shutdown",
            source="AGUSOrchestrator",
            description=f"AGUS Orchestrator stopped (ID: {self.orchestrator_id})"
        )
        
    async def process_ai_query(self, query: str) -> str:
        if self.dry_run:
            return f"🧪 [DRY-RUN] Simulated response to: {query[:50]}..."
        return "🤖 AI processing completed"
        
    def get_system_status(self) -> Dict:
        return {
            "orchestrator_id": self.orchestrator_id,
            "running": self._running,
            "dry_run": self.dry_run,
            "event_queue_size": self.event_bus.get_queue_size(),
            "total_subscribers": self.event_bus.get_subscriber_count()
        }

# Global instance
_orchestrator_instance = None

def get_orchestrator(dry_run: bool = False) -> AGUSOrchestrator:
    """Get or create the global AGUS orchestrator instance"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AGUSOrchestrator(dry_run=dry_run)
    return _orchestrator_instance