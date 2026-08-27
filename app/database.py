from collections import defaultdict

import psycopg

from app.config import (
    settings,
    require_database_url
)


def inspect_postgresql_schema(
    allowed_tables=None
):
    """
    Read live PostgreSQL table/column metadata.

    The production agent does not depend on a manually
    duplicated physical schema.
    """

    require_database_url()

    schema = defaultdict(list)


    with psycopg.connect(
        settings.database_url
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    table_name,
                    column_name,
                    data_type,
                    is_nullable,
                    ordinal_position

                FROM information_schema.columns

                WHERE table_schema = 'public'

                ORDER BY
                    table_name,
                    ordinal_position;
                """
            )


            rows = cursor.fetchall()


    for (
        table_name,
        column_name,
        data_type,
        is_nullable,
        ordinal_position
    ) in rows:

        if (
            allowed_tables
            and
            table_name not in allowed_tables
        ):

            continue


        schema[
            table_name
        ].append(

            {
                "column_name":
                    column_name,

                "data_type":
                    data_type,

                "nullable":
                    is_nullable == "YES",

                "ordinal_position":
                    ordinal_position
            }

        )


    return dict(schema)


def schema_to_prompt(
    schema
):

    sections = []


    for (
        table_name,
        columns
    ) in schema.items():

        sections.append(
            f"Table: {table_name}"
        )

        sections.append(
            "Columns:"
        )


        for column in columns:

            nullable = (
                "NULL allowed"
                if column["nullable"]
                else "NOT NULL"
            )


            sections.append(
                f"- {column['column_name']} "
                f"({column['data_type']}, "
                f"{nullable})"
            )


        sections.append(
            ""
        )


    return "\n".join(
        sections
    ).strip()


def get_loaded_fiscal_years(
    table_name
):

    require_database_url()


    with psycopg.connect(
        settings.database_url
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                f"""
                SELECT DISTINCT fiscal_year

                FROM {table_name}

                WHERE fiscal_year
                      IS NOT NULL

                ORDER BY fiscal_year;
                """
            )


            return [

                row[0]

                for row
                in cursor.fetchall()
            ]


def get_table_row_count(
    table_name
):

    require_database_url()


    with psycopg.connect(
        settings.database_url
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM {table_name};
                """
            )


            return cursor.fetchone()[0]


def execute_readonly_sql(
    sql
):
    """
    Execute already validated SQL.

    Independent DB-level safeguards:

    - readonly_agent credentials should be used
    - READ ONLY transaction
    - statement timeout
    - bounded result retrieval
    """

    require_database_url()


    with psycopg.connect(
        settings.database_url
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                "SET TRANSACTION READ ONLY;"
            )


            cursor.execute(
                f"""
                SET LOCAL statement_timeout =
                '{settings.statement_timeout_ms}ms';
                """
            )


            cursor.execute(
                sql
            )


            columns = [

                description.name

                for description
                in cursor.description
            ]


            raw_rows = cursor.fetchmany(
                settings.max_result_rows
                + 1
            )


    truncated = (
        len(raw_rows)
        >
        settings.max_result_rows
    )


    raw_rows = raw_rows[
        :settings.max_result_rows
    ]


    rows = [

        dict(
            zip(
                columns,
                row
            )
        )

        for row
        in raw_rows
    ]


    return {

        "rows":
            rows,

        "row_count":
            len(rows),

        "truncated":
            truncated,

        "max_rows":
            settings.max_result_rows
    }
