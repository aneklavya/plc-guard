"""PLCGuard web UI: scan Structured Text and browse the evaluation results.

Run with:  streamlit run app.py

Example programs reuse the committed LLM cache, so they cost no API calls.
Pasted code calls the NVIDIA API, either with the visitor's own key or with
the server's key (NVIDIA_API_KEY), capped per session and per day.
"""
from __future__ import annotations

import datetime
import json
import os
import threading

import pandas as pd
import streamlit as st

from plcguard import rules
from plcguard.evaluate import load_dataset
from plcguard.llm import DEFAULT_CACHE, LLMClient, LLMError, load_dotenv
from plcguard.llm_detector import LLMDetector
from plcguard.obfuscate import obfuscate
from plcguard.taxonomy import CWE, DESCRIPTIONS
from plcguard.tracking import RUN_LOG, dataset_hash, read_runs

ROOT = DEFAULT_CACHE.parent.parent
MAX_CHARS = 20_000
SESSION_LIMIT = int(os.environ.get("PLCGUARD_SESSION_LIMIT", "5"))
DAILY_LIMIT = int(os.environ.get("PLCGUARD_DAILY_LIMIT", "200"))

RESULTS_NOTE = (
    "**Reading the results.** On the dev split the rules look perfect because they were "
    "written alongside those programs; on the held-out split they find well under half "
    "of the bugs. See docs/04-stage2-llm.md for the full analysis.")

load_dotenv()
st.set_page_config(page_title="PLCGuard", page_icon="🛡️", layout="wide")


@st.cache_resource
def dataset():
    return {p.file: p for p in load_dataset(ROOT / "dataset")}


@st.cache_resource
def known_sources() -> set[tuple[str, ...]]:
    """Dataset programs (both variants) as line tuples, which is all the prompt
    depends on: their LLM replies are in the cache."""
    progs = dataset().values()
    return ({tuple(p.source.splitlines()) for p in progs}
            | {tuple(obfuscate(p.source).splitlines()) for p in progs})


@st.cache_resource
def daily_counter() -> dict:
    return {"day": None, "count": 0, "lock": threading.Lock()}


def take_server_quota() -> bool:
    c = daily_counter()
    with c["lock"]:
        today = datetime.date.today()
        if c["day"] != today:
            c["day"], c["count"] = today, 0
        if c["count"] >= DAILY_LIMIT:
            return False
        c["count"] += 1
        return True


def run_llm(source: str, own_key: str) -> list:
    cached = tuple(source.splitlines()) in known_sources()
    client = LLMClient("nvidia", api_key=own_key or "",
                       cache_dir=DEFAULT_CACHE if cached else None)
    if not cached and not own_key:
        used = st.session_state.get("live_scans", 0)
        if used >= SESSION_LIMIT:
            raise LLMError(f"session limit of {SESSION_LIMIT} live scans reached; "
                           "add your own NVIDIA key in the sidebar to continue")
        if not take_server_quota():
            raise LLMError("today's shared quota is used up; add your own NVIDIA key "
                           "in the sidebar to continue")
        st.session_state["live_scans"] = used + 1
    return LLMDetector(client)(source)


def findings_table(findings, source: str) -> pd.DataFrame:
    lines = source.splitlines()
    return pd.DataFrame([{
        "Line": f.line,
        "Type": str(f.vuln_type),
        "CWE": CWE[f.vuln_type],
        "Detector": "rules" if f.source == "rules" else "LLM",
        "Code": lines[f.line - 1].strip() if 0 < f.line <= len(lines) else "",
        "Explanation": f.message,
    } for f in findings])


# -- sidebar ------------------------------------------------------------------

with st.sidebar:
    st.title("🛡️ PLCGuard")
    st.caption("Vulnerability detection for IEC 61131-3 Structured Text")
    detector = st.radio("Detector", ["Rules", "LLM (Nemotron)", "Both"], index=2)
    own_key = st.text_input("Your NVIDIA API key (optional)", type="password",
                            help="Free from build.nvidia.com. Used only for your "
                                 "scans and never stored.")
    if not own_key:
        left = max(SESSION_LIMIT - st.session_state.get("live_scans", 0), 0)
        st.caption(f"Live LLM scans of pasted code left this session: {left}. "
                   "Example programs are free (cached).")
    st.markdown("[Source on GitHub](https://github.com/aneklavya/plc-guard)")

scan_tab, results_tab, about_tab = st.tabs(["Scan", "Evaluation results", "About"])

# -- scan ---------------------------------------------------------------------

