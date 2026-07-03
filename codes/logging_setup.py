# codes/logging_setup.py
"""
Centralized logging setup for PAINDICATOR.

All modules should obtain their logger through get_logger(__name__) so that
every log line ends up in a single file (paindicator_debug.log in the working
directory) with a consistent format.

This module is idempotent: calling setup_logging() multiple times (or after
another module already called logging.basicConfig, e.g. renderer_scene.py)
does not duplicate handlers.
"""

import logging
import os

LOG_FILENAME = "paindicator_debug.log"

_configured = False


def setup_logging(level: int = logging.DEBUG) -> None:
    """
    Configure the root logger to write to paindicator_debug.log.
    Safe to call multiple times — only the first call installs handlers.
    """
    global _configured
    if _configured:
        return

    root = logging.getLogger()

    # If another module (e.g. renderer_scene) already installed a handler via
    # basicConfig, do not add a second file handler for the same file.
    log_path = os.path.join(os.getcwd(), LOG_FILENAME)
    already_has_file_handler = any(
        isinstance(h, logging.FileHandler)
        and getattr(h, "baseFilename", None) == os.path.abspath(log_path)
        for h in root.handlers
    )

    if not already_has_file_handler:
        try:
            handler = logging.FileHandler(log_path, encoding="utf-8")
            handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            ))
            root.addHandler(handler)
        except OSError:
            # Working directory not writable (rare) — fall back to console only.
            pass

    root.setLevel(level)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger, ensuring logging is configured first."""
    setup_logging()
    return logging.getLogger(name)
