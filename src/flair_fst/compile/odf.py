"""
Load an ODS spreadsheet into a WFST definition.
"""

import csv
import logging
from os import PathLike
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union
from odfdo import Document
from .definition import Definition
from .csv import load_definition as load_csv_definition

LOGGER = logging.getLogger(Path(__file__).stem)


def convert_to_csvs(path: Union[str, PathLike], outdir: Union[str, PathLike]) -> None:
    """Dump out worksheets to CSV files in a directory."""
    doc = Document(Path(path))
    outdir = Path(outdir)
    for s in doc.body.sheets:
        if s.name is None:
            continue
        s.optimize_width()
        outpath = (outdir / s.name.lower()).with_suffix(".csv")
        with open(outpath, "w", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            for row in s.iter_rows():
                writer.writerow([cell.value for cell in row.cells])


def load_definition(path: Union[str, PathLike]) -> Definition:
    """Compile a Definition from an ODF spreadsheet."""
    # The easiest and laziest way to do this: Dump everything to CSV
    # files then use the CSV code (sorry not sorry)
    with TemporaryDirectory() as tempdir:
        convert_to_csvs(path, tempdir)
        return load_csv_definition(tempdir)
