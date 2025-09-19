#!/usr/bin/env python3
"""
⏰ AGUS JOB SCHEDULER SYSTEM
Advanced job scheduling with persistence and monitoring integration.
"""

import asyncio
import json
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import threading
import heapq

from .agus_core import AGUSOrchestrator, EventType, Event, get_orchestrator
from .util import logger


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(Enum):
    SYSTEM_MAINTENANCE = "system_maintenance"
    RISK_ASSESSMENT = "risk_assessment"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    DATA_CLEANUP = "data_cleanup"
    HEALTH_CHECK = "health_check"
    CUSTOM = "custom"


@dataclass
class ScheduledJob:
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    job_type: JobType = JobType.CUSTOM
    callback: Optional[Callable] = None
    schedule_time: datetime = field(default_factory=datetime.now)
    interval_seconds: Optional[int] = None  # For recurring jobs
    max_retries: int = 3
    retry_count: int = 0
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


class JobScheduler:
    """
    Advanced job scheduler with persistence and monitoring integration
    """
    
    def __init__(self, orchestrator: AGUSOrchestrator = None):
        self.orchestrator = orchestrator or get_orchestrator()
        self.jobs: Dict[str, ScheduledJob] = {}
        self.job_queue = []  # Priority queue
        self._running = False
        self._scheduler_thread = None
        self._lock = threading.RLock()
        self.persistence_file = "bot/scheduled_jobs.json"
        
        # Load persisted jobs
        self._load_jobs()
        
    def schedule_job(self, 
                    name: str,
                    callback: Callable,
                    schedule_time: datetime = None,
                    interval_seconds: int = None,
                    job_type: JobType = JobType.CUSTOM,
                    max_retries: int = 3,
                    context: Dict[str, Any] = None) -> str:
        """Schedule a new job"""
        
        if schedule_time is None:
            schedule_time = datetime.now()
            
        job = ScheduledJob(
            name=name,
            job_type=job_type,
            callback=callback,
            schedule_time=schedule_time,
            interval_seconds=interval_seconds,
            max_retries=max_retries,
            context=context or {},
            next_run=schedule_time
        )
        
        with self._lock:
            self.jobs[job.job_id] = job
            heapq.heappush(self.job_queue, (schedule_time.timestamp(), job.job_id))
        
        self._persist_jobs()
        
        # Emit event
        self.orchestrator.event_bus.publish(Event(
            event_type=EventType.JOB_EXECUTED,
            source="JobScheduler",
            data={
                "action": "job_scheduled",
                "job_id": job.job_id,
                "name": job.name,
                "type": job.job_type.value,
                "schedule_time": schedule_time.isoformat()
            }
        ))
        
        logger.info(f"⏰ Job scheduled: {name} ({job.job_id}) at {schedule_time}")
        return job.job_id
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a scheduled job"""
        with self._lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                if job.status in [JobStatus.PENDING, JobStatus.RUNNING]:
                    job.status = JobStatus.CANCELLED
                    job.updated_at = datetime.now()
                    self._persist_jobs()
                    
                    # Emit event
                    self.orchestrator.event_bus.publish(Event(
                        event_type=EventType.JOB_EXECUTED,
                        source="JobScheduler",
                        data={
                            "action": "job_cancelled",
                            "job_id": job_id,
                            "name": job.name
                        }
                    ))
                    
                    logger.info(f"❌ Job cancelled: {job.name} ({job_id})")
                    return True
        return False
    
    def get_job_status(self, job_id: str) -> Optional[ScheduledJob]:
        """Get job status"""
        return self.jobs.get(job_id)
    
    def list_jobs(self, status_filter: JobStatus = None) -> List[ScheduledJob]:
        """List all jobs, optionally filtered by status"""
        jobs = list(self.jobs.values())
        if status_filter:
            jobs = [job for job in jobs if job.status == status_filter]
        return sorted(jobs, key=lambda x: x.created_at, reverse=True)
    
    def start_scheduler(self):
        """Start the job scheduler"""
        if self._running:
            return
            
        self._running = True
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="AGUSJobScheduler",
            daemon=True
        )
        self._scheduler_thread.start()
        logger.info("⏰ Job scheduler started")
    
    def stop_scheduler(self):
        """Stop the job scheduler"""
        self._running = False
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5.0)
        logger.info("⏰ Job scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self._running:
            try:
                current_time = datetime.now()
                jobs_to_run = []
                
                with self._lock:
                    # Check for jobs ready to run
                    while self.job_queue:
                        schedule_time, job_id = self.job_queue[0]
                        
                        if schedule_time <= current_time.timestamp():
                            heapq.heappop(self.job_queue)
                            if job_id in self.jobs:
                                job = self.jobs[job_id]
                                if job.status == JobStatus.PENDING:
                                    jobs_to_run.append(job)
                        else:
                            break
                
                # Execute jobs outside of lock
                for job in jobs_to_run:
                    asyncio.create_task(self._execute_job(job))
                
                # Sleep briefly
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"❌ Scheduler loop error: {e}")
                time.sleep(5.0)
    
    async def _execute_job(self, job: ScheduledJob):
        """Execute a single job"""
        try:
            job.status = JobStatus.RUNNING
            job.last_run = datetime.now()
            job.updated_at = datetime.now()
            
            # Log action to StateStore
            self.orchestrator.state_store.log_action(
                action_type="job_execution_start",
                source="JobScheduler",
                description=f"Starting job: {job.name} ({job.job_id})"
            )
            
            # Execute the callback
            if asyncio.iscoroutinefunction(job.callback):
                result = await job.callback(job.context)
            else:
                result = job.callback(job.context)
            
            job.result = result
            job.status = JobStatus.COMPLETED
            
            # Schedule next run if recurring
            if job.interval_seconds:
                job.next_run = datetime.now() + timedelta(seconds=job.interval_seconds)
                job.status = JobStatus.PENDING
                with self._lock:
                    heapq.heappush(self.job_queue, (job.next_run.timestamp(), job.job_id))
            
            # Emit success event
            self.orchestrator.event_bus.publish(Event(
                event_type=EventType.JOB_EXECUTED,
                source="JobScheduler",
                data={
                    "action": "job_completed",
                    "job_id": job.job_id,
                    "name": job.name,
                    "success": True,
                    "result": str(result)[:500]  # Truncate large results
                }
            ))
            
            # Log success
            self.orchestrator.state_store.log_action(
                action_type="job_execution_complete",
                source="JobScheduler",
                description=f"Job completed successfully: {job.name}",
                success=True
            )
            
            logger.info(f"✅ Job completed: {job.name} ({job.job_id})")
            
        except Exception as e:
            job.error = str(e)
            job.retry_count += 1
            job.updated_at = datetime.now()
            
            if job.retry_count < job.max_retries:
                # Retry after delay
                retry_delay = min(300, 60 * job.retry_count)  # Max 5 minutes
                job.next_run = datetime.now() + timedelta(seconds=retry_delay)
                job.status = JobStatus.PENDING
                
                with self._lock:
                    heapq.heappush(self.job_queue, (job.next_run.timestamp(), job.job_id))
                
                logger.warning(f"⚠️ Job failed, retrying: {job.name} ({job.retry_count}/{job.max_retries})")
            else:
                job.status = JobStatus.FAILED
                logger.error(f"❌ Job failed permanently: {job.name} - {e}")
            
            # Emit failure event
            self.orchestrator.event_bus.publish(Event(
                event_type=EventType.SYSTEM_ERROR,
                source="JobScheduler",
                data={
                    "action": "job_failed",
                    "job_id": job.job_id,
                    "name": job.name,
                    "error": str(e),
                    "retry_count": job.retry_count
                }
            ))
            
            # Log failure
            self.orchestrator.state_store.log_action(
                action_type="job_execution_failed",
                source="JobScheduler",
                description=f"Job failed: {job.name} - {str(e)}",
                success=False
            )
        
        finally:
            self._persist_jobs()
    
    def _load_jobs(self):
        """Load jobs from persistence file"""
        try:
            persistence_path = Path(self.persistence_file)
            if persistence_path.exists():
                with open(persistence_path, 'r') as f:
                    jobs_data = json.load(f)
                    
                for job_data in jobs_data:
                    # Reconstruct job (without callback - that's runtime only)
                    job = ScheduledJob(
                        job_id=job_data['job_id'],
                        name=job_data['name'],
                        job_type=JobType(job_data['job_type']),
                        schedule_time=datetime.fromisoformat(job_data['schedule_time']),
                        interval_seconds=job_data.get('interval_seconds'),
                        max_retries=job_data.get('max_retries', 3),
                        retry_count=job_data.get('retry_count', 0),
                        status=JobStatus(job_data['status']),
                        created_at=datetime.fromisoformat(job_data['created_at']),
                        updated_at=datetime.fromisoformat(job_data['updated_at']),
                        last_run=datetime.fromisoformat(job_data['last_run']) if job_data.get('last_run') else None,
                        next_run=datetime.fromisoformat(job_data['next_run']) if job_data.get('next_run') else None,
                        result=job_data.get('result'),
                        error=job_data.get('error'),
                        context=job_data.get('context', {})
                    )
                    
                    self.jobs[job.job_id] = job
                    
                    # Re-queue pending jobs
                    if job.status == JobStatus.PENDING and job.next_run:
                        heapq.heappush(self.job_queue, (job.next_run.timestamp(), job.job_id))
                        
        except Exception as e:
            logger.error(f"❌ Error loading jobs: {e}")
    
    def _persist_jobs(self):
        """Persist jobs to file"""
        try:
            jobs_data = []
            for job in self.jobs.values():
                job_data = {
                    'job_id': job.job_id,
                    'name': job.name,
                    'job_type': job.job_type.value,
                    'schedule_time': job.schedule_time.isoformat(),
                    'interval_seconds': job.interval_seconds,
                    'max_retries': job.max_retries,
                    'retry_count': job.retry_count,
                    'status': job.status.value,
                    'created_at': job.created_at.isoformat(),
                    'updated_at': job.updated_at.isoformat(),
                    'last_run': job.last_run.isoformat() if job.last_run else None,
                    'next_run': job.next_run.isoformat() if job.next_run else None,
                    'result': job.result,
                    'error': job.error,
                    'context': job.context
                }
                jobs_data.append(job_data)
            
            persistence_path = Path(self.persistence_file)
            persistence_path.parent.mkdir(exist_ok=True)
            
            with open(persistence_path, 'w') as f:
                json.dump(jobs_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Error persisting jobs: {e}")
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        total_jobs = len(self.jobs)
        status_counts = {}
        
        for status in JobStatus:
            status_counts[status.value] = len([j for j in self.jobs.values() if j.status == status])
        
        return {
            "total_jobs": total_jobs,
            "status_counts": status_counts,
            "queue_size": len(self.job_queue),
            "running": self._running
        }


# Global scheduler instance
_scheduler_instance = None

def get_job_scheduler() -> JobScheduler:
    """Get or create the global job scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = JobScheduler()
    return _scheduler_instance