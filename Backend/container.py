import docker
import constants


def container_run(client, lang: str, filepath: str, inputpath: str):

    instancia = client.containers.run(
        image=constants.ContainerImage[lang],
        command="sleep infinity", ## constants.CompileCMD[lang]
        volumes={
                filepath: {'bind': constants.ContainerVolume[lang], 'mode': 'ro'},
                inputpath: {'bind': "/codigo/input.txt", 'mode':'ro'}
                },
        network_disabled=True,
        mem_limit="256m",
        stdout=True,
        stderr=True,
        detach=True,
        cpu_period=100000,
        cpu_quota=50000,
        pids_limit=50
    )

    return instancia

def container_result(instancia):
    return instancia.wait(timeout=10)

def container_out(instancia):
    return instancia.logs(stdout=True, stderr=True).decode("utf-8")
