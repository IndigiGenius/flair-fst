"""
Bridge pyfoma and rustfst
"""

import logging
import operator
import re
from collections import deque
from functools import reduce
from pathlib import Path
from typing import cast, Collection, Sequence, Tuple, Union, Iterator, Set

from pyfoma import FST
from pyfoma.flag import FlagOp, FlagStringFilter, EMPTY, FLAGRE2, FLAGRE3


from .tr import Tr
from .trs import Trs
from .symbol_table import SymbolTable
from .fst import Fst
from .fst.vector_fst import VectorFst
from .fst.const_fst import ConstFst
from .iterators import TrsIterator, MutableTrsIterator, StateIterator
from .drawing_config import DrawingConfig
from .string_paths_iterator import StringPathsIterator

__all__ = [
    "Tr",
    "Trs",
    "SymbolTable",
    "Fst",
    "VectorFst",
    "ConstFst",
    "TrsIterator",
    "MutableTrsIterator",
    "StateIterator",
    "StringPathsIterator",
    "DrawingConfig",
    "pyfoma2rust",
    "eliminate_flags",
    "pairs",
]

LOGGER = logging.getLogger(Path(__file__).stem)


def get_labels_from_label(label: str) -> Tuple[str, str]:
    """Get input and output labels from a pyfoma state."""
    return label[0], label[-1]


def get_symbol(symtab: SymbolTable, sym: str, update: bool = False) -> int:
    """Get a symbol from symtab, adding if necessary and converting
    epsilons."""
    if update:
        return symtab.add_symbol(sym) if sym != "" else 0
    else:
        return cast(int, symtab.find(sym)) if sym != "" else 0


def pyfoma2rust(
    fst: FST,
    symtab: Union[SymbolTable, None] = None,
    alphabet: Union[Sequence[str], None] = None,
) -> VectorFst:
    """Convert pyfoma FST to rustfst VectorFst."""
    vfst = VectorFst()
    state_id = vfst.add_state()
    vfst.set_start(state_id)
    q = deque([(state_id, fst.initialstate)])
    statenums = {fst.initialstate: state_id}
    update_syms = False
    # Always share a symbol table since pyfoma does that
    if symtab is None:
        if alphabet is not None:
            symtab = SymbolTable.from_symbols(list(alphabet))
        else:
            symtab = SymbolTable()
        update_syms = True
        for sym in sorted(fst.alphabet):
            symtab.add_symbol(sym)
    states_with_dot_arcs = []
    used_symbols: Set[str] = set()
    while q:
        state_id, state = q.popleft()
        for label in sorted(state.transitions):
            isym, osym = get_labels_from_label(label)
            if isym == "." or osym == ".":
                states_with_dot_arcs.append((state, label, isym, osym))
            else:
                used_symbols.update((isym, osym))
            # Note: not entirely deterministic
            arcs = state.transitions[label]
            for arc in sorted(arcs, key=operator.attrgetter("weight")):
                if arc.targetstate not in statenums:
                    target_id = vfst.add_state()
                    statenums[arc.targetstate] = target_id
                    q.append((target_id, arc.targetstate))
                else:
                    target_id = statenums[arc.targetstate]
                ilabel = get_symbol(symtab, isym, update_syms)
                olabel = get_symbol(symtab, osym, update_syms)
                vfst.add_tr(state_id, Tr(ilabel, olabel, arc.weight, target_id))
    # Now that we know what all the symbols are, we can expand
    # dot-arcs.  Note that in pyfoma, these don't really mean what you
    # might think, as "." is only intended to match things outside the
    # vocabulary of the entire FST.  This is kind of weird and only
    # works because pyfoma uses dynamic vocabularies for its FSTs, but
    # many things in pyfoma (specifically the implementation of
    # negation) depend on it.  We can sort of emulate it here by
    # adding arcs to match things that are in the total vocabulary,
    # but outside the set of labels actually used by the FST.
    if "" in used_symbols:
        used_symbols.remove("")
    # list(symtab) here works around a bug in rustfst
    all_symbols = set(sym for idx, sym in list(symtab) if idx != 0)
    dot_symbols = all_symbols - used_symbols
    if "." in dot_symbols:
        dot_symbols.remove(".")
    # Note that this is quite similar to pyfoma.algorithms._harmonize_alphabet
    for dotsym in dot_symbols:
        for state, label, isym, osym in states_with_dot_arcs:
            state_id = statenums[state]
            ilabel, olabel = (
                # This cast is due to a bug in rustfst's type annotations
                cast(int, symtab.find(dotsym if sym == "." else sym))
                for sym in (isym, osym)
            )
            arcs = state.transitions[label]
            for arc in sorted(arcs, key=operator.attrgetter("weight")):
                target_id = statenums[arc.targetstate]
                vfst.add_tr(state_id, Tr(ilabel, olabel, arc.weight, target_id))
    for s in fst.finalstates:
        if s not in statenums:
            LOGGER.warning("Final state %r is not accessible", s)
        else:
            vfst.set_final(statenums[s], s.finalweight)
    # Do this after creating the symbol tables as it becomes immutable
    vfst.set_input_symbols(symtab)
    vfst.set_output_symbols(symtab)
    return vfst


