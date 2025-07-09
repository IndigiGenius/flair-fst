"""
Output FSTs and other JSON for web page
"""

import argparse
import csv
import itertools
import json
import logging
from pathlib import Path
from time import time
from typing import Dict, Set, TypedDict

from pyfoma import FST, State  # type: ignore

from flair_fst import rules, lexicon
from flair_fst.fst import RLG, eliminate_flags, tojson
from flair_fst.rustfst import eliminate_flags as rusty_eliminator
from flair_fst.rustfst import pyfoma2rust
from rustfst.algorithms.minimize import MinimizeConfig, minimize_with_config

LOGGER = logging.getLogger(Path(__file__).stem)


class Gloss (TypedDict, total=False):
    gloss: str
    root: str
    ref: str
    page: str


def make_glosses():
    glosses = {}
    for path in itertools.chain(
        (DATADIR / "roots").glob("*.csv"),
        (DATADIR / "clitics").glob("*.csv"),
        (DATADIR / "suffixes").glob("*.csv"),
    ):
        with open(path, "rt", encoding="utf-8-sig") as infh:
            reader = csv.DictReader(infh)
            if "gloss" in reader.fieldnames:
                for row in reader:
                    if "form" not in row:
                        continue
                    if row["gloss"]:
                        gloss = Gloss(gloss=row["gloss"].replace("<", "&lt;"))
                        for field in "root", "ref", "page":
                            if row.get(field):
                                gloss[field] = row[field]
                        glosses[row["form"]] = gloss
            elif "description" in reader.fieldnames:
                for row in reader:
                    if "morph" not in row:
                        continue
                    if row.get("description"):
                        gloss = Gloss(gloss=row["description"].replace("<", "&lt;"))
                        if row.get("citation"):
                            gloss["ref"] = row["citation"]
                        if row.get("page"):
                            gloss["page"] = row["page"]
                        if row.get("form"):
                            gloss["root"] = row["form"]
                        glosses[row["morph"]] = gloss
    return glosses


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


def make_fst_rust(file_filter: str = ".*", root_filter: str = ".*") -> FST:
    """Compile the complete FST from lexicon and rules, faster."""
    start = time()
    lex = lexicon.make_lexicon(file_filter=file_filter, root_filter=root_filter)
    cvs = extract_cvs(lex)
    LOGGER.info("Make lexicon: %.1fms", (time() - start) * 1000)
    start = time()
    fst = FST.rlg(lex, "Word")
    rfst = rusty_eliminator(pyfoma2rust(fst, alphabet=lexicon.ALPHABET))
    LOGGER.info(
        "Compile lexicon: %.1fms (%d states)",
        (time() - start) * 1000,
        rfst.num_states(),
    )
    start = time()
    for _, regex in rules.make_templates(cvs):
        rregex = pyfoma2rust(regex, symtab=rfst.input_symbols())
        rfst.tr_sort(False)
        rfst = rfst.compose(rregex)
    LOGGER.info(
        "Apply templates: %.1fms (%d states)",
        (time() - start) * 1000,
        rfst.num_states(),
    )
    start = time()
    # Don't forget to delete the templates!
    detemplate = rules.rule("$^rewrite(($T):'')")
    rregex = pyfoma2rust(detemplate, symtab=rfst.input_symbols())
    rfst.tr_sort(False)
    rfst = rfst.compose(rregex)
    LOGGER.info(
        "Delete templates: %.1fms (%d states)",
        (time() - start) * 1000,
        rfst.num_states(),
    )
    start = time()
    for regex in rules.RULES:
        rregex = pyfoma2rust(regex, symtab=rfst.input_symbols())
        rfst.tr_sort(False)
        rfst = rfst.compose(rregex)
    LOGGER.info(
        "Apply rules: %.1fms (%d states)", (time() - start) * 1000, rfst.num_states()
    )
    start = time()
    # Do not try to determinize, it will not terminate, and the resulting FST is big
    rfst.rm_epsilon()
    minimize_with_config(rfst, MinimizeConfig(allow_nondet=True))
    LOGGER.info(
        "Optimize: %.1fms (%d states)", (time() - start) * 1000, rfst.num_states()
    )
    # We will... uh, just convert it back to a pyfoma FST for the
    # moment (but seriously dumping out a rustfst as json is really
    # easy, and also should be in rustfst)
    symtab = rfst.input_symbols()
    if symtab is None:
        raise ValueError("FST somehow has no symbol table?!?")
    alphabet = set(sym for idx, sym in symtab if idx != 0)
    alphabet.add("")
    fst = FST(alphabet=alphabet)
    states: Dict[int, State] = {}

    def add_state(s: int) -> State:
        if s in states:
            return states[s]
        states[s] = State()
        if rfst.is_start(s):
            fst.initialstate = states[s]
        if rfst.is_final(s):
            fst.finalstates.add(states[s])
            state.finalweight = rfst.final(s)
        fst.states.add(states[s])
        return states[s]

    for s in rfst.states():
        assert s is not None  # WTF
        state = add_state(s)
        for tr in rfst.trs(s):
            assert tr is not None  # WTF
            target = add_state(tr.next_state)
            ilabel = "" if tr.ilabel == 0 else symtab.find(tr.ilabel)
            olabel = "" if tr.olabel == 0 else symtab.find(tr.olabel)
            state.add_transition(target, (ilabel, olabel), tr.weight)
    return fst


def make_fst(file_filter: str = ".*", root_filter: str = ".*"):
    """Compile the complete FST from lexicon and rules."""
    start = time()
    lex = lexicon.make_lexicon(file_filter=file_filter, root_filter=root_filter)
    cvs = extract_cvs(lex)
    LOGGER.info("Make lexicon: %.1fms", (time() - start) * 1000)
    start = time()
    lexfst = (
        eliminate_flags(FST.rlg(lex, "Word")).epsilon_remove().determinize().minimize()
    )  # type: ignore
    LOGGER.info("Compile lexicon: %.1fms", (time() - start) * 1000)
    start = time()
    templatefst = rules.make_template_fst(cvs)
    lexfst = lexfst.compose(templatefst).epsilon_remove().determinize().minimize()  # type: ignore
    LOGGER.info("Apply templates: %.1fms", (time() - start) * 1000)
    start = time()
    rulefst = rules.make_fst()
    LOGGER.info("Make rules: %.1fms", (time() - start) * 1000)
    start = time()
    fst = lexfst.compose(rulefst).epsilon_remove().determinize().minimize()  # type: ignore
    LOGGER.info("Apply rules: %.1fms", (time() - start) * 1000)
    return fst


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file-filter", help="Limit vocabulary files by regex", default=".*"
    )
    parser.add_argument("--root-filter", help="Limit word roots by regex", default=".*")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    lexfst = make_fst_rust(file_filter=args.file_filter, root_filter=args.root_filter)
    with open("js/lex.json", "wt") as outfh:
        outfh.write(tojson(lexfst))
    approxfst = make_approx()
    approx_json = tojson(approxfst)
    with open("js/approx.json", "wt") as outfh:
        outfh.write(approx_json)
    glosses = make_glosses()
    with open("js/gloss.json", "wt") as outfh:
        json.dump(glosses, outfh, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
