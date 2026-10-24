"""PLCGuard web UI: scan Structured Text and browse the evaluation results.

Run with:  streamlit run app.py

Example programs reuse the committed LLM cache, so they cost no API calls.
Pasted code calls the NVIDIA API, either with the visitor's own key or with
the server's key (NVIDIA_API_KEY), capped per session and per day.
"""
from __future__ import annotations

import datetime
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
from plcguard.tracking import RUN_LOG, read_runs

ROOT = DEFAULT_CACHE.parent.parent
MAX_CHARS = 20_000
SESSION_LIMIT = int(os.environ.get("PLCGUARD_SESSION_LIMIT", "5"))
DAILY_LIMIT = int(os.environ.get("PLCGUARD_DAILY_LIMIT", "200"))

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
    st.markdown("Zero-shot evaluation on 20 labeled programs (10 vulnerable, 10 clean, "
                "11 labeled vulnerabilities). LLM rows are the mean ± std of 3 runs.")
    latest = {}
    for run in read_runs(RUN_LOG):
        latest[(run["detector"], run.get("model", "-"), run["variant"])] = run
    rows = []
    for (det, model, variant), run in sorted(latest.items(), key=lambda kv: (kv[0][2], kv[0][0])):
        m = run["metrics"]
        rows.append({"Detector": det, "Model": model, "Code": variant,
                     "Precision": m["precision"]["mean"], "Recall": m["recall"]["mean"],
                     "F1": m["f1"]["mean"], "F1 std": m["f1"]["std"],
                     "Clean files flagged": f"{m['clean_flagged']['mean']:.1f} / {run['clean_files']}"})
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df.style.format({"Precision": "{:.2f}", "Recall": "{:.2f}",
                                      "F1": "{:.2f}", "F1 std": "±{:.2f}"}),
                     hide_index=True, use_container_width=True)
        chart = df[df["Detector"] != "hybrid"].assign(
            Config=lambda d: d["Detector"] + " · " + d["Code"])
        st.bar_chart(chart.set_index("Config")[["Precision", "Recall", "F1"]],
                     stack=False, height=320)
        st.markdown(
            "**Reading the results.** The rules are perfect on the original code but miss "
            "45% of the bugs once variables are renamed. Nemotron finds every labeled bug "
            "on both variants, but about a third to a half of its reports are false alarms. "
            "The hybrid (rules ∪ LLM) scores the same as the LLM alone.")
    else:
        st.info("No runs logged yet. Run `python -m plcguard eval`.")

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