def substitute_no_val_flags_symtab(symtab: SymbolTable) -> SymbolTable:
    """Normalize flag symbols, converting `[[$FLAG]]` to
    `[[$FLAG!={}]]` and `[[!$FLAG]]` to `[[$FLAG=={}]]`"""
    # Code adapted from pyfoma._private.eliminate_flags, (c) 2024 Mans
    # Hulden, Apache 2.0 License
    newsyms = SymbolTable()
    for _, sym in list(symtab):
        if m := re.match(FLAGRE2, sym):
            newsyms.add_symbol(f"[[{m.group(1)}={{}}]]")
        elif m := re.match(FLAGRE3, sym):
            if m.group(1) == "!":
                newsyms.add_symbol(f"[[{m.group(2)}=={{}}]]")
            else:
                newsyms.add_symbol(f"[[{m.group(2)}!={{}}]]")
        else:
            newsyms.add_symbol(sym)
    return newsyms


def substitute_no_val_flags(fst: VectorFst) -> VectorFst:
    """Normalize flag symbols in-place, converting `[[$FLAG]]` to
    `[[$FLAG!={}]]` and `[[!$FLAG]]` to `[[$FLAG=={}]]`"""
    isyms = fst.input_symbols() or SymbolTable()
    assert fst.output_symbols() == isyms, (
        "Input and output symbol tables must be shared!"
    )
    newisyms = substitute_no_val_flags_symtab(isyms)
    fst.set_input_symbols(newisyms)
    fst.set_output_symbols(newisyms)
    return fst


## BEGIN code copied from pyfoma (as 2.0 won't make it public)


def set_pos(X, y):
    """Set variable X to value y (i.e. [[$X=y]] | [[$X?=y]])."""
    return FST.re(f"('[[${X}={y}]]' | '[[${X}?={y}]]')")


def set_any(X, ys):
    """Set variable X to any value in ys."""
    res = [set_pos(X, y) for y in ys]
    return reduce(lambda x, y: FST.re("$x | $y", {"x": x, "y": y}), res)


def set_neg(X, y, ys):
    """Set variable X to any value in ys except y."""
    return FST.re("$any - $set", {"any": set_any(X, ys), "set": set_pos(X, y)})


def value_restr(X, y, ys, pos):
    """Return minimal condition for [[$X==y]] (and [[$X?=y]]) or [[$X!=y]] to fail."""
    op = f"('[[${X}=={y}]]'|'[[${X}?={y}]]')" if pos else f"'[[${X}!={y}]]'"
    setval = set_neg(X, y, ys) if pos else set_pos(X, y)
    return FST.re(
        f".* $set (. - $any)* {op} .*", {"set": setval, "any": set_any(X, ys)}
    )


