"""Integration tests — evaluation API."""

from unittest.mock import patch


def test_evaluation_run_dev_mode(auth_client):
    with patch("app.api.evaluation_routes.run_evaluation") as mock_run:
        mock_run.return_value = {
            "summary": {"cases_evaluated": 2},
            "rag_results": [],
            "orchestration_results": [],
            "report_paths": {"json": "/tmp/report.json", "csv": "/tmp/report.csv"},
        }
        response = auth_client.post(
            "/evaluation/run",
            headers=auth_client.auth_headers,
            json={"run_rag": True, "run_orchestration": False, "engine_preference": "heuristic"},
        )

    assert response.status_code == 200
    assert response.json()["summary"]["cases_evaluated"] == 2
    mock_run.assert_called_once()


def test_evaluation_run_requires_auth(client):
    response = client.post("/evaluation/run", json={"run_rag": True})
    assert response.status_code == 401
