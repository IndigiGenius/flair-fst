"""
Make rules from table.
"""

from typing import Dict
from pyfoma import FST

from .definition import Definition


def make_rules(defn: Definition) -> Dict[str, FST]:
    """Create an (ordered) dictionary of rules from the definition."""
    rules = {}
    for name, rule in defn.rules.items():
        rules[name] = FST.regex(rule.regex)
    return rules
