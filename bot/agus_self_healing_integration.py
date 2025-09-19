#!/usr/bin/env python3
"""
🔗 AGUS SELF-HEALING INTEGRATION LAYER
Integration bridge between self-healing system and existing AGUS components.
"""

import asyncio
import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

try:
    from .util import logger
    from .agus_core import AGUSOrchestrator, EventType, Event, Alert, AlertSeverity
    from .agus_self_healing import (
        SelfHealingOrchestrator, 
        LSPError, 
        ErrorSeverity,
        initialize_self_healing,
        get_self_healing
    )
    from .agus_2_hybrid_system import AGUS2HybridSystem
    # Import the actual LSP diagnostics tool
    try:
        from tools.lsp_diagnostic_tool import get_latest_lsp_diagnostics
        LSP_TOOL_AVAILABLE = True
    except ImportError:
        # Fallback for when tools aren't available
        get_latest_lsp_diagnostics = None
        LSP_TOOL_AVAILABLE = False
    AGUS_AVAILABLE = True
except ImportError as e:
    # Fallback logging and classes
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)
    logger.warning(f"AGUS components not fully available: {e}")
    # Fallback classes
    AGUSOrchestrator = None
    EventType = None
    Event = None
    Alert = None
    AlertSeverity = None
    SelfHealingOrchestrator = None
    LSPError = None
    ErrorSeverity = None
    initialize_self_healing = None
    get_self_healing = None
    AGUS2HybridSystem = None
    AGUS_AVAILABLE = False


