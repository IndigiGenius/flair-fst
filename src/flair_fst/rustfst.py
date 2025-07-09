"""
Bridge pyfoma and rustfst
"""

import logging
import operator
from collections import deque
from functools import reduce
from itertools import product
from pathlib import Path
from typing import cast, Sequence, Tuple, Union, Iterable, Set

from pyfoma import FST  # type: ignore
from pyfoma.flag import FlagOp  # type: ignore


from rustfst.fst.vector_fst import VectorFst
from rustfst.symbol_table import SymbolTable
from rustfst.tr import Tr

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
    all_symbols = set(sym for idx, sym in symtab if idx != 0)
    dot_symbols = all_symbols - used_symbols
    if "." in dot_symbols:
        dot_symbols.remove(".")
    # Note that this is quite similar to pyfoma.algorithms._harmonize_alphabet
    for dotsym in dot_symbols:
        for state, label, isym, osym in states_with_dot_arcs:
            state_id = statenums[state]
            ilabel, olabel = (
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


# Code copied from pyfoma 1.0.6 (we can't depend on its internals as they have changed)
EMPTYVAL = "{}"


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
    """Return minimal condition for [[$X==y]] (and [[$X?=y]]) or [[$X!=y]] to fail.
    Precondition: y != "{}"."""
    op = f"('[[${X}=={y}]]'|'[[${X}?={y}]]')" if pos else f"'[[${X}!={y}]]'"
    setval = set_neg(X, y, ys) if pos else set_pos(X, y)
    return FST.re(
        f".* $set (. - $any)* {op} .*", {"set": setval, "any": set_any(X, ys)}
    )


def empty_restr(X, y, ys, pos):
    """Return minimal condition for [[$X=={}]] (and [[$X?={}]]) or [[$X!={}]] to fail."""
    op = f"('[[${X}=={y}]]'|'[[${X}?={y}]]')" if pos else f"'[[${X}!={y}]]'"
    return FST.re(f"(. - $any)* {op} .*", {"any": set_any(X, ys)})


def eq_restr(X1, X2, y1, y2, ys):
    """Return minimal condition for [[$X1==$X2]] or [[$X1!=$X2]] to fail given
    values y1 and y2 (and y1 != "{}")."""
    set1 = FST.re(
        ".* $set (. - $any)*", {"set": set_pos(X1, y1), "any": set_any(X1, ys)}
    )
    set2 = FST.re(
        ".* $set (. - $any)*", {"set": set_pos(X2, y2), "any": set_any(X2, ys)}
    )
    op = f"'[[${X1}!=${X2}]]'" if y1 == y2 else f"'[[${X1}==${X2}]]'"
    return FST.re(f"($set1 & $set2) {op} .*", {"set1": set1, "set2": set2})


def empty_eq_restr(X1, X2, ys):
    """Return minimal condition for [[$X1==$X2]] or [[$X1!=$X2]] to fail given
    values that the value of X1 is "{}"."""
    set1 = FST.re("(. - $any)*", {"any": set_any(X1, ys)})
    set2 = FST.re(
        ".* $set (. - $any)*",
        {"set": set_neg(X2, EMPTYVAL, ys), "any": set_any(X2, ys)},
    )
    return FST.re("($set1 & $set2) '[[${X1}==${X2}]]' .*", {"set1": set1, "set2": set2})


def get_value_tests(Xs, ys):
    """Return a list of tests for [[$X==y]], [[$X?=y]] and [[$X!=y]] flags which
    valid strings have to pass."""
    tests = []
    for X in Xs:
        for y in ys:
            tests.append(value_restr(X, y, ys, pos=True))
            tests.append(value_restr(X, y, ys, pos=False))
            if y == EMPTYVAL:
                tests.append(empty_restr(X, y, ys, pos=False))
            else:
                tests.append(empty_restr(X, y, ys, pos=True))
    return [FST.re(".* - $r", {"r": r}) for r in tests]


def get_eq_tests(Xs, ys):
    """Return a list of tests for [[$X==$Y]], [[$X!=$Y]] flags which valid strings
    have to pass."""
    tests = []
    for X1, X2 in product(Xs, repeat=2):
        if X1 != X2:
            for y1, y2 in product(ys, ys):
                tests.append(eq_restr(X1, X2, y1, y2, ys))
            tests.append(empty_eq_restr(X1, X2, ys))
    return [FST.re(".* - $r", {"r": r}) for r in tests]


def make_flag_filter_fsts(
    alphabet: Iterable[str],
) -> Tuple[Union[FST, None], Union[FST, None]]:
    """Make flag filter and cleanup FSTs."""
    flags = [FlagOp(sym) for sym in alphabet if FlagOp.is_flag(sym)]
    Xs = set(flag.var[1:] for flag in flags)
    if len(Xs) == 0:
        return (None, None)
    ys = set(flag.val for flag in flags if flag.var[1:] in Xs)
    ys.add(EMPTYVAL)

    tests = get_value_tests(Xs, ys) + get_eq_tests(Xs, ys)
    flag_filter = reduce(lambda x, y: FST.re("$x & $y", {"x": x, "y": y}), tests)
    # We have added some (bogus) flags because of EMPTYVAL
    flags = [sym for sym in flag_filter.alphabet if FlagOp.is_flag(sym)]
    clean = reduce(
        lambda x, y: FST.re("$x @ $y", {"x": x, "y": y}),
        [FST.re(f"$^rewrite('{flag}':'')") for flag in flags],
    )
    return flag_filter, clean


def invert(fst: VectorFst) -> VectorFst:
    """Invert an FST in-place.

    While waiting for a new release of rustfst, here this is."""
    for s in fst.states():
        assert s is not None  # WTF
        # bad api. no donut.
        tr_it = fst.mutable_trs(s)
        while not tr_it.done():
            tr = tr_it.value()
            assert tr is not None  # WTF
            tr.olabel, tr.ilabel = tr.ilabel, tr.olabel
            tr_it.set_value(tr)
            next(tr_it)
    return fst


def eliminate_flags(fst: VectorFst) -> VectorFst:
    """Return a new VectorFst with flags removed.

    Equivalent to eliminate_flags or eliminate_fst_flags (whatever
    it's called these days) but for FSTs that have already been
    converted to rustfst."""
    isyms = fst.input_symbols()
    newfst = fst.copy()
    if isyms is None:
        LOGGER.warning("FST has no symbol table, cannot remove flags")
        return newfst
    flag_filter, clean = make_flag_filter_fsts(sym for _, sym in isyms)
    if flag_filter is None or clean is None:
        return newfst

    # Make sure that all of the new flag symbols are in the symbol table
    newsyms = isyms.copy()
    for sym in clean.alphabet:
        if sym != "":
            newsyms.add_symbol(sym)
    newfst.set_input_symbols(newsyms)
    newfst.set_output_symbols(newsyms)
    # Now apply the flag filters
    rflag_filter = pyfoma2rust(flag_filter, symtab=newfst.input_symbols())
    rclean = pyfoma2rust(clean, symtab=newfst.input_symbols())
    newfst.tr_sort(False)
    rflag_filter.tr_sort(True)
    rclean.tr_sort(True)
    newfst = newfst.compose(rflag_filter).compose(rclean)
    invert(newfst)
    newfst.tr_sort(False)
    newfst = newfst.compose(rclean)
    invert(newfst)
    return newfst
