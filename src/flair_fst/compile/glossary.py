"""
Make glossary from all lexicon tables.
"""

import itertools
from typing import List, Union

from flair_fst.definition import Definition, MorphDefinition, WordDefinition
from flair_fst.models import Gloss, Glossary


def make_glossary(defn: Definition) -> Glossary:
    """Make output glossary from tables in definition."""
    glosses: Glossary = {}
    entry: Union[WordDefinition, MorphDefinition]
    tables: List = [
        defn.words,
        *defn.prefixes.values(),
        defn.stems,
        *defn.suffixes.values(),
    ]
    for entry in itertools.chain.from_iterable(tables):
        if not entry.glosses:
            continue
        for lang, text in entry.glosses.items():
            # form, base for words and morph, form for others
            morph, form = entry[0:2]
            gloss = Gloss(gloss=text, form=form)
            if entry.ref:
                gloss["ref"] = entry.ref
            if entry.page is not None:
                gloss["page"] = str(entry.page)
            glosses.setdefault(morph, {})[lang] = gloss
    return glosses
