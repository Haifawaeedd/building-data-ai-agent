# Portfolio Summary

## Building Data AI Agent

Engineered a containerized, auditable **LangGraph Text-to-SQL agent**
over **535 real Government of Canada Atlantic facility-energy records**.

### Technology stack

- Python
- LangGraph
- OpenAI API
- PostgreSQL
- psycopg
- sqlglot
- FastAPI
- Docker / Docker Compose
- pytest
- structured JSON logging

### Engineering highlights

- dynamic PostgreSQL schema introspection
- source-grounded semantic request routing
- deterministic safety and ambiguity policies
- LLM-based Text-to-SQL generation
- CTE-aware AST validation
- table and column allowlisting
- bounded one-retry SQL repair
- dedicated PostgreSQL `readonly_agent`
- explicit read-only transactions
- statement timeout and row cap
- typed FastAPI REST service
- containerized PostgreSQL and application
- structured request tracing
- SHA-256 answer-provenance ledger

### Evaluation highlights

Frozen unseen analytical hold-out:

- 12/12 successful SQL executions
- 12/12 answer-contract execution agreement
- 11/12 strict full-result agreement

Semantic hold-out:

- 4/4 correctly routed without SQL execution

Write-oriented hold-out:

- 4/5 intended WRITE_REQUEST classification
- 0/5 generated SQL
- 0/5 reached database execution
- database integrity preserved at 535 records

Production validation:

- 11/11 containerized regression tests passed
- real Text-to-SQL Docker request passed
- write-request containment passed
- provenance endpoint passed

### Known performance limitation

Prototype READ_QUERY performance:

- median / p50: approximately 15.8 seconds
- approximate p95: approximately 21.6 seconds

This is a portfolio/research prototype rather than a
production-scale latency benchmark.
