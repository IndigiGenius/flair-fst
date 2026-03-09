"""
Set of tables that can be compiled into a WFST.

The input may come as a spreadsheet (ODS or XLSX) or as a directory of CSV files.
"""

import logging
import re
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import (
    Collection,
    Dict,
    Iterable,
    List,
    Literal,
    NamedTuple,
    TypeGuard,
    Union,
)

from pyfoma import FST

SEMIRE = re.compile(r"\s+;\s+")
GLOSSRE = re.compile(r"gloss(?:\s+(.*))?")
MDLINKRE = re.compile(r"\[[^\]]+\]\(([^\)]+)\)")
LOG = logging.getLogger(__name__)


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

    @property
    def multichar_symbols(self) -> Collection[str]:
        """Set of multi-chararacter symbols defined in this lexicon."""
        return self.symbols.keys()

    @classmethod
    def from_csv(cls, path: Union[str, PathLike]) -> "Definition":
        from flair_fst.definition.csv import load_definition

        return load_definition(path)

    @classmethod
    def from_odf(cls, path: Union[str, PathLike]) -> "Definition":
        from flair_fst.definition.odf import load_definition

        return load_definition(path)

    @classmethod
    def from_xlsx(cls, path: Union[str, PathLike]) -> "Definition":
        from flair_fst.definition.xlsx import load_definition

        return load_definition(path)

    @classmethod
    def from_path(cls, path: Union[str, PathLike]) -> "Definition":
        path = Path(path)

        if path.is_dir():
            return Definition.from_csv(path)
        if path.suffix.lower() == ".ods":
            return Definition.from_odf(path)
        if path.suffix.lower() == ".xlsx":
            return Definition.from_xlsx(path)
        raise RuntimeError(f"Unknown or unsupported file extension: {path}")

    def compile(self) -> "FST":
        from flair_fst.compile import compile

        return compile(self)


class WordDefinition(NamedTuple):
    """Definition of a fully composed word or invariant form."""

    form: str
    base: str
    idx: Union[int, None]
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
            glosses=glosses,
        )


class MorphDefinition(NamedTuple):
    """Definition of a morpheme (prefix, root, suffix, etc)."""

    morph: str
    form: str
    idx: Union[int, None]
    flags: List[str]
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
        flagtext = row["flags"].strip()
        flags = SEMIRE.split(flagtext) if flagtext else []
        return cls(
            morph=row["morph"].strip(),
            form=row["form"].strip(),
            ref=row["ref"].strip(),
            idx=None if row["index"] == "" else int(row["index"]),
            page=None if row["page"] == "" else int(row["page"]),
            flags=flags,
            glosses=glosses,
        )


FIXQUOTES = {
    ord("‘"): "'",
    ord("’"): "'",
    ord("“"): '"',
    ord("”"): '"',
    ord(" "): " ",
}


class RuleDefinition(NamedTuple):
    """Definition of an alternation rule."""

    regex: str
    ref: str
    page: Union[int, None]

    @classmethod
    def from_row(cls, row: Dict[str, str]):
        """Load from a row in a CSV reader."""
        # Remove smart quotes and non-breaking spaces from regex,
        # since we can't easily stop LibreOffice and Excel from
        # putting them in
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
        # odfdo markdown-ifies links and there's no way to
        # stop it, so un-markdown them here
        url = row["url"]
        if m := MDLINKRE.match(url):
            url = m[1]
        url = url.strip("/")  # for some reason Excel begs to differ
        bibliography[abbrev] = BibliographyRecord(
            url=url,
            citation=row["citation"],
            page_offset=int(row["page offset"]) if row["page offset"] else 0,
        )
    return bibliography


def is_up_down(direction: str) -> TypeGuard[Literal["up", "down"]]:
    """Ensure that a string is literally "up" or "down"."""
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
