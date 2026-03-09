#!/usr/bin/env python3

"""Command-line tool for FLAIR-FST.

Compiles and runs WFST models from spreadsheet descriptions.

This functionality is also available directly in the FLAIR-FST library
and from its REST API.

"""

import argparse
import html
import json
import logging
from pathlib import Path
from typing import TextIO

from flair_fst.models import Bibliography, Glossary

LOG = logging.getLogger("flair-fst")
ASSETS = Path(__file__).parent / "assets"


def new_command(args: argparse.Namespace) -> None:
    """Create a new template spreadsheet or CSV directory."""
    import shutil

    template = ASSETS / "template.ods"
    if args.output.suffix == "":
        from flair_fst.definition.odf import convert_to_csvs

        args.output.mkdir(exist_ok=True, parents=True)
        convert_to_csvs(template, args.output)
    elif args.output.suffix.lower() == ".ods":
        shutil.copy(template, args.output)
    elif args.output.suffix.lower() == ".xlsx":
        shutil.copy(template.with_suffix(".xlsx"), args.output)
    else:
        raise RuntimeError(
            f"Unrecognized or unsupported extension {args.output.suffix}"
        )


def compile_command(args: argparse.Namespace) -> None:
    """Compile a spreadsheet into a WFST."""
    from flair_fst import Definition, compile_lexicon, test_lexicon

    defn = Definition.from_path(args.input)
    if args.output is None:
        args.output = args.input.with_suffix(".flairfst")
    args.output.mkdir(exist_ok=args.force)

    compile_lexicon(defn, args.output)
    if not args.no_test:
        errors = test_lexicon(defn, args.output)
        for testcase in errors:
            LOG.error("Test case failed: %r", testcase)


