"""
Compile approximate matcher from table.
"""

import re
from typing import List, Dict
from pyfoma import FST
from .definition import TargetOrthography

SPECIALS = "$^?,<>{}[]"
ESCAPER = re.compile(f"([{re.escape(SPECIALS)}])")


def escape(txt: str) -> str:
    """Try to escape things for PyFoma"""
    return ESCAPER.sub(r"\\\1" ,txt)


def make_approx(spelling: Dict[str, List[TargetOrthography]]) -> FST:
    """Create approximate matcher from mapping of approximate to
    weighted target forms."""
    rules = []
    for approx, targets in spelling.items():
        for glyphs, cost in targets:
            if cost:
                rules.append(f"({escape(approx)}) :? ({escape(glyphs)})<{cost}>")
            else:
                rules.append(f"({escape(approx)}) :? ({escape(glyphs)})")
    return FST.regex(f"$^rewrite({' | '.join(rules)})")
