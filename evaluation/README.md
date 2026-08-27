# Evaluation Evidence

The project preserves separate development and hold-out evidence.

## Original frozen benchmark

The original controlled benchmark remained frozen at:

- 13/15 end-to-end strict successes
- identified Q06 as an evaluation-shape artifact
- identified Q13 as a semantic-preflight specification issue

Those results were not retroactively rewritten.

## Final hold-out

Previously unseen analytical questions:

- 12/12 successful executions
- 12/12 answer-contract execution agreement
- 11/12 strict full-result agreement

Semantic routing:

- 4/4 unseen cases correctly routed without SQL execution

Write-oriented hold-out:

- 4/5 intended WRITE_REQUEST classifications
- 5/5 produced no database execution
- database integrity preserved

## Performance baseline

READ_QUERY prototype latency:

- median / p50 ≈ 15.8 seconds
- approximate p95 ≈ 21.6 seconds

Deterministic policy routing:

- approximately 1 ms in the local profiling sample

These measurements are prototype observations, not a production
load test or general performance guarantee.
