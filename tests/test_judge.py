import io
from pathlib import Path
from unittest.mock import Mock
import warnings
import zipfile

import docker
import pytest
from sqlalchemy import text

import constants
import crud
import main


PAYLOAD = {"code": "int main(void) { return 0; }", "input": "ação\n", "lang": "C"}


def results(engine):
    with engine.connect() as conn:
        return conn.execute(text("SELECT * FROM submissions_result")).mappings().all()


def submit(environment, monkeypatch):
    api, client, instance, engine = environment
    # O lifespan usa um cliente falso próprio; cada teste seleciona o seu executor.
    monkeypatch.setattr(main, "client", client)
    return api.post("/submit", json=PAYLOAD)


def test_success_persists_utf8_and_releases_resources(environment, monkeypatch):
    api, client, instance, engine = environment
    response = submit(environment, monkeypatch)
    assert response.status_code == 200
    assert response.json() == {"output": "olá\n", "errout": "", "flag": False, "time": "0.01"}
    assert results(engine)[0]["exit_code"] == 0
    instance.remove.assert_called_once_with(force=True)
    kwargs = client.containers.run.call_args.kwargs
    source, stdin = kwargs["volumes"]
    assert not Path(source).parent.exists()
    assert not Path(stdin).exists()
    assert kwargs["network_disabled"] is True
    assert kwargs["read_only"] is True
    assert kwargs["user"] == "1000:1000"
    assert kwargs["cap_drop"] == ["ALL"]
    saved = Path(constants.submissionDir) / "1"
    assert (saved / "in.txt").read_bytes() == "ação\n".encode()
    assert (saved / "out.txt").read_bytes() == "olá\n".encode()
    assert api.get("/submission/1").status_code == 200
    assert "olá" in api.get("/submission/1").text
    assert "/submission/1" in api.get("/submissions").text


def test_compilation_error_preserves_exit_code(environment, monkeypatch):
    _, _, instance, engine = environment
    instance.exec_run.side_effect = [(1, b"compiler error")]
    response = submit(environment, monkeypatch)
    assert response.json()["errout"] == "Compilation Error"
    assert results(engine)[0]["exit_code"] == 1
    instance.remove.assert_called_once_with(force=True)
    assert instance.exec_run.call_count == 1
    source = next(iter(environment[1].containers.run.call_args.kwargs["volumes"]))
    assert not Path(source).parent.exists()


@pytest.mark.parametrize("exit_code,elapsed,expected", [
    (124, b"10.00", "Time Limit Exceeded"),
    (137, b"11.00", "Time Limit Exceeded"),
    (137, b"0.02", "Runtime Error"),
    (139, b"0.01", "Runtime Error"),
    (143, b"0.01", "Runtime Error"),
])
def test_runtime_verdicts(environment, monkeypatch, exit_code, elapsed, expected):
    instance, engine = environment[2:]
    instance.exec_run.side_effect = [(0, b""), (exit_code, (b"", elapsed))]
    response = submit(environment, monkeypatch)
    assert response.json()["flag"] is True
    assert response.json()["errout"] == expected
    assert results(engine)[0]["exit_code"] == exit_code


def test_empty_output_and_missing_time_do_not_crash(environment, monkeypatch):
    environment[2].exec_run.side_effect = [(0, b""), (0, (None, None))]
    response = submit(environment, monkeypatch)
    assert response.status_code == 200
    assert response.json()["output"] == ""


def test_non_utf8_output_does_not_turn_success_into_error(environment, monkeypatch):
    environment[2].exec_run.side_effect = [(0, b""), (0, (b"\xff", b"0.01"))]
    response = submit(environment, monkeypatch)
    assert response.json()["flag"] is False
    assert response.json()["output"] == "\ufffd"


@pytest.mark.parametrize("stage", ["create", "execute"])
def test_docker_failure_is_recorded_and_temp_files_are_cleaned(environment, monkeypatch, stage):
    _, client, instance, engine = environment
    failure = docker.errors.DockerException("unavailable")
    if stage == "create":
        client.containers.run.side_effect = failure
    else:
        instance.exec_run.side_effect = failure
    response = submit(environment, monkeypatch)
    assert response.status_code == 503
    assert results(engine)[0]["exit_code"] == -1
    source = next(iter(client.containers.run.call_args.kwargs["volumes"]))
    assert not Path(source).parent.exists()
    if stage == "execute":
        instance.remove.assert_called_once_with(force=True)


