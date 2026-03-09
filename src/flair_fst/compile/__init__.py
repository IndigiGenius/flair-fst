"""Compile a definition into a WFST."""

import logging
import time

from pyfoma import FST

from flair_fst.definition import Definition

LOG = logging.getLogger(__name__)


def compile(defn: Definition) -> FST:
    """Compile an FST from a definition."""
    from flair_fst.compile.lexicon import make_lexicon
    from flair_fst.compile.rules import make_rules

    lex: FST = make_lexicon(defn).eliminate_flags()  # type: ignore
    rules = make_rules(defn)
    for name, rule in rules.items():
        lex.compose(rule)  # type: ignore
    return lex


def rusty_compile(defn: Definition) -> FST:
    """Compile an FST from a definition."""
    from flair_fst.compile.lexicon import make_lexicon
    from flair_fst.compile.rules import make_rules
    from flair_fst.rustfst import (
        eliminate_flags,
        pyfoma2rust,
        rust2pyfoma,
    )
    from flair_fst.rustfst.algorithms.minimize import (
        MinimizeConfig,
        minimize_with_config,
    )

    start = time.time()
    lex: FST = make_lexicon(defn)
    LOG.info("Make lexicon: %.1fms", (time.time() - start) * 1000)
    start = time.time()
    rules = make_rules(defn)
    # Define the full alphabet so that '.' will work properly (we hope)
    for rule in rules.values():
        lex.alphabet.update(rule.alphabet)
    LOG.info("Make rules: %.1fms", (time.time() - start) * 1000)
    start = time.time()
    rlex = pyfoma2rust(lex)
    rlex = eliminate_flags(rlex)
    LOG.info(
        "Compile lexicon: %.1fms (%d states)",
        (time.time() - start) * 1000,
        rlex.num_states(),
    )
    for name, rule in rules.items():
        rregex = pyfoma2rust(rule, symtab=rlex.input_symbols())
        rlex.tr_sort(False)
        rlex = rlex.compose(rregex)
    LOG.info(
        "Apply rules: %.1fms (%d states)",
        (time.time() - start) * 1000,
        rlex.num_states(),
    )
    start = time.time()
    rlex.rm_epsilon()
    minimize_with_config(rlex, MinimizeConfig(allow_nondet=True))
    LOG.info(
        "Optimize: %.1fms (%d states)",
        (time.time() - start) * 1000,
        rlex.num_states(),
    )
    # TODO: Add save to JSON functionality directly from rustfst
    return rust2pyfoma(rlex)
