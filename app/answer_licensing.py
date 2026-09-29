"""Deterministic licensing for database-result answers.

This module only verifies that displayed cells are copied from rows returned by
an executed, validated read query. It does not prove that generated SQL matches
the user's intended meaning.
"""

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal


RESULT_SUPPORTED = "RESULT_SUPPORTED"
RESULT_BOUNDED = "RESULT_BOUNDED"
WITHHELD = "WITHHELD"
NOT_APPLICABLE = "NOT_APPLICABLE"
DEFAULT_MAX_DISPLAY_ROWS = 10

LICENSE_SCOPE = (
    "Displayed cells are copied from rows returned by an executed, validated "
    "read query. This check does not independently verify that the SQL matches "
    "the user's intended question."
)


def _safe_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _check(name, passed):
    return {"name": name, "passed": bool(passed)}


def evaluate_answer_license(
    *,
    request_type,
    validation_status,
    execution_status,
    rows,
    result_truncated=False,
    max_display_rows=DEFAULT_MAX_DISPLAY_ROWS,
):
    """Return a narrow, auditable decision for a database-backed answer."""

    if request_type != "READ_QUERY":
        return {
            "answer_license": NOT_APPLICABLE,
            "answer_evidence": [],
            "verification_checks": [],
            "withholding_reason": None,
            "license_scope": LICENSE_SCOPE,
            "displayed_row_count": 0,
        }

    rowset_valid = isinstance(rows, list) and all(
        isinstance(row, Mapping) for row in rows
    )
    checks = [
        _check("read_query", True),
        _check("sql_validation_passed", validation_status == "VALID"),
        _check("database_execution_succeeded", execution_status == "SUCCESS"),
        _check("result_is_list_of_rows", rowset_valid),
        _check("database_result_not_truncated", not result_truncated),
        _check(
            "within_answer_display_limit",
            rowset_valid and len(rows) <= max_display_rows,
        ),
        {
            "name": "question_to_sql_semantics",
            "passed": None,
            "status": "not_assessed",
        },
    ]

    failed_reason = None
    if validation_status != "VALID":
        failed_reason = "The SQL did not pass validation."
    elif execution_status != "SUCCESS":
        failed_reason = "The database query did not complete successfully."
    elif not rowset_valid:
        failed_reason = "The database result was not a valid list of rows."

    if failed_reason:
        status = WITHHELD
        evidence = []
        displayed_count = 0
    else:
        displayed = rows[:max_display_rows]
        evidence = [
            {
                "row_index": row_index,
                "field": field,
                "value": _safe_value(value),
            }
            for row_index, row in enumerate(displayed)
            for field, value in row.items()
        ]
        displayed_count = len(displayed)
        status = (
            RESULT_BOUNDED
            if result_truncated or len(rows) > max_display_rows
            else RESULT_SUPPORTED
        )

    return {
        "answer_license": status,
        "answer_evidence": evidence,
        "verification_checks": checks,
        "withholding_reason": failed_reason,
        "license_scope": LICENSE_SCOPE,
        "displayed_row_count": displayed_count,
    }


def _cell(value):
    if value is None:
        rendered = "NULL"
    elif isinstance(value, (date, datetime)):
        rendered = value.isoformat()
    else:
        rendered = str(value)
    return rendered.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_result_table(
    rows,
    *,
    result_truncated=False,
    max_display_rows=DEFAULT_MAX_DISPLAY_ROWS,
):
    """Render only database-returned values; do not add model-written claims."""

    if not rows:
        return "The executed query returned no matching rows."

    displayed = rows[:max_display_rows]
    columns = list(dict.fromkeys(
        column for row in displayed for column in row.keys()
    ))
    if not columns:
        return "The executed query returned rows with no displayable columns."

    lines = [
        "Values returned by the executed database query:",
        "",
        "| " + " | ".join(_cell(column) for column in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in displayed:
        lines.append(
            "| " + " | ".join(_cell(row.get(column)) for column in columns) + " |"
        )

    if result_truncated:
        lines.extend([
            "",
            "The database result was truncated at its retrieval limit. "
            "Completeness-based conclusions are not licensed.",
        ])
    elif len(rows) > max_display_rows:
        lines.extend([
            "",
            f"Showing the first {max_display_rows} of {len(rows)} returned rows.",
        ])

    return "\n".join(lines)
