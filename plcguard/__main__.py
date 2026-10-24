"""Command line: python -m plcguard {scan,eval,summary} ..."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

from . import rules
from .evaluate import evaluate, load_dataset, to_markdown
from .llm import DEFAULT_CACHE, PROVIDERS, LLMClient, LLMError
from .llm_detector import PROMPT_VERSION, HybridDetector, LLMDetector, prompt_fingerprint
from .obfuscate import obfuscate
from .st_parser import STParseError
from .taxonomy import CWE
from .tracking import aggregate, log_run, manifest, read_runs, summary_markdown

ROOT = Path(__file__).resolve().parent.parent
DETECTORS = ["rules", "llm", "hybrid"]


def make_client(args) -> LLMClient | None:
    if args.detector == "rules":
        return None
    return LLMClient(args.provider, args.model or "", temperature=args.temperature,
                     cache_dir=None if args.no_cache else DEFAULT_CACHE)


def make_detector(args, client: LLMClient | None, sample: int = 0):
    if client is None:
        return rules.check
    return (LLMDetector if args.detector == "llm" else HybridDetector)(client, sample)


def run_name(args, client: LLMClient | None) -> str:
    if client is None:
        return "rules"
    slug = re.sub(r"[^A-Za-z0-9.]+", "-", client.model).strip("-")
    return f"{args.detector}_{slug}"


def _st_files(paths: list[str]) -> list[Path]:
    files = []
    for p in map(Path, paths):
        files.extend(sorted(p.glob("*.st")) if p.is_dir() else [p])
    return files


def cmd_scan(args) -> int:
    detector = make_detector(args, make_client(args))
    results, exit_code = {}, 0
    for path in _st_files(args.paths):
        try:
            findings = detector(path.read_text(encoding="utf-8"))
        except (STParseError, LLMError) as exc:
            print(f"{path}: error: {exc}", file=sys.stderr)
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
    dataset = Path(args.dataset)
    programs = load_dataset(dataset)
    if args.variant == "obfuscated":
        for prog in programs:
            prog.source = obfuscate(prog.source)
    client = make_client(args)
    repeats = 1 if client is None else args.repeats  # the rules are deterministic

    t0, reports = time.monotonic(), []
    for i in range(repeats):
        report = evaluate(make_detector(args, client, i), programs, args.line_tolerance)
        if report["parse_errors"] == len(programs):
            print(f"every program failed, no report written: "
                  f"{report['programs'][0]['error']}", file=sys.stderr)
            return 2
        reports.append(report)
        if repeats > 1:
            print(f"repeat {i + 1}/{repeats}: F1 {report['micro']['f1']:.2f}", file=sys.stderr)

    config = {"detector": args.detector, "variant": args.variant,
              "line_tolerance": args.line_tolerance, "repeats": repeats,
              "clean_files": reports[0]["file_level"]["clean_files"],
              "wall_seconds": round(time.monotonic() - t0, 1)}
    if client is not None:
        config.update(provider=client.provider, model=client.model,
                      temperature=client.temperature, prompt_version=PROMPT_VERSION,
                      prompt_hash=prompt_fingerprint(), llm_calls=client.calls,
                      cache_hits=client.cache_hits)
    run = manifest(config, dataset)
    run["metrics"] = aggregate(reports)

    name = run_name(args, client)
    report = {**reports[0], "run": run, "repeat_reports": reports[1:]}
    md = to_markdown(reports[0], f"PLCGuard evaluation: {name} ({args.variant} dataset)")
    md += _run_markdown(run)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}_{args.variant}.json").write_text(json.dumps(report, indent=2),
                                                     encoding="utf-8")
    (out / f"{name}_{args.variant}.md").write_text(md, encoding="utf-8")
    if not args.no_log:
        log_run(run, out / "runs.jsonl")
    print(md)
    if client is not None:
        print(f"LLM requests: {client.calls}, cache hits: {client.cache_hits}",
              file=sys.stderr)
    return 0


def _run_markdown(run: dict) -> str:
    m = run["metrics"]
    lines = ["", "## Run", ""]
    if m["n"] > 1:
        lines.append(f"Tables above are repeat 1 of {m['n']}. Across repeats: "
                     f"F1 {m['f1']['mean']:.2f} ± {m['f1']['std']:.2f}, "
                     f"recall {m['recall']['mean']:.2f} ± {m['recall']['std']:.2f}, "
                     f"precision {m['precision']['mean']:.2f} ± {m['precision']['std']:.2f}.")
        lines.append("")
    keys = ["timestamp", "git_commit", "git_dirty", "dataset_hash", "provider", "model",
            "temperature", "prompt_version", "prompt_hash", "repeats", "llm_calls",
            "cache_hits", "wall_seconds"]
    lines += [f"- {k}: `{run[k]}`" for k in keys if k in run]
    return "\n".join(lines) + "\n"


def cmd_summary(args) -> int:
    out = Path(args.out)
    md = summary_markdown(read_runs(out / "runs.jsonl"))
    (out / "SUMMARY.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


def cmd_models(args) -> int:
    try:
        ids = LLMClient(args.provider, cache_dir=None).list_models()
    except LLMError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("\n".join(i for i in ids if args.filter.lower() in i.lower()))
    return 0


def _llm_args(p):
    p.add_argument("--detector", choices=DETECTORS, default="rules")
    p.add_argument("--provider", choices=PROVIDERS, default="gemini")
    p.add_argument("--model", help="model id (default: provider default or $PLCGUARD_MODEL)")
    p.add_argument("--no-cache", action="store_true", help="always call the API")
    p.add_argument("--temperature", type=float, default=0.0)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="plcguard",
                                 description="Detect vulnerabilities in IEC 61131-3 ST code")
    sub = ap.add_subparsers(dest="cmd", required=True)

    scan = sub.add_parser("scan", help="scan .st files or directories")
    scan.add_argument("paths", nargs="+")
    _llm_args(scan)
    scan.add_argument("--json", action="store_true")
    scan.set_defaults(func=cmd_scan)

    ev = sub.add_parser("eval", help="benchmark a detector on the labeled dataset")
    _llm_args(ev)
    ev.add_argument("--dataset", default=str(ROOT / "dataset"))
    ev.add_argument("--out", default=str(ROOT / "results"))
    ev.add_argument("--line-tolerance", type=int, default=1)
    ev.add_argument("--variant", choices=["original", "obfuscated"], default="original",
                    help="'obfuscated' renames every variable to v1, v2, ...")
    ev.add_argument("--repeats", type=int, default=1,
                    help="independent LLM runs, reported as mean ± std")
    ev.add_argument("--no-log", action="store_true", help="don't append to runs.jsonl")
    ev.set_defaults(func=cmd_eval)

    sm = sub.add_parser("summary", help="write results/SUMMARY.md from the run log")
    sm.add_argument("--out", default=str(ROOT / "results"))
    sm.set_defaults(func=cmd_summary)

    md = sub.add_parser("models", help="list model ids an OpenAI-compatible provider serves")
    md.add_argument("--provider", choices=[k for k, v in PROVIDERS.items() if "base_url" in v],
                    default="nvidia")
    md.add_argument("--filter", default="", help="substring to match, e.g. nemotron")
    md.set_defaults(func=cmd_models)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
