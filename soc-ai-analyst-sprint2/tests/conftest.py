from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.core.ids import generate_case_id
from app.main import create_app


@pytest.fixture
def application(tmp_path):
    return create_app(database_path=tmp_path / "cases.sqlite3")


@pytest.fixture
def id_factory(application):
    factory = Mock(wraps=generate_case_id)
    application.state.case_service.id_factory = factory
    return factory


@pytest.fixture
def client(application, id_factory):
    with TestClient(application) as test_client:
        yield test_client
