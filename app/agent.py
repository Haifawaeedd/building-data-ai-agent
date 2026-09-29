import json
from typing import (
    TypedDict,
    Any
)

from openai import OpenAI

from langgraph.graph import (
    StateGraph,
    END
)

from app.config import (
    settings,
    require_openai_key
)

from app.answer_licensing import (
    evaluate_answer_license,
    render_result_table,
)

from app.database import (
    execute_readonly_sql
)

from app.guardrails import (
    validate_sql_professional
)

from app.schema import (
    DYNAMIC_SCHEMA_CONTEXT,
    SEMANTIC_LIVE_SCHEMA,
    LOADED_FISCAL_YEARS
)

from app.semantic_router import (
    classify_request,
    DOMAIN_SEMANTIC_CONTRACTS
)


def _client():

    require_openai_key()

    return OpenAI(
        api_key=
            settings.openai_api_key
    )


def generate_sql(
    question
):

    fiscal_year_context = (
        ", ".join(
            LOADED_FISCAL_YEARS
        )

        if LOADED_FISCAL_YEARS

        else "none detected"
    )


    instructions = f"""
You are a PostgreSQL Text-to-SQL assistant.

Translate the user question into exactly ONE SQL query.

LIVE DATABASE SCHEMA:

{DYNAMIC_SCHEMA_CONTEXT}

SOURCE-GROUNDED SEMANTICS:

{SEMANTIC_LIVE_SCHEMA}

DOMAIN INTERPRETATION CONTRACTS:

{DOMAIN_SEMANTIC_CONTRACTS}

Fiscal years currently present:

{fiscal_year_context}

DATABASE CODES:

NS = Nova Scotia
NB = New Brunswick
NL = Newfoundland and Labrador
PE = Prince Edward Island

STRICT RULES:

1. PostgreSQL syntax only.
2. SELECT or WITH only.
3. Use only tables in the live schema.
4. Use only columns in the live schema.
5. Never invent columns or tables.
6. Never modify database state.
7. Never access system schemas.
8. Treat NULL as missing.
9. Zero is not automatically missing.
10. Follow domain contracts exactly.
11. "records that report <metric>"
    means IS NOT NULL.
12. Do NOT add > 0 unless positive/non-zero
    quantity is explicitly requested.
13. Use deterministic ordering for rankings.
14. Return SQL only.
15. No Markdown.
16. No explanation.
"""


    response = _client().responses.create(

        model=
            settings.openai_model,

        instructions=
            instructions,

        input=
            question
    )


    return (
        response.output_text
        .strip()
    )


def repair_sql(
    question,
    previous_sql,
    failure_reason
):

    instructions = f"""
You are the SQL repair component of a safe
PostgreSQL Text-to-SQL system.

LIVE DATABASE SCHEMA:

{DYNAMIC_SCHEMA_CONTEXT}

SOURCE SEMANTICS:

{SEMANTIC_LIVE_SCHEMA}

DOMAIN CONTRACTS:

{DOMAIN_SEMANTIC_CONTRACTS}

Rules:

1. Return exactly one PostgreSQL query.
2. SELECT or WITH only.
3. Never modify database state.
4. Use only live tables and columns.
5. Never bypass security controls.
6. Treat NULL as missing.
7. Preserve original analytical intent.
8. Fix only what is necessary.
9. Return SQL only.
10. No Markdown.
"""


    repair_input = f"""
ORIGINAL USER QUESTION:

{question}

PREVIOUS SQL:

{previous_sql}

FAILURE:

{failure_reason}

Return the corrected SQL.
"""


    response = _client().responses.create(

        model=
            settings.openai_model,

        instructions=
            instructions,

        input=
            repair_input
    )


    return (
        response.output_text
        .strip()
    )



def execute_sql_bounded(
    sql
):
    """
    Defense in depth:

    AST validation happens here again before
    the database boundary.
    """

    valid, reason = (
        validate_sql_professional(
            sql
        )
    )


    if not valid:

        raise ValueError(
            f"SQL_BLOCKED: {reason}"
        )


    return execute_readonly_sql(
        sql
    )


