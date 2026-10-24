"""Experiment tracking: run manifests, an append-only run log, a summary table.

Every evaluation records enough to reproduce it: code version (git commit and
whether the tree was dirty), dataset hash, detector config, prompt version and
hash. Runs are appended to results/runs.jsonl and never rewritten, so a result
quoted in the README can always be traced back to the run that produced it.
"""
from __future__ import annotations

import hashlib
import json
import platform
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN_LOG = ROOT / "results" / "runs.jsonl"


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                              timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def dataset_hash(dataset_dir: Path) -> str:
    """Hash of labels.json and every program, independent of line endings."""
    h = hashlib.sha256()
    files = [dataset_dir / "labels.json", *sorted((dataset_dir / "programs").glob("*.st"))]
    for f in files:
        h.update(f.name.encode())
        h.update(f.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]


def manifest(config: dict, dataset_dir: Path) -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": _git("rev-parse", "--short", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "python": platform.python_version(),
        "dataset_hash": dataset_hash(dataset_dir),
        **config,
    }


def aggregate(reports: list[dict]) -> dict:
    """Mean and sample std of the headline metrics over repeated runs."""
    def stats(values):
        return {"mean": statistics.fmean(values),
                "std": statistics.stdev(values) if len(values) > 1 else 0.0,
                "values": values}
    return {
        "n": len(reports),
        "precision": stats([r["micro"]["precision"] for r in reports]),
        "recall": stats([r["micro"]["recall"] for r in reports]),
        "f1": stats([r["micro"]["f1"] for r in reports]),
        "clean_flagged": stats([r["file_level"]["clean_flagged"] for r in reports]),
        "errors": stats([r["parse_errors"] for r in reports]),
    }


def log_run(run: dict, path: Path = RUN_LOG) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(run, sort_keys=True) + "\n")


def read_runs(path: Path = RUN_LOG) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def summary_markdown(runs: list[dict]) -> str:
    """Latest run per (detector, model, prompt, variant) as one comparison table."""
    latest: dict[tuple, dict] = {}
    for r in runs:
        key = (r["detector"], r.get("model", ""), r.get("prompt_hash", ""), r["variant"])
        latest[key] = r
    out = ["# PLCGuard results summary", "",
           "Latest run per configuration, generated from `results/runs.jsonl` by "
           "`python -m plcguard summary`. Mean ± std over repeated runs.", "",
           "| Detector | Model | Variant | Runs | Precision | Recall | F1 | "
           "Clean flagged | Errors | Commit | Dataset |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]

    def ms(s, fmt=".2f"):
        return f"{s['mean']:{fmt}}" + (f" ± {s['std']:{fmt}}" if s["std"] else "")

    for r in sorted(latest.values(), key=lambda r: (r["variant"], r["detector"],
                                                     r.get("model", ""))):
        m = r["metrics"]
        commit = r["git_commit"] + ("+dirty" if r["git_dirty"] else "")
        out.append(f"| {r['detector']} | {r.get('model') or '-'} | {r['variant']} | {m['n']} | "
                   f"{ms(m['precision'])} | {ms(m['recall'])} | {ms(m['f1'])} | "
                   f"{ms(m['clean_flagged'], '.1f')}/{r['clean_files']} | "
                   f"{ms(m['errors'], '.1f')} | {commit} | {r['dataset_hash']} |")
    return "\n".join(out) + "\n"
