"""
Logger Utility v2.1 - Enhanced logging for development and debugging.

Features:
- Per-action log files with correct naming
- Source location tracking (file, class, function, line)
- Performance timing for debugging bottlenecks
- Session state saving/resuming (JSON)
- Windows-compatible console output
"""
import logging
import os
import sys
import io
import time
import json
import inspect
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler
from functools import wraps

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass


# =============================================================================
# SESSION STATE MANAGER
# =============================================================================

class SessionState:
    """
    Manages session state for resume functionality.
    Saves progress to JSON file so scraping can be resumed.
    """
    
    def __init__(self, action_name: str, state_dir: str = "data/sessions"):
        self.action_name = action_name
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.state_file = self.state_dir / f"{action_name}_state.json"
        self.state = {}
        
    def save(self, **kwargs):
        """Save session state to JSON"""
        self.state.update(kwargs)
        self.state['last_updated'] = datetime.now().isoformat()
        self.state['action_name'] = self.action_name
        
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Could not save session state: {e}")
    
    def load(self) -> Optional[Dict]:
        """Load session state from JSON"""
        if not self.state_file.exists():
            return None
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                self.state = json.load(f)
                return self.state
        except Exception:
            return None
    
    def exists(self) -> bool:
        """Check if there's a saved session"""
        return self.state_file.exists()
    
    def get_summary(self) -> str:
        """Get human-readable summary of saved state"""
        if not self.exists():
            return "No saved session"
        
        state = self.load()
        if not state:
            return "No saved session"
        
        lines = [f"Saved session from {state.get('last_updated', 'unknown')}:"]
        
        # Show relevant fields
        for key, value in state.items():
            if key not in ['last_updated', 'action_name']:
                if isinstance(value, list):
                    lines.append(f"  • {key}: {len(value)} items")
                else:
                    lines.append(f"  • {key}: {value}")
        
        return "\n".join(lines)
    
    def clear(self):
        """Delete session state file"""
        if self.state_file.exists():
            os.remove(self.state_file)
            self.state = {}
    
    def ask_resume(self) -> bool:
        """Ask user if they want to resume or start over"""
        if not self.exists():
            return False  # Nothing to resume
        
        print("\n" + "=" * 50)
        print("📂 PREVIOUS SESSION FOUND")
        print("=" * 50)
        print(self.get_summary())
        print("-" * 50)
        
        choice = input("Resume previous session? (y/n) [y]: ").strip().lower()
        
        if choice == 'n':
            self.clear()
            print("🗑️ Previous session cleared. Starting fresh.")
            return False
        else:
            print("▶️ Resuming previous session...")
            return True


# =============================================================================
# ENHANCED LOGGER
# =============================================================================

