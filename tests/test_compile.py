"""
Tests for compiling WFSTs from input tables.
"""

from pathlib import Path
from flair_fst.compile import Definition
from flair_fst.compile.odf import load_definition

import pytest

TESTDIR = Path(__file__).parent / "data"


@pytest.fixture
def defn() -> Definition:
    return load_definition(TESTDIR / "example.ods")


def test_load_ods(defn) -> None:
    """Test basic loading from ODS."""
    assert defn.stems


def test_approx(defn) -> None:
    """Test building approximate matching table."""
    from flair_fst.compile.approx import make_approx

    approx = make_approx(defn.spelling)
    assert ("ça", 1.0) in approx.generate("sa", weights=True)
    assert ("œuf", 0.0) in approx.generate("oeuf", weights=True)


def test_lexicon(defn) -> None:
    """Test RLG lexicon construction from tables."""
    from flair_fst.compile.lexicon import make_rlg, make_lexicon
    from flair_fst import pairs

    print(defn.stems)
    print(make_rlg(defn))
    fsg = make_lexicon(defn)
    for up, down in pairs(fsg):
        print(up, down)


def test_rules(defn) -> None:
    """Test rule construction from tables."""
    from flair_fst.compile.rules import make_rules

    print(defn.rules)
    rules = make_rules(defn)
    assert list(rules["nostem"].apply("mang-")) == []
    assert list(rules["deldash"].apply("mang-+ons")) == ["mang+ons"]
    assert list(rules["gspell"].apply("mang+ons")) == ["mange+ons"]
    assert list(rules["delmorph"].apply("mange+ons")) == ["mangeons"]


def test_glossary(defn) -> None:
    """Test construction of glossary from, uh, glosses."""
    from flair_fst.compile.glossary import make_glossary

    glossary = make_glossary(defn)
    print(glossary)


def test_bibliography(defn) -> None:
    """Test construction of bibliography."""
    from flair_fst.compile.bibliography import make_bibliography

    bibliography = make_bibliography(defn)
    print(bibliography)
