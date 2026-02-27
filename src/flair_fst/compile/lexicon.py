"""
Compile lexicon from definitions.
"""

import itertools
from typing import Tuple
from pyfoma import FST

from flair_fst import RLG
from .definition import Definition


def make_rlg(defn: Definition) -> Tuple[RLG, str]:
    """Create a right-linear grammar from the tables in defn.

    This is an intermediate step, see `make_lexicon` for more
    information.

    """
    lex: RLG = {}
    start: Union[str, None] = None
    prefix_names = [*defn.prefixes, "stem"]
    for name, continuation in itertools.pairwise(prefix_names):
        if start is None:
            start = name
        sublex = [("", continuation)]
        for m in defn.prefixes[name]:
            sublex.append(((m.morph, m.form), continuation))
        lex[name] = sublex
    if start is None:
        start = "stem"
    suffix_names = [*defn.suffixes, "#"]
    continuation = suffix_names[0]
    sublex = []
    for m in defn.stems:
        sublex.append(((m.morph, m.form), continuation))
    lex["stem"] = sublex
    for name, continuation in itertools.pairwise(suffix_names):
        sublex = [("", continuation)]
        for m in defn.suffixes[name]:
            sublex.append(((m.morph, m.form), continuation))
        lex[name] = sublex
    return lex, start


def make_lexicon(defn: Definition) -> FST:
    """Compile a lexicon from the tables in defn.

    By default this assumes a strict ordering of optional prefixes, an
    obligatory stem, and optional suffixes, using their insertion
    order in the `prefixes` and `suffixes` dictionaries, as you might
    encounter in a polysynthetic language.

    TODO: This will be modifiable using continuation classes.

    """
    rlg, start = make_rlg(defn)
    return FST.rlg(rlg, start)
