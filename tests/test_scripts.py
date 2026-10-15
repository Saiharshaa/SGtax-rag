"""The scripts aren't imported by other tests, so at least check that each one compiles."""

import py_compile
from pathlib import Path

import pytest

SCRIPTS = sorted((Path(__file__).resolve().parent.parent / "scripts").glob("*.py"))


@pytest.mark.parametrize("script", SCRIPTS, ids=[script.name for script in SCRIPTS])
def test_script_compiles(script, tmp_path):
    py_compile.compile(str(script), cfile=str(tmp_path / "out.pyc"), doraise=True)
