# 8. Glossary

| Term | Meaning |
|---|---|
| **Actuator** | Device the PLC moves or switches: motor, pump, valve, heater. |
| **Adjudication** | Deciding, finding by finding, whether a reported issue is real. Needed when labels may be incomplete. |
| **CI** | Continuous Integration: tests run automatically on every push (GitHub Actions here). |
| **Context** (parser) | The chain of `IF`/`CASE`/loop conditions an assignment runs under. |
| **CWE** | Common Weakness Enumeration, MITRE's numbered catalogue of software weakness types (e.g. CWE-20 Improper Input Validation). |
| **Data contamination / test leakage** | Test data reaching the model (in training or in the prompt), which inflates scores. Why our prompt has no dataset examples. |
| **Data flow** | How values move from one variable to another through assignments. |
| **F1** | Harmonic mean of precision and recall: 2PR/(P+R). |
| **False positive (FP)** | Reported but not real (per our labels). A false alarm. |
| **False negative (FN)** | Real but not reported. A miss. |
| **HMI** | Human-Machine Interface, the operator touchscreen. Talks to the PLC over the network. |
| **Holding register** | A 16-bit Modbus read/write value; `%MW` in OpenPLC. |
| **Hybrid detector** | Union of rule findings and LLM findings. |
| **ICS** | Industrial Control System: PLCs, HMIs, SCADA, networks. |
| **IEC 61131-3** | Standard defining PLC programming languages, including Structured Text. |
| **IMDSv2** | AWS instance metadata service, version 2 (requires a session token; blocks some attacks). |
| **Interlock** | Condition that must hold before equipment may run (e-stop released, level OK, ...). |
| **Localisation** | Whether a correct finding also points at the right line (±1 here). |
| **Logic bomb** | Hidden code that changes behaviour when a trigger (count, date, value) is reached. |
| **MatIEC** | OpenPLC's compiler from IEC 61131-3 to C. To be used in Stage 3. |
| **Micro average** | Sum TP/FP/FN over all classes, then compute P/R/F1 once. |
| **Mixture of Experts (MoE)** | Model architecture where only some sub-networks ("experts") run per token; e.g. 550B total, 55B active. |
| **MLOps** | Practices for reliable, reproducible ML experiments and deployments. |
| **Modbus/TCP** | Common industrial protocol on port 502, with no authentication or encryption. |
| **NIM** | NVIDIA Inference Microservices; the hosted API behind build.nvidia.com. |
| **Obfuscation** (here) | Renaming all variables to `v1, v2, ...` while keeping the logic identical. |
| **OpenAI-compatible API** | An API using the same request/response format as OpenAI's chat completions. |
| **OpenPLC** | Open-source PLC runtime and editor. |
| **PLC** | Programmable Logic Controller. |
| **POU** | Program Organisation Unit: PROGRAM, FUNCTION_BLOCK or FUNCTION. |
| **Precision** | TP / (TP + FP): how much of what was reported is correct. |
| **Prompt hash** | Hash of the exact prompt text, logged per run, so prompt changes are traceable. |
| **Recall** | TP / (TP + FN): how many real bugs were found. |
| **Recursive-descent parser** | A parser with one function per grammar construct, calling each other. |
| **Run manifest** | Record of code version, data hash, model and settings for one evaluation. |
| **Scan cycle** | The PLC loop: read inputs, run program, write outputs, repeat. |
| **SSM Parameter Store** | AWS service for storing config and secrets (`SecureString` is encrypted). |
| **SSM Session Manager** | AWS shell access to an instance without SSH or open ports. |
| **Streamlit** | Python library for building web apps from scripts. |
| **Structured Text (ST)** | Pascal-like text language of IEC 61131-3. |
| **Temperature** | LLM sampling randomness; 0 = most likely token each time. |
| **Terraform** | Infrastructure-as-code tool: plan, apply, destroy cloud resources from files. |
| **Token** (parser) | Smallest unit of source code: identifier, number, operator, ... |
| **True positive (TP)** | Reported and real. |
| **Zero-shot** | The model gets instructions but no worked examples. |
