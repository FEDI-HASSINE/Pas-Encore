"""Pytest configuration.

Ensures the project root is added to sys.path so tests and scripts can
import from `src` without setting PYTHONPATH manually.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))