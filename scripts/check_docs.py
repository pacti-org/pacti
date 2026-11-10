"""Execute public documentation, maintained examples, and notebook code."""

from __future__ import annotations

import json
from pathlib import Path
import re
import runpy
import subprocess  # noqa: S404
import sys

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_FILES = (ROOT / "README.md", ROOT / "docs/gr1-contracts.md")
NOTEBOOKS = (
    "docs/getting_started.ipynb",
    "examples/Quotient gives feedback amplifier.ipynb",
)


def execute_markdown_snippets(path: Path) -> None:
    """Execute each standalone Python block from a Markdown document."""
    snippets = re.findall(r"```python\n(.*?)```", path.read_text(encoding="utf-8"), re.S)
    for index, snippet in enumerate(snippets, start=1):
        exec(compile(snippet, f"{path}:python-block-{index}", "exec"), {})  # noqa: S102
    print(f"PASS: {path.relative_to(ROOT)} ({len(snippets)} Python blocks)")


def check_local_markdown_links(path: Path) -> None:
    """Require every repository-relative Markdown link target to exist."""
    for raw_target in re.findall(r"\[[^]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
        target = raw_target.split("#", maxsplit=1)[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"broken local link in {path}: {raw_target}")


def execute_notebook(relative: str) -> None:
    """Execute a notebook's code cells in order without rewriting outputs."""
    path = ROOT / relative
    namespace = {"__name__": "__main__"}
    notebook = json.loads(path.read_text(encoding="utf-8"))
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            source = "".join(cell["source"])
            exec(compile(source, f"{relative}:cell{index}", "exec"), namespace)  # noqa: S102
    print(f"PASS: {relative}")


def execute_examples() -> None:
    """Run maintained tutorial and operation examples in fresh namespaces."""
    for relative in ("examples/gr1_quickstart.py", "examples/gr1_contract_operations.py"):
        runpy.run_path(str(ROOT / relative), run_name="__main__")
        print(f"PASS: {relative}")

    subprocess.run(  # noqa: S603
        [sys.executable, str(ROOT / "examples/aeb_gr1_composition.py"), "--no-report"],  # noqa: S603
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        timeout=5 * 60,
    )
    print("PASS: examples/aeb_gr1_composition.py --no-report")


def main() -> None:
    """Run every executable-documentation regression."""
    for path in MARKDOWN_FILES:
        check_local_markdown_links(path)
        execute_markdown_snippets(path)
    execute_examples()
    for relative in NOTEBOOKS:
        execute_notebook(relative)


if __name__ == "__main__":
    main()
