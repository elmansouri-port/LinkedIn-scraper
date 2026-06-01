"""
Centralized logging module for LinkedIn Scraper.

Provides clean, consistent logging across CLI, API, and all services.
"""
import logging
import sys
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler

# Custom SUCCESS level (between INFO and WARNING)
SUCCESS_LEVEL = 25
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")


def _success(self, message, *args, **kwargs):
    if self.isEnabledFor(SUCCESS_LEVEL):
        self._log(SUCCESS_LEVEL, message, args, **kwargs)

logging.Logger.success = _success


def _setup_logger(
    name: str,
    level: str = "INFO",
    console: bool = True,
    file_output: bool = True,
    log_dir: str = "data/logs",
    log_file: Optional[str] = None,
) -> logging.Logger:
    """Create and configure a logger.

    Args:
        name: Logger name (typically module or action name)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console: Enable console output
        file_output: Enable file output
        log_dir: Directory for log files
        log_file: Specific log filename (None for auto-generated)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    logger.propagate = False

    numeric_level = logger.level

    # Console handler - clean, readable format
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(_ConsoleFormatter())
        logger.addHandler(console_handler)

    # File handler - detailed format for debugging
    if file_output:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        if log_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"{name}_{timestamp}.log"

        file_handler = RotatingFileHandler(
            log_path / log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(_FileFormatter())
        logger.addHandler(file_handler)

    return logger


class _ConsoleFormatter(logging.Formatter):
    """Clean console formatter with level-based coloring."""

    _LEVEL_COLORS = {
        logging.DEBUG: "\033[36m",      # Cyan
        logging.INFO: "\033[37m",       # White
        SUCCESS_LEVEL: "\033[32m",      # Green
        logging.WARNING: "\033[33m",    # Yellow
        logging.ERROR: "\033[31m",      # Red
        logging.CRITICAL: "\033[1;31m", # Bold Red
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        time_str = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        color = self._LEVEL_COLORS.get(record.levelno, "")
        level_name = record.levelname

        # Truncate long level names for alignment
        level_display = f"{level_name:<8}"

        msg = f"{color}[{time_str}] {level_display}{self._RESET} {record.getMessage()}"
        return msg


class _FileFormatter(logging.Formatter):
    """Detailed formatter for log files."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


# ---------------------------------------------------------------------------
# Module-level logger registry
# ---------------------------------------------------------------------------
_loggers: Dict[str, logging.Logger] = {}
_initialized = False
_default_level: str = "INFO"
_default_console: bool = True
_default_file: bool = True
_default_log_dir: str = "data/logs"


def init_logging(
    level: str = "INFO",
    console: bool = True,
    file_output: bool = True,
    log_dir: str = "data/logs",
) -> None:
    """Initialize the logging system. Call once at application startup.

    Args:
        level: Default log level
        console: Enable console output for all loggers
        file_output: Enable file output for all loggers
        log_dir: Directory for log files
    """
    global _initialized, _default_level, _default_console, _default_file, _default_log_dir
    if _initialized:
        return

    _default_level = level.upper()
    _default_console = console
    _default_file = file_output
    _default_log_dir = log_dir
    os.makedirs(log_dir, exist_ok=True)
    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger using the defaults set by init_logging().

    Args:
        name: Logger name (e.g., "scraper.group", "api.connections")

    Returns:
        Configured logger instance
    """
    if name not in _loggers:
        _loggers[name] = _setup_logger(
            name,
            level=_default_level,
            console=_default_console,
            file_output=_default_file,
            log_dir=_default_log_dir,
        )
    return _loggers[name]


def get_logger_with_file(name: str, log_file: str) -> logging.Logger:
    """Get or create a logger with a specific log file.

    Args:
        name: Logger name
        log_file: Specific log filename

    Returns:
        Configured logger instance
    """
    if name not in _loggers:
        _loggers[name] = _setup_logger(name, log_file=log_file)
    return _loggers[name]


def close_logger(name: str) -> None:
    """Close and remove a logger.

    Args:
        name: Logger name
    """
    if name in _loggers:
        logger = _loggers.pop(name)
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)


# ---------------------------------------------------------------------------
# Session State Manager (separate from logging)
# ---------------------------------------------------------------------------

class SessionState:
    """Manages session state for resume functionality."""

    def __init__(self, action_name: str, state_dir: str = "data/sessions"):
        self.action_name = action_name
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / f"{action_name}_state.json"
        self.state: Dict[str, Any] = {}

    def save(self, **kwargs) -> None:
        """Save session state to JSON."""
        self.state.update(kwargs)
        self.state["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.state["action_name"] = self.action_name

        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            get_logger("session").error(f"Could not save session state: {e}")

    def load(self) -> Optional[Dict[str, Any]]:
        """Load session state from JSON."""
        if not self.state_file.exists():
            return None
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                self.state = json.load(f)
                return self.state
        except Exception:
            return None

    def exists(self) -> bool:
        return self.state_file.exists()

    def get_summary(self) -> str:
        if not self.exists():
            return "No saved session"
        state = self.load()
        if not state:
            return "No saved session"
        lines = [f"Saved session from {state.get('last_updated', 'unknown')}:"]
        for key, value in state.items():
            if key not in ("last_updated", "action_name"):
                if isinstance(value, list):
                    lines.append(f"  - {key}: {len(value)} items")
                else:
                    lines.append(f"  - {key}: {value}")
        return "\n".join(lines)

    def clear(self) -> None:
        if self.state_file.exists():
            os.remove(self.state_file)
            self.state = {}

    def ask_resume(self) -> bool:
        """Ask user if they want to resume or start over."""
        if not self.exists():
            return False

        print("\n" + "=" * 50)
        print("PREVIOUS SESSION FOUND")
        print("=" * 50)
        print(self.get_summary())
        print("-" * 50)

        try:
            choice = input("Resume previous session? (y/n) [y]: ").strip().lower()
        except EOFError:
            choice = "y"

        if choice == "n":
            self.clear()
            print("Previous session cleared. Starting fresh.")
            return False
        else:
            print("Resuming previous session...")
            return True
