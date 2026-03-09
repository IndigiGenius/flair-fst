"""
Make rules from table.
"""

from typing import Dict

from pyfoma import FST

from flair_fst import Definition


def make_rules(defn: Definition) -> Dict[str, FST]:
    """Create an (ordered) dictionary of rules from the definition."""
    rules = {}
    syms = defn.multichar_symbols or None
    for name, rule in defn.rules.items():
        rules[name] = FST.regex(rule.regex, multichar_symbols=syms)
    return rules
