"""Command line entry point."""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from . import report
from .runner import compare, load_replies, load_yaml, run_suite


def _load_judge(spec: str | None):
    """Load a judge function given as 'module:function'."""
    if not spec:
        return None
    module_name, _, func_name = spec.partition(":")
    if not func_name:
        raise SystemExit("--judge must look like module:function")
    sys.path.insert(0, str(Path.cwd()))
    return getattr(importlib.import_module(module_name), func_name)


def _cmd_run(args) -> int:
    result = run_suite(load_yaml(args.cases), load_replies(args.replies), _load_judge(args.judge))
    formats = {"text": report.to_text, "markdown": report.to_markdown, "json": report.to_json}
    output = formats[args.format](result)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(output + "\n", encoding="utf-8")
        print(f"Report written to {args.out}")
    else:
        print(output)
    return 0 if result.pass_rate >= args.min_pass_rate else 1


def _cmd_compare(args) -> int:
    suite = load_yaml(args.cases)
    before = run_suite(suite, load_replies(args.before))
    after = run_suite(suite, load_replies(args.after))
    print(f"Before: {before.passed} of {before.total} passed ({before.pass_rate:.0%})")
    print(f"After:  {after.passed} of {after.total} passed ({after.pass_rate:.0%})")
    print()
    groups = compare(before, after)
    print(report.comparison_text(groups))
    return 1 if groups["regressed"] else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="convo-evals", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run a suite against one set of replies")
    run.add_argument("cases", help="YAML file of test cases")
    run.add_argument("--replies", required=True, help="YAML file of recorded replies")
    run.add_argument("--format", choices=["text", "markdown", "json"], default="text")
    run.add_argument("--out", help="write the report to this file")
    run.add_argument("--min-pass-rate", type=float, default=1.0,
                     help="exit with an error below this pass rate, from 0 to 1 (default 1)")
    run.add_argument("--judge", help="judge function as module:function, for 'judge' checks")
    run.set_defaults(func=_cmd_run)

    cmp_ = sub.add_parser("compare", help="compare two sets of replies on the same suite")
    cmp_.add_argument("cases")
    cmp_.add_argument("--before", required=True)
    cmp_.add_argument("--after", required=True)
    cmp_.set_defaults(func=_cmd_compare)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
