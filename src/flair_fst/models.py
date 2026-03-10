"""Data structures for the JSON lexicon format.

Currently a mixture of TypedDict and dataclasses but will migrate to
Pydantic soon.

"""

# SPDX-FileCopyrightText: 2025-present IndigiGenius
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, List, Tuple, TypedDict, Union

__all__ = ["Orthography", "Morphology", "Glossary", "Gloss", "Bibliography"]

TransitionsDict = Dict[int, Dict[str, List[Union[int, Tuple[int, float]]]]]


class FSTDict(TypedDict):
    t: TransitionsDict
    f: Dict[int, float]
    s: Dict[str, int]


Orthography = FSTDict
Morphology = FSTDict


class Gloss(TypedDict, total=False):
    """Glossary entry."""

    gloss: str
    form: str
    ref: str
    page: str


Glossary = Dict[str, Dict[str, Gloss]]


class BibliographyRecord(TypedDict):
    """Bibliography entry."""

    url: str
    citation: str
    pageOffset: int


Bibliography = Dict[str, BibliographyRecord]
