# Building Data AI Agent — Technical Portfolio Evidence Brief

## Portfolio entry

**Building Data AI Agent | Trustworthy Agent Engineering**  
Python · LangGraph · PostgreSQL · FastAPI · `sqlglot` · Docker · pytest

Built a production-oriented, bounded Text-to-SQL agent over 535 Government of Canada Atlantic facility-energy records. The system constrains LLM-generated actions through semantic preflight, live-schema grounding, AST and allowlist validation, read-only database execution, a one-retry repair limit, structured traces, component-level failure diagnosis, and SHA-256 provenance records.

Evaluation was deliberately layered rather than reduced to one accuracy score. Repository records report 12/12 successful executions and 12/12 answer-contract agreement on a 12-question analytical hold-out, with 11/12 strict full-result agreement. Five write-oriented prompts produced no SQL and never reached database execution, although one was assigned the wrong safe policy label. These findings are scoped to the recorded dataset, schema, prompts, and runtime; they are not evidence of general Text-to-SQL accuracy or production security.

## CV versions

### One-line version

Built a bounded LangGraph Text-to-SQL research prototype with read-only PostgreSQL tools, AST/allowlist guardrails, one-retry repair, trace-based failure diagnosis, provenance, and scoped regression evaluation.

### Two-bullet version

- Engineered a bounded LangGraph Text-to-SQL agent with live-schema grounding, `sqlglot` validation, read-only PostgreSQL execution, one-retry repair, structured tracing, and provenance fingerprints.
- Added component-level diagnostics and CI-tested operational metrics; documented frozen hold-out results and explicitly separated safe execution containment from routing accuracy and environment-dependent validation.

### Evidence-rich three-bullet version

- Built a production-oriented LangGraph data agent over 535 federal facility-energy records, constraining model actions with semantic preflight, live-schema grounding, SQL AST/allowlist validation, and a read-only database boundary.
- Implemented trace-based outcome diagnosis and operational metrics for safe containment, repair use, latency, and component failures; five focused v2 diagnostic tests pass in the repository's lightweight CI scope.
- Recorded narrow hold-out evidence: 12/12 successful analytical executions, 11/12 strict full-result agreement, and 0/5 write-oriented prompts reaching database execution; results are limited to the documented schema, dataset, task distribution, and runtime.

## Research direction

My Building Data AI Agent project explores how trustworthy AI principles can govern systems that translate model outputs into executable actions. I designed an explicit control harness around the LLM, including semantic routing, live environmental grounding, structural SQL validation, read-only tool permissions, bounded repair, trace-based diagnosis, and provenance. I also separated semantic classification from behavioral containment: in the recorded write-request hold-out, one prompt received the wrong policy label, yet none generated SQL or reached the database. This distinction motivates a broader research direction: how can agent permissions and claims be calibrated to the strength of available policy, validation, provenance, and runtime evidence?

## Claim-evidence matrix

| Claim | Evidence status | Defensible interpretation |
|---|---|---|
| Component-level diagnosis is implemented | Direct | Source code defines observable outcome and failure categories and exposes them through the API. |
| Operational aggregation is implemented | Direct | Source code computes success, repair, latency, outcome, and failure summaries. |
| v2 diagnostic behavior is regression-tested | Direct but narrow | Five focused tests pass; CI is configured to compile the code and run only this diagnostic test module. |
| The agent has layered safety controls | Direct for implementation | Code and configuration implement routing, SQL validation, retry bounds, and documented database controls. Runtime enforcement still depends on deployment configuration. |
| Hold-out performance was strong | Recorded, scoped evidence | CSV artifacts and evaluation documentation report the stated results for a small frozen hold-out under the recorded setup. |
| Write prompts were behaviorally contained | Recorded, scoped evidence | The five recorded cases generated no SQL and reached no database execution; one routing label was incorrect. |
| The full v2 stack is end-to-end validated | Not demonstrated | The 11/11 containerized suite predates v2, and the repository explicitly keeps the new tests separate from that figure. |
| The system is production-secure or production-scale | Not demonstrated | There is no penetration test, certification, deployment study, production metrics backend, or load test. |
| Results generalize to other databases or tasks | Not demonstrated | Evaluation is tied to one schema, one domain, a small hold-out, and nondeterministic external model behavior. |

## Safe wording for interviews

> The repository demonstrates the control architecture, diagnostic logic, and focused regression behavior directly. It also preserves benchmark artifacts from a specific configured environment. I present those benchmark results as scoped experimental evidence—not as proof of production security, broad generalization, or a complete v2 end-to-end validation.

## Reproducibility anchors

- Repository: `Haifawaeedd/building-data-ai-agent`
- Merged commit: `11c2119031d0ac73334aa69289afc18946d62b2a`
- Evidence files: `README.md`, `docs/EVALUATION.md`, `.github/workflows/ci.yml`, `app/diagnostics.py`, `tests/test_diagnostics.py`, `evaluation/`, and `notebooks/Building_Data_AI_Agent_Production_v2.ipynb`
