import json
import re

from openai import OpenAI

from app.config import (
    settings,
    require_openai_key
)

from app.schema import (
    SEMANTIC_LIVE_SCHEMA,
    LOADED_FISCAL_YEARS
)


DESTRUCTIVE_INTENT_PATTERNS = [

    r"\bdelete\b",

    (
        r"\bremove\b.*"
        r"\b(record|row|facility|data)"
    ),

    r"\bdrop\b",

    r"\bupdate\b",

    r"\bchange\b.*\b(to|value|status)",

    r"\bmodify\b",

    r"\binsert\b",

    r"\btruncate\b",

    r"\balter\b",

    (
        r"\bcreate\b.*"
        r"\b(table|role|database)"
    )
]


UNSUPPORTED_CONCEPT_PATTERNS = {

    "occupancy":
        (
            r"\boccupan(?:cy|t|ts)\b"
            r"|\boccupancy[_ ]?rate\b"
        ),

    "water_consumption":
        (
            r"\bwater\s+"
            r"(?:use|usage|consumption)\b"
        ),

    "construction_year":
        (
            r"\byear\s+built\b"
            r"|\bconstruction\s+year\b"
            r"|\boldest\s+building\b"
            r"|\bbuilding\s+age\b"
        ),

    "retrofit":
        r"\bretrofit\s+(?:status|cost)\b",

    "energy_star":
        r"\benergy\s*star\b"
}


AMBIGUOUS_CONCEPT_PATTERNS = {

    "energy_efficiency":
        (
            r"\b(?:most|least)?\s*"
            r"energy\s+efficient\b"
        ),

    "overall_performance":
        (
            r"\bbest\s+"
            r"(?:overall\s+)?performance\b"
        ),

    "sustainability":
        r"\bmost\s+sustainable\b"
}


SUPPORTED_CONCEPT_PATTERNS = {

    "electricity_clean_kwh":
        (
            r"\bclean\s+electricity\b"
            r"|\bclean\s+electricity\s+generation\b"
            r"|\belectricity\s+from\s+clean\s+generation\b"
            r"|\bclean\s+generation\s+sources?\b"
        )
}


DOMAIN_SEMANTIC_CONTRACTS = """
DOMAIN INTERPRETATION CONTRACTS

1. "records that report <metric>" means:
   corresponding_field IS NOT NULL.

2. "facilities that report <metric>" means:
   corresponding_field IS NOT NULL.

3. "positive <metric>", "greater than zero",
   or explicit positive wording means:
   corresponding_field > 0.

4. Zero is a reported value and is not automatically
   missing.

5. If the database contains only one fiscal year,
   do not ask the user to specify a fiscal year unless
   another time period is explicitly requested.

6. "most energy efficient", "best performing",
   and "most sustainable" require clarification unless
   a metric is specified.

7. Unsupported concepts must not be silently replaced
   with another database field.

8. READ_QUERY must not contain a clarification request.
"""


def detect_destructive_intent(
    question
):

    normalized = (
        question.lower()
    )


    return any(

        re.search(
            pattern,
            normalized
        )

        for pattern
        in DESTRUCTIVE_INTENT_PATTERNS
    )


