"""
Load an ODS spreadsheet into a WFST definition.
"""

import csv
import logging
from os import PathLike
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union

from openpyxl import load_workbook

from flair_fst import Definition
from flair_fst.definition.csv import load_definition as load_csv_definition

LOG = logging.getLogger(__name__)


def convert_to_csvs(path: Union[str, PathLike], outdir: Union[str, PathLike]) -> None:
    """Dump out worksheets to CSV files in a directory."""
    doc = load_workbook(str(path), read_only=True, data_only=True)
    outdir = Path(outdir)
    for sheet in doc:
        outpath = (outdir / sheet.title.lower()).with_suffix(".csv")
        with open(outpath, "w", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            for row in sheet.rows:
                writer.writerow([cell.value for cell in row])


def load_definition(path: Union[str, PathLike]) -> Definition:
    """Compile a Definition from an XLSX spreadsheet."""
    # The easiest and laziest way to do this: Dump everything to CSV
    # files then use the CSV code (sorry not sorry)
    with TemporaryDirectory() as tempdir:
        convert_to_csvs(path, tempdir)
        return load_csv_definition(tempdir)
