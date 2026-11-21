"""Repair loop: code extraction, I/O-map check, retry with feedback (offline)."""
from plcguard import repair as repair_mod
from plcguard.compile_check import CompileResult
from plcguard.llm import LLMClient
from plcguard.repair import Repairer, extract_code, io_problems
from plcguard.taxonomy import Finding, VulnType

VULN = """PROGRAM Pump
  VAR
    hmi_start AT %QX1.0 : BOOL;
    low_level AT %IX0.0 : BOOL;
    pump      AT %QX0.0 : BOOL;
  END_VAR
  pump := hmi_start;
END_PROGRAM
"""
FIXED = VULN.replace("pump := hmi_start;", "pump := hmi_start AND NOT low_level;")
TARGET = [Finding(VulnType.MISSING_INTERLOCK, 7, "pump ignores low level")]


class ScriptedClient(LLMClient):
    """Returns canned replies: repair prompts get `repairs`, reviews get `reviews`."""

    def __init__(self, repairs, reviews):
        super().__init__("nvidia", "fake", api_key="k", cache_dir=None)
        self.repairs, self.reviews, self.prompts = list(repairs), list(reviews), []

    def complete(self, system, user, sample=0):
        self.prompts.append(user)
        return (self.repairs if "PLC security engineer" in system else self.reviews).pop(0)


def test_extract_code_prefers_the_st_block():
    reply = "<think>hmm</think>Here:\n```st\n" + FIXED + "```\n- added interlock"
    assert extract_code(reply) == FIXED


def test_extract_code_without_fences():
    assert extract_code("Sure. " + FIXED.strip() + " Done.").startswith("PROGRAM Pump")


def test_io_problems_detects_rewiring():
    moved = FIXED.replace("%QX0.0", "%QX0.5")
    removed = FIXED.replace("    low_level AT %IX0.0 : BOOL;\n", "")
    assert io_problems(VULN, FIXED) == []
    assert io_problems(VULN, moved) == ["PUMP moved from %QX0.0 to %QX0.5"]
    assert io_problems(VULN, removed) == ["LOW_LEVEL AT %IX0.0 was removed or renamed"]


def test_retry_with_feedback_until_accepted(monkeypatch):
    compiles = iter([CompileResult(False, ["line 7: error: ';' missing"]),
                     CompileResult(True, [])])
    monkeypatch.setattr(repair_mod.compile_check, "compile_st", lambda code: next(compiles))
    client = ScriptedClient(
        repairs=["```st\n" + FIXED.replace(";\nEND_PROGRAM", "\nEND_PROGRAM") + "```",
                 "```st\n" + FIXED + "```"],
        reviews=['{"findings": []}', '{"findings": []}'])
    res = Repairer(client, max_attempts=3).repair(VULN, TARGET)
    assert res.fixed and len(res.attempts) == 2
    assert not res.attempts[0].accepted
    retry_prompt = [p for p in client.prompts if "rejected" in p][0]
    assert "does not compile" in retry_prompt and "';' missing" in retry_prompt


def test_still_flagged_is_not_accepted(monkeypatch):
    monkeypatch.setattr(repair_mod.compile_check, "compile_st", lambda code: CompileResult(True, []))
    still = '{"findings": [{"type": "MISSING_INTERLOCK", "line": 7}]}'
    client = ScriptedClient(repairs=["```st\n" + VULN + "```"] * 2, reviews=[still] * 2)
    res = Repairer(client, max_attempts=2).repair(VULN, TARGET)
    assert not res.fixed and len(res.attempts) == 2
    assert res.attempts[-1].llm_remaining == ["MISSING_INTERLOCK"]
