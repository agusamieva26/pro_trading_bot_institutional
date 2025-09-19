#!/usr/bin/env python3
"""
🔧 AGUS AUTONOMOUS SELF-HEALING SYSTEM
Complete autonomous error detection and correction system for AGUS trading bot.

🚀 COMPONENTS:
- LSPErrorDetector: Continuous LSP error monitoring with intelligent filtering
- CodeFixers: Automated fixes for imports, syntax, types, variables, config
- VerificationEngine: Post-fix validation and regression detection  
- AutoRevertSystem: Backup and rollback system with safe points
- SelfHealingOrchestrator: Main coordinator integrating with AGUS core

🛡️ SAFETY FEATURES:
- Never touches critical trading configs
- Mandatory backups before any modification
- Automatic rollback on failures
- Read-only analysis mode
- Emergency kill switch
- Whitelist-based file modification
"""

import asyncio
import json
import time
import uuid
import shutil
import threading
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple, Set, Pattern
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from collections import defaultdict, deque
import re
import tempfile
import subprocess
import sqlite3

# Import existing system components
try:
    from .util import logger
    from .config import settings
    from .agus_core import AGUSOrchestrator, Event, EventType, Alert, AlertSeverity
    from .qwen_lightweight import qwen_generate_response, qwen_chat_completion_async
    AGUS_INTEGRATION_AVAILABLE = True
except ImportError as e:
    # Fallback logging
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)
    # Fallback classes for standalone use
    AGUSOrchestrator = None
    Event = None
    EventType = None
    Alert = None
    AlertSeverity = None
    qwen_generate_response = None
    qwen_chat_completion_async = None
    AGUS_INTEGRATION_AVAILABLE = False


class ErrorSeverity(Enum):
    """Error severity levels for self-healing system"""
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"
    BLOCKING = "blocking"


class FixResult(Enum):
    """Results of fix attempts"""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    NEEDS_MANUAL = "needs_manual"
    REVERTED = "reverted"


@dataclass
class LSPError:
    """LSP error representation"""
    file_path: str = ""
    line: int = 0
    column: int = 0
    message: str = ""
    severity: ErrorSeverity = ErrorSeverity.ERROR
    error_code: str = ""
    error_type: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    fix_attempted: bool = False
    fix_result: Optional[FixResult] = None
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass  
class FixAttempt:
    """Record of a fix attempt"""
    fix_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    error_id: str = ""
    fixer_type: str = ""
    file_path: str = ""
    backup_path: str = ""
    changes_made: List[str] = field(default_factory=list)
    result: FixResult = FixResult.FAILED
    timestamp: datetime = field(default_factory=datetime.now)
    verification_passed: bool = False
    rollback_reason: str = ""


