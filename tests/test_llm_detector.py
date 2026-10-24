import io
import json
import urllib.error
from pathlib import Path

import pytest

from plcguard import llm as llm_mod
from plcguard.evaluate import evaluate, load_dataset
from plcguard.llm import LLMClient, LLMError
from plcguard.llm_detector import HybridDetector, LLMDetector, build_prompt, parse_response
from plcguard.taxonomy import VulnType

DATASET = Path(__file__).resolve().parent.parent / "dataset"
SRC = "PROGRAM P\n  VAR\n    a AT %MW0 : INT;\n    b AT %QW0 : INT;\n  END_VAR\n  b := a;\nEND_PROGRAM\n"


class FakeClient(LLMClient):
    """LLMClient whose network layer returns canned replies."""

    def __init__(self, replies, **kw):
        super().__init__("gemini", "fake-model", api_key="k", cache_dir=None, **kw)
        self.replies = list(replies)
        self.prompts = []

    def _request(self, system, user):
        self.prompts.append((system, user))
        self.calls += 1
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


def _reply(*items):
    return json.dumps({"findings": [dict(zip(("type", "line", "variable", "explanation"), i))
                                    for i in items]})


# -- prompt -------------------------------------------------------------------

def test_prompt_numbers_lines_and_lists_every_class():
    system, user = build_prompt(SRC)
    assert "6 | " in user and "b := a;" in user
    for t in VulnType:
        assert t.value in system


def test_prompt_never_contains_labels_or_file_names():
    for prog in load_dataset(DATASET):
        system, user = build_prompt(prog.source)
        text = (system + user).lower()
        assert "_vuln" not in text and "_clean" not in text and prog.file.lower() not in text
        for v in prog.vulns:
            if v.description:
                assert v.description.lower() not in text


# -- response parsing ---------------------------------------------------------

def test_parse_plain_json():
    fs = parse_response(_reply(("INPUT_VALIDATION", 6, "a", "unchecked")))
    assert [(f.vuln_type, f.line, f.variable, f.source) for f in fs] == \
        [(VulnType.INPUT_VALIDATION, 6, "a", "llm")]


@pytest.mark.parametrize("wrap", [
    "```json\n{}\n```",
    "Here is my analysis:\n{}\nHope this helps.",
])
def test_parse_tolerates_fences_and_prose(wrap):
    fs = parse_response(wrap.format(_reply(("DIV_BY_ZERO", 3, "x", ""))))
    assert [f.vuln_type for f in fs] == [VulnType.DIV_BY_ZERO]


def test_parse_normalises_and_drops_unknown_types():
    text = json.dumps({"findings": [
        {"type": "missing interlock", "line": "7"},
        {"type": "BUFFER_OVERFLOW", "line": 2},
        {"type": "LOGIC_BOMB", "line": "n/a"},
        "garbage",
    ]})
    fs = parse_response(text)
    assert [(f.vuln_type, f.line) for f in fs] == \
        [(VulnType.MISSING_INTERLOCK, 7), (VulnType.LOGIC_BOMB, 0)]


def test_parse_accepts_bare_list_and_empty():
    assert parse_response('[{"type": "OOB_INDEX", "line": 1}]')[0].vuln_type == VulnType.OOB_INDEX
    assert parse_response('{"findings": []}') == []


def test_parse_rejects_non_json():
    with pytest.raises(LLMError):
        parse_response("I could not find any issues.")


# -- detectors ----------------------------------------------------------------

def test_llm_detector_end_to_end():
    client = FakeClient([_reply(("INPUT_VALIDATION", 6, "a", "unchecked"))])
    fs = LLMDetector(client)(SRC)
    assert fs[0].rule == "gemini:fake-model" and client.calls == 1


def test_hybrid_is_union_of_rules_and_llm():
    client = FakeClient([_reply(("LOGIC_BOMB", 2, "", "made up"))])
    types = {f.vuln_type for f in HybridDetector(client)(SRC)}
    assert types == {VulnType.INPUT_VALIDATION, VulnType.LOGIC_BOMB}


def test_evaluate_with_fake_llm_counts_bad_replies_as_errors():
    progs = load_dataset(DATASET)[:2]
    client = FakeClient(["not json", '{"findings": []}'])
    report = evaluate(LLMDetector(client), progs)
    assert report["parse_errors"] == 1


# -- client: cache and retry --------------------------------------------------

def test_cache_avoids_second_request(tmp_path):
    client = FakeClient(['{"findings": []}'])
    client.cache_dir = tmp_path
    assert client.complete("s", "u") == client.complete("s", "u")
    assert client.calls == 1 and client.cache_hits == 1
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_cache_key_depends_on_model(tmp_path):
    a, b = FakeClient(["1"]), FakeClient(["2"])
    a.cache_dir = b.cache_dir = tmp_path
    b.model = "other-model"
    assert (a.complete("s", "u"), b.complete("s", "u")) == ("1", "2")


def _http_error(code, body="", headers=None):
    return urllib.error.HTTPError("u", code, "err", headers or {}, io.BytesIO(body.encode()))


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_post_retries_on_429_using_retry_delay(monkeypatch):
    sleeps, outcomes = [], [
        _http_error(429, '{"error": {"details": [{"retryDelay": "7s"}]}}'),
        _http_error(503),
        _Resp(b'{"ok": true}'),
    ]

    def fake_urlopen(req, timeout):
        o = outcomes.pop(0)
        if isinstance(o, Exception):
            raise o
        return o

    monkeypatch.setattr(llm_mod.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(llm_mod.time, "sleep", sleeps.append)
    client = LLMClient("gemini", "m", api_key="k", cache_dir=None)
    assert client._post("https://x.test", {}, {}) == {"ok": True}
    assert sleeps == [8.0, 4] and client.calls == 3


def test_post_does_not_retry_client_errors(monkeypatch):
    def fake_urlopen(req, timeout):
        raise _http_error(400, "bad model")

    monkeypatch.setattr(llm_mod.urllib.request, "urlopen", fake_urlopen)
    client = LLMClient("gemini", "m", api_key="k", cache_dir=None)
    with pytest.raises(LLMError, match="HTTP 400"):
        client._post("https://x.test", {}, {})
    assert client.calls == 1


def test_missing_key_is_reported(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(llm_mod, "load_dotenv", lambda: None)
    with pytest.raises(LLMError, match="GEMINI_API_KEY"):
        LLMClient("gemini", cache_dir=tmp_path).complete("s", "u")


def test_think_block_is_stripped():
    reply = '<think>maybe {"findings": [] } ... </think>\n{"findings": [{"type": "INPUT_VALIDATION", "line": 3}]}'
    fs = parse_response(reply)
    assert [f.line for f in fs] == [3]


def test_nvidia_uses_openai_compatible_endpoint(monkeypatch):
    seen = {}

    def fake_post(self, url, headers, body):
        seen.update(url=url, auth=headers["Authorization"], model=body["model"])
        return {"choices": [{"message": {"content": '{"findings": []}'}}]}

    monkeypatch.setattr(llm_mod.LLMClient, "_post", fake_post)
    client = LLMClient("nvidia", api_key="nvapi-test", cache_dir=None)
    assert client.complete("s", "u") == '{"findings": []}'
    assert seen == {"url": "https://integrate.api.nvidia.com/v1/chat/completions",
                    "auth": "Bearer nvapi-test",
                    "model": "nvidia/nemotron-3-ultra-550b-a55b"}
