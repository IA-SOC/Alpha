import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.core.config import Settings

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("limit", [2, 51])
def test_configured_limit_matches_validation_and_openapi(limit, tmp_path):
    # Configuration is read once at startup; test it in a fresh interpreter.
    env = dict(
        os.environ,
        MAX_ALERTS_PER_CASE=str(limit),
        CASE_DATABASE_PATH=str(tmp_path / "cases.sqlite3"),
    )
    code = """
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import settings
from tests.helpers import make_case
with TestClient(create_app()) as c:
    n = settings.max_alerts_per_case
    assert c.post('/api/v1/cases', json=make_case(count=n)).status_code == 201
    over_limit = make_case(count=n+1, case_id='other')
    assert c.post('/api/v1/cases', json=over_limit).status_code == 422
    schema = c.get('/openapi.json').json()
    properties = schema['components']['schemas']['IncidentCase']['properties']
    assert properties['alerts']['maxItems'] == n
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("pointer", ["", "event.id", "/bad~escape", "/bad~"])
def test_bad_identifier_configuration_fails_early(pointer):
    with pytest.raises(ValueError, match="JSON Pointer"):
        Settings(elastic_alert_id_pointer=pointer)


def test_non_positive_limit_fails_early():
    with pytest.raises(ValueError, match="positive"):
        Settings(max_alerts_per_case=0)
