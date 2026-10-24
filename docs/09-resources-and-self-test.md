# 9. Resources and self-test

## Resources

Search for these by name; they are standard starting points.

**PLCs and Structured Text**
- OpenPLC project (autonomylogic.com): runtime, editor, and docs. Write a
  small ST program in the editor and run it; nothing teaches ST faster.
- IEC 61131-3 introductions: search "IEC 61131-3 Structured Text tutorial"
  (PLCopen also has free material).

**ICS / PLC security**
- *Top 20 Secure PLC Coding Practices* (plc-security.com): practical
  checklist; several of our 8 classes map directly onto it.
- MITRE ATT&CK for ICS: how attackers operate against industrial systems.
- Background cases: Stuxnet (2010), Triton/Trisis (2017, safety
  controllers), Oldsmar water plant (2021).
- Modbus security: read the Modbus/TCP spec overview and try `pymodbus`
  against an OpenPLC instance (Stage 5).

**LLMs for code and security**
- Search Google Scholar for "LLM4PLC" (LLMs generating verified PLC code) and
  "LLM vulnerability detection" surveys.
- Papers that question LLM vulnerability-detection results: search
  "LLM vulnerability detection evaluation pitfalls" and "data leakage code
  benchmarks".
- Recent publications from the CARES Lab at Texas A&M.

**Tools used here**
- NVIDIA API catalog: build.nvidia.com (models, keys, limits).
- Streamlit docs: docs.streamlit.io.
- Terraform AWS provider docs: registry.terraform.io/providers/hashicorp/aws.

## Self-test

Try to answer before reading the answer.

**1. Why is `%MW` treated as untrusted?**
It is a Modbus holding register. Modbus/TCP has no authentication, so anyone
who can reach port 502 can write it, including an attacker.

**2. Your rules score F1 1.00. Why aren't you proud of that?**
I wrote the rules and the dataset together, so they agree by construction.
The informative number is recall 0.55 after renaming variables, which shows
the rules depend on names.

**3. Which rules fail on obfuscated code, and why?**
MISSING_INTERLOCK, HARDCODED_CREDENTIAL, UNPROTECTED_CRITICAL_VAR and one
UNSAFE_STATE_TRANSITION case. They recognise pumps, e-stops, PINs, trip points
and bypass signals by name. The data-flow rules (input validation, array
index, division, logic bomb) survive.

**4. Why zero-shot? Wouldn't examples help?**
They probably would, but with 20 programs any example from the dataset in the
prompt leaks test data. Few-shot would need examples from outside the dataset.

**5. Why 3 repeats at temperature 0?**
Temperature 0 is not fully deterministic on hosted APIs. F1 varied by ±0.05
between identical runs, so a single run could mislead.

**6. The hybrid scored exactly the same as the LLM. Why?**
The rules' findings are a subset of the LLM's true positives, and the rules
have no false positives, so the union adds nothing. Rules would be more useful
as a filter on LLM findings.

**7. Is precision 0.65 bad?**
For a deployed tool, yes: about a third of alerts would be false alarms, and
operators ignore noisy tools. But some "false positives" look like real issues
the labels missed (network-writable PIN register; no false-flame check before
purge), so the true precision is uncertain until findings are adjudicated.

**8. Why does precision drop on renamed code if recall doesn't?**
Names help the model recognise *safe* code. `maint_due_lamp := cycle_count >
864000` is obviously harmless; `v6 := v7 > 864000` was flagged as a logic bomb.

**9. How can someone reproduce your numbers without an API key?**
Every LLM reply is cached in `results/llm_cache/` (keyed by a hash of
provider, model, temperature, prompt and repeat index) and committed. Running
`eval` again hits the cache. Manifests record commit, dataset hash and prompt
hash.

**10. What are the biggest threats to validity?**
Small, synthetic dataset written by one person; possible label noise; one
model and one prompt; short programs unlike real plant code.

**11. Why doesn't the API key go into Terraform?**
Terraform variables end up in plain text in the state file. The key goes into
SSM Parameter Store, and the server reads it at boot with a narrowly scoped
IAM permission.

**12. What will Stage 3 add?**
For each finding, ask the LLM for a patched program, then verify: it still
compiles (MatIEC), the rules and LLM no longer report the bug, and the
behaviour is preserved; retry if not. The measure is how many vulnerable
programs get fixed without breaking anything.
