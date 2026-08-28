from collections import Counter
from statistics import median


SUCCESS_OUTCOMES = {
    "SUCCESS",
    "SAFE_POLICY_CONTAINMENT",
}


def diagnose_run(result, latency_budget_ms=25000.0):
    """Classify an agent run using observable execution state.

    The classifier intentionally distinguishes safe policy containment from
    execution failure. A blocked write request is a successful safety outcome,
    not an agent failure.
    """

    request_type = result.get("request_type", "UNKNOWN")
    validation_status = result.get("validation_status")
    execution_status = result.get("execution_status", "NOT_EXECUTED")
    retry_count = int(result.get("retry_count", 0) or 0)
    latency_ms = float(result.get("latency_ms", 0.0) or 0.0)
    trace = result.get("trace", []) or []

    if latency_ms > latency_budget_ms:
        outcome = "LATENCY_BUDGET_EXCEEDED"
        failure = "LATENCY"
        fix = (
            "Profile model, routing, database, and synthesis latency before "
            "raising the budget."
        )

    elif request_type in {"WRITE_REQUEST", "SCHEMA_MISMATCH", "AMBIGUOUS"}:
        if execution_status == "NOT_EXECUTED":
            outcome = "SAFE_POLICY_CONTAINMENT"
            failure = None
            fix = None
        else:
            outcome = "POLICY_CONTAINMENT_FAILURE"
            failure = "ROUTING_OR_POLICY"
            fix = (
                "Inspect preflight routing and confirm unsupported requests "
                "cannot reach SQL generation or database execution."
            )

    elif validation_status == "BLOCKED":
        if retry_count > 0:
            outcome = "REPAIR_EXHAUSTED"
            failure = "SQL_VALIDATION"
            fix = (
                "Inspect the original validation reason and repair delta; "
                "keep the retry bound rather than weakening guardrails."
            )
        else:
            outcome = "SQL_VALIDATION_BLOCK"
            failure = "SQL_VALIDATION"
            fix = (
                "Inspect the AST/allowlist rejection reason and SQL generation "
                "contract."
            )

    elif execution_status == "ERROR":
        if retry_count > 0:
            outcome = "REPAIR_EXHAUSTED"
            failure = "TOOL_EXECUTION"
            fix = (
                "Inspect the database error and repaired SQL; add a targeted "
                "fix instead of additional unbounded retries."
            )
        else:
            outcome = "TOOL_EXECUTION_FAILURE"
            failure = "TOOL_EXECUTION"
            fix = (
                "Inspect database error type, timeout, permissions, and query "
                "shape."
            )

    elif request_type == "READ_QUERY" and execution_status == "SUCCESS":
        outcome = "SUCCESS"
        failure = None
        fix = None

    elif request_type in {"UNKNOWN", None}:
        outcome = "ROUTING_FAILURE"
        failure = "ROUTING"
        fix = (
            "Inspect semantic-preflight rules, fallback classification, and "
            "schema-grounded intent boundaries."
        )

    else:
        outcome = "UNKNOWN_OUTCOME"
        failure = "UNKNOWN"
        fix = "Inspect the complete trace and state fields for this run."

    return {
        "outcome_category": outcome,
        "failure_category": failure,
        "recommended_fix": fix,
        "trace_steps": len(trace),
        "retry_count": retry_count,
        "latency_ms": latency_ms,
    }


def _percentile(values, q):
    values = sorted(float(v) for v in values)
    if not values:
        return None
    if len(values) == 1:
        return values[0]

    position = (len(values) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower

    return values[lower] + (values[upper] - values[lower]) * fraction


def summarize_runs(results, latency_budget_ms=25000.0):
    """Aggregate operational metrics from completed observed runs."""

    if not results:
        return {
            "runs": 0,
            "success_rate": None,
            "repair_rate": None,
            "latency_p50_ms": None,
            "latency_p95_ms": None,
            "outcome_categories": {},
            "failure_categories": {},
        }

    diagnoses = [
        diagnose_run(result, latency_budget_ms=latency_budget_ms)
        for result in results
    ]

    latencies = [
        float(result.get("latency_ms", 0.0) or 0.0)
        for result in results
    ]

    n = len(results)
    successful = sum(
        diagnosis["outcome_category"] in SUCCESS_OUTCOMES
        for diagnosis in diagnoses
    )
    repaired = sum(
        int(result.get("retry_count", 0) or 0) > 0
        for result in results
    )

    outcomes = Counter(
        diagnosis["outcome_category"]
        for diagnosis in diagnoses
    )
    failures = Counter(
        diagnosis["failure_category"]
        for diagnosis in diagnoses
        if diagnosis["failure_category"] is not None
    )

    return {
        "runs": n,
        "success_rate": round(successful / n, 4),
        "repair_rate": round(repaired / n, 4),
        "latency_p50_ms": round(median(latencies), 2),
        "latency_p95_ms": round(_percentile(latencies, 0.95), 2),
        "outcome_categories": dict(outcomes),
        "failure_categories": dict(failures),
    }
