#!/usr/bin/env python3
"""CLI adapter for local, host-driven Golden-case Eval checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lib import golden_eval


def _default_root(case_path: str) -> Path:
    case = Path(case_path).resolve()
    return case.parent.parent if case.parent.name == "cases" else case.parent


def _emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    else:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate local Golden-case Eval evidence without model APIs.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    validate = subcommands.add_parser("validate-case")
    validate.add_argument("--file", required=True)
    validate.add_argument("--root")
    validate.add_argument("--json", action="store_true")
    brief = subcommands.add_parser("brief")
    brief.add_argument("--case", required=True)
    brief.add_argument("--root")
    brief.add_argument("--json", action="store_true")
    check = subcommands.add_parser("check")
    check.add_argument("--case", required=True)
    check.add_argument("--receipt", required=True)
    check.add_argument("--root")
    check.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "validate-case":
        result = golden_eval.validate_case(args.file, args.root or _default_root(args.file))
        _emit(result, args.json)
        return 0 if result["valid"] else 1
    if args.command == "brief":
        result = golden_eval.validate_case(args.case, args.root or _default_root(args.case))
        if not result["valid"]:
            _emit(result, args.json)
            return 1
        case, _fixture_digests, digest = golden_eval.load_valid_case(args.case, args.root or _default_root(args.case))
        if args.json:
            _emit({"case_id": case["case_id"], "case_digest": digest, "brief": golden_eval.render_brief(case, digest)}, True)
        else:
            print(golden_eval.render_brief(case, digest))
        return 0
    result = golden_eval.check_receipt(args.case, args.receipt, args.root or _default_root(args.case))
    _emit(result, args.json)
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
