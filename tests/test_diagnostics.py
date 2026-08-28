from app.diagnostics import (
    diagnose_run,
    summarize_runs,
)


def test_successful_read_query_is_success():
    result = {
        "request_type": "READ_QUERY",
        "validation_status": "VALID",
        "execution_status": "SUCCESS",
        "retry_count": 0,
        "latency_ms": 800,
        "trace": ["request_preflight", "execute_sql"],
    }

    diagnosis = diagnose_run(result)

    assert diagnosis["outcome_category"] == "SUCCESS"
    assert diagnosis["failure_category"] is None


def test_write_request_non_execution_is_safe_containment():
    result = {
        "request_type": "WRITE_REQUEST",
        "execution_status": "NOT_EXECUTED",
        "retry_count": 0,
        "latency_ms": 2,
        "trace": ["request_preflight", "policy_response"],
    }

    diagnosis = diagnose_run(result)

    assert diagnosis["outcome_category"] == "SAFE_POLICY_CONTAINMENT"
    assert diagnosis["failure_category"] is None


def test_failed_repair_is_classified_by_component():
    result = {
        "request_type": "READ_QUERY",
        "validation_status": "VALID",
        "execution_status": "ERROR",
        "retry_count": 1,
        "latency_ms": 1200,
        "trace": [
            "request_preflight",
            "generate_sql",
            "execute_sql_error",
            "repair_sql_retry_1",
            "execute_sql_error",
        ],
    }

    diagnosis = diagnose_run(result)

    assert diagnosis["outcome_category"] == "REPAIR_EXHAUSTED"
    assert diagnosis["failure_category"] == "TOOL_EXECUTION"


def test_latency_budget_has_explicit_outcome():
    result = {
        "request_type": "READ_QUERY",
        "validation_status": "VALID",
        "execution_status": "SUCCESS",
        "retry_count": 0,
        "latency_ms": 30000,
        "trace": [],
    }

    diagnosis = diagnose_run(result, latency_budget_ms=25000)

    assert diagnosis["outcome_category"] == "LATENCY_BUDGET_EXCEEDED"
    assert diagnosis["failure_category"] == "LATENCY"


def test_operational_summary_separates_safe_containment_from_failure():
    results = [
        {
            "request_type": "READ_QUERY",
            "validation_status": "VALID",
            "execution_status": "SUCCESS",
            "retry_count": 0,
            "latency_ms": 100,
            "trace": [],
        },
        {
            "request_type": "WRITE_REQUEST",
            "execution_status": "NOT_EXECUTED",
            "retry_count": 0,
            "latency_ms": 1,
            "trace": [],
        },
        {
            "request_type": "READ_QUERY",
            "validation_status": "VALID",
            "execution_status": "ERROR",
            "retry_count": 1,
            "latency_ms": 200,
            "trace": [],
        },
    ]

    metrics = summarize_runs(results)

    assert metrics["runs"] == 3
    assert metrics["success_rate"] == 0.6667
    assert metrics["repair_rate"] == 0.3333
    assert metrics["failure_categories"] == {"TOOL_EXECUTION": 1}
