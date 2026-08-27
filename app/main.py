from typing import (
    Optional,
    List
)

from fastapi import (
    FastAPI,
    HTTPException
)

from pydantic import (
    BaseModel,
    Field
)

from app.config import (
    settings
)

from app.observability import (
    invoke_agent_observed
)

from app.provenance import (
    build_provenance_ledger,
    append_provenance_ledger
)

from app.schema import (
    dynamic_schema,
    LOADED_FISCAL_YEARS,
    DATASET_PROVENANCE
)


api = FastAPI(

    title=
        "Building Data AI Agent",

    description=
        (
            "Auditable read-only LangGraph "
            "Text-to-SQL service for Atlantic "
            "Canada federal-facility energy data."
        ),

    version=
        "0.1.0"
)


class AgentQueryRequest(
    BaseModel
):

    question: str = Field(
        ...,
        min_length=3,
        max_length=1000
    )


class AgentQueryResponse(
    BaseModel
):

    question: str

    request_type: str

    answer: str

    execution_status: str

    validation_status: Optional[
        str
    ] = None

    decision_source: Optional[
        str
    ] = None

    sql: Optional[
        str
    ] = None

    retry_count: int = 0

    result_truncated: bool = False

    request_id: Optional[
        str
    ] = None

    latency_ms: Optional[
        float
    ] = None

    trace: List[str]


@api.get(
    "/health"
)
def health():

    return {

        "status":
            "ok",

        "service":
            "building-data-ai-agent",

        "version":
            "0.1.0",

        "database_mode":
            "read-only",

        "agent_framework":
            "LangGraph",

        "max_sql_retries":
            settings.max_sql_retries,

        "statement_timeout_ms":
            settings.statement_timeout_ms,

        "max_result_rows":
            settings.max_result_rows
    }


@api.get(
    "/schema"
)
def schema():

    return {

        "tables":
            list(
                dynamic_schema.keys()
            ),

        "columns": {

            table_name: [

                {

                    "name":
                        column[
                            "column_name"
                        ],

                    "type":
                        column[
                            "data_type"
                        ],

                    "nullable":
                        column[
                            "nullable"
                        ]
                }

                for column
                in columns
            ]

            for (
                table_name,
                columns
            )
            in dynamic_schema.items()
        },

        "fiscal_years":
            LOADED_FISCAL_YEARS,

        "dataset":
            DATASET_PROVENANCE
    }


@api.post(
    "/query",
    response_model=
        AgentQueryResponse
)
def query_agent(
    request: AgentQueryRequest
):

    question = (
        request.question
        .strip()
    )


    try:

        result = (
            invoke_agent_observed(
                question
            )
        )


    except Exception as error:

        raise HTTPException(

            status_code=500,

            detail=
                (
                    "The agent could not "
                    "complete the request."
                )

        ) from error


    return AgentQueryResponse(

        question=
            question,

        request_type=
            result.get(
                "request_type",
                "UNKNOWN"
            ),

        answer=
            result.get(
                "answer",
                ""
            ),

        execution_status=
            result.get(
                "execution_status",
                "NOT_EXECUTED"
            ),

        validation_status=
            result.get(
                "validation_status"
            ),

        decision_source=
            result.get(
                "decision_source"
            ),

        sql=
            result.get(
                "sql"
            ),

        retry_count=
            result.get(
                "retry_count",
                0
            ),

        result_truncated=
            result.get(
                "result_truncated",
                False
            ),

        request_id=
            result.get(
                "request_id"
            ),

        latency_ms=
            result.get(
                "latency_ms"
            ),

        trace=
            result.get(
                "trace",
                []
            )
    )


@api.post(
    "/query/provenance"
)
def query_with_provenance(
    request: AgentQueryRequest
):

    question = (
        request.question
        .strip()
    )


    try:

        ledger = (
            build_provenance_ledger(
                question
            )
        )


        append_provenance_ledger(
            ledger
        )


        return ledger


    except Exception as error:

        raise HTTPException(

            status_code=500,

            detail=
                (
                    "The agent could not "
                    "complete the provenance "
                    "request."
                )

        ) from error
