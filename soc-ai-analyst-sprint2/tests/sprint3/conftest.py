from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.sprint3.cases import load_case


@pytest.fixture(scope="session")
def sprint3_result(tmp_path_factory):
    path = tmp_path_factory.mktemp("sprint3-assigned") / "cases.sqlite3"
    cache = {}
    with TestClient(create_app(database_path=path)) as client:

        def run(name):
            if name not in cache:
                payload = load_case(name)
                response = client.post("/api/v1/cases", json=payload)
                assert response.status_code == 201, response.text
                case_id = response.json()["case_id"]
                response = client.post(f"/api/v1/cases/{case_id}/investigate")
                assert response.status_code == 200, response.text
                cache[name] = response.json()

            return deepcopy(cache[name])

        yield run
