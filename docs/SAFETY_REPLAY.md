# Offline SQL safety replay

This tool answers: which existing SQL validator blocks this fixed candidate,
and would the other validator still block it if that layer were absent?
It also records disagreements with the author's expected policy, including
false rejections. It evaluates the actual functions in `app/guardrails.py`;
it does not implement a second, simplified copy of the guardrails.

## Run

From the repository root, with Python 3.11 or later:

```bash
python -m pip install sqlglot==30.20.0 sqlparse==0.6.0 pytest
python -m app.safety_replay evaluation/safety_replay/cases.json --json-output report.json --markdown-output report.md
python -m pytest -q tests/test_diagnostics.py tests/test_safety_replay.py
```

No OpenAI key, Docker, database connection, or downloaded dataset is needed.
The JSON input contains `schema.allowed_tables`, `schema.known_columns`, and
`cases` with unique `id`, `sql`, `expected` (`PASS` or `BLOCK`), and optional
`rationale`. `schema_origin` documents where the supplied schema came from.
The current validator uses a flat column set; this tool does not add per-table
column resolution or multi-schema support.

Add `--fail-on-mismatch` to return a nonzero exit code for a full-configuration
expectation mismatch or evaluator error. The committed exploratory cases
intentionally produce exit code 1 with that flag. Without it, a generated report
is not a declaration that the policy passed. CI tests whether the replay tool
correctly exposes the known gaps; CI success is not safety-benchmark perfection.

## What the first experiment found

Thirteen manually authored synthetic cases use a minimal schema snapshot with
the original table name and three column names. **The original 535 data records
were not loaded or queried.** These cases are separate from all previous
hold-out and containerized results. No model generated these candidates.

- Four cases are blocked by both lexical and AST checks independently.
- Three cases (unknown table, unknown column, unapproved schema) rely on the AST
  layer: removing it changes BLOCK to PASS.
- One allowed string-literal query is rejected because the lexical filter sees
  the word `DELETE` inside a string. The AST check passes it.
- `SELECT pg_sleep(1)` passes both checks. Its BLOCK label represents a desired
  analytical-use policy against deliberate delays, not an existing documented
  function denylist. This is a candidate policy-coverage gap, not evidence of
  successful database execution, data modification, or a timeout bypass.

See [the generated table](../evaluation/safety_replay/report.md) and
[full machine-readable evidence](../evaluation/safety_replay/report.json).

## Interpretation

Each check runs independently so the normal pipeline's early return does not
hide the other check. The four variants are both checks, lexical only, AST only,
and neither. A variant blocks if an enabled check blocks. With no block but an
evaluator error it is UNKNOWN. Exceptions are not counted as successful blocks.
An attribution containing errors is marked INCOMPLETE even if another check
blocks. Removing both checks produces PASS by construction, not a real
unprotected database experiment.

This is a fixed-input ablation: the SQL and supplied schema stay constant.
It does not estimate what a model would generate after routing or repair changes,
and does not establish causal effects on the complete agent. Neither production
checks nor database permissions are disabled during replay. The report cannot
be used to authorize execution; no replay result is fed into the agent.

JSON captures input, schema, guardrail-source and replay-source SHA-256 hashes,
parser versions, per-layer reasons, and count denominators. Hashes identify the
examined artifacts; they are not signed attestations. Results can depend on
parser versions. The synthetic sample is too small and deliberately selected
to estimate real-world failure rates or compare products.

## Implementation boundary and next evidence

The AST function accepts explicit schema sets for offline evaluation. Existing
callers still resolve `app.schema` when a snapshot is not supplied. The lexical
keyword iteration is sorted to make reasons deterministic. This addition does
not claim to fix the existing guardrails, make the system production-secure,
or introduce a globally novel method.

Live routing, model generation, bounded repair, actual PostgreSQL role enforcement,
timeouts, and answer correctness remain NOT TESTED here. The next experiment
would use recorded SQL and a captured live schema, followed by a separate,
isolated database test. That work must distinguish observed database results
from offline predictions and must preserve these negative examples.
