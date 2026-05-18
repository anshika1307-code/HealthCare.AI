"""
tests/integration/conftest.py
-------------------------------
Shared fixtures for integration tests.

Adds src/ and repo root to sys.path so all imports work when pytest is
invoked from the repo root.
"""

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
for p in (_ROOT / "src", _ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Clear the in-memory rate-limit counters before every integration test.

    Without this, rapid test execution exhausts the 20/minute per-IP quota
    and turns expected-200 responses into 429s.
    """
    from serving.api import _limiter

    _limiter._storage.reset()
    yield
    _limiter._storage.reset()