class DevLogger:
    """
    Enhanced logger for development and debugging.
    
    Features:
    - Tracks source location (file, class, function, line)
    - Performance timing
    - Per-action log files
    - Session state management
    """
    
    # Custom SUCCESS level
    SUCCESS = 25
    logging.addLevelName(SUCCESS, "SUCCESS")
    
    # ANSI colors
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[37m',       # White
        'SUCCESS': '\033[32m',    # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'TIMING': '\033[34m',     # Blue
        'RESET': '\033[0m',
    }
    
    EMOJI = {
        'DEBUG': '🔍',
        'INFO': 'ℹ️ ',
        'SUCCESS': '✅',
        'WARNING': '⚠️ ',
        'ERROR': '❌',
        'CRITICAL': '🚨',
        'TIMING': '⏱️ ',
    }
    
    def __init__(self, action_name: str, log_dir: str = "data/logs",
                 console_output: bool = True, file_output: bool = True,
                 verbose: bool = True, include_source: bool = True):
        """
        Initialize logger.
        
        Args:
            action_name: Name of the action (used for log file name)
            log_dir: Directory for log files
            console_output: Print to console
            file_output: Save to file
            verbose: Show DEBUG level
            include_source: Include source file/function in logs
        """
        self.action_name = action_name
        self.include_source = include_source
        self.verbose = verbose
        
        # Create log directory
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create unique log file name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"{action_name}_{timestamp}.log"
        
        # Setup Python logger
        self.logger = logging.getLogger(f"linkedin.{action_name}.{timestamp}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        
        # File handler with detailed format
        if file_output:
            file_handler = RotatingFileHandler(
                self.log_file,
                maxBytes=10485760,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            
            # Detailed format for file
            file_format = "%(asctime)s | %(levelname)-8s | %(source)s | %(message)s"
            file_handler.setFormatter(SourceFormatter(file_format))
            self.logger.addHandler(file_handler)
        
        # Console handler with simpler format
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
            console_handler.setFormatter(ConsoleFormatter(include_source))
            self.logger.addHandler(console_handler)
        
        # Session state
        self.session = SessionState(action_name)
        
        # Timing tracker
        self.timings = {}
        self.start_time = datetime.now()
        
        # Log session start
        self._log_header()
    
    def _log_header(self):
        """Log session header with metadata"""
        self.logger.info("=" * 60, extra={'source': 'SYSTEM'})
        self.logger.info(f"ACTION: {self.action_name.upper()}", extra={'source': 'SYSTEM'})
        self.logger.info(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}", extra={'source': 'SYSTEM'})
        self.logger.info(f"Log file: {self.log_file.name}", extra={'source': 'SYSTEM'})
        self.logger.info("=" * 60, extra={'source': 'SYSTEM'})
    
    def _get_source(self) -> str:
        """Get source location (file:function:line)"""
        if not self.include_source:
            return ""
        
        # Walk up the stack to find the actual caller
        stack = inspect.stack()
        for i, frame in enumerate(stack):
            # Skip logger internals
            if 'logger.py' not in frame.filename and 'logging' not in frame.filename:
                filename = os.path.basename(frame.filename)
                return f"{filename}:{frame.function}:{frame.lineno}"
        
        return "unknown"
    
    def debug(self, message: str):
        """Log debug message with source"""
        self.logger.debug(message, extra={'source': self._get_source()})
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message, extra={'source': self._get_source()})
    
    def success(self, message: str):
        """Log success message"""
        self.logger.log(self.SUCCESS, message, extra={'source': self._get_source()})
    
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message, extra={'source': self._get_source()})
    
    def error(self, message: str):
        """Log error message"""
        self.logger.error(message, extra={'source': self._get_source()})
    
    def critical(self, message: str):
        """Log critical message"""
        self.logger.critical(message, extra={'source': self._get_source()})
    
    # =========================================================================
    # TIMING METHODS
    # =========================================================================
    
    def start_timer(self, name: str):
        """Start a named timer"""
        self.timings[name] = {'start': time.time(), 'end': None}
        self.debug(f"⏱️ Timer started: {name}")
    
    def stop_timer(self, name: str) -> float:
        """Stop a named timer and return duration"""
        if name not in self.timings:
            return 0.0
        
        self.timings[name]['end'] = time.time()
        duration = self.timings[name]['end'] - self.timings[name]['start']
        self.debug(f"⏱️ Timer stopped: {name} = {duration:.2f}s")
        return duration
    
    def time_operation(self, name: str):
        """Context manager for timing operations"""
        return TimingContext(self, name)
    
    # =========================================================================
    # STATE METHODS
    # =========================================================================
    
    def save_state(self, **kwargs):
        """Save session state for resume"""
        self.session.save(**kwargs)
        self.debug(f"💾 State saved: {list(kwargs.keys())}")
    
    def load_state(self) -> Optional[Dict]:
        """Load saved session state"""
        return self.session.load()
    
    def ask_resume(self) -> bool:
        """Ask user if they want to resume"""
        return self.session.ask_resume()
    
    def clear_state(self):
        """Clear saved state"""
        self.session.clear()
    
    # =========================================================================
    # STATS & SUMMARY
    # =========================================================================
    
    def log_stats(self, stats: Dict[str, Any]):
        """Log statistics"""
        self.info("-" * 40)
        self.info("STATISTICS:")
        for key, value in stats.items():
            self.info(f"  {key}: {value}")
        self.info("-" * 40)
    
    def log_timings(self):
        """Log all recorded timings"""
        if not self.timings:
            return
        
        self.info("-" * 40)
        self.info("PERFORMANCE TIMINGS:")
        
        total = 0
        for name, timing in self.timings.items():
            if timing['end']:
                duration = timing['end'] - timing['start']
                total += duration
                self.info(f"  {name}: {duration:.2f}s")
        
        self.info(f"  TOTAL: {total:.2f}s")
        self.info("-" * 40)
    
    def close(self):
        """Close logger and log footer"""
        duration = datetime.now() - self.start_time
        
        self.logger.info("=" * 60, extra={'source': 'SYSTEM'})
        self.logger.info(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", extra={'source': 'SYSTEM'})
        self.logger.info(f"Duration: {duration}", extra={'source': 'SYSTEM'})
        self.logger.info("=" * 60, extra={'source': 'SYSTEM'})
        
        # Log timings if any
        self.log_timings()
        
        # Close handlers
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)


