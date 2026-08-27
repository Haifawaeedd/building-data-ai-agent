# Evaluation Methodology

## Evaluation philosophy

The project intentionally avoids reporting one global
"accuracy" number for all agent behavior.

Different system properties are evaluated separately:

1. SQL validation
2. SQL execution
3. execution-result agreement
4. semantic routing
5. write-request classification
6. write-request execution containment
7. database integrity
8. latency

This distinction prevents a safe-but-misclassified request
from being treated as equivalent to an executed destructive request.

---

## Frozen development benchmark

The original controlled analytical benchmark contained 15 cases.

**Final frozen result: 13/15 end-to-end strict successes.**

The benchmark was preserved rather than retroactively rewritten
after failure analysis.

### Q06 failure audit

The generated SQL returned the requested top-five ranking correctly
but included additional contextual columns.

The original strict full-row comparator therefore marked the
case as a failure.

A later contract-aware audit classified this as an
**evaluation-shape artifact** rather than a ranking error.

### Q13 failure audit

The initial semantic preflight rejected a clean-electricity-generation
question even though the live schema contained:

`electricity_clean_kwh`

The failure exposed a semantic specification issue rather than
physical schema absence.

Source-grounded semantic metadata and explicit domain contracts
were added after this observation.

The original benchmark remains **13/15**.

---

## Final frozen hold-out

A new set of previously unseen questions was used once after
semantic remediation.

### Analytical queries

| Metric | Result |
|---|---:|
| Questions | 12 |
| Successful executions | **12/12** |
| Strict full-result agreement | **11/12** |
| Answer-contract execution agreement | **12/12** |
| Queries requiring repair | **0/12** |

Strict agreement Wilson 95% CI:

**64.6% – 98.5%**

Answer-contract agreement Wilson 95% CI:

**75.7% – 100%**

The intervals are wide because the hold-out is small.

---

## Semantic-routing hold-out

| Metric | Result |
|---|---:|
| Cases | 4 |
| Correct routing without SQL execution | **4/4** |

These cases included unsupported concepts and ambiguous
analytical definitions.

---

## Write-oriented hold-out

| Metric | Result |
|---|---:|
| Cases | 5 |
| Intended WRITE_REQUEST classification | **4/5** |
| SQL generated | **0/5** |
| Database execution | **0/5** |

One request was classified as `SCHEMA_MISMATCH` rather than
`WRITE_REQUEST`.

It still produced:

- no SQL
- no database execution
- no database modification

Classification quality and execution containment are therefore
reported separately.

---

## Database integrity

Before and after the safety evaluation:

```text
Rows before: 535
Rows after:  535
```

**Database integrity was preserved.**

---

## Containerized regression suite

The final production Docker image passed:

**11/11 automated tests**

The suite covers:

- API health behavior
- request validation
- write-request containment
- deterministic semantic routing
- supported semantic mappings
- SQL guardrail behavior
- unknown-column rejection
- unknown-table rejection
- write-statement rejection

---

## Final Docker validation

The full containerized stack passed:

- PostgreSQL startup
- Government CSV loading
- 535-record verification
- readonly_agent verification
- FastAPI health check
- dynamic schema endpoint
- containerized pytest
- real Text-to-SQL request
- write-request containment
- provenance endpoint
- database-integrity verification

---

## Performance baseline

A small local performance profile included:

- 5 READ_QUERY requests
- 3 deterministic policy requests

Observed READ_QUERY latency:

- mean: approximately 14.8 seconds
- median / p50: approximately 15.8 seconds
- approximate p95: approximately 21.6 seconds

Observed deterministic policy routing:

- approximately 1 millisecond median

This is a prototype baseline, not a production load test.

---

## Claims intentionally not made

The project does not claim:

- 100% general Text-to-SQL accuracy
- deterministic LLM behavior
- generalization to arbitrary databases
- formal security certification
- production-scale latency
- penetration-test coverage
- PostGIS support in the current version

The 12/12 answer-contract result applies only to the documented
frozen hold-out under the current schema and task distribution.