def empty_restr(X, y, ys, pos):
    """Return minimal condition for [[$X=={}]] (and [[$X?={}]]) or [[$X!={}]] to fail."""
    op = f"('[[${X}=={y}]]'|'[[${X}?={y}]]')" if pos else f"'[[${X}!={y}]]'"
    return FST.re(f"(. - $any)* {op} .*", {"any": set_any(X, ys)})


def get_value_tests(Xs, ys):
    """Return a list of tests for [[$X==y]], [[$X?=y]] and [[$X!=y]] flags which
    valid strings have to pass."""
    tests = []
    for X in Xs:
        for y in ys:
            tests.append(value_restr(X, y, ys, pos=True))
            tests.append(value_restr(X, y, ys, pos=False))
            if y == EMPTY:
                tests.append(empty_restr(X, y, ys, pos=False))
            else:
                tests.append(empty_restr(X, y, ys, pos=True))
    return [FST.re(".* - $r", {"r": r}) for r in tests]


## END code copied from pyfoma


def eliminate_flags(
    fst: VectorFst, Xs: Union[Collection[str], None] = None
) -> VectorFst:
    """Return a new VectorFst with flags removed.

    Equivalent to eliminate_flags or eliminate_fst_flags (whatever
    it's called these days) but for FSTs that have already been
    converted to rustfst."""
    # Code adapted from pyfoma._private.eliminate_flags, (c) 2024 Mans
    # Hulden, Apache 2.0 License
    isyms = fst.input_symbols()
    if isyms is None:
        LOGGER.warning("FST has no symbol table, cannot remove flags")
        return fst
    assert fst.output_symbols() == isyms, (
        "Input and output symbol tables must be shared!"
    )
    newfst = substitute_no_val_flags(fst.copy())
    flags = [
        FlagOp(sym) for _, sym in list(newfst.input_symbols()) if FlagOp.is_flag(sym)
    ]
    if Xs is None:
        Xs = set(flag.var[1:] for flag in flags)
    if len(Xs) == 0:
        return newfst
    ys = set(flag.val for flag in flags if flag.var[1:] in Xs)
    ys.add(EMPTY)

    tests = get_value_tests(Xs, ys)
    flag_filter = reduce(lambda x, y: FST.re("$x & $y", {"x": x, "y": y}), tests)
    flags = [sym for sym in flag_filter.alphabet if FlagOp.is_flag(sym)]
    clean = reduce(
        lambda x, y: FST.re("$x @ $y", {"x": x, "y": y}),
        [FST.re(f"$^rewrite('{flag}':'')") for flag in flags],
    )

    # Make sure that all of the new flag symbols are in the symbol
    # table, along with everything else (this is essential because of
    # the weird way .-arcs work in pyfoma)
    newsyms = isyms.copy()
    for sym in clean.alphabet:
        if sym != "":
            newsyms.add_symbol(sym)
    newfst.set_input_symbols(newsyms)
    newfst.set_output_symbols(newsyms)

    # Now apply the flag filters
    rflag_filter = pyfoma2rust(flag_filter, symtab=newsyms)
    rclean = pyfoma2rust(clean, symtab=newsyms)

    newfst.tr_sort(False)
    rflag_filter.tr_sort(True)
    rclean.tr_sort(True)
    newfst = newfst.compose(rflag_filter).compose(rclean).invert()
    newfst.tr_sort(False)
    newfst = newfst.compose(rclean).invert()
    return newfst


def pairs(fst: VectorFst) -> Iterator[Tuple[str, str]]:
    alphabet = {sym for _, sym in list(fst.input_symbols())}
    alphabet.update(sym for _, sym in list(fst.output_symbols()))
    flag_filter = FlagStringFilter(alphabet)
    for strpath in StringPathsIterator(fst):
        # ugh
        up = strpath.istring().split()
        down = strpath.ostring().split()
        if flag_filter(down):
            yield (
                "".join(sym for sym in up if not FlagOp.is_flag(sym)),
                "".join(sym for sym in down if not FlagOp.is_flag(sym)),
            )
