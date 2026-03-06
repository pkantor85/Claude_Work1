"""
Pytest conftest — Make the project root importable.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add the project root to sys.path so that `from src.xxx` works in tests
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
