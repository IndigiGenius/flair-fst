# SPDX-FileCopyrightText: 2025-present David Huggins-Daines <dhd@ecolingui.ca>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Some additional FST functions that will make it into pyfoma
"""

import re as pyre
from typing import Dict, List, Union, Tuple

from pyfoma.flag import FlagOp, FlagStringFilter
from pyfoma.fst import FST

# Use this for epsilon labels to be compatible with foma
EPSILON = "@0@"


def escape_state(name: str):
    return pyre.sub(r"\s", "_", name)


def escape_label(sym: str):
    if sym == "":
        return EPSILON
    # FIXME: This is not really going to work!
    return escape_state(sym)


def pairs(fst: FST):
    """
    Yield pairs like foma would do.
    """
    flag_filter = FlagStringFilter(fst.alphabet)
    for _cost, seq in fst.words():
        up, down = [], []
        for tapes in seq:
            up.append(tapes[0])
            down.append(tapes[-1])
        if flag_filter(down):
            yield (
                "".join(sym for sym in up if not FlagOp.is_flag(sym)),
                "".join(sym for sym in down if not FlagOp.is_flag(sym)),
            )


# Type alias for RLG input
RLG = Dict[str, List[Union[Tuple[str, str], Tuple[Tuple[str, str], str]]]]
