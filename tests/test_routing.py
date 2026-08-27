from app.semantic_router import (
    classify_request
)


def test_write_request():

    result = classify_request(
        (
            "Delete every facility "
            "in Nova Scotia."
        )
    )


    assert (
        result["request_type"]
        == "WRITE_REQUEST"
    )


def test_occupancy_schema_mismatch():

    result = classify_request(
        (
            "Which facility has the "
            "highest occupancy rate?"
        )
    )


    assert (
        result["request_type"]
        == "SCHEMA_MISMATCH"
    )


def test_energy_efficiency_ambiguous():

    result = classify_request(
        (
            "Which facility is the "
            "most energy efficient?"
        )
    )


    assert (
        result["request_type"]
        == "AMBIGUOUS"
    )


def test_clean_generation_supported():

    result = classify_request(
        (
            "How many Nova Scotia facility "
            "records report clean electricity "
            "generation?"
        )
    )


    assert (
        result["request_type"]
        == "READ_QUERY"
    )
