"""
Tests for compiling WFSTs from input tables.
"""

from pathlib import Path
from flair_fst.compile.odf import load_definition

TESTDIR = Path(__file__).parent / "data"


def test_load_ods() -> None:
    defn = load_definition(TESTDIR / "example.ods")
    assert defn.words