def test_cleanup_failure_does_not_drop_result(environment, monkeypatch):
    environment[2].remove.side_effect = docker.errors.DockerException("cleanup failed")
    assert submit(environment, monkeypatch).status_code == 200
    assert len(results(environment[3])) == 1


@pytest.mark.parametrize("payload", [
    {**PAYLOAD, "lang": "Python"}, {**PAYLOAD, "lang": ""},
    {**PAYLOAD, "code": ""}, {"code": PAYLOAD["code"]},
])
def test_invalid_submission_rejected_before_execution(environment, payload):
    api, client, _, _ = environment
    assert api.post("/submit", json=payload).status_code == 422
    assert crud.get_submissions() == []
    client.containers.run.assert_not_called()


def test_missing_submission_returns_404(environment):
    api = environment[0]
    assert api.get("/submission/123").status_code == 404
    submission_id = crud.insert_submission_register("C")
    assert api.get(f"/submission/{submission_id}").status_code == 404


def archive(entries):
    data = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(data, "w") as zipped:
            for name, content in entries:
                zipped.writestr(name, content)
    return data.getvalue()


def register_problem(api, zipped, **fields):
    data = {"title": "Soma", "etext": "Some dois números", "time": "1000", "input": "Dois inteiros", "output": "A soma"}
    data.update(fields)
    return api.post("/problem/new", data=data, files={"file": ("cases.zip", zipped, "application/zip")})


def test_problem_saves_metadata_and_testcase_bytes(environment):
    api, _, _, engine = environment
    response = register_problem(api, archive([("1.in", b"1 2\r\n"), ("1.out", b"3\n")]))
    assert response.status_code == 200
    problem_id = response.json()["id"]
    with engine.connect() as conn:
        problem = conn.execute(text("SELECT * FROM problems")).mappings().one()
    assert problem["textarea"] == "Some dois números"
    assert problem["input"] == "Dois inteiros"
    assert problem["output"] == "A soma"
    path = Path(constants.problemsDir) / str(problem_id)
    assert (path / "1.in").read_bytes() == b"1 2\r\n"
    assert (path / "1.out").read_bytes() == b"3\n"


@pytest.mark.parametrize("names", [
    [], ["1.in"], ["1.in", "2.out"], ["2.in", "2.out"],
    ["1.in", "1.out", "1.in"], ["../1.in", "../1.out"],
    ["folder/1.in", "folder/1.out"], ["1.foo.in", "1.foo.out"],
    ["01.in", "01.out"], ["1.in", "1.out", "2.txt"],
])
def test_invalid_zip_rejected_without_database_write(environment, names):
    api, _, _, engine = environment
    assert register_problem(api, archive([(name, b"") for name in names])).status_code == 400
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM problems")).scalar_one() == 0


def test_non_zip_and_invalid_problem_fields(environment):
    api = environment[0]
    assert register_problem(api, b"not a zip").status_code == 400
    valid = archive([("1.in", b""), ("1.out", b"")])
    assert register_problem(api, valid, time="0").status_code == 422
    assert register_problem(api, valid, title="   ").status_code == 422


def test_corrupt_case_is_rejected_before_database_write(environment):
    api, _, _, engine = environment
    zipped = bytearray(archive([("1.in", b"abc"), ("1.out", b"def")]))
    zipped[30 + len("1.in")] ^= 1
    assert register_problem(api, bytes(zipped)).status_code == 400
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM problems")).scalar_one() == 0


def test_unexpected_time_text_is_not_stored_as_elapsed_time(environment, monkeypatch):
    environment[2].exec_run.side_effect = [(0, b""), (139, (None, b"unexpected diagnostic\n"))]
    response = submit(environment, monkeypatch)
    assert response.json()["errout"] == "Runtime Error"
    assert response.json()["time"] == ""


def test_archive_size_and_count_limits():
    fake_archive = Mock()
    fake_archive.infolist.return_value = [zipfile.ZipInfo("1.in") for _ in range(2001)]
    with pytest.raises(main.HTTPException) as error:
        main.validate_testcases(fake_archive)
    assert error.value.status_code == 400
    entry = zipfile.ZipInfo("1.in")
    entry.file_size = 51 * 1024 * 1024
    fake_archive.infolist.return_value = [entry]
    with pytest.raises(main.HTTPException):
        main.validate_testcases(fake_archive)


def test_static_pages_use_same_origin(environment):
    api = environment[0]
    assert api.get("/").status_code == 200
    assert "127.0.0.1:8000" not in api.get("/script.js").text
    assert "127.0.0.1:8000" not in api.get("/problem/new/").text
