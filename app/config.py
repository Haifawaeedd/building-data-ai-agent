import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:

    database_url: str = os.getenv(
        "DATABASE_URL",
        ""
    )

    openai_api_key: str = os.getenv(
        "OPENAI_API_KEY",
        ""
    )

    openai_model: str = os.getenv(
        "OPENAI_MODEL",
        "gpt-5-mini"
    )

    max_sql_retries: int = int(
        os.getenv(
            "MAX_SQL_RETRIES",
            "1"
        )
    )

    statement_timeout_ms: int = int(
        os.getenv(
            "STATEMENT_TIMEOUT_MS",
            "5000"
        )
    )

    max_result_rows: int = int(
        os.getenv(
            "MAX_RESULT_ROWS",
            "200"
        )
    )

    provenance_log_path: str = os.getenv(
        "PROVENANCE_LOG_PATH",
        "logs/agent_provenance_ledger.jsonl"
    )


settings = Settings()


def require_database_url():

    if not settings.database_url:

        raise RuntimeError(
            "DATABASE_URL is not configured."
        )


def require_openai_key():

    if not settings.openai_api_key:

        raise RuntimeError(
            "OPENAI_API_KEY is not configured."
        )
