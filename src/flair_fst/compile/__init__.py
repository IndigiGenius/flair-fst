"""
Compile a set of tables into a WFST.

The input may come as a spreadsheet (ODS or XLSX) or as a directory of CSV files.
"""

import logging
from pathlib import Path
from .definition import Definition

LOGGER = logging.getLogger(Path(__file__).stem)
__all__ = ["Definition"]
