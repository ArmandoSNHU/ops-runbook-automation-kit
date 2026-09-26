from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .checks import load_runbook, render_markdown_report, run_runbook, validate_runbook


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate, run, and render safe IT runbooks.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("validate", "run", "render"):
        sub = subparsers.add_parser(command)
        sub.add_argument("runbook", type=Path)
        if command == "run":
            sub.add_argument("--pretty", action="store_true")

    args = parser.parse_args()
    try:
        runbook = load_runbook(args.runbook)
    except (OSError, UnicodeError, ValueError):
        print("ERROR: Unable to read runbook as UTF-8 JSON.", file=sys.stderr)
        return 2

    errors = validate_runbook(runbook)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if args.command == "validate":
        print("Runbook is valid.")
        return 0

    try:
        results = run_runbook(runbook, base_dir=args.runbook.parent.parent)
    except (OSError, UnicodeError, ValueError):
        print("ERROR: Unable to execute runbook; check targets and access permissions.", file=sys.stderr)
        return 2

    if args.command == "run":
        indent = 2 if args.pretty else None
        print(json.dumps(results, indent=indent))
    else:
        print(render_markdown_report(runbook, results))
    return 0 if all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