class BuildingAgentState(
    TypedDict,
    total=False
):

    question: str

    request_type: str
    preflight_reason: str
    clarification: str
    decision_source: str

    sql: str

    validation_status: str
    validation_reason: str

    rows: list[
        dict[str, Any]
    ]

    execution_status: str
    execution_error: str

    result_truncated: bool

    retry_count: int
    max_retries: int
    repair_reason: str

    answer: str
    answer_license: str
    answer_evidence: list[dict[str, Any]]
    verification_checks: list[dict[str, Any]]
    withholding_reason: str
    license_scope: str

    trace: list[str]


def node_preflight(
    state
):

    decision = classify_request(
        state["question"]
    )


    return {

        "request_type":
            decision[
                "request_type"
            ],

        "preflight_reason":
            decision[
                "reason"
            ],

        "clarification":
            decision.get(
                "clarification",
                ""
            ),

        "decision_source":
            decision.get(
                "decision_source",
                "UNKNOWN"
            ),

        "retry_count":
            0,

        "max_retries":
            settings.max_sql_retries,

        "trace":
            state.get(
                "trace",
                []
            )
            + [
                "request_preflight"
            ]
    }


def route_after_preflight(
    state
):

    if (
        state.get(
            "request_type"
        )
        == "READ_QUERY"
    ):

        return "generate_sql"


    return "policy_response"


def node_policy_response(
    state
):
    """Return a policy or clarification response without licensing it as data."""
    request_type = state.get("request_type")

    if request_type == "WRITE_REQUEST":
        answer = (
            "This agent provides read-only access to facility data and cannot "
            "modify, delete, insert, or alter database records."
        )
    elif request_type == "SCHEMA_MISMATCH":
        answer = (
            state.get("clarification", "").strip()
            or "The requested information is not available in the current dataset."
        )
    elif request_type == "AMBIGUOUS":
        answer = (
            state.get("clarification")
            or "Please clarify the requested metric."
        )
    else:
        answer = "The request cannot be safely processed."

    decision = evaluate_answer_license(
        request_type=request_type,
        validation_status=None,
        execution_status="NOT_EXECUTED",
        rows=[],
    )
    return {
        "answer": answer,
        "execution_status": "NOT_EXECUTED",
        **decision,
        "trace": state.get("trace", []) + ["policy_response"],
    }



def node_generate_sql(
    state
):

    return {

        "sql":
            generate_sql(
                state[
                    "question"
                ]
            ),

        "trace":
            state.get(
                "trace",
                []
            )
            + [
                "generate_sql"
            ]
    }


def node_validate_sql(
    state
):

    valid, reason = (
        validate_sql_professional(
            state["sql"]
        )
    )


    return {

        "validation_status":
            (
                "VALID"
                if valid
                else "BLOCKED"
            ),

        "validation_reason":
            reason,

        "trace":
            state.get(
                "trace",
                []
            )
            + [
                "validate_sql"
            ]
    }


def route_after_validation(
    state
):

    if (
        state.get(
            "validation_status"
        )
        == "VALID"
    ):

        return "execute_sql"


    if (
        state.get(
            "retry_count",
            0
        )
        <
        state.get(
            "max_retries",
            settings.max_sql_retries
        )
    ):

        return "repair_sql"


    return "blocked_answer"


def node_execute_sql(
    state
):

    try:

        execution = (
            execute_sql_bounded(
                state["sql"]
            )
        )


        return {

            "rows":
                execution[
                    "rows"
                ],

            "execution_status":
                "SUCCESS",

            "execution_error":
                "",

            "result_truncated":
                execution[
                    "truncated"
                ],

            "trace":
                state.get(
                    "trace",
                    []
                )
                + [
                    "execute_sql"
                ]
        }


    except Exception as error:

        return {

            "rows":
                [],

            "execution_status":
                "ERROR",

            "execution_error":
                (
                    f"{type(error).__name__}: "
                    f"{error}"
                ),

            "trace":
                state.get(
                    "trace",
                    []
                )
                + [
                    "execute_sql_error"
                ]
        }


def route_after_execution(
    state
):

    if (
        state.get(
            "execution_status"
        )
        == "SUCCESS"
    ):

        return "synthesize_answer"


    if (
        state.get(
            "retry_count",
            0
        )
        <
        state.get(
            "max_retries",
            settings.max_sql_retries
        )
    ):

        return "repair_sql"


    return "database_error"


