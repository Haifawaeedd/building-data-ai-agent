import re

import sqlparse
import sqlglot
from sqlglot import exp

from app.schema import (
    ALLOWED_TABLES,
    discovered_columns
)


BLOCKED_KEYWORDS = {

    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
    "COPY",
    "CALL",
    "DO"
}


def validate_readonly_sql(
    sql
):
    """
    First-line lexical / statement validator.
    """

    if not sql or not sql.strip():

        return (
            False,
            "EMPTY_SQL"
        )


    cleaned = sqlparse.format(
        sql,
        strip_comments=True
    ).strip()


    statements = [

        statement.strip()

        for statement
        in sqlparse.split(
            cleaned
        )

        if statement.strip()
    ]


    if len(statements) != 1:

        return (
            False,
            "MULTIPLE_STATEMENTS_NOT_ALLOWED"
        )


    statement = statements[0]


    if not re.match(
        r"^\s*(SELECT|WITH)\b",
        statement,
        flags=re.IGNORECASE
    ):

        return (
            False,
            "ONLY_SELECT_OR_WITH_ALLOWED"
        )


    upper_sql = (
        statement.upper()
    )


    for keyword in BLOCKED_KEYWORDS:

        if re.search(
            rf"\b{keyword}\b",
            upper_sql
        ):

            return (
                False,
                f"BLOCKED_KEYWORD_{keyword}"
            )


    return (
        True,
        "VALID"
    )


def validate_sql_ast(
    sql
):
    """
    CTE-aware structural SQL validation.

    Enforces:

    - one statement
    - SELECT-containing query
    - no write/admin AST nodes
    - physical-table allowlist
    - system-schema protection
    - physical column validation
    """

    if not sql or not sql.strip():

        return (
            False,
            "EMPTY_SQL"
        )


    try:

        parsed = sqlglot.parse(
            sql,
            read="postgres"
        )

    except Exception as error:

        return (
            False,
            f"PARSE_ERROR: {error}"
        )


    if len(parsed) != 1:

        return (
            False,
            "MULTIPLE_STATEMENTS_NOT_ALLOWED"
        )


    tree = parsed[0]


    blocked_types = (

        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.Create,
        exp.Alter,
        exp.Merge,
        exp.Command
    )


    for blocked_type in blocked_types:

        if tree.find(
            blocked_type
        ) is not None:

            return (
                False,
                (
                    "BLOCKED_AST_NODE_"
                    + blocked_type.__name__.upper()
                )
            )


    if tree.find(
        exp.Select
    ) is None:

        return (
            False,
            "ONLY_READ_QUERIES_ALLOWED"
        )


    cte_names = set()


    for cte in tree.find_all(
        exp.CTE
    ):

        alias = cte.alias

        if alias:

            cte_names.add(
                alias
            )


    physical_tables = set()


    for table in tree.find_all(
        exp.Table
    ):

        table_name = (
            table.name
        )


        if table_name in cte_names:

            continue


        schema_expression = (
            table.args.get(
                "db"
            )
        )


        if schema_expression:

            schema_name = (
                schema_expression.name

                if hasattr(
                    schema_expression,
                    "name"
                )

                else str(
                    schema_expression
                )
            )


            if (
                schema_name.lower()
                != "public"
            ):

                return (
                    False,
                    (
                        "SYSTEM_OR_"
                        "UNAPPROVED_SCHEMA"
                    )
                )


        if table_name:

            physical_tables.add(
                table_name
            )


    unknown_tables = (
        physical_tables
        - ALLOWED_TABLES
    )


    if unknown_tables:

        return (
            False,
            (
                "UNKNOWN_TABLES: "
                + ", ".join(
                    sorted(
                        unknown_tables
                    )
                )
            )
        )


    physical_table_aliases = set(
        ALLOWED_TABLES
    )


    for table in tree.find_all(
        exp.Table
    ):

        if (
            table.name
            in ALLOWED_TABLES
        ):

            alias = table.alias

            if alias:

                physical_table_aliases.add(
                    alias
                )


    defined_aliases = {

        alias.alias

        for alias
        in tree.find_all(
            exp.Alias
        )

        if alias.alias
    }


    for column in tree.find_all(
        exp.Column
    ):

        name = column.name

        qualifier = column.table


        if (
            qualifier
            and
            qualifier
            in physical_table_aliases
        ):

            if (
                name
                not in discovered_columns
            ):

                return (
                    False,
                    (
                        "UNKNOWN_COLUMNS: "
                        + name
                    )
                )


        elif not qualifier:

            if (
                name
                not in discovered_columns
                and
                name
                not in defined_aliases
            ):

                return (
                    False,
                    (
                        "UNKNOWN_COLUMNS: "
                        + name
                    )
                )


    return (
        True,
        "AST_VALID"
    )


def validate_sql_professional(
    sql
):
    """
    Defense-in-depth SQL validator.
    """

    basic_valid, basic_reason = (
        validate_readonly_sql(
            sql
        )
    )


    if not basic_valid:

        return (
            False,
            (
                "BASIC_GUARDRAIL: "
                + basic_reason
            )
        )


    ast_valid, ast_reason = (
        validate_sql_ast(
            sql
        )
    )


    if not ast_valid:

        return (
            False,
            (
                "AST_GUARDRAIL: "
                + ast_reason
            )
        )


    return (
        True,
        "PROFESSIONAL_VALID"
    )
