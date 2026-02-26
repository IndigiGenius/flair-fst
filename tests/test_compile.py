"""
Tests for compiling WFSTs from input tables.
"""

from pathlib import Path
from flair_fst.compile.odf import load_definition
from flair_fst.compile.approx import make_approx

TESTDIR = Path(__file__).parent / "data"


def test_load_ods() -> None:
    """Test basic loading from ODS."""
    defn = load_definition(TESTDIR / "example.ods")
    assert defn.words


def test_approx() -> None:
    """Test building approximate matching table."""
    defn = load_definition(TESTDIR / "example.ods")
    approx = make_approx(defn.spelling)
    assert ("ça", 1.0) in approx.generate("sa", weights=True)
    assert ("œuf", 0.0) in approx.generate("oeuf", weights=True)
