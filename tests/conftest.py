from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

import constants
import crud
import main


@pytest.fixture
def environment(monkeypatch, tmp_path, startup_services):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with engine.begin() as conn:
        for statement in (
            "CREATE TABLE submissions (id INTEGER PRIMARY KEY, language TEXT, date TEXT DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE submissions_result (id INTEGER PRIMARY KEY, submission_id INT, time TEXT, flag BOOL, exit_code INT, errout TEXT)",
            "CREATE TABLE problems (id INTEGER PRIMARY KEY, time INT, title TEXT, textarea TEXT, input TEXT, output TEXT)",
        ):
            conn.execute(text(statement))
    monkeypatch.setattr(crud, "engine", engine)
    monkeypatch.setattr(constants, "submissionDir", str(tmp_path / "submissions"))
    monkeypatch.setattr(constants, "problemsDir", str(tmp_path / "problems"))

    instance = Mock()
    instance.exec_run.side_effect = [(0, b""), (0, (b"ol\xc3\xa1\n", b"0.01\n"))]
    docker_client = Mock()
    docker_client.containers.run.return_value = instance
    monkeypatch.setattr(main, "client", docker_client)
    with TestClient(main.app) as api:
        yield api, docker_client, instance, engine
    engine.dispose()


@pytest.fixture
def startup_services(monkeypatch):
    monkeypatch.setattr(main.docker, "from_env", Mock(return_value=Mock()))
    monkeypatch.setattr(main.models, "create_table", Mock())
