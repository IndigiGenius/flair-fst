#!/usr/bin/env python3

"""Command-line tool for FLAIR-FST.

Compiles and runs WFST models from spreadsheet descriptions.

This functionality is also available directly in the FLAIR-FST library
and from its REST API.

"""

import argparse
import logging
from pathlib import Path
from typing import NoReturn, Optional

LOG = logging.getLogger("flair-fst")


def compile_command(args: argparse.Namespace) -> None:
    """Compile a spreadsheet into a WFST."""
    # Placeholder for actual implementation
    pass


def run_command(args: argparse.Namespace) -> None:
    """Run a WFST in the browser."""
    # Placeholder for actual implementation
    pass


def html_command(args: argparse.Namespace) -> None:
    """Compile a WFST into a standalone HTML tool."""
    # Placeholder for actual implementation
    pass


def derive_command(args: argparse.Namespace) -> None:
    """Derive a spreadsheet from a MinCourse."""
    # Placeholder for actual implementation
    pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")

    # Compile subcommand
    compile_parser = subparsers.add_parser("compile", help="Compile spreadsheet to WFST lexicon")
    compile_parser.add_argument("input", help="Input spreadsheet in ODS format")
    compile_parser.add_argument("-o", "--output", type=Path, help="Output WFST directory (optional)")
    compile_parser.set_defaults(func=compile_command)

    # Run subcommand
    run_parser = subparsers.add_parser("run", help="Run a WFST lexicon in the browser")
    run_parser.add_argument("lexdir", help="Lexicon directory")
    run_parser.add_argument("-p", "--port", type=int, default=8080, help="Port for the HTTP server (default: 8080)")
    run_parser.add_argument("-b", "--browser", action="store_true", help="Open in default browser")
    run_parser.set_defaults(func=run_command)

    # HTML subcommand
    html_parser = subparsers.add_parser("html", help="Compile a WFST into a standalone HTML tool")
    html_parser.add_argument("input", help="Input lexicon directory")
    html_parser.add_argument("-o", "--output", type=Path, help="Output HTML file (optional)")
    html_parser.set_defaults(func=html_command)

    # Derive subcommand
    derive_parser = subparsers.add_parser("derive", help="Derive spreadsheet from MinCourse")
    derive_parser.add_argument("input", help="Input in MinCourse XML format")
    derive_parser.add_argument("-o", "--output", type=Path, help="Output spreadsheet file (optional)")
    derive_parser.set_defaults(func=derive_command)

    args = parser.parse_args()
    
    if not hasattr(args, 'func'):
        parser.print_help()
        parser.exit(status=2, message="Please specify a command.\n")
    
    args.func(args)


if __name__ == '__main__':
    main()
