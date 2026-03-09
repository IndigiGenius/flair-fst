"""
Compile approximate matcher from table.
"""

import re

from pyfoma import FST

from flair_fst.definition import Definition

SPECIALS = "$^?,<>{}[]-+()|"
ESCAPER = re.compile(f"([{re.escape(SPECIALS)}])")


def escape(txt: str) -> str:
    """Try to escape things for PyFoma"""
    return ESCAPER.sub(r"\\\1", txt)


def make_approx(defn: Definition) -> FST:
    """Create approximate matcher from mapping of approximate to
    weighted target forms."""
    rules = []
    for approx, targets in defn.spelling.items():
        for glyphs, cost in targets:
            if cost:
                rules.append(f"({escape(approx)}) :? ({escape(glyphs)})<{cost}>")
            else:
                rules.append(f"({escape(approx)}) :? ({escape(glyphs)})")
    syms = defn.multichar_symbols or None
    return FST.regex(f"$^rewrite({' | '.join(rules)})", multichar_symbols=syms)