def deterministic_semantic_policy(
    question
):

    q = (
        question
        .lower()
        .strip()
    )


    if detect_destructive_intent(
        question
    ):

        return {

            "request_type":
                "WRITE_REQUEST",

            "reason":
                (
                    "Deterministic policy detected "
                    "a database-state modification "
                    "request."
                ),

            "clarification":
                "",

            "decision_source":
                "DETERMINISTIC_POLICY"
        }


    for (
        concept,
        pattern
    ) in UNSUPPORTED_CONCEPT_PATTERNS.items():

        if re.search(
            pattern,
            q,
            flags=re.IGNORECASE
        ):

            return {

                "request_type":
                    "SCHEMA_MISMATCH",

                "reason":
                    (
                        "The requested concept "
                        f"'{concept}' is not represented "
                        "in the current database schema."
                    ),

                "clarification":
                    (
                        "The requested information "
                        "is not available in the "
                        "current dataset."
                    ),

                "decision_source":
                    "DETERMINISTIC_POLICY"
            }


    for (
        concept,
        pattern
    ) in AMBIGUOUS_CONCEPT_PATTERNS.items():

        if re.search(
            pattern,
            q,
            flags=re.IGNORECASE
        ):

            clarification = (
                "Please specify the metric "
                "you want to use."
            )


            if (
                concept
                == "energy_efficiency"
            ):

                clarification = (
                    "Which metric should define "
                    "energy efficiency: electricity "
                    "use per m², emissions per m², "
                    "or another explicitly defined "
                    "measure?"
                )


            return {

                "request_type":
                    "AMBIGUOUS",

                "reason":
                    (
                        f"The concept '{concept}' "
                        "does not have one unique "
                        "database definition."
                    ),

                "clarification":
                    clarification,

                "decision_source":
                    "DETERMINISTIC_POLICY"
            }


    clean_pattern = (
        SUPPORTED_CONCEPT_PATTERNS[
            "electricity_clean_kwh"
        ]
    )


    if re.search(
        clean_pattern,
        q,
        flags=re.IGNORECASE
    ):

        return {

            "request_type":
                "READ_QUERY",

            "reason":
                (
                    "The request maps to the "
                    "source-grounded "
                    "electricity_clean_kwh field: "
                    "electricity from clean "
                    "generation sources."
                ),

            "clarification":
                "",

            "decision_source":
                "DETERMINISTIC_POLICY"
        }


    return None


def _client():

    require_openai_key()

    return OpenAI(
        api_key=
            settings.openai_api_key
    )


def classify_request(
    question
):
    """
    Hybrid semantic routing:

    1. deterministic policy
    2. source-grounded LLM fallback
    """

    deterministic = (
        deterministic_semantic_policy(
            question
        )
    )


    if deterministic is not None:

        return deterministic


    fiscal_year_context = (
        ", ".join(
            LOADED_FISCAL_YEARS
        )

        if LOADED_FISCAL_YEARS

        else "none detected"
    )


    instructions = f"""
You are the semantic preflight component of a safe
Text-to-SQL system.

Do NOT generate SQL.

LIVE DATABASE SCHEMA:

{SEMANTIC_LIVE_SCHEMA}

DOMAIN CONTRACTS:

{DOMAIN_SEMANTIC_CONTRACTS}

Fiscal years currently present:

{fiscal_year_context}

Classify the request as exactly one of:

READ_QUERY
WRITE_REQUEST
SCHEMA_MISMATCH
AMBIGUOUS

Rules:

1. Use only the live schema and source semantics.
2. Do not invent columns.
3. Do not substitute unrelated concepts.
4. Supported natural-language synonyms do not need
   to exactly match database column names.
5. If clarification is genuinely required,
   classify AMBIGUOUS.
6. READ_QUERY must have clarification="".
7. If only one fiscal year exists, do not ask
   which fiscal year the user means unless another
   time period is explicitly requested.

Return JSON only:

{{
  "request_type": "...",
  "reason": "...",
  "clarification": ""
}}
"""


    response = _client().responses.create(

        model=
            settings.openai_model,

        instructions=
            instructions,

        input=
            question
    )


    raw = (
        response.output_text
        .strip()
    )


    raw = re.sub(
        r"^```json\s*",
        "",
        raw,
        flags=re.IGNORECASE
    )


    raw = re.sub(
        r"\s*```$",
        "",
        raw
    )


    try:

        result = json.loads(
            raw
        )

    except Exception:

        return {

            "request_type":
                "AMBIGUOUS",

            "reason":
                (
                    "Semantic fallback did not "
                    "return reliable structured "
                    "output."
                ),

            "clarification":
                (
                    "Please clarify the "
                    "analytical request."
                ),

            "decision_source":
                "FAIL_SAFE"
        }


    allowed = {

        "READ_QUERY",

        "WRITE_REQUEST",

        "SCHEMA_MISMATCH",

        "AMBIGUOUS"
    }


    if (
        result.get(
            "request_type"
        )
        not in allowed
    ):

        return {

            "request_type":
                "AMBIGUOUS",

            "reason":
                (
                    "Invalid semantic "
                    "preflight state."
                ),

            "clarification":
                (
                    "Please clarify the "
                    "analytical request."
                ),

            "decision_source":
                "FAIL_SAFE"
        }


    if (
        result[
            "request_type"
        ]
        == "READ_QUERY"
    ):

        result[
            "clarification"
        ] = ""


    result[
        "decision_source"
    ] = "LLM_FALLBACK"


    return result