class AGUSLSPIntegration:
    """🔍 LSP integration for real error detection"""
    
    def __init__(self, self_healing: SelfHealingOrchestrator):
        self.self_healing = self_healing
        self.last_check = datetime.now()
        
    async def get_lsp_diagnostics(self) -> Optional[List[LSPError]]:
        """Get LSP diagnostics using the actual tool"""
        try:
            # Check if LSP tool is available
            if not LSP_TOOL_AVAILABLE or get_latest_lsp_diagnostics is None:
                logger.debug("LSP diagnostics tool not available, falling back to log detection")
                return await self._detect_errors_from_logs()
            
            # Get diagnostics using the real tool
            result = get_latest_lsp_diagnostics()
            
            if not result:
                return []
            
            # Parse LSP JSON format into LSPError objects
            errors = []
            
            # Handle different result formats
            if isinstance(result, str):
                # Try to parse as JSON first
                try:
                    diagnostics_data = json.loads(result)
                except json.JSONDecodeError:
                    # Parse text format
                    diagnostics_data = self._parse_text_diagnostics(result)
            else:
                diagnostics_data = result
            
            # Convert to LSPError objects
            if isinstance(diagnostics_data, dict):
                # LSP format: {"file_path": [{"line": 1, "column": 1, "message": "...", "severity": "error"}, ...]}
                for file_path, file_errors in diagnostics_data.items():
                    for error_data in file_errors:
                        error = self._convert_to_lsp_error(file_path, error_data)
                        if error:
                            errors.append(error)
            elif isinstance(diagnostics_data, list):
                # List of error objects
                for error_data in diagnostics_data:
                    file_path = error_data.get('file', error_data.get('file_path', 'unknown'))
                    error = self._convert_to_lsp_error(file_path, error_data)
                    if error:
                        errors.append(error)
            
            return errors
            
        except ImportError:
            # Fallback: simulate with workflow logs that contain errors
            return await self._detect_errors_from_logs()
        except Exception as e:
            logger.error(f"❌ Error getting LSP diagnostics: {e}")
            return []
    
    def _parse_text_diagnostics(self, text: str) -> List[Dict]:
        """Parse text-based LSP diagnostics"""
        errors = []
        lines = text.split('\n')
        
        for line in lines:
            if ':' in line and any(keyword in line.lower() for keyword in ['error', 'warning']):
                try:
                    parts = line.split(':')
                    if len(parts) >= 4:
                        file_path = parts[0].strip()
                        line_num = int(parts[1].strip()) if parts[1].strip().isdigit() else 1
                        col_num = int(parts[2].strip()) if parts[2].strip().isdigit() else 1
                        message = ':'.join(parts[3:]).strip()
                        
                        severity = 'error' if 'error' in message.lower() else 'warning'
                        
                        errors.append({
                            'line': line_num,
                            'column': col_num,
                            'message': message,
                            'severity': severity
                        })
                except (ValueError, IndexError):
                    continue
        
        return errors
    
    def _convert_to_lsp_error(self, file_path: str, error_data: Dict) -> Optional[LSPError]:
        """Convert LSP error data to LSPError object"""
        try:
            message = error_data.get('message', '')
            severity_str = error_data.get('severity', 'error').lower()
            
            # Map LSP severity to our severity
            severity_map = {
                'error': ErrorSeverity.ERROR,
                'warning': ErrorSeverity.WARNING,
                'information': ErrorSeverity.INFO,
                'hint': ErrorSeverity.INFO
            }
            
            severity = severity_map.get(severity_str, ErrorSeverity.ERROR)
            
            # Extract error type
            error_type = self._extract_error_type(message)
            
            return LSPError(
                file_path=file_path,
                line=error_data.get('line', 1),
                column=error_data.get('column', 1),
                message=message,
                severity=severity,
                error_type=error_type,
                error_code=error_data.get('code', ''),
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"❌ Error converting LSP error: {e}")
            return None
    
    def _extract_error_type(self, message: str) -> str:
        """Extract error type from message"""
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in ['import', 'module not found', 'cannot import']):
            return 'import'
        elif any(keyword in message_lower for keyword in ['syntax', 'invalid syntax', 'indentation']):
            return 'syntax'
        elif any(keyword in message_lower for keyword in ['name', 'not defined', 'unbound']):
            return 'name'
        elif any(keyword in message_lower for keyword in ['type', 'expected', 'argument']):
            return 'type'
        elif any(keyword in message_lower for keyword in ['attribute', 'has no attribute']):
            return 'attribute'
        elif any(keyword in message_lower for keyword in ['value', 'invalid literal']):
            return 'value'
        elif any(keyword in message_lower for keyword in ['key', 'index']):
            return 'key'
        else:
            return 'unknown'
    
    async def _detect_errors_from_logs(self) -> List[LSPError]:
        """Fallback: detect errors from workflow logs"""
        errors = []
        
        try:
            # Look for recent error patterns in log files
            log_dir = Path("logs")
            if log_dir.exists():
                for log_file in log_dir.glob("*.log"):
                    recent_errors = self._scan_log_for_errors(log_file)
                    errors.extend(recent_errors)
        except Exception as e:
            logger.debug(f"Error scanning logs for errors: {e}")
        
        return errors
    
    def _scan_log_for_errors(self, log_file: Path) -> List[LSPError]:
        """Scan log file for Python errors"""
        errors = []
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            # Look for Python traceback patterns
            for i, line in enumerate(lines):
                if 'Traceback' in line or 'Error:' in line:
                    # Try to extract error information
                    error_info = self._extract_error_from_traceback(lines[i:i+10])
                    if error_info:
                        errors.append(error_info)
                        
        except Exception as e:
            logger.debug(f"Error scanning log file {log_file}: {e}")
        
        return errors
    
    def _extract_error_from_traceback(self, traceback_lines: List[str]) -> Optional[LSPError]:
        """Extract error information from traceback"""
        try:
            # Find the actual error line
            error_line = None
            file_path = "unknown"
            line_num = 0
            
            for line in traceback_lines:
                if 'File "' in line and 'line' in line:
                    # Extract file and line number
                    parts = line.strip().split('"')
                    if len(parts) >= 2:
                        file_path = parts[1]
                    
                    line_parts = line.split('line')
                    if len(line_parts) > 1:
                        try:
                            line_num = int(line_parts[1].strip().split(',')[0])
                        except (ValueError, IndexError):
                            line_num = 0
                            
                elif any(error_type in line for error_type in ['Error:', 'Exception:', 'Warning:']):
                    error_line = line.strip()
                    break
            
            if error_line:
                return LSPError(
                    file_path=file_path,
                    line=line_num,
                    column=0,
                    message=error_line,
                    severity=ErrorSeverity.ERROR,
                    error_type=self._extract_error_type(error_line),
                    timestamp=datetime.now()
                )
        except Exception as e:
            logger.debug(f"Error extracting from traceback: {e}")
        
        return None