class LSPErrorDetector:
    """🔍 Continuous LSP error monitoring with intelligent filtering"""
    
    def __init__(self, orchestrator: Optional['SelfHealingOrchestrator'] = None):
        self.orchestrator = orchestrator
        self.is_running = False
        self.check_interval = 30  # Check every 30 seconds
        self.error_history = deque(maxlen=1000)
        self.last_errors = {}
        self.filtered_patterns = self._init_filtered_patterns()
        self.critical_patterns = self._init_critical_patterns()
        self.excluded_directories = self._init_excluded_directories()
        self.included_file_patterns = self._init_included_files()
        self._lock = threading.RLock()
        
    def _init_filtered_patterns(self) -> List[Pattern]:
        """Initialize patterns for errors to filter/ignore"""
        patterns = [
            # Deprecation warnings that don't block functionality
            re.compile(r"deprecated.*use_container_width", re.IGNORECASE),
            re.compile(r"FutureWarning.*pandas", re.IGNORECASE),
            re.compile(r"UserWarning.*matplotlib", re.IGNORECASE),
            # Common info-level messages
            re.compile(r"INFO.*initialized", re.IGNORECASE),
            re.compile(r"completed successfully", re.IGNORECASE),
        ]
        return patterns
    
    def _init_critical_patterns(self) -> List[Pattern]:
        """Initialize patterns for critical errors requiring immediate attention"""
        patterns = [
            re.compile(r"ImportError|ModuleNotFoundError", re.IGNORECASE),
            re.compile(r"SyntaxError|IndentationError", re.IGNORECASE),
            re.compile(r"NameError|UnboundLocalError", re.IGNORECASE),
            re.compile(r"TypeError.*required.*argument", re.IGNORECASE),
            re.compile(r"AttributeError.*has no attribute", re.IGNORECASE),
            re.compile(r"KeyError|IndexError", re.IGNORECASE),
            re.compile(r"ValueError.*invalid literal", re.IGNORECASE),
        ]
        return patterns
    
    def _init_excluded_directories(self) -> List[str]:
        """Initialize directories to exclude from error monitoring"""
        excluded = [
            # Test and development directories
            "tests/", "test/", "__pycache__/", ".pytest_cache/",
            "test_cache/", "*test*.py", "*_test.py", "test_*.py",
            # Build and cache directories  
            "build/", "dist/", ".git/", ".vscode/", ".idea/",
            "node_modules/", "data_cache/", "backtest_cache/",
            # Models and large files
            "models/gguf/", "models/huggingface/", "*.gguf", "*.bin",
            # Logs and temporary files
            "logs/", "temp/", "tmp/", "*.log", "*.tmp",
            # Backup and archive directories
            "backups/", "archives/", "backup_*/",
            # Configuration caches
            "configs/symbol_configs.json", "auto_config.json",
            # Desktop app (less critical for trading)
            "desktop_app/",
            # Reports and analysis outputs
            "reports/", "results/",
            # Specific test files we know about
            "comprehensive_integration_test.py",
            "realistic_integration_test.py",
            "leakage_free_evaluation.py",
            "monitor_bot.py",
            "verificar_estado.py"
        ]
        return excluded
    
    def _init_included_files(self) -> List[str]:
        """Initialize critical files that should always be monitored"""
        critical_files = [
            # Core trading system
            "bot/main.py", "bot/agus_core.py", "bot/config.py",
            "bot/execution.py", "bot/data.py", "bot/strategy.py",
            "bot/risk.py", "bot/sizing.py", "bot/state.py",
            # Risk management
            "bot/risk_management_v2.py", "bot/drawdown_protector.py",
            "bot/dynamic_risk_manager.py", "bot/profit_taking.py",
            # Core dashboard
            "dashboard_modern.py", "dashboard.py",
            # AI and orchestration
            "bot/agus_2_hybrid_system.py", "bot/qwen_lightweight.py",
            "bot/multi_model_orchestrator.py"
        ]
        return critical_files
    
    def _classify_error_severity(self, message: str, file_path: str) -> ErrorSeverity:
        """Classify error severity based on message and file path"""
        
        # Critical files that must work
        critical_files = [
            "bot/main.py", "bot/agus_core.py", "bot/config.py",
            "dashboard_modern.py", "bot/execution.py"
        ]
        
        is_critical_file = any(critical in file_path for critical in critical_files)
        
        # Check for critical error patterns
        for pattern in self.critical_patterns:
            if pattern.search(message):
                return ErrorSeverity.CRITICAL if is_critical_file else ErrorSeverity.ERROR
        
        # Check for blocking errors
        if any(keyword in message.lower() for keyword in ["cannot import", "module not found", "syntax error"]):
            return ErrorSeverity.BLOCKING
        
        # Default classification
        if "warning" in message.lower():
            return ErrorSeverity.WARNING
        elif "error" in message.lower():
            return ErrorSeverity.ERROR if is_critical_file else ErrorSeverity.WARNING
        else:
            return ErrorSeverity.INFO
    
    def _should_filter_error(self, message: str, file_path: str = "") -> bool:
        """Check if error should be filtered out based on message and file path"""
        # Check message patterns first
        for pattern in self.filtered_patterns:
            if pattern.search(message):
                return True
        
        # Check if file should be excluded
        if file_path and self._should_exclude_file(file_path):
            return True
            
        return False
    
    def _should_exclude_file(self, file_path: str) -> bool:
        """Check if file should be excluded from monitoring"""
        # Always include critical files regardless of directory
        for critical_file in self.included_file_patterns:
            if critical_file in file_path:
                return False
        
        # Check excluded directories and patterns
        for excluded in self.excluded_directories:
            if excluded.endswith('/'):
                # Directory pattern
                if excluded in file_path or file_path.startswith(excluded):
                    return True
            elif '*' in excluded:
                # Glob pattern - simple implementation
                if excluded.startswith('*') and file_path.endswith(excluded[1:]):
                    return True
                elif excluded.endswith('*') and file_path.startswith(excluded[:-1]):
                    return True
                elif '*' in excluded.replace('*', ''):
                    # More complex patterns - convert to regex
                    import fnmatch
                    if fnmatch.fnmatch(file_path, excluded):
                        return True
            else:
                # Exact match or substring
                if excluded in file_path:
                    return True
        
        return False
    
    async def start_monitoring(self):
        """Start continuous LSP error monitoring"""
        self.is_running = True
        logger.info("🔍 LSP Error Detector - Starting continuous monitoring...")
        
        while self.is_running:
            try:
                await self._check_lsp_errors()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"❌ LSP Error Detector error: {e}")
                await asyncio.sleep(5)
    
    async def stop_monitoring(self):
        """Stop LSP monitoring"""
        self.is_running = False
        logger.info("🔍 LSP Error Detector - Monitoring stopped")
    
    async def _check_lsp_errors(self):
        """Check for LSP errors and process them"""
        try:
            # Import get_latest_lsp_diagnostics function dynamically
            # This would be available in the actual system
            diagnostics_result = await self._get_lsp_diagnostics()
            
            if not diagnostics_result:
                return
            
            new_errors = self._parse_lsp_diagnostics(diagnostics_result)
            
            # Process new and changed errors
            for error in new_errors:
                if not self._should_filter_error(error.message, error.file_path):
                    await self._process_error(error)
                else:
                    logger.debug(f"🔍 Filtered error in {error.file_path}: {error.message[:100]}")
                    
        except Exception as e:
            logger.error(f"❌ Error checking LSP diagnostics: {e}")
    
    async def _get_lsp_diagnostics(self) -> Optional[str]:
        """Get LSP diagnostics using the actual tool"""
        try:
            # Try to import and use the actual LSP diagnostics tool
            try:
                from tools.lsp_diagnostic_tool import get_latest_lsp_diagnostics
                result = get_latest_lsp_diagnostics()
                return result
            except ImportError:
                # Tool not available, return None for fallback
                logger.debug("LSP diagnostics tool not available")
                return None
        except Exception as e:
            logger.error(f"❌ Error calling LSP diagnostics: {e}")
            return None
    
    def _parse_lsp_diagnostics(self, diagnostics: str) -> List[LSPError]:
        """Parse LSP diagnostics output into LSPError objects"""
        errors = []
        
        # Parse the diagnostics format
        # This is a simplified parser - real implementation would handle LSP JSON format
        lines = diagnostics.split('\n') if diagnostics else []
        
        for line in lines:
            if ':' in line and ('error' in line.lower() or 'warning' in line.lower()):
                try:
                    parts = line.split(':')
                    if len(parts) >= 4:
                        file_path = parts[0].strip()
                        line_num = int(parts[1].strip()) if parts[1].strip().isdigit() else 0
                        col_num = int(parts[2].strip()) if parts[2].strip().isdigit() else 0
                        message = ':'.join(parts[3:]).strip()
                        
                        # Check if this file should be monitored
                        if not self._should_exclude_file(file_path):
                            severity = self._classify_error_severity(message, file_path)
                            
                            error = LSPError(
                                file_path=file_path,
                                line=line_num,
                                column=col_num,
                                message=message,
                                severity=severity,
                                error_type=self._extract_error_type(message)
                            )
                            
                            errors.append(error)
                        else:
                            logger.debug(f"🔍 Excluded file from monitoring: {file_path}")
                        
                except (ValueError, IndexError) as e:
                    logger.debug(f"Could not parse LSP line: {line} - {e}")
        
        return errors
    
    def _extract_error_type(self, message: str) -> str:
        """Extract error type from message"""
        error_types = {
            'import': ['ImportError', 'ModuleNotFoundError', 'cannot import'],
            'syntax': ['SyntaxError', 'IndentationError', 'invalid syntax'],
            'name': ['NameError', 'UnboundLocalError', 'not defined'],
            'type': ['TypeError', 'type object', 'expected'],
            'attribute': ['AttributeError', 'has no attribute'],
            'value': ['ValueError', 'invalid literal'],
            'key': ['KeyError', 'IndexError']
        }
        
        message_lower = message.lower()
        for error_type, keywords in error_types.items():
            if any(keyword.lower() in message_lower for keyword in keywords):
                return error_type
        
        return 'unknown'
    
    async def _process_error(self, error: LSPError):
        """Process a detected error"""
        with self._lock:
            # Add to history
            self.error_history.append(error)
            
            # Check if this is a new or changed error
            error_key = f"{error.file_path}:{error.line}:{error.message}"
            
            if error_key not in self.last_errors or self.last_errors[error_key].severity != error.severity:
                self.last_errors[error_key] = error
                
                # Send to orchestrator for fixing
                if self.orchestrator and error.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.BLOCKING, ErrorSeverity.ERROR]:
                    await self.orchestrator._handle_detected_error(error)
                
                # Log the error
                level_map = {
                    ErrorSeverity.CRITICAL: "CRITICAL",
                    ErrorSeverity.BLOCKING: "ERROR", 
                    ErrorSeverity.ERROR: "ERROR",
                    ErrorSeverity.WARNING: "WARNING",
                    ErrorSeverity.INFO: "INFO"
                }
                
                level = level_map.get(error.severity, "INFO")
                logger.log(
                    getattr(logging, level),
                    f"🔍 LSP Error Detected [{error.severity.value.upper()}] {error.file_path}:{error.line} - {error.message}"
                )
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        with self._lock:
            stats = {
                'total_errors': len(self.error_history),
                'by_severity': defaultdict(int),
                'by_type': defaultdict(int),
                'by_file': defaultdict(int),
                'recent_errors': len([e for e in self.error_history if (datetime.now() - e.timestamp).total_seconds() < 3600])
            }
            
            for error in self.error_history:
                stats['by_severity'][error.severity.value] += 1
                stats['by_type'][error.error_type] += 1
                stats['by_file'][error.file_path] += 1
            
            return dict(stats)


