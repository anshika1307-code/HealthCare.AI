"""
tests/unit/conftest.py
-----------------------
Shared pytest fixtures for unit tests.
"""

import sys
from pathlib import Path

# Ensure src/ is importable when running pytest from repo root
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
