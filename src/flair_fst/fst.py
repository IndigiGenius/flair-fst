# SPDX-FileCopyrightText: 2025-present David Huggins-Daines <dhd@ecolingui.ca>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Some additional FST functions not available in pyfoma
"""

import json
import operator
import re as pyre
from collections import deque
from os import PathLike
from pathlib import Path
from typing import Dict, Iterator, List, Tuple, Union

from pyfoma.flag import FlagOp, FlagStringFilter
from pyfoma.fst import FST, State

from flair_fst.models import FSTDict, TransitionsDict

# Use this for epsilon labels to be compatible with foma
EPSILON = "@0@"


def escape_state(name: str):
    """Escape state names to ensure Javascript compatibility."""
    return pyre.sub(r"\W", "_", name)


def toatt(
    fst: FST, base: Union[PathLike, str], state_symbols=False, epsilon=EPSILON
) -> None:
    """Save to AT&T format files."""
    fst.save_att(Path(base), state_symbols, epsilon)


# The released pyfoma version of this still has some bugs...
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


# The released pyfoma version of this still has some bugs...
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
            labels = tuple(
                sym.replace(r"\|", "|")
                for sym in pyre.split(r"(?<!\\)\|", tlabel, maxsplit=2)
            )
            for target in targets:
                if isinstance(target, tuple):
                    dest, weight = target
                else:
                    dest = target
                    weight = 0.0
                dest_state = add_up_to(int(dest))
                src_state.add_transition(dest_state, labels, weight)
    return fst


def pairs(fst: FST) -> Iterator[Tuple[str, str]]:
    """Yield pairs like foma would do."""
    flag_filter = FlagStringFilter(fst.alphabet)
    for _cost, seq in fst.words():
        up, down = [], []
        for tapes in seq:
            up.append(tapes[0])
            down.append(tapes[-1])
        if flag_filter(down):
            yield (
                "".join(sym for sym in up if not FlagOp.is_flag(sym)),
                "".join(sym for sym in down if not FlagOp.is_flag(sym)),
            )


# Type aliases for RLG input
RLGEntry = Union[Tuple[str, str], Tuple[Tuple[str, str], str]]
RLG = Dict[str, List[RLGEntry]]
