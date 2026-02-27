"""
Types for WFST definitions found in CSV, ODF, XLSX input files.
"""

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Literal, NamedTuple, TypeGuard, Union

SEMIRE = re.compile(r"\s+;\s+")
GLOSSRE = re.compile(r"gloss(?:\s+(.*))?")


@dataclass
class Definition:
    """Definition of a lexicon for compilation to WFST."""

    words: List["WordDefinition"]
    prefixes: Dict[str, List["MorphDefinition"]]
    stems: List["MorphDefinition"]
    suffixes: Dict[str, List["MorphDefinition"]]
    symbols: Dict[str, "SymbolDefinition"]
    rules: Dict[str, "RuleDefinition"]
    spelling: Dict[str, List["TargetOrthography"]]
    bibliography: Dict[str, "BibliographyRecord"]
    tests: List["TestCase"]


class WordDefinition(NamedTuple):
    """Definition of a fully composed word or invariant form."""

    form: str
    base: str
    idx: Union[int, None]
    tags: List[str]
    ref: str
    page: Union[int, None]
    glosses: Dict[str, str]

    @classmethod
    def from_row(cls, row: Dict[str, str]):
        """Load from a row in a CSV reader."""
        glosses: Dict[str, str] = {}
        for key in row:
            if m := GLOSSRE.match(key):
                lang = m[1] or "_default"
                glosses[lang] = row[key]
        return cls(
            form=row["form"].strip(),
            base=row["base"].strip(),
            ref=row["ref"].strip(),
            idx=None if row["index"] == "" else int(row["index"]),
            page=None if row["page"] == "" else int(row["page"]),
            tags=SEMIRE.split(row["tags"].strip()),
            glosses=glosses,
        )


class MorphDefinition(NamedTuple):
    """Definition of a morpheme (prefix, root, suffix, etc)."""

    morph: str
    form: str
    idx: Union[int, None]
    tags: List[str]
    ref: str
    page: Union[int, None]
    glosses: Dict[str, str]

    @classmethod
    def from_row(cls, row: Dict[str, str]):
        """Load from a row in a CSV reader."""
        glosses: Dict[str, str] = {}
        for key in row:
            if m := GLOSSRE.match(key):
                lang = m[1] or "_default"
                glosses[lang] = row[key]
        return cls(
            morph=row["morph"].strip(),
            form=row["form"].strip(),
            ref=row["ref"].strip(),
            idx=None if row["index"] == "" else int(row["index"]),
            page=None if row["page"] == "" else int(row["page"]),
            tags=SEMIRE.split(row["tags"].strip()),
            glosses=glosses,
        )


FIXQUOTES = {
    ord("‘"): "'",
    ord("’"): "'",
    ord("“"): '"',
    ord("”"): '"',
}


class RuleDefinition(NamedTuple):
    """Definition of an alternation rule."""

    regex: str
    ref: str
    page: Union[int, None]

    @classmethod
    def from_row(cls, row: Dict[str, str]):
        """Load from a row in a CSV reader."""
        # Remove smart quotes from regex, since we can't easily stop
        # LibreOffice and Excel from putting them in
        translate = str.translate
        regex = row["rule"].strip().translate(FIXQUOTES)
        return cls(
            regex=regex,
            ref=row["ref"].strip(),
            page=None if row["page"] == "" else int(row["page"]),
        )


class SymbolDefinition(NamedTuple):
    """Definition of a symbol in the orthography."""

    ipa: str
    ref: str
    page: Union[int, None]

    @classmethod
    def from_row(cls, row: Dict[str, str]):
        """Load from a row in a CSV reader."""
        return cls(
            sym=row["sym"].strip(),
            ipa=row["ipa"].strip(),
            ref=row["ref"].strip(),
            page=None if row["page"] == "" else int(row["page"]),
        )


class TargetOrthography(NamedTuple):
    """Target sequence of glyphs for approximate input or spellchecking."""

    glyphs: str
    cost: float = 1.0


def spelling_from_table(table: Iterable[Dict[str, str]]):
    """Create dictionary of TargetOrthography from a list of rows."""
    result: Dict[str, List[TargetOrthography]] = {}
    for row in table:
        form = row["approximate"].strip()
        glyphs = row["correct"].strip()
        cost = float(row["penalty"] or 0.0)
        target = TargetOrthography(glyphs=glyphs, cost=cost)
        if form not in result:
            result[form] = []
        result[form].append(target)
    return result


class BibliographyRecord(NamedTuple):
    """Bibliography entry."""

    url: str
    citation: str
    page_offset: int


def bibliography_from_table(table: Iterable[Dict[str, str]]):
    """Create dictionary of BibliographyRecord from a list of rows."""
    bibliography = {}
    for row in table:
        abbrev = row["abbreviation"]
        bibliography[abbrev] = BibliographyRecord(
            url=row["url"],
            citation=row["citation"],
            page_offset=int(row["page offset"]) if row["page offset"] else 0,
        )
    return bibliography


def is_up_down(direction: str) -> TypeGuard[Literal["up", "down"]]:
    return direction in ("up", "down")


class TestCase(NamedTuple):
    """Test case for morphological analysis or generation."""

    morph: str
    form: str

    @classmethod
    def from_row(cls, row: Dict[str, str]):
        """Load from a row in a CSV reader."""
        return cls(
            morph=row["morph"].strip(),
            form=row["form"].strip(),
        )
