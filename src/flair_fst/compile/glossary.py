"""
Make glossary from all lexicon tables.
"""

import itertools

from .definition import Definition
from ..models import Glossary, Gloss

def make_glossary(defn: Definition) -> Glossary:
    """Make output glossary from tables in definition."""
    glosses: Glossary = {}
    for entry in itertools.chain.from_iterable([defn.words, *defn.prefixes.values(), defn.stems, *defn.suffixes.values()]):
        if not entry.glosses:
            continue
        for lang, text in entry.glosses.items():
            # form, base for words and morph, form for others
            morph, form = entry[0:2]
            gloss = Gloss(gloss=text, form=entry[1])
            if entry.ref:
                gloss["ref"] = entry.ref
            if entry.page is not None:
                gloss["page"] = entry.page
            glosses.setdefault(morph, {})[lang] = gloss
    return glosses
