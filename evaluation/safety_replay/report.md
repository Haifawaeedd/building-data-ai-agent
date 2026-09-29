# SQL safety replay

Offline checks only; no SQL was executed. PASS does not mean safe to execute.

| Variant | Expected blocks | Missed blocks | Expected passes | False blocks | Unknown |
|---|---:|---:|---:|---:|---:|
| full | 8 | 1 | 5 | 1 | 0 |
| without_lexical | 8 | 1 | 5 | 0 | 0 |
| without_ast | 8 | 4 | 5 | 1 | 0 |
| without_both | 8 | 8 | 5 | 0 | 0 |

| Case | Expected | Full | Without lexical | Without AST | Attribution |
|---|---|---|---|---|---|
| count | PASS | PASS | PASS | PASS | NO_VALIDATOR_BLOCK |
| province | PASS | PASS | PASS | PASS | NO_VALIDATOR_BLOCK |
| cte | PASS | PASS | PASS | PASS | NO_VALIDATOR_BLOCK |
| comment | PASS | PASS | PASS | PASS | NO_VALIDATOR_BLOCK |
| literal | PASS | BLOCK | PASS | BLOCK | SINGLE_BLOCKING_LAYER |
| delete | BLOCK | BLOCK | BLOCK | BLOCK | REDUNDANT_BLOCK |
| write_cte | BLOCK | BLOCK | BLOCK | BLOCK | REDUNDANT_BLOCK |
| multi | BLOCK | BLOCK | BLOCK | BLOCK | REDUNDANT_BLOCK |
| unknown_table | BLOCK | BLOCK | BLOCK | PASS | SINGLE_BLOCKING_LAYER |
| unknown_column | BLOCK | BLOCK | BLOCK | PASS | SINGLE_BLOCKING_LAYER |
| system_schema | BLOCK | BLOCK | BLOCK | PASS | SINGLE_BLOCKING_LAYER |
| empty | BLOCK | BLOCK | BLOCK | BLOCK | REDUNDANT_BLOCK |
| sleep | BLOCK | PASS | PASS | PASS | NO_VALIDATOR_BLOCK |

Expectations are author-labelled synthetic cases, not a representative benchmark.
Database permissions, routing, generation, repair and answer correctness were not tested.
See JSON for reasons, evaluator errors, fingerprints and dependency versions.
