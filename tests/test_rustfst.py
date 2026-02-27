"""Unit testing for rustfst bridge."""

from functools import reduce


from pyfoma import FST
from pyfoma.flag import EMPTY, FlagOp
from flair_fst.fst import pairs
from flair_fst.rustfst import (
    pyfoma2rust,
    eliminate_flags as rusty_eliminator,
    pairs as rusty_pairs,
    get_value_tests,
    StringPathsIterator,
)


def test_eliminate_flags():
    """Make sure rusty_eliminator does what we expect."""
    fst = FST.rlg(
        {
            "Stem": [
                ("'spam'", "Suffix"),
                ("'eggs''[[!$SPAM]]'", "Suffix"),
            ],
            "Suffix": [
                ("'[[$SPAM]]''spam'", "#"),
                ("'eggs'", "#"),
            ],
        },
        "Stem",
    )
    print(str(fst))
    print(list(pairs(fst)))
    assert ("eggsspam", "eggsspam") not in pairs(fst)
    rfst = pyfoma2rust(fst)
    print(str(rfst))
    print(list(rusty_pairs(rfst)))
    assert ("eggsspam", "eggsspam") not in rusty_pairs(rfst)

    fst = fst.eliminate_flags()
    print(str(fst))
    print(list(pairs(fst)))
    assert ("eggsspam", "eggsspam") not in pairs(fst)
    rfst = rusty_eliminator(rfst)
    print(str(rfst))
    print(list(rusty_pairs(rfst)))
    assert ("eggsspam", "eggsspam") not in rusty_pairs(rfst)
