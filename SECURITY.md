# Security Model

Building Data AI Agent is designed as a
**read-only analytical research prototype**.

The system uses multiple independent controls rather than
treating the LLM or SQL validator as a complete security boundary.

---

## 1. Semantic request controls

The preflight layer classifies requests as:

- `READ_QUERY`
- `WRITE_REQUEST`
- `SCHEMA_MISMATCH`
- `AMBIGUOUS`

High-confidence write, unsupported, and ambiguity cases are
handled using deterministic policy rules.

Requests classified as write-oriented terminate before SQL generation.

---

## 2. SQL lexical validation

Generated SQL must follow a read-query form using:

- `SELECT`
- `WITH`

Controls include:

- one SQL statement only
- rejection of known write/admin keywords
- rejection of empty SQL

---

## 3. AST validation

`sqlglot` parses generated SQL structurally.

The validator enforces:

- SELECT-containing queries only
- approved physical tables
- approved columns
- CTE-aware table handling
- approved schema usage
- rejection of write/admin AST nodes

Unknown columns and unknown tables are rejected.

---

## 4. PostgreSQL security boundary

The production application connects using:

`readonly_agent`

The role is configured with:

- no superuser privileges
- no CREATEDB privileges
- no CREATEROLE privileges
- no replication privileges
- SELECT-only access to the application table
- `default_transaction_read_only = on`

Application query execution additionally performs:

`SET TRANSACTION READ ONLY`

This database boundary is intentionally independent of
language-model behavior and application-level SQL validation.

---

## 5. Execution-resource controls

Queries are bounded using:

- statement timeout: 5000 ms
- maximum returned rows: 200
- maximum SQL repair attempts: 1

The repair loop cannot continue indefinitely.

---

## 6. API controls

The current FastAPI application exposes analytical interfaces only.

There is no direct database-mutation endpoint.

Pydantic request validation enforces input constraints.

Internal stack traces and credentials are not intentionally returned
through API responses.

---

## 7. Secret handling

The following local resources are excluded from Git:

- `.env`
- OpenAI API key
- PostgreSQL passwords
- local Government source CSV
- runtime provenance logs

The repository contains `.env.example` with placeholder values only.

---

## 8. Logging controls

Structured logs intentionally focus on operational metadata such as:

- request ID
- request classification
- validation status
- execution status
- retry count
- LangGraph trace
- latency

The logging layer is designed not to record:

- API keys
- database passwords
- complete database connection strings

---

## 9. Provenance fingerprints

SHA-256 fingerprints are generated for selected artifacts:

- live schema
- generated SQL
- executed result payload
- complete provenance ledger

These fingerprints support reproducibility and integrity comparison.

They are not:

- digital signatures
- proof of publisher authenticity
- cryptographic security certification

---

## 10. Observed safety evaluation

In the frozen write-oriented hold-out:

- intended WRITE_REQUEST classification: 4/5
- SQL generated: 0/5
- database execution: 0/5
- database rows before: 535
- database rows after: 535

One write-oriented request was classified as `SCHEMA_MISMATCH`
rather than `WRITE_REQUEST`, but still produced no SQL or execution.

Classification quality and execution containment are therefore
reported separately.

---

## Scope statement

This project is a research and portfolio engineering prototype.

The implemented safeguards should not be interpreted as:

- formal security certification
- penetration-testing evidence
- guarantee against every SQL attack class
- guarantee against every prompt-injection strategy
- production deployment approval

A real public deployment would additionally require:

- authentication and authorization
- API rate limiting
- managed secret storage
- network isolation
- centralized audit logging
- dependency vulnerability scanning
- deployment-specific security testing
- monitoring and alerting
- incident-response procedures
