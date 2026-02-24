"""
Output FSTs and other JSON for web page
"""

import logging
from pathlib import Path
from typing import Set

from pyfoma import FST

from flair_fst.fst import RLG

LOGGER = logging.getLogger(Path(__file__).stem)


def make_approx():
    """Create approximate search transformer for similar/confusable letters."""
    return FST.regex(
        r"""
    $^rewrite(
            | s:?'š'<1>
            | c:?'č'<1>
            | \?:Ɂ
            | 7:Ɂ
            | ʔ:Ɂ
        )
    """
    )


def extract_cvs(lex: RLG) -> Set[str]:
    """Extract the initial CV segments for reduplication."""
    # Could do this with an FST, but won't
    cvs = set()
    for sublex in "Word", "Stem", "BoundRoot", "Root":
        for lhs, rhs in lex[sublex]:
            if lhs == "":
                continue
            if isinstance(lhs, tuple):
                _, lhs = lhs
            m = CV_RE.match(lhs)
            if m:
                cvs.add(m[0])
    return cvs
