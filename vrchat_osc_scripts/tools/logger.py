"""logging_setup

Python logging helper that provides colourised console output and daily‑rotated
log files written beneath a *logs/* directory next to the running process.

The call creates *logs/app.log* (overwriting nothing) and starts a new file at
local midnight each day while keeping all historical logs indefinitely. Console
output is colourised according to the message level.
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
    logging.CRITICAL: "\033[1;31m",  # bold (“dark”) red
    logging.ERROR: "\033[31m",  # red
    logging.WARNING: "\033[33m",  # yellow
    logging.INFO: "\033[37m",  # white
    logging.DEBUG: "\033[90m",  # grey
}


class ColourFormatter(logging.Formatter):
    """Formatter that adds ANSI colours *only* to the console handler.

    The log *record* is temporarily modified so that other handlers (for
    example the file handler) see pristine, plain‑text strings. This avoids
    polluting log files with escape codes while still achieving colourful CLI
    output.

    Parameters
    ----------
    fmt:
        Log message format string using the PEP 3101 ``{}`` style.
    datefmt:
        Datetime format string compatible with :pyfunc:`time.strftime`.
    style:
        The style indicator passed to :pyclass:`logging.Formatter`. Defaults
        to ``"{"``.
    """

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401  (imperative mood is fine)
        """Return the formatted message for *record* with colour adornment."""
        colour_escape: str = LEVEL_COLOURS.get(record.levelno, "")
        original_level_name: str = record.levelname
        original_message: str = record.getMessage()

        record.levelname = f"{colour_escape}{original_level_name}{RESET_ESCAPE}"
        record.msg = f"{colour_escape}{original_message}{RESET_ESCAPE}"

        try:
            return super().format(record)
        finally:
            # Restore the original values so subsequent handlers are unaffected.
            record.levelname = original_level_name
            record.msg = original_message


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------

def setup_logging(
    *,
    log_dir: str | Path = "logs",
    log_file_name: str = "app.log",
    level: int | str = logging.INFO,
) -> None:
    """Initialise a root logger with file + colourised console handlers.

    This function **must** be called exactly once, and *before* any modules in
    your application attempt to obtain loggers. Re‑invoking the function is
    harmless: existing handlers are removed and recreated so that hot‑reloading
    during development does not duplicate output.

    Parameters
    ----------
    log_dir:
        Directory where all log files are stored. It is created on demand.
    log_file_name:
        Base filename for the active log file (e.g. *app.log*). Rotated files
        are automatically suffixed with the date by
        :pyclass:`logging.handlers.TimedRotatingFileHandler`.
    level:
        Logging threshold. Accepts either the numeric level constant or its
        string equivalent ("DEBUG", "INFO", …).
    """
    root_logger: logging.Logger = logging.getLogger()

    # Pylint: calling basicConfig elsewhere can register a handler we need to
    # remove; iterate over a *copy* of the list to avoid mutation issues.
    for existing_handler in root_logger.handlers[:]:
        root_logger.removeHandler(existing_handler)

    root_logger.setLevel(level)

    # ---------------------------------------------------------------------
    # Ensure log directory exists
    # ---------------------------------------------------------------------
    resolved_log_dir: Path = Path(log_dir).resolve()
    resolved_log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path: Path = resolved_log_dir / log_file_name

    # ---------------------------------------------------------------------
    # Common formatter shared by both handlers (without colour)
    # ---------------------------------------------------------------------
    message_format: str = "{asctime}  {levelname:8} {name} – {message}"
    date_format: str = "%Y-%m-%d %H:%M:%S"

    plain_formatter = logging.Formatter(message_format, datefmt=date_format, style="{")

    # ---------------------------------------------------------------------
    # File handler – daily rotation at local midnight, unlimited retention
    # ---------------------------------------------------------------------
    file_handler = TimedRotatingFileHandler(
        filename=log_file_path,
        when="midnight",
        backupCount=0,  # Never delete old logs; each rotation renames the file
        encoding="utf-8",
        utc=False,  # Rotate based on local time
    )
    file_handler.setFormatter(plain_formatter)

    # ---------------------------------------------------------------------
    # Stream handler – colourised console output
    # ---------------------------------------------------------------------
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setFormatter(
        ColourFormatter(message_format, datefmt=date_format, style="{")
    )

    # ---------------------------------------------------------------------
    # Register handlers
    # ---------------------------------------------------------------------
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)
