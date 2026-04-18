"""Test configuration and shared fixtures for flight software tests.

Bootstrap sequence run at import time:

  1. Make flight-software/ importable without a package install.
  2. Install lightweight stubs for optional HW / vendor libraries
     (sgp4, aiofiles, serial, PIL) so tests do not ImportError on
     a bare CI image. The real library is preferred if already
     importable; the stub only fills in missing symbols.

Adding a new optional dependency
--------------------------------
If a flight-software module grows a new `import <lib>` line that
should be optional in tests, extend `_OPTIONAL_STUBS` below. Each
entry says: "if <lib> cannot be imported, install a minimal fake
module exposing <symbols> so imports succeed and test fixtures
can inject their own values."
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from typing import Any

import pytest

# --- 1. path bootstrap -----------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))


# --- 2. optional-dep stubs -------------------------------------------------
#
# Format: module name -> dict of (attribute, value-or-callable).
# value-or-callable: if callable, it's invoked with no args to
# produce the value lazily (e.g. a small class).
#
def _make_sgp4_stub() -> types.ModuleType:
    """Minimal sgp4.api.Satrec stand-in that returns (0, r, v) for any
    jd/fr pair. Enough to satisfy orbit_predictor imports."""
    mod = types.ModuleType("sgp4.api")
    class Satrec:  # noqa: N801  (match upstream PascalCase)
        @classmethod
        def twoline2rv(cls, line1: str, line2: str) -> "Satrec":
            return cls()
        def sgp4(self, jd: float, fr: float) -> tuple[int, tuple[float, float, float], tuple[float, float, float]]:
            return 0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    mod.Satrec = Satrec
    mod.jday = lambda y, m, d, h, mi, s: (0.0, 0.0)
    return mod


def _make_aiofiles_stub() -> types.ModuleType:
    """Minimal aiofiles stub — only the `.open` coroutine is used."""
    mod = types.ModuleType("aiofiles")

    class _FakeAsyncFile:
        def __init__(self, path: str, mode: str) -> None:
            self._path = path
            self._mode = mode
        async def __aenter__(self) -> "_FakeAsyncFile":
            return self
        async def __aexit__(self, *exc: Any) -> None:
            pass
        async def write(self, data: Any) -> None:
            pass
        async def read(self) -> str:
            return ""
        async def close(self) -> None:
            pass

    def _open(path: str, mode: str = "r") -> _FakeAsyncFile:
        return _FakeAsyncFile(path, mode)

    mod.open = _open
    return mod


def _install_stubs() -> None:
    """Install stubs for optional libraries missing from this
    environment. Real library takes priority."""
    installers: dict[str, Any] = {
        "sgp4.api": _make_sgp4_stub,
        "aiofiles": _make_aiofiles_stub,
    }

    for modname, factory in installers.items():
        try:
            importlib.import_module(modname)
        except ImportError:
            stub = factory()
            sys.modules[modname] = stub
            # If the stub is a submodule (e.g. "sgp4.api"), register
            # the parent package skeleton too so `from sgp4.api import`
            # resolves.
            parent, _, _ = modname.rpartition(".")
            if parent and parent not in sys.modules:
                sys.modules[parent] = types.ModuleType(parent)


_install_stubs()


# --- 3. common fixtures ----------------------------------------------------

@pytest.fixture
def sample_config() -> dict[str, Any]:
    """Minimal mission config for testing."""
    return {
        "mission": {"name": "UniSat-Test", "version": "0.1.0"},
        "orbit": {"altitude_km": 550, "inclination_deg": 97.6, "type": "SSO"},
        "subsystems": {
            "obc": {"enabled": True},
            "eps": {"enabled": True, "solar_panels": 6, "panel_efficiency": 0.295},
            "comm": {"enabled": True},
            "adcs": {"enabled": True},
            "gnss": {"enabled": True},
            "camera": {"enabled": False},
            "payload": {"enabled": True, "type": "radiation_monitor"},
        },
    }
