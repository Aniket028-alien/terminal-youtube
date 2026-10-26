"""Tunable settings and shared paths."""

from __future__ import annotations

import logging
from pathlib import Path

# ---------------- Search / loading ----------------

INITIAL_RESULTS = 20
RESULTS_INCREMENT = 20
SCROLL_LOAD_MARGIN = 8   # load more when this close to the bottom (in rows)

# ---------------- Grid layout ----------------

MIN_CARD_WIDTH = 34      # cards never get narrower than this (in cells)
MAX_COLUMNS = 8
GRID_GUTTER = 1

TEXT_ROWS = 3            # 2 title lines + 1 channel line
CARD_CHROME = 4          # border (2) + vertical padding (2)
CELL_ASPECT = 2.0        # terminal cell height / width, roughly

# ---------------- Playback ----------------

QUALITIES = [144, 240, 360, 480, 720, 1080, 1440, 2160]
DEFAULT_QUALITY = 1080
SPEED_STEP = 0.25
MIN_SPEED = 0.25
MAX_SPEED = 4.0

# ---------------- Paths ----------------

APP_CACHE_DIR = Path.home() / ".cache" / "terminal-youtube"
CACHE_DIR = APP_CACHE_DIR / "thumbnails"
LOG_FILE = APP_CACHE_DIR / "app.log"


def setup_logging() -> None:
    """Create cache directories and send warnings/errors to the log file."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=str(LOG_FILE), level=logging.WARNING)
