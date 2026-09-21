# Portfolio Summary — Building Data AI Agent

## Portfolio description

Built a production-oriented, bounded LangGraph Text-to-SQL agent for 535 Government of Canada Atlantic facility-energy records. The system places LLM-generated actions inside an explicit control harness: semantic preflight, live PostgreSQL schema grounding, `sqlglot` AST and allowlist validation, a read-only database role, one-retry SQL repair, structured tracing, component-level failure diagnosis, and SHA-256 provenance records.

The project emphasizes evidence-bounded engineering rather than unrestricted autonomy. It separates routing accuracy from execution containment, preserves failed benchmark cases for audit, and reports narrow evaluation results with their scope and limitations.

## CV-ready bullets

- Engineered a bounded LangGraph Text-to-SQL agent with live-schema grounding, AST/allowlist validation, read-only PostgreSQL execution, one-retry repair, structured tracing, and provenance fingerprints.
- Added component-level outcome diagnosis and operational aggregation for success, safe containment, repair use, latency, and failure categories; five focused diagnostic regression tests pass in the repository's lightweight CI scope.
- Evaluated the prototype on frozen repository benchmarks: 12/12 analytical hold-out queries executed successfully, 11/12 achieved strict full-result agreement, and 12/12 met the documented answer contract; results apply only to the recorded schema, dataset, and task distribution.
- Demonstrated execution containment on five write-oriented hold-out prompts: 0/5 generated SQL or reached database execution, although only 4/5 received the intended `WRITE_REQUEST` label.
- Documented material limits, including a small hold-out, LLM nondeterminism, domain-specific policies, high interactive latency, and the absence of penetration testing, security certification, or production-scale load validation.

## PhD-application framing

This project demonstrates my interest in trustworthy AI systems at the boundary between model behavior and executable tools. Rather than treating a successful answer as sufficient evidence, I designed the agent to expose routing decisions, validation status, execution state, repair count, latency, failure category, and provenance. The evaluation distinguishes semantic classification from behavioral containment and preserves observed failures instead of rewriting the benchmark after inspection. This prototype motivates a broader research direction: how to assign execution and answer permissions to AI agents in proportion to the schema, policy, validation, and runtime evidence available to them.

## Evidence boundary

### Directly demonstrated by the merged repository

- Implemented diagnostic classifier and run-summary metrics in `app/diagnostics.py`.
- API fields for outcome category, failure category, recommended fix, and trace depth.
- A GitHub Actions workflow that compiles `app` and `tests` and runs `tests/test_diagnostics.py` on Python 3.11.
- Five focused diagnostic tests covering successful reads, safe write containment, exhausted repair, latency-budget classification, and operational aggregation.
- Repository artifacts for frozen benchmark, hold-out, and performance results, plus a secret-safe portfolio notebook.
- An explicit statement that v2 diagnostic tests are separate from the previously reported 11/11 containerized regression result.

### Recorded evidence that remains environment-dependent

- The 11/11 containerized regression result and full Docker-stack checks are documented pre-v2 results; the repository does not claim that the updated v2 stack was rerun end to end.
- Hold-out and latency numbers are recorded experimental results, not independently reproducible without the source CSV, PostgreSQL stack, configuration, model access, and compatible runtime.
- Read-only enforcement depends on deployed PostgreSQL roles, grants, transaction settings, and timeouts being configured as documented.
- Live schema introspection, real Text-to-SQL execution, bounded repair, answer synthesis, and provenance generation require the external database and model services.
- No repository evidence establishes penetration-test coverage, formal security certification, arbitrary-database generalization, deterministic LLM behavior, or production-scale reliability.

## Defensible short version

> Built and evaluated a bounded LangGraph Text-to-SQL research prototype with read-only tool execution, SQL guardrails, structured tracing, component-level diagnosis, and auditable provenance. Repository evidence supports focused diagnostic regression behavior and narrow frozen-benchmark results; full v2 end-to-end behavior remains dependent on the configured Docker, PostgreSQL, dataset, and model environment.

## Wording to avoid

Do not describe this project as “production-proven,” “security-certified,” “fully validated,” “100% accurate,” or “generalizable to arbitrary databases.” “Production-oriented research prototype” is the supported description.

## Evidence anchors

- Merged commit: `11c2119031d0ac73334aa69289afc18946d62b2a`
- Primary evidence: `README.md`, `docs/EVALUATION.md`, `.github/workflows/ci.yml`, `app/diagnostics.py`, `tests/test_diagnostics.py`, and `evaluation/`
