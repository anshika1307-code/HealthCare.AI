"""
tests/integration/conftest.py
-------------------------------
Shared fixtures for integration tests.

Adds src/ and repo root to sys.path so all imports work when pytest is
invoked from the repo root.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for p in (_ROOT / "src", _ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