def node_repair_sql(
    state
):

    if (
        state.get(
            "validation_status"
        )
        == "BLOCKED"
    ):

        failure_reason = (
            state.get(
                "validation_reason",
                "SQL validation failed."
            )
        )


    else:

        failure_reason = (
            state.get(
                "execution_error",
                "SQL execution failed."
            )
        )


    repaired = repair_sql(

        question=
            state["question"],

        previous_sql=
            state.get(
                "sql",
                ""
            ),

        failure_reason=
            failure_reason
    )


    retry_count = (
        state.get(
            "retry_count",
            0
        )
        + 1
    )


    return {

        "sql":
            repaired,

        "retry_count":
            retry_count,

        "repair_reason":
            failure_reason,

        "validation_status":
            "PENDING",

        "validation_reason":
            "",

        "execution_status":
            "PENDING",

        "execution_error":
            "",

        "trace":
            state.get(
                "trace",
                []
            )
            + [
                (
                    "repair_sql_retry_"
                    f"{retry_count}"
                )
            ]
    }


def node_synthesize_answer(
    state
):
    decision = evaluate_answer_license(
        request_type=state.get("request_type"),
        validation_status=state.get("validation_status"),
        execution_status=state.get("execution_status"),
        rows=state.get("rows"),
        result_truncated=state.get("result_truncated", False),
    )

    if decision["answer_license"] == "WITHHELD":
        answer = (
            "Answer withheld: "
            + (decision["withholding_reason"] or "the result was not verifiable.")
        )
    else:
        answer = render_result_table(
            state.get("rows", []),
            result_truncated=state.get("result_truncated", False),
        )

    return {
        "answer": answer,
        **decision,
        "trace": state.get("trace", []) + ["render_evidence_checked_answer"],
    }



def node_blocked_answer(
    state
):
    decision = evaluate_answer_license(
        request_type=state.get("request_type"),
        validation_status=state.get("validation_status"),
        execution_status="BLOCKED",
        rows=[],
        result_truncated=False,
    )
    return {
        "answer": (
            "The query could not be safely validated after the allowed repair attempt."
        ),
        "execution_status": "BLOCKED",
        **decision,
        "trace": state.get("trace", []) + ["blocked_answer"],
    }



def node_database_error(
    state
):
    decision = evaluate_answer_license(
        request_type=state.get("request_type"),
        validation_status=state.get("validation_status"),
        execution_status="ERROR",
        rows=[],
        result_truncated=False,
    )
    return {
        "answer": (
            "The database query could not be completed after the allowed repair attempt."
        ),
        "execution_status": "ERROR",
        **decision,
        "trace": state.get("trace", []) + ["database_error"],
    }



def build_agent():

    workflow = StateGraph(
        BuildingAgentState
    )


    workflow.add_node(
        "request_preflight",
        node_preflight
    )

    workflow.add_node(
        "policy_response",
        node_policy_response
    )

    workflow.add_node(
        "generate_sql",
        node_generate_sql
    )

    workflow.add_node(
        "validate_sql",
        node_validate_sql
    )

    workflow.add_node(
        "repair_sql",
        node_repair_sql
    )

    workflow.add_node(
        "execute_sql",
        node_execute_sql
    )

    workflow.add_node(
        "synthesize_answer",
        node_synthesize_answer
    )

    workflow.add_node(
        "blocked_answer",
        node_blocked_answer
    )

    workflow.add_node(
        "database_error",
        node_database_error
    )


    workflow.set_entry_point(
        "request_preflight"
    )


    workflow.add_conditional_edges(

        "request_preflight",

        route_after_preflight,

        {

            "generate_sql":
                "generate_sql",

            "policy_response":
                "policy_response"
        }
    )


    workflow.add_edge(
        "policy_response",
        END
    )


    workflow.add_edge(
        "generate_sql",
        "validate_sql"
    )


    workflow.add_conditional_edges(

        "validate_sql",

        route_after_validation,

        {

            "execute_sql":
                "execute_sql",

            "repair_sql":
                "repair_sql",

            "blocked_answer":
                "blocked_answer"
        }
    )


    workflow.add_edge(
        "repair_sql",
        "validate_sql"
    )


    workflow.add_conditional_edges(

        "execute_sql",

        route_after_execution,

        {

            "synthesize_answer":
                "synthesize_answer",

            "repair_sql":
                "repair_sql",

            "database_error":
                "database_error"
        }
    )


    workflow.add_edge(
        "synthesize_answer",
        END
    )


    workflow.add_edge(
        "blocked_answer",
        END
    )


    workflow.add_edge(
        "database_error",
        END
    )


    return workflow.compile()


building_agent = build_agent()
