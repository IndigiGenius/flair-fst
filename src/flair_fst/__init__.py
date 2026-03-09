# SPDX-FileCopyrightText: 2025-present David Huggins-Daines <dhd@ecolingui.ca>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Public interface to flair_fst.
"""

import json
from pathlib import Path
from typing import List, Tuple

from pyfoma import FST

from .compile.approx import make_approx
from .compile.bibliography import make_bibliography
from .compile.glossary import make_glossary
from .definition import Definition
from .fst import RLG, RLGEntry, todict

__all__ = ["FST", "RLG", "RLGEntry", "Definition", "compile_lexicon"]


def compile_lexicon(defn: Definition, path: Path) -> None:
    """Compile a definition to an output lexicon."""

    lex = defn.compile()
    with open(path / "morphology.json", "w") as outfh:
        json.dump(todict(lex), outfh, ensure_ascii=False, indent=2)
    speling = make_approx(defn)
    with open(path / "orthography.json", "w") as outfh:
        json.dump(todict(speling), outfh, ensure_ascii=False, indent=2)
    glossary = make_glossary(defn)
    with open(path / "glossary.json", "w") as outfh:
        json.dump(glossary, outfh, ensure_ascii=False, indent=2)
    bib = make_bibliography(defn)
    with open(path / "bibliography.json", "w") as outfh:
        json.dump(bib, outfh, ensure_ascii=False, indent=2)