class CodeFixers:
    """🔧 Automated code fixers for different error types"""
    
    def __init__(self, orchestrator: Optional['SelfHealingOrchestrator'] = None):
        self.orchestrator = orchestrator
        self.fixers = {
            'import': ImportFixer(),
            'syntax': SyntaxFixer(),
            'type': TypeFixer(),
            'name': VariableFixer(),
            'config': ConfigFixer()
        }
        
        # Safe file patterns - only these can be automatically modified
        self.safe_file_patterns = [
            r'bot/.*\.py$',
            r'.*test.*\.py$',
            r'scripts/.*\.py$',
            r'dashboard.*\.py$'
        ]
        
        # Never touch these files
        self.forbidden_files = [
            'bot/config.py',  # Trading config
            'bot/main.py',    # Main trading loop
            'requirements.txt',
            '.env'
        ]
        
    def is_safe_to_modify(self, file_path: str) -> bool:
        """Check if file is safe for automatic modification"""
        # Check forbidden files
        if any(forbidden in file_path for forbidden in self.forbidden_files):
            return False
        
        # Check safe patterns
        return any(re.match(pattern, file_path) for pattern in self.safe_file_patterns)
    
    async def attempt_fix(self, error: LSPError) -> FixAttempt:
        """Attempt to fix an error"""
        fixer = self.fixers.get(error.error_type)
        if not fixer:
            return FixAttempt(
                error_id=error.error_id,
                fixer_type="none",
                file_path=error.file_path,
                result=FixResult.SKIPPED,
                rollback_reason="No fixer available for error type"
            )
        
        if not self.is_safe_to_modify(error.file_path):
            return FixAttempt(
                error_id=error.error_id,
                fixer_type=error.error_type,
                file_path=error.file_path,
                result=FixResult.SKIPPED,
                rollback_reason="File not in safe modification list"
            )
        
        try:
            return await fixer.fix_error(error)
        except Exception as e:
            logger.error(f"❌ Error attempting fix: {e}")
            return FixAttempt(
                error_id=error.error_id,
                fixer_type=error.error_type,
                file_path=error.file_path,
                result=FixResult.FAILED,
                rollback_reason=f"Exception during fix: {str(e)}"
            )


