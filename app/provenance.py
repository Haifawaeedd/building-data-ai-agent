import hashlib
import json
from datetime import (
    datetime,
    timezone
)
from pathlib import Path

from app.config import (
    settings
)

from app.observability import (
    invoke_agent_observed
)

from app.schema import (
    dynamic_schema,
    DATASET_PROVENANCE
)


def stable_json(
    value
):

    return json.dumps(

        value,

        sort_keys=True,

        ensure_ascii=False,

        default=str,

        separators=(
            ",",
            ":"
        )
    )


def fingerprint(
    value
):

    if value is None:

        return None


    payload = (

        value

        if isinstance(
            value,
            str
        )

        else stable_json(
            value
        )
    )


    return hashlib.sha256(

        payload.encode(
            "utf-8"
        )

    ).hexdigest()


LIVE_SCHEMA_FINGERPRINT = (
    fingerprint(
        dynamic_schema
    )
)


def build_provenance_ledger(
    question
):

    result = (
        invoke_agent_observed(
            question
        )
    )


    request_type = result.get(
        "request_type",
        "UNKNOWN"
    )


    sql = result.get(
        "sql"
    )


    rows = result.get(
        "rows",
        []
    )


    trace = result.get(
        "trace",
        []
    )


    if (
        request_type
        == "READ_QUERY"

        and

        result.get(
            "execution_status"
        )
        == "SUCCESS"
    ):

        grounding_mode = (
            "DATABASE_EXECUTED"
        )

        provenance_status = (
            "GROUNDED"
        )


    else:

        grounding_mode = (
            "POLICY_ONLY"
        )


        if request_type in {

            "WRITE_REQUEST",
            "SCHEMA_MISMATCH",
            "AMBIGUOUS"

        }:

            provenance_status = (
                "CONTROLLED_NON_EXECUTION"
            )


        else:

            provenance_status = (
                "UNRESOLVED"
            )


    result_payload = {

        "rows":
            rows,

        "row_count":
            len(rows),

        "truncated":
            result.get(
                "result_truncated",
                False
            )
    }


    ledger = {

        "ledger_version":
            "1.0",

        "request_id":
            result.get(
                "request_id"
            ),

        "timestamp_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "request": {

            "question":
                question,

            "request_type":
                request_type,

            "preflight_reason":
                result.get(
                    "preflight_reason"
                ),

            "decision_source":
                result.get(
                    "decision_source"
                )
        },

        "provenance": {

            "status":
                provenance_status,

            "grounding_mode":
                grounding_mode,

            "source":
                DATASET_PROVENANCE,

            "schema_fingerprint_sha256":
                LIVE_SCHEMA_FINGERPRINT
        },

        "sql_evidence": {

            "sql_generated":
                sql is not None,

            "sql":
                sql,

            "sql_fingerprint_sha256":
                fingerprint(
                    sql
                ),

            "validation_status":
                result.get(
                    "validation_status"
                ),

            "validation_reason":
                result.get(
                    "validation_reason"
                )
        },

        "execution": {

            "status":
                result.get(
                    "execution_status"
                ),

            "row_count":
                len(rows),

            "result_truncated":
                result.get(
                    "result_truncated",
                    False
                ),

            "max_result_rows":
                settings.max_result_rows,

            "statement_timeout_ms":
                settings.statement_timeout_ms,

            "retry_count":
                result.get(
                    "retry_count",
                    0
                ),

            "max_retries":
                settings.max_sql_retries,

            "result_fingerprint_sha256":
                (

                    fingerprint(
                        result_payload
                    )

                    if grounding_mode
                    == "DATABASE_EXECUTED"

                    else None
                )
        },

        "agent_trace": {

            "nodes":
                trace,

            "path":
                " → ".join(
                    trace
                )
        },

        "response": {

            "answer":
                result.get(
                    "answer",
                    ""
                )
        },

        "performance": {

            "latency_ms":
                result.get(
                    "latency_ms"
                )
        }
    }


    ledger[
        "ledger_fingerprint_sha256"
    ] = fingerprint(
        ledger
    )


    return ledger


def append_provenance_ledger(
    ledger
):

    path = Path(
        settings.provenance_log_path
    )


    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    with path.open(
        "a",
        encoding="utf-8"
    ) as file:

        file.write(

            json.dumps(
                ledger,
                ensure_ascii=False,
                default=str
            )

            + "\n"
        )


    return path
