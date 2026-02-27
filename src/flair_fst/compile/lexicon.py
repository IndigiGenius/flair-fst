"""
Compile lexicon from definitions.
"""

import itertools
from typing import List, Tuple, Union
from pyfoma import FST

from flair_fst import RLG, RLGEntry
from .definition import Definition, MorphDefinition


def make_pair(m: MorphDefinition) -> Tuple[str, str]:
    """Make the transduction pair for a morph including flags"""
    if not m.flags:
        return (m.morph, m.form)
    tagtext = "".join(f"'[[{flag}]]'" for flag in m.flags)
    return (f"{m.morph}{tagtext}", f"{m.form}{tagtext}")


def make_rlg(defn: Definition) -> RLG:
    """Create a right-linear grammar from the tables in defn.

    This is an intermediate step, see `make_lexicon` for more
    information.

    """
    lex: RLG = {"START": []}
    if defn.words:
        lex["START"].append(("", "words"))
        lex["words"] = []
        for w in defn.words:
            lex["words"].append((w.form, "#"))
    start: Union[str, None] = None
    prefix_names = [*defn.prefixes, "stems"]
    for name, continuation in itertools.pairwise(prefix_names):
        if start is None:
            start = name
        sublex: List[RLGEntry] = [("", continuation)]
        for m in defn.prefixes[name]:
            sublex.append((make_pair(m), continuation))
        lex[name] = sublex
    if start is None:
        start = "stems"
    lex["START"].append(("", start))
    suffix_names = [*defn.suffixes, "#"]
    continuation = suffix_names[0]
    sublex = []
    for m in defn.stems:
        sublex.append((make_pair(m), continuation))
    lex["stems"] = sublex
    for name, continuation in itertools.pairwise(suffix_names):
        sublex = [("", continuation)]
        for m in defn.suffixes[name]:
            sublex.append((make_pair(m), continuation))
        lex[name] = sublex
    return lex


def make_lexicon(defn: Definition) -> FST:
    """Compile a lexicon from the tables in defn.

    By default this assumes a strict ordering of optional prefixes, an
    obligatory stem, and optional suffixes, using their insertion
    order in the `prefixes` and `suffixes` dictionaries, as you might
    encounter in a polysynthetic language.

    TODO: This will be modifiable using continuation classes.

    """
    rlg = make_rlg(defn)
    return FST.rlg(rlg, "START")
