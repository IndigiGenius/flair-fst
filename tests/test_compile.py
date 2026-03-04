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


def test_load_csv(defn) -> None:
    """Test loading from CSVs."""
    from flair_fst.compile.csv import load_definition as load_csv_definition

    csv_defn = load_csv_definition(TESTDIR / "example-csv")
    assert csv_defn == defn


def test_load_ods(defn) -> None:
    """Test basic loading from ODS."""
    assert defn.stems


def test_approx(defn) -> None:
    """Test building approximate matching table."""
    from flair_fst.compile.approx import make_approx

    approx = make_approx(defn)
    assert ("ça", 1.0) in approx.generate("sa", weights=True)
    assert ("œuf", 0.0) in approx.generate("oeuf", weights=True)


def test_lexicon(defn) -> None:
    """Test RLG lexicon construction from tables."""
    from flair_fst.compile.lexicon import make_rlg, make_lexicon
    from flair_fst.fst import pairs

    rlg = make_rlg(defn)
    print(rlg)
    assert "START" in rlg
    assert "words" in rlg
    assert "stems" in rlg
    fsg = make_lexicon(defn)
    assert list(fsg.apply("démarche")) == ["démarche"]
    assert list(fsg.apply("manger+1pl")) == ["mang-+ons"]
    # Make sure flags work
    assert list(fsg.apply("dé-gagner+1sg")) == []


def test_rules(defn) -> None:
    """Test rule construction from tables."""
    from flair_fst.compile.rules import make_rules

    rules = make_rules(defn)
    assert list(rules["nostem"].apply("mang-")) == []
    assert list(rules["deldash"].apply("mang-+ons")) == ["mang+ons"]
    assert list(rules["gspell"].apply("mang+ons")) == ["mange+ons"]
    assert list(rules["delmorph"].apply("mange+ons")) == ["mangeons"]


def test_symbols(defn) -> None:
    """Verify the treatment of multi-character symbols."""
    assert "gn" in defn.multichar_symbols
    from flair_fst.compile.lexicon import make_lexicon
    fsg = make_lexicon(defn)
    assert "gn" in fsg.alphabet
    assert fsg.tokenize_against_alphabet("gagner") == "g a gn e r".split()


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


def test_full_compile(defn) -> None:
    """Test fully compiled lexicon and rules."""
    from flair_fst.fst import pairs
    from flair_fst.compile import compile

    lex = compile(defn)
    for up, down in pairs(lex):
        print(up, down)
    assert "mangons" not in lex.apply("manger+1pl")
    assert "mangeons" in lex.apply("manger+1pl")
