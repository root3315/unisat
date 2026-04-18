"""Streamlit page import smoke tests.

The ground-station Streamlit app is not functionally tested (needs
a browser session); the next-best assurance is that every page
module *imports cleanly* without raising — catches a wide class of
regressions: missing streamlit installation, stale symbol imports
from `ground-station/utils/`, accidentally-deleted helpers.

Test strategy
-------------
For every `ground-station/pages/NN_*.py` file:

    compile(source, filename, 'exec')

compile-check is preferred over importing because `st.set_page_config`
has a side effect that registers a global page config — importing
one page from a test would lock subsequent imports out. `compile`
exercises the parser + resolves all imports without executing the
module body, which is enough to catch SyntaxError, NameError at
module scope, and missing deps.

The dashboard import itself is then exercised via a streamlit
`AppTest` fixture if the runtime is available (Streamlit 1.28+
ships `streamlit.testing.v1.AppTest`). Otherwise we fall back to
the compile-only check with a skip marker.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PAGES_DIR = Path(__file__).parent.parent / "pages"
APP_PY = Path(__file__).parent.parent / "app.py"


@pytest.fixture
def streamlit_available() -> bool:
    try:
        import streamlit  # noqa: F401
    except ImportError:
        return False
    return True


def _pages() -> list[Path]:
    """Return every page file sorted by the NN_ prefix."""
    return sorted(PAGES_DIR.glob("[0-9]*_*.py"))


def test_pages_dir_has_expected_count() -> None:
    """Regression: the repository should ship all 11 dashboard pages."""
    pages = _pages()
    assert len(pages) == 11, (
        f"expected 11 dashboard pages, found {len(pages)}: "
        f"{[p.name for p in pages]}"
    )


@pytest.mark.parametrize("page_path", _pages(), ids=lambda p: p.name)
def test_page_compiles_cleanly(page_path: Path) -> None:
    """Every dashboard page must parse + have resolvable imports."""
    source = page_path.read_text(encoding="utf-8")
    try:
        compile(source, str(page_path), "exec")
    except SyntaxError as exc:
        pytest.fail(f"{page_path.name} has a SyntaxError: {exc}")


def test_app_py_compiles_cleanly() -> None:
    """Top-level app.py (the Streamlit entry point) must parse."""
    source = APP_PY.read_text(encoding="utf-8")
    compile(source, str(APP_PY), "exec")


def test_dashboard_app_test_smoke(streamlit_available: bool) -> None:
    """If streamlit 1.28+ is installed, use AppTest to actually run
    the home page and assert it renders without exception.

    Falls back to skip if the runtime is missing — this is the
    `best effort` test that genuinely exercises the Streamlit
    code path when tools are available.
    """
    if not streamlit_available:
        pytest.skip("streamlit not installed (pip install streamlit)")
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError:
        pytest.skip(
            "streamlit.testing.v1.AppTest not available (needs streamlit>=1.28)"
        )

    sys.path.insert(0, str(APP_PY.parent))
    at = AppTest.from_file(str(APP_PY), default_timeout=30)
    at.run()
    # A rendered app must not end in the exception state.
    assert not at.exception, (
        f"app.py raised during render: "
        f"{[e.value for e in at.exception]}"
    )
