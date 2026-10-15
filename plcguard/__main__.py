"""Command line: python -m plcguard {scan,eval} ..."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import rules
from .evaluate import evaluate, load_dataset, to_markdown
from .obfuscate import obfuscate
from .st_parser import STParseError
from .taxonomy import CWE

ROOT = Path(__file__).resolve().parent.parent
DETECTORS = {"rules": rules.check}


def _st_files(paths: list[str]) -> list[Path]:
    files = []
    for p in map(Path, paths):
        files.extend(sorted(p.glob("*.st")) if p.is_dir() else [p])
    return files


def cmd_scan(args) -> int:
    detector = DETECTORS[args.detector]
    results, exit_code = {}, 0
    for path in _st_files(args.paths):
        try:
            findings = detector(path.read_text(encoding="utf-8"))
        except STParseError as exc:
            print(f"{path}: parse error: {exc}", file=sys.stderr)
            exit_code = 2
            continue
        results[str(path)] = [f.to_dict() for f in findings]
        if findings:
            exit_code = max(exit_code, 1)
        if not args.json:
            for f in findings:
                print(f"{path}:{f.line}: [{f.vuln_type} {CWE[f.vuln_type]}] {f.message}")
    if args.json:
        print(json.dumps(results, indent=2))
    elif exit_code == 0:
        print("no findings")
    return exit_code


def cmd_eval(args) -> int:
    programs = load_dataset(Path(args.dataset))
    if args.variant == "obfuscated":
        for prog in programs:
            prog.source = obfuscate(prog.source)
    report = evaluate(DETECTORS[args.detector], programs, args.line_tolerance)
    name = f"{args.detector}_{args.variant}"
    md = to_markdown(report, f"PLCGuard evaluation: {args.detector} ({args.variant} dataset)")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / f"{name}.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="plcguard",
                                 description="Detect vulnerabilities in IEC 61131-3 ST code")
    sub = ap.add_subparsers(dest="cmd", required=True)

    scan = sub.add_parser("scan", help="scan .st files or directories")
    scan.add_argument("paths", nargs="+")
    scan.add_argument("--detector", choices=DETECTORS, default="rules")
    scan.add_argument("--json", action="store_true")
    scan.set_defaults(func=cmd_scan)

    ev = sub.add_parser("eval", help="benchmark a detector on the labeled dataset")
    ev.add_argument("--detector", choices=DETECTORS, default="rules")
    ev.add_argument("--dataset", default=str(ROOT / "dataset"))
    ev.add_argument("--out", default=str(ROOT / "results"))
    ev.add_argument("--line-tolerance", type=int, default=1)
    ev.add_argument("--variant", choices=["original", "obfuscated"], default="original",
                    help="'obfuscated' renames every variable to v1, v2, ...")
    ev.set_defaults(func=cmd_eval)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
