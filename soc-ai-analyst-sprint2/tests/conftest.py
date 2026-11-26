import os
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.core.ids import generate_case_id
from app.main import create_app

TESTS_ROOT = Path(__file__).resolve().parent
TEST_TYPES = {"unit", "integration", "security", "regression"}


def pytest_collection_modifyitems(items):
    """Derive each backend category from its folder before pytest applies -m."""
    for item in items:
        if not item.path.is_relative_to(TESTS_ROOT):
            continue
        group = item.path.relative_to(TESTS_ROOT).parts[0]
        if group in TEST_TYPES:
            item.add_marker(group)


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


os.environ["SOC_AUTO_INVESTIGATE"] = "false"