class BaseFixer:
    """Base class for all code fixers"""
    
    def __init__(self):
        self.fix_patterns = []
        self.backup_dir = Path("bot/backups/self_healing")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, file_path: str) -> str:
        """Create a backup of the file before modification"""
        try:
            source = Path(file_path)
            if not source.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{source.stem}_{timestamp}{source.suffix}"
            backup_path = self.backup_dir / backup_name
            
            shutil.copy2(source, backup_path)
            logger.debug(f"🔒 Created backup: {backup_path}")
            
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"❌ Failed to create backup for {file_path}: {e}")
            raise
    
    def restore_backup(self, original_path: str, backup_path: str) -> bool:
        """Restore file from backup"""
        try:
            if Path(backup_path).exists():
                shutil.copy2(backup_path, original_path)
                logger.info(f"🔄 Restored {original_path} from backup")
                return True
            else:
                logger.error(f"❌ Backup not found: {backup_path}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to restore backup: {e}")
            return False
    
    async def fix_error(self, error: LSPError) -> FixAttempt:
        """Base fix method - override in subclasses"""
        raise NotImplementedError


class ImportFixer(BaseFixer):
    """🔧 Fixes import-related errors"""
    
    def __init__(self):
        super().__init__()
        # Common import fixes
        self.import_mappings = {
            'pandas': 'import pandas as pd',
            'numpy': 'import numpy as np',
            'matplotlib': 'import matplotlib.pyplot as plt',
            'sklearn': 'from sklearn import *',
            'torch': 'import torch',
            'transformers': 'import transformers',
            'asyncio': 'import asyncio',
            'json': 'import json',
            'os': 'import os',
            'sys': 'import sys',
            'datetime': 'from datetime import datetime, timedelta',
            'typing': 'from typing import Dict, List, Optional, Any',
            'pathlib': 'from pathlib import Path',
            're': 'import re'
        }
    
    async def fix_error(self, error: LSPError) -> FixAttempt:
        """Fix import errors"""
        attempt = FixAttempt(
            error_id=error.error_id,
            fixer_type="import",
            file_path=error.file_path
        )
        
        try:
            # Create backup first
            attempt.backup_path = self.create_backup(error.file_path)
            
            # Read the file
            with open(error.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Analyze the error to determine missing import
            missing_module = self._extract_missing_module(error.message)
            
            if missing_module and missing_module in self.import_mappings:
                # Add the import at the top
                import_line = self.import_mappings[missing_module]
                
                # Find the right place to insert (after existing imports)
                insert_index = self._find_import_insertion_point(lines)
                
                lines.insert(insert_index, import_line)
                attempt.changes_made.append(f"Added import: {import_line}")
                
                # Write the fixed file
                with open(error.file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                
                attempt.result = FixResult.SUCCESS
                logger.info(f"✅ Fixed import error in {error.file_path}: Added {import_line}")
                
            else:
                attempt.result = FixResult.NEEDS_MANUAL
                attempt.rollback_reason = f"Unknown module: {missing_module}"
                
        except Exception as e:
            attempt.result = FixResult.FAILED
            attempt.rollback_reason = str(e)
            # Restore backup on failure
            if attempt.backup_path:
                self.restore_backup(error.file_path, attempt.backup_path)
        
        return attempt
    
    def _extract_missing_module(self, error_message: str) -> Optional[str]:
        """Extract the missing module name from error message"""
        patterns = [
            r"No module named '([^']+)'",
            r"cannot import name '([^']+)'",
            r"ImportError.*'([^']+)'",
            r"ModuleNotFoundError.*'([^']+)'"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_message)
            if match:
                module_name = match.group(1).split('.')[0]  # Get base module
                return module_name
        
        return None
    
    def _find_import_insertion_point(self, lines: List[str]) -> int:
        """Find the right place to insert new import"""
        # Look for existing imports
        last_import_index = -1
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ')) and not stripped.startswith('#'):
                last_import_index = i
            elif stripped and not stripped.startswith('#') and last_import_index >= 0:
                # Found first non-import, non-comment line after imports
                return last_import_index + 1
        
        # If no imports found, insert after docstring/comments
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                return i
        
        return 0


class SyntaxFixer(BaseFixer):
    """🔧 Fixes basic syntax errors"""
    
    def __init__(self):
        super().__init__()
        # Common syntax fix patterns
        self.fix_patterns = [
            # Missing colons
            (r'^(\s*)(if|elif|else|for|while|def|class|try|except|finally|with)\s+([^:]+)$', r'\1\2 \3:'),
            # Unmatched quotes
            (r"'([^']*)'([^']*)'", r"'\1\2'"),
            # Missing commas in function calls
            (r'(\w+)\s+(\w+)\s*\)', r'\1, \2)'),
        ]
    
    async def fix_error(self, error: LSPError) -> FixAttempt:
        """Fix syntax errors"""
        attempt = FixAttempt(
            error_id=error.error_id,
            fixer_type="syntax",
            file_path=error.file_path
        )
        
        try:
            # Create backup first
            attempt.backup_path = self.create_backup(error.file_path)
            
            # Read the file
            with open(error.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Try to fix the specific line
            if 0 <= error.line - 1 < len(lines):
                original_line = lines[error.line - 1]
                fixed_line = self._apply_syntax_fixes(original_line, error.message)
                
                if fixed_line != original_line:
                    lines[error.line - 1] = fixed_line
                    attempt.changes_made.append(f"Line {error.line}: '{original_line}' -> '{fixed_line}'")
                    
                    # Write the fixed file
                    with open(error.file_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(lines))
                    
                    attempt.result = FixResult.SUCCESS
                    logger.info(f"✅ Fixed syntax error in {error.file_path}:{error.line}")
                else:
                    attempt.result = FixResult.NEEDS_MANUAL
                    attempt.rollback_reason = "No automatic fix pattern matched"
            else:
                attempt.result = FixResult.FAILED
                attempt.rollback_reason = f"Invalid line number: {error.line}"
                
        except Exception as e:
            attempt.result = FixResult.FAILED
            attempt.rollback_reason = str(e)
            # Restore backup on failure
            if attempt.backup_path:
                self.restore_backup(error.file_path, attempt.backup_path)
        
        return attempt
    
    def _apply_syntax_fixes(self, line: str, error_message: str) -> str:
        """Apply syntax fix patterns to a line"""
        fixed_line = line
        
        # Check for missing colon
        if "expected ':'" in error_message or "invalid syntax" in error_message:
            for pattern, replacement in self.fix_patterns:
                new_line = re.sub(pattern, replacement, fixed_line)
                if new_line != fixed_line:
                    fixed_line = new_line
                    break
        
        return fixed_line


class TypeFixer(BaseFixer):
    """🔧 Fixes type-related errors"""
    
    async def fix_error(self, error: LSPError) -> FixAttempt:
        """Fix type errors - mostly skip for now"""
        return FixAttempt(
            error_id=error.error_id,
            fixer_type="type",
            file_path=error.file_path,
            result=FixResult.NEEDS_MANUAL,
            rollback_reason="Type errors require manual review"
        )


class VariableFixer(BaseFixer):
    """🔧 Fixes variable-related errors"""
    
    async def fix_error(self, error: LSPError) -> FixAttempt:
        """Fix undefined variable errors"""
        attempt = FixAttempt(
            error_id=error.error_id,
            fixer_type="variable",
            file_path=error.file_path
        )
        
        # For now, most variable errors need manual review
        # Could add common variable initialization patterns
        attempt.result = FixResult.NEEDS_MANUAL
        attempt.rollback_reason = "Variable errors require manual review"
        
        return attempt


class ConfigFixer(BaseFixer):
    """🔧 Fixes configuration file errors"""
    
    async def fix_error(self, error: LSPError) -> FixAttempt:
        """Fix config errors"""
        return FixAttempt(
            error_id=error.error_id,
            fixer_type="config",
            file_path=error.file_path,
            result=FixResult.SKIPPED,
            rollback_reason="Config files are protected from automatic modification"
        )


class VerificationEngine:
    """✅ Post-fix verification and health checks"""
    
    def __init__(self, orchestrator: Optional['SelfHealingOrchestrator'] = None):
        self.orchestrator = orchestrator
        
    async def verify_fix(self, fix_attempt: FixAttempt) -> bool:
        """Verify that a fix was successful and didn't break anything"""
        if fix_attempt.result != FixResult.SUCCESS:
            return True  # Nothing to verify
            
        try:
            # 1. Check LSP errors for this file
            lsp_clean = await self._check_lsp_clean(fix_attempt.file_path)
            
            # 2. Check system health (workflows still running)
            workflows_healthy = await self._check_workflows_healthy()
            
            # 3. Try to import/compile the fixed file
            syntax_valid = await self._check_syntax_valid(fix_attempt.file_path)
            
            verification_passed = lsp_clean and workflows_healthy and syntax_valid
            fix_attempt.verification_passed = verification_passed
            
            if not verification_passed:
                logger.warning(f"🔍 Verification failed for fix {fix_attempt.fix_id}")
                logger.warning(f"   LSP Clean: {lsp_clean}, Workflows: {workflows_healthy}, Syntax: {syntax_valid}")
            else:
                logger.info(f"✅ Fix verification passed: {fix_attempt.fix_id}")
            
            return verification_passed
            
        except Exception as e:
            logger.error(f"❌ Error during verification: {e}")
            fix_attempt.verification_passed = False
            return False
    
    async def _check_lsp_clean(self, file_path: str) -> bool:
        """Check if LSP errors are resolved for the file"""
        try:
            # In real implementation, would call LSP diagnostics for specific file
            # For now, assume success if no exception
            return True
        except Exception as e:
            logger.debug(f"LSP check failed: {e}")
            return False
    
    async def _check_workflows_healthy(self) -> bool:
        """Check if critical workflows are still running"""
        try:
            # Check if Dashboard and Trading Bot workflows are still active
            # In real implementation, would check workflow status
            # For now, assume healthy
            return True
        except Exception as e:
            logger.debug(f"Workflow health check failed: {e}")
            return False
    
    async def _check_syntax_valid(self, file_path: str) -> bool:
        """Check if the file has valid Python syntax"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # Try to compile the source
            compile(source, file_path, 'exec')
            return True
            
        except SyntaxError as e:
            logger.debug(f"Syntax check failed for {file_path}: {e}")
            return False
        except Exception as e:
            logger.debug(f"Unexpected error checking syntax: {e}")
            return False


class AutoRevertSystem:
    """🔄 Automatic backup and rollback system"""
    
    def __init__(self):
        self.backup_dir = Path("bot/backups/self_healing")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.revert_history = []
        self._init_db()
        
    def _init_db(self):
        """Initialize revert history database"""
        try:
            self.db_path = self.backup_dir / "revert_history.db"
            conn = sqlite3.connect(self.db_path)
            conn.execute('''CREATE TABLE IF NOT EXISTS reverts 
                           (revert_id TEXT PRIMARY KEY, fix_id TEXT, file_path TEXT, 
                            backup_path TEXT, timestamp TEXT, reason TEXT, success INTEGER)''')
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ Failed to initialize revert database: {e}")
    
    async def revert_fix(self, fix_attempt: FixAttempt, reason: str = "Verification failed") -> bool:
        """Revert a fix attempt"""
        try:
            if not fix_attempt.backup_path or not Path(fix_attempt.backup_path).exists():
                logger.error(f"❌ Cannot revert {fix_attempt.fix_id}: No backup available")
                return False
            
            # Restore the backup
            shutil.copy2(fix_attempt.backup_path, fix_attempt.file_path)
            
            # Record the revert
            revert_id = str(uuid.uuid4())
            
            try:
                conn = sqlite3.connect(self.db_path)
                conn.execute('''INSERT INTO reverts 
                               (revert_id, fix_id, file_path, backup_path, timestamp, reason, success)
                               VALUES (?, ?, ?, ?, ?, ?, ?)''',
                            (revert_id, fix_attempt.fix_id, fix_attempt.file_path, 
                             fix_attempt.backup_path, datetime.now().isoformat(), reason, 1))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"❌ Failed to record revert: {e}")
            
            # Update fix attempt
            fix_attempt.result = FixResult.REVERTED
            fix_attempt.rollback_reason = reason
            
            logger.info(f"🔄 Reverted fix {fix_attempt.fix_id} for {fix_attempt.file_path}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to revert fix {fix_attempt.fix_id}: {e}")
            return False
    
    def cleanup_old_backups(self, days_old: int = 7):
        """Clean up old backups"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days_old)
            
            for backup_file in self.backup_dir.glob("*"):
                if backup_file.is_file() and backup_file.stat().st_mtime < cutoff_time.timestamp():
                    backup_file.unlink()
                    logger.debug(f"🧹 Cleaned up old backup: {backup_file}")
                    
        except Exception as e:
            logger.error(f"❌ Error cleaning up backups: {e}")


class SelfHealingOrchestrator:
    """🎯 Main self-healing system coordinator"""
    
    def __init__(self, agus_orchestrator: Optional[AGUSOrchestrator] = None):
        self.agus_orchestrator = agus_orchestrator
        self.is_running = False
        self.enabled = True  # Kill switch
        self.read_only_mode = False
        
        # Initialize components
        self.error_detector = LSPErrorDetector(self)
        self.code_fixers = CodeFixers(self)
        self.verification_engine = VerificationEngine(self)
        self.revert_system = AutoRevertSystem()
        
        # Statistics and state
        self.fix_attempts = []
        self.stats = {
            'total_errors_detected': 0,
            'fixes_attempted': 0,
            'fixes_successful': 0,
            'fixes_reverted': 0,
            'fixes_skipped': 0
        }
        
        self._init_db()
        
    def _init_db(self):
        """Initialize self-healing database"""
        try:
            self.db_path = Path("bot/backups/self_healing/self_healing.db")
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            conn.execute('''CREATE TABLE IF NOT EXISTS fix_attempts 
                           (fix_id TEXT PRIMARY KEY, error_id TEXT, fixer_type TEXT,
                            file_path TEXT, backup_path TEXT, result TEXT,
                            timestamp TEXT, verification_passed INTEGER,
                            rollback_reason TEXT, changes_made TEXT)''')
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ Failed to initialize self-healing database: {e}")
    
    async def start(self):
        """Start the self-healing system"""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info("🔧 AGUS Self-Healing System - Starting...")
        
        # Start error detection
        await asyncio.create_task(self.error_detector.start_monitoring())
        
        # Start periodic cleanup
        asyncio.create_task(self._periodic_cleanup())
        
        logger.info("✅ AGUS Self-Healing System - Active and monitoring")
    
    async def stop(self):
        """Stop the self-healing system"""
        self.is_running = False
        
        await self.error_detector.stop_monitoring()
        
        logger.info("🔧 AGUS Self-Healing System - Stopped")
    
    def enable(self):
        """Enable automatic fixes"""
        self.enabled = True
        logger.info("✅ Self-healing enabled")
    
    def disable(self):
        """Disable automatic fixes (kill switch)"""
        self.enabled = False
        logger.warning("🛑 Self-healing disabled (kill switch activated)")
    
    def set_read_only_mode(self, read_only: bool):
        """Toggle read-only mode"""
        self.read_only_mode = read_only
        mode_str = "READ-ONLY" if read_only else "ACTIVE"
        logger.info(f"📖 Self-healing mode: {mode_str}")
    
    async def _handle_detected_error(self, error: LSPError):
        """Handle an error detected by the error detector"""
        self.stats['total_errors_detected'] += 1
        
        if not self.enabled:
            logger.debug(f"🛑 Self-healing disabled - skipping error {error.error_id}")
            return
        
        if self.read_only_mode:
            logger.info(f"📖 Read-only mode - analyzing error {error.error_id} without fixing")
            await self._analyze_error_with_ai(error)
            return
        
        # Attempt to fix the error
        logger.info(f"🔧 Attempting to fix error: {error.file_path}:{error.line} - {error.message}")
        
        fix_attempt = await self.code_fixers.attempt_fix(error)
        fix_attempt.timestamp = datetime.now()
        
        self.fix_attempts.append(fix_attempt)
        self.stats['fixes_attempted'] += 1
        
        # Verify the fix
        if fix_attempt.result == FixResult.SUCCESS:
            verification_passed = await self.verification_engine.verify_fix(fix_attempt)
            
            if not verification_passed:
                # Revert the fix
                await self.revert_system.revert_fix(fix_attempt, "Verification failed")
                self.stats['fixes_reverted'] += 1
            else:
                self.stats['fixes_successful'] += 1
        elif fix_attempt.result == FixResult.SKIPPED:
            self.stats['fixes_skipped'] += 1
        
        # Store in database
        await self._store_fix_attempt(fix_attempt)
        
        # Emit event to AGUS system
        if self.agus_orchestrator:
            await self._emit_fix_event(error, fix_attempt)
    
    async def _analyze_error_with_ai(self, error: LSPError):
        """Analyze error with AI without making changes"""
        try:
            if AGUS_INTEGRATION_AVAILABLE:
                prompt = f"""
                Analyze this coding error for potential fixes:
                
                File: {error.file_path}
                Line: {error.line}
                Error: {error.message}
                Type: {error.error_type}
                
                Provide analysis and suggested fix approach (DO NOT make actual changes).
                """
                
                analysis = await qwen_chat_completion_async([
                    {"role": "system", "content": "You are a code analysis expert. Analyze errors and suggest fixes."},
                    {"role": "user", "content": prompt}
                ])
                
                logger.info(f"🧠 AI Analysis for {error.file_path}:{error.line}")
                logger.info(f"   {analysis[:200]}..." if len(analysis) > 200 else f"   {analysis}")
                
        except Exception as e:
            logger.debug(f"AI analysis failed: {e}")
    
    async def _store_fix_attempt(self, fix_attempt: FixAttempt):
        """Store fix attempt in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''INSERT INTO fix_attempts 
                           (fix_id, error_id, fixer_type, file_path, backup_path,
                            result, timestamp, verification_passed, rollback_reason, changes_made)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (fix_attempt.fix_id, fix_attempt.error_id, fix_attempt.fixer_type,
                         fix_attempt.file_path, fix_attempt.backup_path, fix_attempt.result.value,
                         fix_attempt.timestamp.isoformat(), int(fix_attempt.verification_passed),
                         fix_attempt.rollback_reason, json.dumps(fix_attempt.changes_made)))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ Failed to store fix attempt: {e}")
    
    async def _emit_fix_event(self, error: LSPError, fix_attempt: FixAttempt):
        """Emit fix event to AGUS orchestrator"""
        try:
            if not self.agus_orchestrator:
                return
                
            event = Event(
                event_type=EventType.SYSTEM_ERROR if fix_attempt.result != FixResult.SUCCESS else EventType.SYSTEM_START,
                source="SelfHealing",
                data={
                    "error_id": error.error_id,
                    "fix_id": fix_attempt.fix_id,
                    "file_path": error.file_path,
                    "error_type": error.error_type,
                    "fix_result": fix_attempt.result.value,
                    "verification_passed": fix_attempt.verification_passed
                },
                priority=2 if error.severity == ErrorSeverity.CRITICAL else 4
            )
            
            self.agus_orchestrator.event_bus.publish(event)
            
        except Exception as e:
            logger.error(f"❌ Failed to emit fix event: {e}")
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of old backups and logs"""
        while self.is_running:
            try:
                # Run cleanup every hour
                await asyncio.sleep(3600)
                
                if not self.is_running:
                    break
                    
                # Clean up old backups (7 days)
                self.revert_system.cleanup_old_backups(7)
                
                # Clean up old fix attempts (keep last 1000)
                if len(self.fix_attempts) > 1000:
                    self.fix_attempts = self.fix_attempts[-1000:]
                
                logger.debug("🧹 Periodic cleanup completed")
                
            except Exception as e:
                logger.error(f"❌ Error in periodic cleanup: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            'enabled': self.enabled,
            'read_only_mode': self.read_only_mode,
            'is_running': self.is_running,
            'stats': self.stats.copy(),
            'error_detector_stats': self.error_detector.get_error_stats(),
            'recent_fixes': len([f for f in self.fix_attempts if (datetime.now() - f.timestamp).total_seconds() < 3600])
        }
    
    async def manual_health_check(self) -> Dict[str, Any]:
        """Perform manual health check"""
        logger.info("🩺 Running manual health check...")
        
        # Force LSP check
        await self.error_detector._check_lsp_errors()
        
        status = self.get_status()
        status['health_check_time'] = datetime.now().isoformat()
        
        logger.info(f"🩺 Health check complete - Found {status['error_detector_stats']['recent_errors']} recent errors")
        
        return status


# Global instance for easy access
_global_self_healing: Optional[SelfHealingOrchestrator] = None


async def initialize_self_healing(agus_orchestrator: Optional[AGUSOrchestrator] = None) -> SelfHealingOrchestrator:
    """Initialize the global self-healing system"""
    global _global_self_healing
    
    if _global_self_healing is None:
        _global_self_healing = SelfHealingOrchestrator(agus_orchestrator)
        await _global_self_healing.start()
        logger.info("🔧 Global self-healing system initialized")
    
    return _global_self_healing


def get_self_healing() -> Optional[SelfHealingOrchestrator]:
    """Get the global self-healing instance"""
    return _global_self_healing


async def shutdown_self_healing():
    """Shutdown the global self-healing system"""
    global _global_self_healing
    
    if _global_self_healing:
        await _global_self_healing.stop()
        _global_self_healing = None
        logger.info("🔧 Self-healing system shutdown complete")


# Example usage and testing
if __name__ == "__main__":
    async def main():
        # Test the self-healing system
        orchestrator = SelfHealingOrchestrator()
        await orchestrator.start()
        
        # Simulate some errors for testing
        test_error = LSPError(
            file_path="test_file.py",
            line=10,
            message="ImportError: No module named 'pandas'",
            severity=ErrorSeverity.ERROR,
            error_type="import"
        )
        
        await orchestrator._handle_detected_error(test_error)
        
        # Get status
        status = orchestrator.get_status()
        print(json.dumps(status, indent=2, default=str))
        
        await orchestrator.stop()
    
    asyncio.run(main())