def run_command(args: argparse.Namespace) -> None:
    """Run a WFST in the browser."""
    import threading
    import webbrowser
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    from pathlib import Path

    assets = Path(__file__).parent / "assets"

    class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *_args, **_kwargs):
            super().__init__(*_args, directory=assets, **_kwargs)

        def translate_path(self, path):
            path = super().translate_path(path)
            before, _, after = path.partition("@LEXICON@/")
            if after:
                lexpath = (args.lexdir / Path(after)).resolve()
                return str(lexpath)
            return path

    address = "127.0.0.1"
    server = HTTPServer((address, args.port), CustomHTTPRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    webbrowser.open(f"http://{address}:{args.port}")


def html_command(args: argparse.Namespace) -> None:
    """Compile a WFST into a standalone HTML tool.

    This tool is also formatted semantically such that the glossary
    and bibliography can be viewed without the accompanying
    Javascript code to run the WFST.
    """
    if args.output is None:
        args.output = args.input.with_suffix(".html")

    # Split the HTML in a few places (this is a bit fragile, take care
    # not to reformat it!)
    html = (ASSETS / "index.html").read_text(encoding="utf-8")
    with open(args.output, "w", encoding="utf-8") as outfh:
        before, _, html = html.partition('<link rel="stylesheet" href="style.css" />')
        outfh.write(before)
        outfh.write('<style type="text/css">\n')
        outfh.write((ASSETS / "style.css").read_text(encoding="utf-8"))
        outfh.write("</style>\n")
        before, _, html = html.partition(
            '<script type="module" src="flair-fst.js"></script>'
        )
        outfh.write(before)
        outfh.write('<script type="module">\n')
        outfh.write((ASSETS / "flair-fst.js").read_text(encoding="utf-8"))
        outfh.write("</script>\n")
        before, _, html = html.partition('<flair-fst base="@LEXICON@"></flair-fst>')
        outfh.write(before)
        outfh.write("""<flair-fst>
        <script class="orthography" type="application/json">
""")
        # TODO: Escape comments and script tags (**very** unlikely to
        # happen), see
        # https://html.spec.whatwg.org/multipage/scripting.html#restrictions-for-contents-of-script-elements
        outfh.write((args.input / "orthography.json").read_text(encoding="utf-8"))
        outfh.write("""
        </script>
        <script class="morphology" type="application/json">
""")
        outfh.write((args.input / "morphology.json").read_text(encoding="utf-8"))
        outfh.write("""
        </script>""")
        # Glossary and bibliography are formatted as <dl>
        with open(args.input / "glossary.json") as infh:
            # TODO: validate with Pydantic if necessary
            glossary: Glossary = json.load(infh)
            make_dl_glossary(glossary, outfh)
        with open(args.input / "bibliography.json") as infh:
            # TODO: validate with Pydantic if necessary
            bibliography: Bibliography = json.load(infh)
            make_dl_bibliography(bibliography, outfh)
        outfh.write("""
        </flair-fst>""")
        outfh.write(html)


def make_dl_glossary(glossary: Glossary, outfh: TextIO) -> None:
    outfh.write("""
    <dl class="glossary">""")
    for morph, glosses in glossary.items():
        outfh.write(f"""
        <dt>{html.escape(morph)}</dt> """)
        for lang, gloss in glosses.items():
            tag = "<dd"
            if lang != "_default":
                tag += f' lang="{html.escape(lang)}"'
            if ref := gloss.get("ref"):
                tag += f' data-ref="{html.escape(ref)}"'
            if page := gloss.get("page"):
                tag += f' data-page="{html.escape(page)}"'
            if form := gloss.get("form"):
                tag += f' data-form="{html.escape(form)}"'
            tag += ">"
            outfh.write(f"""
        {tag}{html.escape(gloss["gloss"])}</dd>""")
    outfh.write("""
    </dl>""")


def make_dl_bibliography(bibliography: Bibliography, outfh: TextIO) -> None:
    outfh.write("""
    <dl class="bibliography">""")
    for abbrev, defn in bibliography.items():
        outfh.write(f"""
        <dt>{html.escape(abbrev)}</dt>""")
        if url := defn.get("url"):
            outfh.write(
                f"""
        <dd data-page-offset="{defn["pageOffset"]}"><a href="{url}">{html.escape(defn["citation"])}</a></dd>"""
            )
        else:
            outfh.write(
                f"""
        <dd data-page-offset="{defn["pageOffset"]}">{html.escape(defn["citation"])}</dd>"""
            )
    outfh.write("""
    </dl>""")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")

    new_parser = subparsers.add_parser(
        "new", help="Create template spreadsheet or CSV files"
    )
    new_parser.add_argument(
        "output",
        type=Path,
        help="Path to new template, with format determined by extension",
    )
    new_parser.set_defaults(func=new_command)

    compile_parser = subparsers.add_parser(
        "compile", help="Compile spreadsheet to WFST lexicon"
    )
    compile_parser.add_argument(
        "input", type=Path, help="Input spreadsheet, either ODS or directory of CSV"
    )
    compile_parser.add_argument(
        "-o", "--output", type=Path, help="Output WFST directory (optional)"
    )
    compile_parser.add_argument(
        "-f", "--force", action="store_true", help="Overwrite output directory"
    )
    compile_parser.add_argument("--no-test", help="Do not run tests")
    compile_parser.set_defaults(func=compile_command)

    run_parser = subparsers.add_parser("run", help="Run a WFST lexicon in the browser")
    run_parser.add_argument("lexdir", help="Lexicon directory")
    run_parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8080,
        help="Port for the HTTP server (default: 8080)",
    )
    run_parser.add_argument(
        "-b", "--browser", action="store_true", help="Open in default browser"
    )
    run_parser.set_defaults(func=run_command)

    html_parser = subparsers.add_parser(
        "html", help="Compile a WFST into a standalone HTML tool"
    )
    html_parser.add_argument("input", type=Path, help="Input lexicon directory")
    html_parser.add_argument(
        "-o", "--output", type=Path, help="Output HTML file (optional)"
    )
    html_parser.set_defaults(func=html_command)

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)

    if not hasattr(args, "func"):
        parser.print_help()
        parser.exit(status=2, message="Please specify a command.\n")

    try:
        args.func(args)
    except (FileExistsError, RuntimeError) as e:
        parser.error(str(e))


if __name__ == "__main__":
    main()
