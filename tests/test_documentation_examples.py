"""Regression tests for public GR(1) onboarding documentation."""

from importlib import util
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


def load_module(name: str, relative: str):
    """Load a repository script without modifying the import path."""
    spec = util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None
    assert spec.loader is not None
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("relative", ["README.md", "docs/gr1-contracts.md"])
def test_markdown_python_blocks_execute(relative):
    """Protect imports, signatures, and semantic assertions shown to users."""
    checker = load_module("check_docs", "scripts/check_docs.py")
    path = ROOT / relative
    checker.check_local_markdown_links(path)
    checker.execute_markdown_snippets(path)


def test_quickstart_executes_meaningful_workflow():
    """Protect refinement, merge, composition, quotient, and round trip."""
    quickstart = load_module("gr1_quickstart", "examples/gr1_quickstart.py")
    quickstart.main()


def test_aeb_no_report_mode_avoids_output_file(monkeypatch):
    """Keep the documented AEB onboarding command side-effect free."""
    aeb = load_module("aeb_gr1_documentation", "examples/aeb_gr1_composition.py")
    called = []
    monkeypatch.setattr(aeb, "run_audit", lambda: called.append(True))
    monkeypatch.setattr(
        aeb.Path,
        "open",
        lambda *args, **kwargs: pytest.fail("--no-report must not open a report file"),
    )
    aeb.main(["--no-report"])
    assert called == [True]
