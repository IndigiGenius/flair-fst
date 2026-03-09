"""Make bibliography from bibliography table.

This doesn't do much of anything for the moment as the bibliography is
already basically in the right format.
"""

from flair_fst.definition import Definition
from flair_fst.models import Bibliography, BibliographyRecord


def make_bibliography(defn: Definition) -> Bibliography:
    """Make output bibliography from tables in definition."""
    return {
        name: BibliographyRecord(
            url=entry.url, citation=entry.citation, pageOffset=entry.page_offset
        )
        for name, entry in defn.bibliography.items()
    }