with scan_tab:
    files = sorted(dataset())
    choice = st.selectbox("Start from an example program, or paste your own code",
                          ["(paste my own)"] + files, index=files.index("04_conveyor_vuln.st") + 1)
    rename = st.checkbox("Rename all variables to v1, v2, … (robustness test)",
                         help="The rules rely on names; the LLM should not.")
    default = "" if choice == "(paste my own)" else dataset()[choice].source
    source = st.text_area("Structured Text", default, height=380,
                          key=f"src_{choice}", max_chars=MAX_CHARS)
    if rename and source.strip():
        try:
            source = obfuscate(source)
        except Exception as exc:
            st.warning(f"Could not rename variables: {exc}")

    if st.button("Scan", type="primary", disabled=not source.strip()):
        found, errors = [], []
        if detector in ("Rules", "Both"):
            try:
                found += rules.check(source)
            except Exception as exc:
                errors.append(f"Rule checker could not parse the code: {exc}")
        if detector in ("LLM (Nemotron)", "Both"):
            with st.spinner("Asking Nemotron (can take 10–30 s)…"):
                try:
                    found += run_llm(source, own_key.strip())
                except LLMError as exc:
                    errors.append(f"LLM: {exc}")
        for e in errors:
            st.error(e)
        found.sort(key=lambda f: (f.line, str(f.vuln_type)))
        if found:
            st.subheader(f"{len(found)} finding(s)")
            st.dataframe(findings_table(found, source), hide_index=True,
                         use_container_width=True)
        elif not errors:
            st.success("No vulnerabilities reported.")

        if choice != "(paste my own)":
            label = dataset()[choice]
            with st.expander("Ground-truth label for this example"):
                if not label.vulns:
                    st.write("Clean program: no vulnerabilities.")
                for v in label.vulns:
                    st.markdown(f"- **{v.type}** at line {', '.join(map(str, v.lines))}: "
                                f"{v.description}")
        if rename:
            with st.expander("Code as scanned (variables renamed)"):
                st.code(source, language="pascal", line_numbers=True)

# -- results ------------------------------------------------------------------

with results_tab:
    current = dataset_hash(ROOT / "dataset")
    progs = list(dataset().values())
    st.markdown(f"Zero-shot evaluation on {len(progs)} labeled programs "
                f"({sum(p.vulnerable for p in progs)} vulnerable, "
                f"{sum(not p.vulnerable for p in progs)} clean, "
                f"{sum(len(p.vulns) for p in progs)} labeled vulnerabilities). "
                "**dev** = scenarios 01–10, seen while building the rules and prompt v1; "
                "**held-out** = scenarios 11–30, written afterwards. "
                "LLM rows are the mean ± std of 3 runs.")
    split_label = st.radio("Split", ["held-out (honest)", "dev", "all"], horizontal=True,
                           key="split")
    split = {"held-out (honest)": "heldout"}.get(split_label, split_label)
    latest = {}
    for run in read_runs(RUN_LOG):
        if run["dataset_hash"] == current and run.get("split", "all") == split:
            latest[(run["detector"], run.get("model", "-"), run.get("prompt_version", "-"),
                    run["variant"])] = run
    rows = []
    for (det, model, prompt, variant), run in sorted(latest.items(),
                                                     key=lambda kv: (kv[0][3], kv[0][0], kv[0][2])):
        m = run["metrics"]
        rows.append({"Detector": det, "Prompt": prompt, "Code": variant,
                     "Precision": m["precision"]["mean"], "Recall": m["recall"]["mean"],
                     "F1": m["f1"]["mean"], "F1 std": m["f1"]["std"],
                     "Clean files flagged": f"{m['clean_flagged']['mean']:.1f} / {run['clean_files']}",
                     "Model": model})
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df.style.format({"Precision": "{:.2f}", "Recall": "{:.2f}",
                                      "F1": "{:.2f}", "F1 std": "±{:.2f}"}),
                     hide_index=True, use_container_width=True)
        chart = df[df["Detector"] != "hybrid"].assign(
            Config=lambda d: d["Detector"] + " " + d["Prompt"].where(d["Prompt"] != "-", "")
            + " · " + d["Code"])
        st.bar_chart(chart.set_index("Config")[["Precision", "Recall", "F1"]],
                     stack=False, height=320)
        st.markdown(RESULTS_NOTE)
    else:
        st.info("No runs on the current dataset yet. Run `python -m plcguard eval`.")

    repairs = sorted((ROOT / "results").glob("repair_*.json"))
    if repairs:
        st.subheader("Repair (Stage 3)")
        rep = json.loads(repairs[-1].read_text(encoding="utf-8"))
        m = rep["by_split"][split]
        if m["programs"]:
            cols = st.columns(4)
            cols[0].metric("Fixed and verified", f"{m['fixed']} / {m['programs']}")
            cols[1].metric("Fixed on first try", f"{m['fixed_first_try_rate']:.0%}")
            cols[2].metric("Compiles (MatIEC)", f"{m['compile_rate']:.0%}")
            cols[3].metric("I/O map kept", f"{m['io_preserved_rate']:.0%}")
            st.caption("Each vulnerable program is repaired by the LLM given its labeled "
                       "findings, then accepted only if it compiles with MatIEC, keeps every "
                       "AT address, and an independent LLM re-scan no longer finds the bug "
                       "(up to 3 attempts with feedback).")

# -- about --------------------------------------------------------------------

with about_tab:
    st.markdown("""
PLCGuard looks for security weaknesses in PLC programs written in IEC 61131-3
Structured Text, the language that runs pumps, conveyors and burners.

- **Rules**: a parser plus hand-written data-flow checks. Precise, but tied to
  naming and patterns.
- **LLM**: NVIDIA Nemotron 3 Ultra reads the numbered code and reports findings as
  JSON, zero-shot (no examples from the dataset, temperature 0).

The code you paste is only analysed, never executed.

**Vulnerability classes**
""")
    st.dataframe(pd.DataFrame([{"Class": str(t), "CWE": CWE[t], "Meaning": d}
                               for t, d in DESCRIPTIONS.items()]),
                 hide_index=True, use_container_width=True)
