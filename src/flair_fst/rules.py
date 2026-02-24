"""
Tools for making alternation rules.
"""

import logging
from copy import copy
from unicodedata import normalize

from pyfoma import FST  # type: ignore

LOGGER = logging.getLogger(__name__)
CLASSES = {}


def rule(txt: str) -> FST:
    norm = normalize("NFC", txt)
    if norm != txt:
        LOGGER.warning("rule text is not NFC: %s", txt)
        txt = norm
    return FST.regex(txt, CLASSES)


RULES = []


def add_rule(txt: str) -> FST:
    r = rule(txt)
    RULES.append(r)
    return r


def make_fst() -> FST:
    """Make the rules as an FST"""
    regex = copy(RULES[0])
    for r in RULES:
        regex.compose(r)  # type: ignore
    return regex.determinize().minimize()  # type: ignore