class AGUSSelfHealingBridge:
    """🌉 Bridge between AGUS systems and self-healing"""
    
    def __init__(self, agus_orchestrator: Optional[AGUSOrchestrator] = None):
        self.agus_orchestrator = agus_orchestrator
        self.agus_2_system: Optional[AGUS2HybridSystem] = None
        self.self_healing: Optional[SelfHealingOrchestrator] = None
        self.lsp_integration: Optional[AGUSLSPIntegration] = None
        self.event_subscriptions = []
        self.is_integrated = False
        
    async def initialize_integration(self):
        """Initialize the full integration"""
        try:
            logger.info("🔗 Initializing AGUS Self-Healing Integration...")
            
            # Initialize self-healing system
            if not self.self_healing:
                self.self_healing = await initialize_self_healing(self.agus_orchestrator)
            
            # Initialize LSP integration
            self.lsp_integration = AGUSLSPIntegration(self.self_healing)
            
            # Initialize AGUS 2.0 if available
            if AGUS_AVAILABLE:
                try:
                    self.agus_2_system = AGUS2HybridSystem()
                    logger.info("✅ AGUS 2.0 system connected")
                except Exception as e:
                    logger.warning(f"AGUS 2.0 initialization failed: {e}")
            
            # Set up event subscriptions
            await self._setup_event_subscriptions()
            
            # Replace LSP error detection with real implementation
            if self.self_healing and self.lsp_integration:
                # Replace the detector's check method with our enhanced version
                original_check = self.self_healing.error_detector._check_lsp_errors
                self.self_healing.error_detector._check_lsp_errors = self._enhanced_lsp_check
            
            self.is_integrated = True
            logger.info("✅ AGUS Self-Healing Integration completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize AGUS Self-Healing Integration: {e}")
            raise
    
    async def _setup_event_subscriptions(self):
        """Set up event subscriptions for integration"""
        if not self.agus_orchestrator:
            return
        
        # Subscribe to system errors
        self.agus_orchestrator.event_bus.subscribe(
            EventType.SYSTEM_ERROR,
            self._handle_system_error
        )
        
        # Subscribe to system start events
        self.agus_orchestrator.event_bus.subscribe(
            EventType.SYSTEM_START,
            self._handle_system_event
        )
        
        self.event_subscriptions.extend([
            (EventType.SYSTEM_ERROR, self._handle_system_error),
            (EventType.SYSTEM_START, self._handle_system_event)
        ])
    
    async def _handle_system_error(self, event: Event):
        """Handle system error events"""
        try:
            if not self.self_healing or not self.self_healing.enabled:
                return
            
            logger.info(f"🔗 Self-healing bridge received system error: {event.data.get('title', 'Unknown')}")
            
            # Trigger health check
            if self.self_healing:
                await self.self_healing.manual_health_check()
            
            # Analyze error with AGUS 2.0 if available
            if self.agus_2_system and event.data.get('message'):
                try:
                    query = f"Analyze this system error and suggest fixes: {event.data['message']}"
                    response = await self.agus_2_system.process_query(
                        query=query,
                        query_type="technical",
                        priority=2
                    )
                    logger.info(f"🧠 AGUS 2.0 Error Analysis: {response.content[:200]}...")
                except Exception as e:
                    logger.debug(f"AGUS 2.0 error analysis failed: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error in system error handler: {e}")
    
    async def _enhanced_lsp_check(self):
        """Enhanced LSP check using real diagnostics"""
        try:
            # Get real LSP errors from our integration
            errors = await self.lsp_integration.get_lsp_diagnostics()
            
            if not errors:
                return
            
            # Apply filtering using the detector's filtering logic
            detector = self.self_healing.error_detector
            
            # Process each error
            for error in errors:
                if not detector._should_filter_error(error.message, error.file_path):
                    await detector._process_error(error)
                else:
                    logger.debug(f"🔍 Filtered error in {error.file_path}: {error.message[:100]}")
                    
        except Exception as e:
            logger.error(f"❌ Error in enhanced LSP check: {e}")
    
    async def _handle_system_event(self, event: Event):
        """Handle general system events"""
        try:
            logger.debug(f"🔗 Self-healing bridge received event: {event.event_type.value}")
        except Exception as e:
            logger.error(f"❌ Error in system event handler: {e}")
    
    async def emergency_repair(self, error_description: str) -> Dict[str, Any]:
        """Emergency repair triggered by critical trading bot errors"""
        try:
            logger.warning(f"🚨 Emergency repair triggered: {error_description}")
            
            if not self.self_healing:
                return {"status": "error", "message": "Self-healing not initialized"}
            
            # Enable emergency mode
            original_mode = self.self_healing.read_only_mode
            self.self_healing.set_read_only_mode(False)
            self.self_healing.enable()
            
            try:
                # Force immediate health check
                health_status = await self.self_healing.manual_health_check()
                
                # Analyze with AI if available
                ai_analysis = None
                if self.agus_2_system:
                    try:
                        query = f"EMERGENCY: Trading bot critical error requiring immediate fix: {error_description}"
                        response = await self.agus_2_system.process_query(
                            query=query,
                            query_type="emergency",
                            priority=1
                        )
                        ai_analysis = response.content
                    except Exception as e:
                        logger.error(f"AI analysis failed: {e}")
                
                result = {
                    "status": "completed",
                    "health_check": health_status,
                    "ai_analysis": ai_analysis,
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"✅ Emergency repair completed")
                return result
                
            finally:
                # Restore original mode
                self.self_healing.set_read_only_mode(original_mode)
                
        except Exception as e:
            logger.error(f"❌ Emergency repair failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get integration status"""
        status = {
            "integrated": self.is_integrated,
            "agus_orchestrator": self.agus_orchestrator is not None,
            "agus_2_system": self.agus_2_system is not None,
            "self_healing": self.self_healing is not None and self.self_healing.is_running,
            "lsp_integration": self.lsp_integration is not None,
            "event_subscriptions": len(self.event_subscriptions),
            "last_check": datetime.now().isoformat()
        }
        
        if self.self_healing:
            status["self_healing_status"] = self.self_healing.get_status()
        
        return status
    
    async def shutdown(self):
        """Shutdown integration"""
        try:
            logger.info("🔗 Shutting down AGUS Self-Healing Integration...")
            
            # Unsubscribe from events
            if self.agus_orchestrator:
                for event_type, callback in self.event_subscriptions:
                    self.agus_orchestrator.event_bus.unsubscribe(event_type, callback)
            
            # Shutdown self-healing
            if self.self_healing:
                await self.self_healing.stop()
            
            self.is_integrated = False
            logger.info("✅ AGUS Self-Healing Integration shutdown completed")
            
        except Exception as e:
            logger.error(f"❌ Error during integration shutdown: {e}")


# Global integration instance
_integration_bridge: Optional[AGUSSelfHealingBridge] = None


async def initialize_agus_self_healing_integration(
    agus_orchestrator: Optional[AGUSOrchestrator] = None
) -> AGUSSelfHealingBridge:
    """Initialize the global AGUS self-healing integration"""
    global _integration_bridge
    
    if _integration_bridge is None:
        _integration_bridge = AGUSSelfHealingBridge(agus_orchestrator)
        await _integration_bridge.initialize_integration()
        logger.info("🔗 Global AGUS Self-Healing Integration initialized")
    
    return _integration_bridge


def get_agus_self_healing_integration() -> Optional[AGUSSelfHealingBridge]:
    """Get the global integration bridge"""
    return _integration_bridge


async def shutdown_agus_self_healing_integration():
    """Shutdown the global integration"""
    global _integration_bridge
    
    if _integration_bridge:
        await _integration_bridge.shutdown()
        _integration_bridge = None
        logger.info("🔗 Global AGUS Self-Healing Integration shutdown")


# Convenience functions for external use
async def trigger_emergency_repair(error_description: str) -> Dict[str, Any]:
    """Trigger emergency repair from external systems"""
    bridge = get_agus_self_healing_integration()
    if bridge:
        return await bridge.emergency_repair(error_description)
    else:
        return {"status": "error", "message": "Integration not initialized"}


def get_self_healing_status() -> Dict[str, Any]:
    """Get comprehensive self-healing status"""
    bridge = get_agus_self_healing_integration()
    if bridge:
        return bridge.get_integration_status()
    else:
        return {"status": "error", "message": "Integration not initialized"}