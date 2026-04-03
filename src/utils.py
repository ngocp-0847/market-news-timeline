"""Utility functions for Market News Timeline."""

import os
import yaml
from pathlib import Path
from datetime import datetime
import pytz


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def load_config(config_path: str = None) -> dict:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = get_project_root() / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dirs():
    """Ensure data and output directories exist."""
    root = get_project_root()
    (root / "data").mkdir(exist_ok=True)
    (root / "output").mkdir(exist_ok=True)


def now_vietnam() -> datetime:
    """Get current time in Vietnam timezone."""
    tz = pytz.timezone("Asia/Ho_Chi_Minh")
    return datetime.now(tz)


def truncate_text(text: str, max_len: int = 80) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
