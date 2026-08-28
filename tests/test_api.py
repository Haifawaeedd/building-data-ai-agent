from fastapi.testclient import TestClient

from app.main import api


client = TestClient(api)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["diagnostics"] == "component-level"


def test_invalid_input():
    response = client.post(
        "/query",
        json={"question": ""},
    )

    assert response.status_code == 422


def test_write_request_no_sql():
    response = client.post(
        "/query",
        json={
            "question": "Delete every facility in Nova Scotia.",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["request_type"] == "WRITE_REQUEST"
    assert payload["execution_status"] == "NOT_EXECUTED"
    assert payload["sql"] is None
    assert payload["outcome_category"] == "SAFE_POLICY_CONTAINMENT"
    assert payload["failure_category"] is None
