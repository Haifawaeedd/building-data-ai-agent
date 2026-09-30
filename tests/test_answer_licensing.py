import json
import subprocess
import sys
from pathlib import Path

from app.answer_licensing import (
    NOT_APPLICABLE,
    RESULT_BOUNDED,
    RESULT_SUPPORTED,
    WITHHELD,
    evaluate_answer_license,
    render_result_table,
)


def decide(**overrides):
    values = {
        "request_type": "READ_QUERY",
        "validation_status": "VALID",
        "execution_status": "SUCCESS",
        "rows": [{"province": "Nova Scotia", "total_kwh": 42}],
        "result_truncated": False,
    }
    values.update(overrides)
    return evaluate_answer_license(**values)


def test_complete_read_result_is_supported_by_result():
    decision = decide()

    assert decision["answer_license"] == RESULT_SUPPORTED
    assert decision["answer_evidence"] == [
        {"row_index": 0, "field": "province", "value": "Nova Scotia"},
        {"row_index": 0, "field": "total_kwh", "value": 42},
    ]
    assert decision["verification_checks"][-1]["status"] == "not_assessed"


def test_empty_successful_query_is_a_supported_empty_result():
    decision = decide(rows=[])

    assert decision["answer_license"] == RESULT_SUPPORTED
    assert decision["answer_evidence"] == []
    assert render_result_table([]) == "The executed query returned no matching rows."


def test_truncated_result_is_bounded():
    decision = decide(result_truncated=True)

    assert decision["answer_license"] == RESULT_BOUNDED
    assert decision["verification_checks"][4]["passed"] is False


def test_display_limit_is_bounded_and_evidence_matches_displayed_rows():
    rows = [{"value": index} for index in range(12)]
    decision = decide(rows=rows)

    assert decision["answer_license"] == RESULT_BOUNDED
    assert decision["displayed_row_count"] == 10
    assert len(decision["answer_evidence"]) == 10
    assert "first 10 of 12 returned rows" in render_result_table(rows)


def test_unvalidated_sql_is_withheld():
    decision = decide(validation_status="BLOCKED")

    assert decision["answer_license"] == WITHHELD
    assert decision["answer_evidence"] == []
    assert decision["withholding_reason"] == "The SQL did not pass validation."


def test_failed_execution_is_withheld():
    decision = decide(execution_status="ERROR")

    assert decision["answer_license"] == WITHHELD
    assert decision["withholding_reason"] == "The database query did not complete successfully."


def test_policy_or_clarification_response_is_not_applicable():
    decision = decide(request_type="AMBIGUOUS")

    assert decision["answer_license"] == NOT_APPLICABLE
    assert decision["answer_evidence"] == []


def test_table_escapes_markdown_and_marks_nulls():
    answer = render_result_table(
        [{"label": "a|b", "note": "line1\nline2", "value": None}]
    )

    assert "a\\|b" in answer
    assert "line1 line2" in answer
    assert "NULL" in answer


def test_evaluation_runner_passes_its_frozen_cases():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "evaluation" / "run_answer_licensing.py")],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)

    assert report["cases"] >= 8
    assert report["passed"] == report["cases"]
    assert report["failed"] == 0
