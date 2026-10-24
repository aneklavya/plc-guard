import json
from pathlib import Path

from plcguard.__main__ import main
from plcguard.tracking import aggregate, dataset_hash, read_runs, summary_markdown

DATASET = Path(__file__).resolve().parent.parent / "dataset"


def _report(p, r, f1, flagged=0, errors=0):
    return {"micro": {"precision": p, "recall": r, "f1": f1},
            "file_level": {"clean_flagged": flagged}, "parse_errors": errors}


def test_dataset_hash_is_stable_and_ignores_line_endings(tmp_path):
    (tmp_path / "programs").mkdir()
    (tmp_path / "labels.json").write_bytes(b"{}\n")
    (tmp_path / "programs" / "a.st").write_bytes(b"x := 1;\n")
    h = dataset_hash(tmp_path)
    (tmp_path / "programs" / "a.st").write_bytes(b"x := 1;\r\n")
    assert dataset_hash(tmp_path) == h
    (tmp_path / "programs" / "a.st").write_bytes(b"x := 2;\n")
    assert dataset_hash(tmp_path) != h
    assert dataset_hash(DATASET) == dataset_hash(DATASET)


def test_aggregate_mean_and_std():
    m = aggregate([_report(1, 0.5, 0.6), _report(1, 0.7, 0.8)])
    assert m["n"] == 2
    assert abs(m["f1"]["mean"] - 0.7) < 1e-9
    assert abs(m["f1"]["std"] - 0.1414) < 1e-3
    assert aggregate([_report(1, 1, 1)])["f1"]["std"] == 0.0


def test_eval_writes_manifest_and_appends_to_log(tmp_path, capsys):
    for _ in range(2):
        assert main(["eval", "--out", str(tmp_path)]) == 0
    runs = read_runs(tmp_path / "runs.jsonl")
    assert len(runs) == 2
    run = runs[-1]
    for key in ("timestamp", "git_commit", "git_dirty", "dataset_hash", "metrics"):
        assert key in run
    assert run["dataset_hash"] == dataset_hash(DATASET)
    report = json.loads((tmp_path / "rules_original.json").read_text(encoding="utf-8"))
    assert report["run"]["detector"] == "rules"

    assert main(["summary", "--out", str(tmp_path)]) == 0
    summary = (tmp_path / "SUMMARY.md").read_text(encoding="utf-8")
    assert summary.count("| rules |") == 1  # latest run per configuration only


def test_summary_separates_prompt_versions():
    base = {"detector": "llm", "model": "m", "variant": "original", "git_commit": "abc",
            "git_dirty": False, "dataset_hash": "d", "clean_files": 10,
            "metrics": aggregate([_report(1, 1, 1)])}
    md = summary_markdown([{**base, "prompt_hash": "p1"}, {**base, "prompt_hash": "p2"}])
    assert md.count("| llm |") == 2
