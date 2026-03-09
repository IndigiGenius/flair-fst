import csv
import logging
from os import PathLike
from pathlib import Path
from typing import Dict, Iterator, Union

from . import (
    Definition,
    MorphDefinition,
    RuleDefinition,
    SymbolDefinition,
    TestCase,
    WordDefinition,
    bibliography_from_table,
    spelling_from_table,
)

LOGGER = logging.getLogger(Path(__file__).stem)


def _get_reader(directory: Path, name: str) -> Iterator[Dict[str, str]]:
    try:
        with open(directory / name, newline="", encoding="utf-8-sig") as fh:
            yield from csv.DictReader(fh)
    except FileNotFoundError:
        yield from ()


def load_definition(path: Union[str, PathLike]) -> Definition:
    """Compile a Definition from a directory of CSV files."""
    directory = Path(path)
    words = [
        WordDefinition.from_row(row)
        for row in _get_reader(directory, "words.csv")
        if row["form"]
    ]
    stems = [
        MorphDefinition.from_row(row)
        for row in _get_reader(directory, "stems.csv")
        if row["morph"]
    ]
    # Note that Python dicts preserve ordering, which is very important here
    prefixes = {
        path.stem: [
            MorphDefinition.from_row(row)
            for row in _get_reader(directory, path.name)
            if row["morph"]
        ]
        for path in sorted(directory.glob("*prefix*.csv"))
    }
    suffixes = {
        path.stem: [
            MorphDefinition.from_row(row)
            for row in _get_reader(directory, path.name)
            if row["morph"]
        ]
        for path in sorted(directory.glob("*suffix*.csv"))
    }
    rules = {
        row["name"]: RuleDefinition.from_row(row)
        for row in _get_reader(directory, "rules.csv")
    }
    symbols = {
        row["sym"]: SymbolDefinition.from_row(row)
        for row in _get_reader(directory, "symbols.csv")
    }
    spelling = spelling_from_table(_get_reader(directory, "spelling.csv"))
    bib = bibliography_from_table(_get_reader(directory, "bibliography.csv"))
    tests = [TestCase.from_row(row) for row in _get_reader(directory, "tests.csv")]

    return Definition(
        words=words,
        prefixes=prefixes,
        stems=stems,
        suffixes=suffixes,
        rules=rules,
        symbols=symbols,
        spelling=spelling,
        bibliography=bib,
        tests=tests,
    )
