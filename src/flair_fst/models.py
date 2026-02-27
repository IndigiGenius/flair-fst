"""Data structures for the JSON lexicon format.

Currently a mixture of TypedDict and dataclasses but will migrate to
Pydantic soon.

"""

from typing import Dict, List, Union, Tuple, TypedDict


TransitionsDict = Dict[int, Dict[str, List[Union[int, Tuple[int, float]]]]]


class FSTDict(TypedDict):
    t: TransitionsDict
    f: Dict[int, float]
    s: Dict[str, int]


class Gloss(TypedDict, total=False):
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
