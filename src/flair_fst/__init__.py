# SPDX-FileCopyrightText: 2025-present David Huggins-Daines <dhd@ecolingui.ca>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Some additional FST functions that will make it into pyfoma
"""

import json
import operator
import re as pyre
from collections import deque
from os import PathLike
from pathlib import Path
from typing import Dict, Iterable, List, TextIO, Tuple, TypedDict, Union

from pyfoma import FST, State  # type: ignore
from pyfoma.flag import FlagOp, FlagStringFilter  # type: ignore

# Brokenness in pyfoma
try:
    from pyfoma.eliminate_flags import eliminate_flags  # type: ignore  # noqa: F401
except ImportError:
    from pyfoma.algorithms import eliminate_flags  # type: ignore  # noqa: F401

# Use this for epsilon labels to be compatible with foma
EPSILON = "@0@"


# NOTE: These next two will go away with pyfoma >= 1.1 (or the next version)
def _multichar_matcher(multichar_symbols: Iterable[str]) -> pyre.Pattern:
    """Create matcher for unquoted multichar symbols in lexicons and
    regular expressions."""
    ordered = [sym for sym in multichar_symbols if len(sym) > 1]
    ordered.sort(key=len, reverse=True)
    return pyre.compile(
        r"('(?:\\'|[^'])*')|(" + "|".join(pyre.escape(sym) for sym in ordered) + r")"
    )


def _multichar_replacer(matchobj: pyre.Match):
    """Replace character or quoted string with quoted thing."""
    quoted, sym = matchobj.groups()
    if quoted is not None:
        return quoted
    return "'" + sym.replace("'", r"\'") + "'"


def escape_state(name: str):
    return pyre.sub(r"\s", "_", name)


def escape_label(sym: str):
    if sym == "":
        return EPSILON
    # FIXME: This is not really going to work!
    return escape_state(sym)


def toatt(fst: FST, base: PathLike, state_symbols=False):
    """Save to AT&T format files."""
    path = Path(base).with_suffix(".fst")
    ssympath = path.with_suffix(".ssyms")
    isympath = path.with_suffix(".isyms")
    osympath = path.with_suffix(".osyms")
    # Number states and create state symbol table (see
    # todict() for why we must do this in a repeatable way)
    q = deque([fst.initialstate])
    states: List[State] = []
    ssyms: List[str] = []
    ssymtab = {}
    while q:
        state = q.popleft()
        if state.name is None or not state_symbols:
            name = str(len(ssyms))
        else:
            name = escape_state(state.name)
        ssymtab[id(state)] = name
        ssyms.append(name)
        states.append(state)
        # Make sure to sort here too as the order of insertion will
        # vary as a consequence of different ordering of states
        for label, arcs in sorted(
            state.transitions.items(), key=operator.itemgetter(0)
        ):
            # FIXME: it is not possible to guarantee the ordering
            # here.  Consider not using `set` for arcs.
            for arc in sorted(arcs, key=operator.attrgetter("weight")):
                if id(arc.targetstate) not in ssymtab:
                    q.append(arc.targetstate)
    if state_symbols:
        with open(ssympath, "wt") as outfh:
            for idx, name in enumerate(ssyms):
                print(f"{name}\t{idx}", file=outfh)
    # Do a second pass to output the FST itself (we will always have
    # to do this because of the need to number states)
    isyms = {EPSILON: 0}
    osyms = {EPSILON: 0}

    def output_state(s: State, outfh: TextIO):
        name = ssymtab[id(s)]
        for label, arcs in sorted(
            state.transitions.items(), key=operator.itemgetter(0)
        ):
            if len(label) == 1:
                isym = osym = escape_label(label[0])
            else:
                isym, osym = (escape_label(x) for x in label)
            if isym not in isyms:
                isyms[isym] = len(isyms)
            if osym not in osyms:
                osyms[osym] = len(osyms)
            for transition in sorted(arcs, key=operator.attrgetter("weight")):
                dest = ssymtab[id(transition.targetstate)]
                fields = [
                    name,
                    dest,
                    isym,
                    osym,
                ]
                if transition.weight != 0.0:
                    fields.append(str(transition.weight))
                print("\t".join(fields), file=outfh)
        # NOTE: These are not required to be at the end of the file
        if s in fst.finalstates:
            name = ssymtab[id(s)]
            if s.finalweight != 0.0:
                print(f"{name}\t{s.finalweight}", file=outfh)
            else:
                print(name, file=outfh)

    with open(path, "wt") as outfh:
        for state in states:
            output_state(state, outfh)
    with open(isympath, "wt") as outfh:
        for name, idx in isyms.items():
            print(f"{name}\t{idx}", file=outfh)
    with open(osympath, "wt") as outfh:
        for name, idx in osyms.items():
            print(f"{name}\t{idx}", file=outfh)


TransitionsDict = Dict[int, Dict[str, List[Union[int, Tuple[int, float]]]]]


class FSTDict(TypedDict):
    t: TransitionsDict
    f: Dict[int, float]
    s: Dict[str, int]


def todict(fst: FST) -> FSTDict:
    """Create a dictionary form of the FST for export to JSON."""
    # Traverse, renumbering all the states, because:
    # 1. It removes unreachable states and saves space/bandwidth
    # 2. The JS code requires the initial state to have number 0
    # 3. pyfoma uses a `set` to store states, and sets are not
    #    order-preserving in Python, while dicts are, so two FSTs
    #    created with the same input to `FST.regex` will end up with
    #    different state numberings and thus different JSON unless we
    #    enforce an ordering on them here.
    q = deque([fst.initialstate])
    states: List[State] = []
    statenums: Dict[int, int] = {}
    while q:
        state = q.popleft()
        if id(state) in statenums:
            continue
        statenums[id(state)] = len(states)
        states.append(state)
        # Make sure to sort here too as the order of insertion will
        # vary as a consequence of different ordering of states
        for label, arcs in sorted(
            state.transitions.items(), key=operator.itemgetter(0)
        ):
            # FIXME: This is not guaranteed to give an ordering for nondeterministic FSTs
            for arc in sorted(arcs, key=operator.attrgetter("weight")):
                if id(arc.targetstate) not in statenums:
                    q.append(arc.targetstate)
    transitions: TransitionsDict = {}
    finals = {}
    alphabet: Dict[str, int] = {}
    for src, state in enumerate(states):
        for label, arcs in sorted(
            state.transitions.items(), key=operator.itemgetter(0)
        ):
            if len(label) == 1:
                isym = osym = label[0]
            else:
                isym, osym = label
            for sym in isym, osym:
                # Omit epsilon from symbol table
                if sym == "":
                    continue
                if sym not in alphabet:
                    # Reserve 0, 1, 2 for epsilon, identity, unknown
                    alphabet[sym] = 3 + len(alphabet)
            isym, osym = (pyre.sub(r"\\?\|", r"\|", sym) for sym in (isym, osym))
            tlabel = isym if isym == osym else f"{isym}|{osym}"
            # Nothing to do to the symbols beyond that as pyfoma
            # already uses the same convention of epsilon='', and JSON
            # encoding will take care of escaping everything for us.
            for arc in sorted(arcs, key=operator.attrgetter("weight")):
                transitions.setdefault(src, {}).setdefault(tlabel, []).append(
                    statenums[id(arc.targetstate)]
                    if arc.weight == 0.0
                    else (statenums[id(arc.targetstate)], arc.weight)
                )
        if state in fst.finalstates:
            finals[src] = 0.0
    return {
        "t": transitions,
        "s": alphabet,
        "f": finals,
    }


def tojson(fst: FST, indent=None):
    """Create JSON (which is also Javascript) for an FST for use with
    foma_apply_down.js"""
    return json.dumps(todict(fst), ensure_ascii=False, indent=indent)


def fromdict(fstdict: Dict) -> FST:
    """Recreate an FST from dictionary form."""
    fst = FST(alphabet=set(fstdict["s"].keys()))
    states: List[State] = []

    def add_up_to(state_idx: int):
        while len(states) <= state_idx:
            state = State()
            idx = len(states)
            states.append(state)
            fst.states.add(state)
            if idx == 0:
                fst.initialstate = state
            if idx in fstdict["f"]:
                fst.finalstates.add(state)
                state.finalweight = fstdict["f"][idx]
            elif str(idx) in fstdict["f"]:
                fst.finalstates.add(state)
                state.finalweight = fstdict["f"][str(idx)]
        return states[state_idx]

    for src, arcs in fstdict["t"].items():
        src_state = add_up_to(int(src))
        for tlabel, targets in arcs.items():
            labels = tuple(sym.replace(r"\|", "|")
                           for sym
                           in pyre.split(r"(?<!\\)\|", tlabel, maxsplit=2))
            for target in targets:
                if isinstance(target, tuple):
                    dest, weight = target
                else:
                    dest = target
                    weight = 0.0
                dest_state = add_up_to(int(dest))
                src_state.add_transition(dest_state, labels, weight)
    return fst


def pairs(fst: FST):
    """
    Yield pairs like foma would do.
    """
    flag_filter = FlagStringFilter(fst.alphabet)
    for _cost, seq in fst.words():
        up, down = [], []
        for tapes in seq:
            up.append(tapes[0])
            down.append(tapes[-1])
        if flag_filter(down):
            yield "".join(up), "".join(sym for sym in down if not FlagOp.is_flag(sym))


# Type alias for RLG input
RLG = Dict[str, List[Union[Tuple[str, str], Tuple[Tuple[str, str], str]]]]
