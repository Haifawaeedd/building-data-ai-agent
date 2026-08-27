from app.guardrails import (
    validate_sql_professional
)


def test_safe_select():

    sql = """
    SELECT
        facility,
        electricity_total_kwh

    FROM federal_facilities_energy

    WHERE province = 'NS'

    LIMIT 5;
    """


    valid, reason = (
        validate_sql_professional(
            sql
        )
    )


    assert valid is True

    assert reason == (
        "PROFESSIONAL_VALID"
    )


def test_unknown_column_blocked():

    sql = """
    SELECT occupancy_rate
    FROM federal_facilities_energy;
    """


    valid, reason = (
        validate_sql_professional(
            sql
        )
    )


    assert valid is False

    assert (
        "UNKNOWN_COLUMNS"
        in reason
    )


def test_unknown_table_blocked():

    valid, reason = (
        validate_sql_professional(
            "SELECT * FROM users;"
        )
    )


    assert valid is False

    assert (
        "UNKNOWN_TABLES"
        in reason
    )


def test_write_statement_blocked():

    valid, _ = (
        validate_sql_professional(
            """
            DELETE FROM
            federal_facilities_energy;
            """
        )
    )


    assert valid is False
