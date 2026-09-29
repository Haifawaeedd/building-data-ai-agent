"""Offline, fixed-SQL guardrail ablation. Never connects to or executes SQL."""
import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

from app import guardrails

VARIANTS = {
    "full": ("lexical", "ast"),
    "without_lexical": ("ast",),
    "without_ast": ("lexical",),
    "without_both": (),
}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def _check(call):
    try:
        allowed, reason = call()
        return {"decision": "PASS" if allowed else "BLOCK", "reason": reason}
    except Exception as error:
        # An evaluator error is not evidence that a guardrail blocked SQL.
        return {"decision": "ERROR", "reason": type(error).__name__}


def _decision(checks, enabled):
    states = [checks[name]["decision"] for name in enabled]
    if "BLOCK" in states:
        return "BLOCK"
    if "ERROR" in states:
        return "UNKNOWN"
    return "PASS"


def replay(bundle):
    """Compare the same candidate against independently evaluated actual checks.

    PASS means passed these validators, never permission to execute.
    Expectations are fixture-author labels, not learned ground truth.
    """
    schema = bundle["schema"]
    for key in ("allowed_tables", "known_columns"):
        if (not isinstance(schema.get(key), list)
                or not all(isinstance(v, str) and v for v in schema[key])):
            raise ValueError(f"schema.{key} must be a list of nonempty strings")
    cases = bundle["cases"]
    if not isinstance(cases, list) or not cases:
        raise ValueError("cases must be a nonempty list")
    ids = set()
    rows = []
    for case in cases:
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            raise ValueError("case IDs must be unique nonempty strings")
        ids.add(case_id)
        if case.get("expected") not in {"PASS", "BLOCK"}:
            raise ValueError("expected must be PASS or BLOCK")
        if not isinstance(case.get("sql"), str):
            raise ValueError("sql must be a string")
        sql = case["sql"]
        checks = {
            "lexical": _check(lambda: guardrails.validate_readonly_sql(sql)),
            "ast": _check(lambda: guardrails.validate_sql_ast(
                sql, allowed_tables=set(schema["allowed_tables"]),
                known_columns=set(schema["known_columns"]))),
        }
        variants = {name: _decision(checks, enabled)
                    for name, enabled in VARIANTS.items()}
        blockers = [name for name, check in checks.items()
                    if check["decision"] == "BLOCK"]
        errors = [name for name, check in checks.items()
                  if check["decision"] == "ERROR"]
        if errors:
            attribution = "INCOMPLETE"
        elif len(blockers) == 2:
            attribution = "REDUNDANT_BLOCK"
        elif len(blockers) == 1:
            attribution = "SINGLE_BLOCKING_LAYER"
        else:
            attribution = "NO_VALIDATOR_BLOCK"
        rows.append({
            "id": case_id, "sql": sql, "expected": case["expected"],
            "rationale": case.get("rationale", ""), "checks": checks,
            "variants": variants, "blocking_layers": blockers,
            "attribution": attribution,
            "full_matches_expectation": variants["full"] == case["expected"],
            "database_enforcement": "NOT_TESTED",
        })
    summary = {}
    for variant in VARIANTS:
        expected_blocks = [r for r in rows if r["expected"] == "BLOCK"]
        expected_passes = [r for r in rows if r["expected"] == "PASS"]
        summary[variant] = {
            "cases": len(rows),
            "expected_block_cases": len(expected_blocks),
            "expected_pass_cases": len(expected_passes),
            "missed_blocks": sum(r["variants"][variant] == "PASS" for r in expected_blocks),
            "false_blocks": sum(r["variants"][variant] == "BLOCK" for r in expected_passes),
            "unknown": sum(r["variants"][variant] == "UNKNOWN" for r in rows),
            "evaluator_error_cases": sum(any(c["decision"] == "ERROR" for c in r["checks"].values()) for r in rows),
        }
    return {
        "format_version": 1,
        "scope": "offline_fixed_sql_validator_ablation",
        "sql_executed": False,
        "excluded": ["semantic_router", "LLM_generation", "repair", "database_enforcement", "answer_correctness"],
        "schema_origin": bundle.get("schema_origin", "UNSPECIFIED"),
        "input_sha256": fingerprint(bundle),
        "schema_sha256": fingerprint(schema),
        "guardrails_sha256": hashlib.sha256(Path(guardrails.__file__).read_bytes()).hexdigest(),
        "replay_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "dependencies": {name: version(name) for name in ("sqlglot", "sqlparse")},
        "summary": summary, "cases": rows,
    }


def markdown(report):
    lines = ["# SQL safety replay", "", "Offline checks only; no SQL was executed. PASS does not mean safe to execute.", "",
             "| Variant | Expected blocks | Missed blocks | Expected passes | False blocks | Unknown |",
             "|---|---:|---:|---:|---:|---:|"]
    for variant, s in report["summary"].items():
        lines.append(f"| {variant} | {s['expected_block_cases']} | {s['missed_blocks']} | {s['expected_pass_cases']} | {s['false_blocks']} | {s['unknown']} |")
    lines += ["", "| Case | Expected | Full | Without lexical | Without AST | Attribution |",
              "|---|---|---|---|---|---|"]
    for row in report["cases"]:
        label = row["id"].replace("|", "\\|").replace("\n", " ").replace("\r", " ")
        v = row["variants"]
        lines.append(f"| {label} | {row['expected']} | {v['full']} | {v['without_lexical']} | {v['without_ast']} | {row['attribution']} |")
    lines += ["", "Expectations are author-labelled synthetic cases, not a representative benchmark.",
              "Database permissions, routing, generation, repair and answer correctness were not tested.",
              "See JSON for reasons, evaluator errors, fingerprints and dependency versions.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--fail-on-mismatch", action="store_true")
    args = parser.parse_args()
    report = replay(json.loads(args.input.read_text()))
    data = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.json_output:
        args.json_output.write_text(data)
    else:
        print(data, end="")
    if args.markdown_output:
        args.markdown_output.write_text(markdown(report))
    if args.fail_on_mismatch and any(
        not r["full_matches_expectation"] or any(c["decision"] == "ERROR" for c in r["checks"].values())
        for r in report["cases"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
