"""logging_setup

Python logging helper that provides colourised console output and daily‑rotated
log files written beneath a *logs/* directory next to the running process.
"""

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Final

__all__: Final[list[str]] = [
    "setup_logging",
    "ColourFormatter",
]

# ---------------------------------------------------------------------------
# ANSI colour escapes used for terminal output
# ---------------------------------------------------------------------------
RESET_ESCAPE: Final = "\033[0m"
LEVEL_COLOURS: Final[dict[int, str]] = {
    logging.CRITICAL: "\033[1;31m",
    logging.ERROR: "\033[31m",
    logging.WARNING: "\033[33m",
    logging.INFO: "\033[37m",
    logging.DEBUG: "\033[90m",
}


class ColourFormatter(logging.Formatter):
    """Formatter that adds ANSI colours *only* to the console handler."""

    def format(self, record: logging.LogRecord) -> str:
        """Return the formatted message for *record* with colour adornment."""
        colour_escape = LEVEL_COLOURS.get(record.levelno, "")
        original_level_name = record.levelname
        original_msg = record.getMessage()

        record.levelname = f"{colour_escape}{original_level_name}{RESET_ESCAPE}"
        record.msg = f"{colour_escape}{original_msg}{RESET_ESCAPE}"

        try:
            return super().format(record)
        finally:
            record.levelname = original_level_name
            record.msg = original_msg


def setup_logging(
    log_dir: str | Path = "logs",
    log_file_name: str = "app.log",
    level: int | str = logging.INFO,
) -> None:
    """Initialise root logger with file + colourised console handlers."""

    root_logger = logging.getLogger()

    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    root_logger.setLevel(level)

    # Ensure logs directory exists
    resolved_log_dir = Path(log_dir).resolve()
    resolved_log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = resolved_log_dir / log_file_name

    # Logging format strings (old style)
    log_format = "%(asctime)s %(levelname)-8s %(name)s – %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    plain_formatter = logging.Formatter(log_format, datefmt=date_format)

    # File handler
    file_handler = TimedRotatingFileHandler(
        filename=log_file_path,
        when="midnight",
        backupCount=0,
        encoding="utf-8",
        utc=False,
    )
    file_handler.setFormatter(plain_formatter)

    # Console handler with colour
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setFormatter(ColourFormatter(log_format, datefmt=date_format))

    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)
