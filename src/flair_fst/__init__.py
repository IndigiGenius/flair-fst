# SPDX-FileCopyrightText: 2025-present David Huggins-Daines <dhd@ecolingui.ca>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Public interface to flair_fst.
"""

from pyfoma import FST
from .fst import RLG

__all__ = ["FST", "RLG"]

