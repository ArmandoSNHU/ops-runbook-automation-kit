from __future__ import annotations

import argparse
import json
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
    runbook = load_runbook(args.runbook)

    if args.command == "validate":
        errors = validate_runbook(runbook)
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        print("Runbook is valid.")
        return 0

    results = run_runbook(runbook, base_dir=args.runbook.parent.parent)

    if args.command == "run":
        indent = 2 if args.pretty else None
        print(json.dumps(results, indent=indent))
        return 0

    if args.command == "render":
        print(render_markdown_report(runbook, results))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

