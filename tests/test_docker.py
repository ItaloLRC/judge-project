"""Opt-in: JUDGE_DOCKER_TESTS=1, com as imagens judge/c e judge/cpp construídas."""
import os

import docker
import pytest

import constants
import container
import filesystem


pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(os.environ.get("JUDGE_DOCKER_TESTS") != "1", reason="Requer Docker e JUDGE_DOCKER_TESTS=1"),
]


@pytest.fixture(scope="module")
def docker_client():
    client = docker.from_env()
    try:
        client.ping()
        yield client
    finally:
        client.close()


@pytest.mark.parametrize("lang,code,compile_ok,exit_code,output", [
    ("C", '#include <stdio.h>\nint main(void){int a,b; scanf("%d%d",&a,&b); fprintf(stderr,"debug"); printf("%d\\n",a+b);}', True, 0, b"3\n"),
    ("C++", '#include <iostream>\nint main(){int a,b; std::cin>>a>>b; std::cerr<<"debug"; std::cout<<a+b<<"\\n";}', True, 0, b"3\n"),
    ("C", "invalid C", False, None, None),
    ("C", "int main(void){return 42;}", True, 42, b""),
    ("C", "int main(void){for(;;){}}", True, 124, b""),
    ("C", "#include <signal.h>\nint main(void){signal(SIGTERM,SIG_IGN);for(;;){}}", True, 137, b""),
])
def test_real_compilation_and_execution(docker_client, tmp_path, lang, code, compile_ok, exit_code, output):
    source = tmp_path / constants.langPath[lang]
    stdin = tmp_path / "input.txt"
    filesystem.write_file(str(source), code)
    filesystem.write_file(str(stdin), "1 2\n")
    instance = container.container_run(docker_client, lang, str(source), str(stdin))
    try:
        compiled, _ = instance.exec_run(constants.CompileCMD[lang])
        assert (compiled == 0) is compile_ok
        if compile_ok:
            status, (stdout, elapsed) = instance.exec_run(constants.RunCMD, demux=True)
            assert status == exit_code
            assert (stdout or b"") == output
            assert float(elapsed.strip()) >= 0
    finally:
        instance.remove(force=True)


def test_infinite_output_is_bounded(docker_client, tmp_path):
    source = tmp_path / "main.c"
    stdin = tmp_path / "input.txt"
    source.write_text('#include <stdio.h>\nint main(void){for(;;){puts("output");}}', encoding="utf-8")
    stdin.write_bytes(b"")
    instance = container.container_run(docker_client, "C", str(source), str(stdin))
    try:
        assert instance.exec_run(constants.CompileCMD["C"])[0] == 0
        status, (stdout, elapsed) = instance.exec_run(constants.RunCMD, demux=True)
        assert status != 0
        assert len(stdout or b"") <= 1048576
        assert float(elapsed.strip()) < 10
    finally:
        instance.remove(force=True)