class TimingContext:
    """Context manager for timing operations"""
    
    def __init__(self, logger: DevLogger, name: str):
        self.logger = logger
        self.name = name
    
    def __enter__(self):
        self.logger.start_timer(self.name)
        return self
    
    def __exit__(self, *args):
        self.logger.stop_timer(self.name)


class SourceFormatter(logging.Formatter):
    """Formatter that includes source location"""
    
    def format(self, record):
        if not hasattr(record, 'source'):
            record.source = 'unknown'
        return super().format(record)


class ConsoleFormatter(logging.Formatter):
    """Console formatter with colors and emojis"""
    
    COLORS = {
        logging.DEBUG: '\033[36m',
        logging.INFO: '\033[37m',
        25: '\033[32m',  # SUCCESS
        logging.WARNING: '\033[33m',
        logging.ERROR: '\033[31m',
        logging.CRITICAL: '\033[35m',
    }
    
    EMOJI = {
        logging.DEBUG: '🔍',
        logging.INFO: 'ℹ️ ',
        25: '✅',  # SUCCESS
        logging.WARNING: '⚠️ ',
        logging.ERROR: '❌',
        logging.CRITICAL: '🚨',
    }
    
    RESET = '\033[0m'
    
    def __init__(self, include_source: bool = True):
        super().__init__()
        self.include_source = include_source
    
    def format(self, record):
        emoji = self.EMOJI.get(record.levelno, '')
        source = getattr(record, 'source', '')
        
        if self.include_source and source and source != 'SYSTEM':
            return f"{emoji} [{source}] {record.getMessage()}"
        else:
            return f"{emoji} {record.getMessage()}"


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

# Global logger registry
_loggers: Dict[str, DevLogger] = {}


def get_logger(action_name: str, **kwargs) -> DevLogger:
    """Get or create a logger for an action"""
    if action_name not in _loggers:
        _loggers[action_name] = DevLogger(action_name, **kwargs)
    return _loggers[action_name]


def close_logger(action_name: str):
    """Close and remove a logger"""
    if action_name in _loggers:
        _loggers[action_name].close()
        del _loggers[action_name]


# Backward compatibility aliases
ActionLogger = DevLogger
init_logger = get_logger


def log_info(message: str):
    print(f"ℹ️  {message}")

def log_success(message: str):
    print(f"✅ {message}")

def log_warning(message: str):
    print(f"⚠️  {message}")

def log_error(message: str):
    print(f"❌ {message}")


# =============================================================================
# DECORATOR FOR TIMING
# =============================================================================

def timed(name: Optional[str] = None):
    """Decorator to time a function"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            timer_name = name or f"{func.__module__}.{func.__name__}"
            start = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start
            print(f"⏱️ {timer_name}: {duration:.2f}s")
            return result
        return wrapper
    return decorator
