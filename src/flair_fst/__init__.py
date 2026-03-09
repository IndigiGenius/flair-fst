# SPDX-FileCopyrightText: 2025-present David Huggins-Daines <dhd@ecolingui.ca>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Public interface to flair_fst.
"""

import json
from pathlib import Path
from typing import List

from pyfoma import FST, State

from flair_fst.compile.approx import make_approx
from flair_fst.compile.bibliography import make_bibliography
from flair_fst.compile.glossary import make_glossary
from flair_fst.definition import Definition, TestCase
from flair_fst.fst import RLG, RLGEntry, fromdict, pairs, todict

__all__ = ["FST", "RLG", "RLGEntry", "Definition", "compile_lexicon", "test_lexicon"]


def compile_lexicon(defn: Definition, path: Path) -> None:
    """Compile a definition to an output lexicon."""

    lex = defn.compile()
    with open(path / "morphology.json", "w", encoding="utf-8") as outfh:
        json.dump(todict(lex), outfh, ensure_ascii=False, indent=2)
    speling = make_approx(defn)
    with open(path / "orthography.json", "w", encoding="utf-8") as outfh:
        json.dump(todict(speling), outfh, ensure_ascii=False, indent=2)
    glossary = make_glossary(defn)
    with open(path / "glossary.json", "w", encoding="utf-8") as outfh:
        json.dump(glossary, outfh, ensure_ascii=False, indent=2)
    bib = make_bibliography(defn)
    with open(path / "bibliography.json", "w", encoding="utf-8") as outfh:
        json.dump(bib, outfh, ensure_ascii=False, indent=2)


def test_lexicon(defn: Definition, path: Path) -> List[TestCase]:
    """Test a compiled lexicon, returning a list of mismatches."""
    errors = []
    with open(path / "morphology.json", encoding="utf-8") as infh:
        lex = fromdict(json.load(infh))
        for testcase in defn.tests:
            forms = FST.from_strings([testcase.morph], defn.multichar_symbols)
            forms.compose(make_boundary_inserter()).project(-1)
            forms.compose(lex)
            expected = testcase.form.strip()
            if expected == "":
                if len(forms.finalstates) > 0:
                    errors.append(testcase)
            else:
                for _, form in pairs(forms):
                    if form == expected:
                        break
                else:
                    errors.append(testcase)
    return errors


def make_boundary_inserter() -> FST:
    """Optionally insert word boundaries.

    We can't do this with $^rewrite() because # is used internally in
    its definition (this is probably a bug in pyfoma).
    """
    inserter: FST = FST(alphabet={".", "#"})
    (state0,) = inserter.states
    state0.finalweight = 0
    state1 = State(finalweight=0)
    inserter.states.add(state1)
    inserter.finalstates = {state0, state1}
    state0.add_transition(state0, (".", "."))
    state0.add_transition(state0, ("#", "#"))
    state0.add_transition(state1, ("", "#"))
    state1.add_transition(state0, (".", "."))
    state1.add_transition(state0, ("#", "#"))
    return inserter
