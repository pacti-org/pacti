"""
ISC License

Copyright (c) 2019, Timothée Mazzucotelli

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""

import glob
import importlib
import os
import pathlib
import re
import ssl
import sys
from io import StringIO
from pathlib import Path
from typing import List, Optional, Pattern
from urllib.request import urlopen
import shutil

ssl._create_default_https_context = ssl._create_unverified_context

from duty import duty

DIR_SEARCH = ["src", "tests"]
PY_SRC_PATHS = (Path(_) for _ in DIR_SEARCH)
PY_SRC_LIST = tuple(str(_) for _ in PY_SRC_PATHS)
PY_SRC = " ".join(PY_SRC_LIST)
JN_DIR_SEARCH = ["src", "tests", "docs"]
JNB_SRC = " ".join([el for src in JN_DIR_SEARCH for el in glob.glob(src+"/**/*.ipynb", recursive=True)])
TESTING = os.environ.get("TESTING", "0") in {"1", "true"}
CI = os.environ.get("CI", "0") in {"1", "true", "yes", ""}
WINDOWS = os.name == "nt"
PTY = not WINDOWS and not CI
MYPY_FLAGS = "--allow-any-generics --implicit-reexport --allow-untyped-calls"
FLAKE8_FLAGS_JN = "--ignore=D100,WPS226,WPS421,WPS111,BLK100,E402,WPS331,WPS221,WPS231,N806,WPS114,D212"

sys.stdin.reconfigure(encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')

#FLAKE8_FLAGS_JN = ""

#sys.stdin.reconfigure(encoding='utf-8')
#sys.stdout.reconfigure(encoding='utf-8')

def update_changelog(
    inplace_file: str,
    marker: str,
    version_regex: str,
    template: str="keepachangelog",
    convention="basic"
) -> None:
    """
    Update the given changelog file in place.

    Arguments:
        inplace_file: The file to update in-place.
        marker: The line after which to insert new contents.
        version_regex: A regular expression to find currently documented versions in the file.
        template_url: The URL to the Jinja template used to render contents.
    """
    from git_changelog.cli import build_and_render
    build_and_render(
        repository=".",
        output=inplace_file,
        convention=convention,
        template=template,
        parse_trailers=True,
        parse_refs=False,
        bump_latest=False,
        in_place=True,
        marker_line=marker,
        version_regex=version_regex,
    )


@duty
def changelog(ctx):
    """
    Update the changelog in-place with latest commits.

    Arguments:
        ctx: The context instance (passed automatically).
    """
    ctx.run(
        update_changelog,
        kwargs={
            "inplace_file": "CHANGELOG.md",
            "marker": "<!-- insertion marker -->",
            "version_regex": r"^## \[v?(?P<version>[^\]]+)",
        },
        title="Updating changelog",
        pty=PTY,
    )


@duty(pre=["check_quality", "check_types", "check_dependencies"])
def check(ctx):
    """
    Check it all!

    Arguments:
        ctx: The context instance (passed automatically).
    """


@duty
def check_quality(ctx, files=PY_SRC):
    """
    Check the code quality.

    Arguments:
        ctx: The context instance (passed automatically).
        files: The files to check.
    """
    """Latest Flake8 cause problems with dependencies. Suppress for now."""
    ctx.run(f"flake8 --config=config/flake8.ini {files}", title="Checking code quality", pty=PTY)

@duty  # noqa: WPS231
def check_jn_quality(ctx):  # noqa: WPS231
    """
    Check notebook quality.

    Arguments:
        ctx: The context instance (passed automatically).
        files: The files to check.
    """
    """Latest Flake8 cause problems with dependencies. Suppress for now."""
    ctx.run(f"nbqa flake8 {FLAKE8_FLAGS_JN} --config=config/flake8.ini {JNB_SRC}", title="Checking notebook quality", pty=PTY)

@duty
def tox(ctx):
    """
    Run tox

    Arguments:
        ctx: The context instance (passed automatically).
    """
    ctx.run(f"tox --workdir . --root . -c config/tox.ini", title="Testing over platforms", pty=PTY, capture=False)


@duty
def check_dependencies(ctx):
    """
    Check for vulnerabilities in dependencies.

    Arguments:
        ctx: The context instance (passed automatically).
    """
    # undo possible patching
    # see https://github.com/pyupio/safety/issues/348
    for module in sys.modules:  # noqa: WPS528
        if module.startswith("safety.") or module == "safety":
            del sys.modules[module]  # noqa: WPS420

    importlib.invalidate_caches()

    # reload original, unpatched safety
    from safety.formatter import SafetyFormatter
    from safety.safety import calculate_remediations
    from safety.safety import check as safety_check
    from safety.util import read_requirements

    # retrieve the list of dependencies
    requirements = ctx.run(
        ["pdm", "export", "-f", "requirements", "--without-hashes"],
        title="Exporting dependencies as requirements",
        allow_overrides=False,
    )

    # check using safety as a library
    def safety():  # noqa: WPS430
        packages = list(read_requirements(StringIO(requirements)))
        vulns, db_full = safety_check(packages=packages, ignore_vulns="")
        remediations = calculate_remediations(vulns, db_full)
        output_report = SafetyFormatter("text").render_vulnerabilities(
            announcements=[],
            vulnerabilities=vulns,
            remediations=remediations,
            full=True,
            packages=packages,
        )
        if vulns:
            print(output_report)
            return False
        return True

    ctx.run(safety, title="Checking dependencies")




@duty  # noqa: WPS231
def check_types(ctx):  # noqa: WPS231
    """
    Check that the code is correctly typed.

    Arguments:
        ctx: The context instance (passed automatically).
    """
    ctx.run(f"mypy --strict {MYPY_FLAGS} --config-file=config/mypy.ini {PY_SRC}", title="Type-checking", pty=PTY)


@duty  # noqa: WPS231
def check_jn_types(ctx):  # noqa: WPS231
    """
    Check that notebooks are correctly typed.

    Arguments:
        ctx: The context instance (passed automatically).
    """
    ctx.run(f"nbqa mypy --strict {MYPY_FLAGS} --config-file=config/mypy.ini {JNB_SRC}", title="Type checking notebooks", pty=PTY)


@duty(silent=True)
def clean(ctx):
    """
    Delete temporary files.

    Arguments:
        ctx: The context instance (passed automatically).
    """
    shutil.rmtree(".coverage*",ignore_errors=True)
    shutil.rmtree(".mypy_cache",ignore_errors=True)
    shutil.rmtree(".pytest_cache",ignore_errors=True)
    shutil.rmtree("tests/.pytest_cache",ignore_errors=True)
    shutil.rmtree("build",ignore_errors=True)
    shutil.rmtree("dist",ignore_errors=True)
    shutil.rmtree("htmlcov",ignore_errors=True)
    shutil.rmtree("pip-wheel-metadata",ignore_errors=True)
    shutil.rmtree("site",ignore_errors=True)
    shutil.rmtree("__pycache__",ignore_errors=True)
    shutil.rmtree(".venv",ignore_errors=True)



@duty
def format(ctx):
    """
    Run formatting tools on the code.

    Arguments:
        ctx: The context instance (passed automatically).
    """
    ctx.run(
        f"autoflake -ir --exclude tests/fixtures --ignore-init-module-imports --remove-all-unused-imports {PY_SRC}",
        title="Removing unused imports",
        pty=PTY,
    )
    ctx.run(f"isort {PY_SRC}", title="Ordering imports", pty=PTY)
    ctx.run(f"black {PY_SRC}", title="Formatting code", pty=PTY)
    ############
    ctx.run(
        f"nbqa autoflake -ir --ignore-init-module-imports --remove-all-unused-imports {PY_SRC}",
        title="Removing unused imports",
        pty=PTY,
    )
    ctx.run(f"nbqa isort {PY_SRC}", title="Ordering imports", pty=PTY)
    ctx.run(f"nbqa black {PY_SRC}", title="Formatting code", pty=PTY)


@duty
def release(ctx, version):
    """
    Release a new Python package.

    Arguments:
        ctx: The context instance (passed automatically).
        version: The new version number to use.
    """
    ctx.run("git add pyproject.toml CHANGELOG.md", title="Staging files", pty=PTY)
    ctx.run(["git", "commit", "-m", f"chore: Prepare release {version}"], title="Committing changes", pty=PTY)
    ctx.run(f"git tag {version}", title="Tagging commit", pty=PTY)
    if not TESTING:
        ctx.run("git push", title="Pushing commits", pty=False)
        ctx.run("git push --tags", title="Pushing tags", pty=False)
        ctx.run("pdm build", title="Building dist/wheel", pty=PTY)
        ctx.run("twine upload --skip-existing dist/*", title="Publishing version", pty=PTY)


@duty(silent=True)
def coverage(ctx):
    """
    Report coverage as text and HTML.

    Arguments:
        ctx: The context instance (passed automatically).
    """
    ctx.run("coverage combine", nofail=True)
    ctx.run("coverage report --rcfile=config/coverage.ini", capture=False)
    ctx.run("coverage xml --rcfile=config/coverage.ini")
    ctx.run("coverage html --rcfile=config/coverage.ini")


@duty
def test(ctx, match: str = ""):
    """
    Run the test suite.

    Arguments:
        ctx: The context instance (passed automatically).
        match: A pytest expression to filter selected tests.
    """
    py_version = f"{sys.version_info.major}{sys.version_info.minor}"
    os.environ["COVERAGE_FILE"] = f".coverage.{py_version}"
    ctx.run(
        ["pytest", "-c", "config/pytest.ini", "-n", "auto", "-k", match, "tests"],
        title="Running tests",
        pty=PTY,
    )
