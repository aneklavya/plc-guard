"""Command line: python -m plcguard {scan,eval,summary} ..."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import rules
from .evaluate import evaluate, load_dataset, to_markdown
from .llm import DEFAULT_CACHE, PROVIDERS, LLMClient, LLMError
from .llm_detector import PROMPTS, HybridDetector, LLMDetector, prompt_fingerprint
from .obfuscate import obfuscate
from .st_parser import STParseError
from .taxonomy import CWE
from .tracking import (aggregate, dataset_hash, log_run, manifest, read_runs,
                       summary_markdown)

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
    return (LLMDetector if args.detector == "llm" else HybridDetector)(
        client, sample, getattr(args, "prompt", "v1"))


def run_name(args, client: LLMClient | None) -> str:
    if client is None:
        return "rules"
    slug = re.sub(r"[^A-Za-z0-9.]+", "-", client.model).strip("-")
    prompt = getattr(args, "prompt", "v1")
    return f"{args.detector}_{slug}" + ("" if prompt == "v1" else f"_{prompt}")


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


class _Memo:
    """Remember a detector's answer per source, so per-split scoring and
    parallel prefetching never call the LLM twice for the same program."""

    def __init__(self, detector):
        self.detector, self.cache = detector, {}

    def __call__(self, source):
        if source not in self.cache:
            try:
                self.cache[source] = (self.detector(source), None)
            except Exception as exc:  # re-raised to evaluate(), which records it
                self.cache[source] = (None, exc)
        findings, exc = self.cache[source]
        if exc is not None:
            raise exc
        return findings

    def prefetch(self, sources, workers: int):
        if workers > 1:
            with ThreadPoolExecutor(workers) as pool:
                list(pool.map(self._quiet, sources))

    def _quiet(self, source):
        try:
            self(source)
        except Exception:
            pass


SPLITS = ("all", "dev", "heldout")


def cmd_eval(args) -> int:
    dataset = Path(args.dataset)
    programs = load_dataset(dataset)
    if args.variant == "obfuscated":
        for prog in programs:
            prog.source = obfuscate(prog.source)
    client = make_client(args)
    repeats = 1 if client is None else args.repeats  # the rules are deterministic
    subsets = {s: (programs if s == "all" else [p for p in programs if p.split == s])
               for s in SPLITS}
    subsets = {s: progs for s, progs in subsets.items() if progs}

    t0 = time.monotonic()
    reports: dict[str, list[dict]] = {s: [] for s in subsets}
    for i in range(repeats):
        detector = _Memo(make_detector(args, client, i))
        detector.prefetch([p.source for p in programs], args.workers)
        for split, progs in subsets.items():
            report = evaluate(detector, progs, args.line_tolerance)
            if split == "all" and report["parse_errors"] == len(progs):
                print(f"every program failed, no report written: "
                      f"{report['programs'][0]['error']}", file=sys.stderr)
                return 2
            reports[split].append(report)
        if repeats > 1:
            print(f"repeat {i + 1}/{repeats}: F1 {reports['all'][-1]['micro']['f1']:.2f}",
                  file=sys.stderr)

    wall = round(time.monotonic() - t0, 1)
    name = run_name(args, client)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for split, reps in reports.items():
        config = {"detector": args.detector, "variant": args.variant, "split": split,
                  "line_tolerance": args.line_tolerance, "repeats": repeats,
                  "programs": len(subsets[split]),
                  "clean_files": reps[0]["file_level"]["clean_files"],
                  "wall_seconds": wall}
        if client is not None:
            config.update(provider=client.provider, model=client.model,
                          temperature=client.temperature, prompt_version=args.prompt,
                          prompt_hash=prompt_fingerprint(args.prompt), llm_calls=client.calls,
                          cache_hits=client.cache_hits)
        run = manifest(config, dataset)
        run["metrics"] = aggregate(reps)
        suffix = "" if split == "all" else f"_{split}"
        report = {**reps[0], "run": run, "repeat_reports": reps[1:]}
        md = to_markdown(reps[0], f"PLCGuard evaluation: {name} "
                                  f"({args.variant} dataset, {split} split)")
        md += _run_markdown(run)
        (out / f"{name}_{args.variant}{suffix}.json").write_text(json.dumps(report, indent=2),
                                                                 encoding="utf-8")
        (out / f"{name}_{args.variant}{suffix}.md").write_text(md, encoding="utf-8")
        if not args.no_log:
            log_run(run, out / "runs.jsonl")
        if split == "all":
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
    keys = ["timestamp", "git_commit", "git_dirty", "dataset_hash", "split", "programs",
            "provider", "model",
            "temperature", "prompt_version", "prompt_hash", "repeats", "llm_calls",
            "cache_hits", "wall_seconds"]
    lines += [f"- {k}: `{run[k]}`" for k in keys if k in run]
    return "\n".join(lines) + "\n"


def cmd_summary(args) -> int:
    out = Path(args.out)
    md = summary_markdown(read_runs(out / "runs.jsonl"),
                          None if args.all_datasets else dataset_hash(Path(args.dataset)))
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
    p.add_argument("--prompt", choices=sorted(PROMPTS), default="v1",
                   help="LLM system prompt version")


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
    ev.add_argument("--workers", type=int, default=1,
                    help="parallel LLM requests (the free API is slow, not busy)")
    ev.set_defaults(func=cmd_eval)

    sm = sub.add_parser("summary", help="write results/SUMMARY.md from the run log")
    sm.add_argument("--out", default=str(ROOT / "results"))
    sm.add_argument("--dataset", default=str(ROOT / "dataset"))
    sm.add_argument("--all-datasets", action="store_true",
                    help="include runs on earlier versions of the dataset")
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
