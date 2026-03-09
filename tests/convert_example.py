"""Convert example spreadsheets to CSVs."""

from pathlib import Path

from flair_fst.definition.odf import convert_to_csvs


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ods", help="ODS file input", type=Path)
    parser.add_argument("outdir", help="CSV output directory", type=Path)
    args = parser.parse_args()

    args.outdir.mkdir(exist_ok=True, parents=True)
    convert_to_csvs(args.ods, args.outdir)


if __name__ == "__main__":
    main()
