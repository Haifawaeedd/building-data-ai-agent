import json
import logging
import time
import uuid
from datetime import (
    datetime,
    timezone
)

from app.agent import (
    building_agent
)


logger = logging.getLogger(
    "building_data_ai_agent"
)


logger.setLevel(
    logging.INFO
)


if not logger.handlers:

    handler = logging.StreamHandler()


    handler.setFormatter(
        logging.Formatter(
            "%(message)s"
        )
    )


    logger.addHandler(
        handler
    )


def log_event(
    event_type,
    **fields
):

    event = {

        "timestamp":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "event_type":
            event_type,

        **fields
    }


    logger.info(
        json.dumps(
            event,
            default=str
        )
    )


def invoke_agent_observed(
    question
):

    request_id = str(
        uuid.uuid4()
    )


    started = (
        time.perf_counter()
    )


    log_event(

        "agent_request_started",

        request_id=
            request_id,

        question_length=
            len(question)
    )


    try:

        result = (
            building_agent.invoke(

                {
                    "question":
                        question,

                    "trace":
                        []
                }

            )
        )


        latency_ms = round(

            (
                time.perf_counter()
                - started
            )
            * 1000,

            2
        )


        log_event(

            "agent_request_completed",

            request_id=
                request_id,

            request_type=
                result.get(
                    "request_type"
                ),

            execution_status=
                result.get(
                    "execution_status"
                ),

            validation_status=
                result.get(
                    "validation_status"
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

            sql_generated=
                result.get(
                    "sql"
                )
                is not None,

            trace=
                result.get(
                    "trace",
                    []
                ),

            latency_ms=
                latency_ms
        )


        result[
            "request_id"
        ] = request_id


        result[
            "latency_ms"
        ] = latency_ms


        return result


    except Exception as error:

        latency_ms = round(

            (
                time.perf_counter()
                - started
            )
            * 1000,

            2
        )


        log_event(

            "agent_request_failed",

            request_id=
                request_id,

            error_type=
                type(
                    error
                ).__name__,

            latency_ms=
                latency_ms
        )


        raise
