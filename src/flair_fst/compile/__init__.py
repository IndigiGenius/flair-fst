"""
Compile a set of tables into a WFST.

The input may come as a spreadsheet (ODS or XLSX) or as a directory of CSV files.
"""

import logging
from pathlib import Path
from pyfoma import FST
from .definition import Definition
from .lexicon import make_lexicon
from .rules import make_rules

LOGGER = logging.getLogger(Path(__file__).stem)
__all__ = ["Definition", "compile"]


def compile(defn: Definition) -> FST:
    """Compile an FST from a definition."""
    lex = make_lexicon(defn)
    rules = make_rules(defn)
    for name, rule in rules.items():
        lex.compose(rule)
    return lex
