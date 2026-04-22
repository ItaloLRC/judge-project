from fastapi import FastAPI, Query, Path, Body, Header
from enum import Enum
from pydantic import BaseModel
from typing import Annotated
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import tempfile
import docker

## crud basico

## get - read data
## delete - delete data
## post - create data
## put = update data

app = FastAPI()

BASE = os.path.dirname(__file__) # Pega o endereço do arquivo atual

class OutCodeAreaText(BaseModel):
    output: str = None
    errout: str = None
    flag: bool = False

class InCodeAreaText(BaseModel):
    code: str = None
    lang: str = None

CompileCMD = {
    "C++":["sh", "-c", "g++ /codigo/newfile.cpp -o /tmp/newfile && /tmp/newfile"],
    "C":["sh", "-c", "gcc /codigo/newfile.c -o /tmp/newfile && /tmp/newfile"]
}

ContainerVolume = {
    "C++":"/codigo/newfile.cpp",
    "C":"/codigo/newfile.c"
}

ContainerImage = {
    "C++":"judge/cpp:latest",
    "C":"judge/c:latest"
}

client = docker.from_env()

## UM ARQUIVO PARA CONTROLAR ARQUIVOS/CRIAÇAO
## OUTRO PARA CRIAR O DOCKER
## UM ORQUESTRADOR


@app.post("/submit")
async def Submit(InCurrentCode: InCodeAreaText):

    print(InCurrentCode.lang)

    OutCurrentCode = OutCodeAreaText()
    # Bitmask para capturar erros, talvez...

    with tempfile.TemporaryDirectory() as codetmpdir: # Cria diretório temporário para o arquivo do código fonte

        filepath = os.path.join(codetmpdir, "teste.c") # Endereço para o arquivo do código fonte

        with open(filepath, "w+") as f: #Criação do arquivo e a abertura dele
            f.write(InCurrentCode.code) #Escrever código enviado no arquivo criado

        print(123)

        #Container
        instancia = client.containers.run(
            image=ContainerImage[InCurrentCode.lang],
            command=CompileCMD[InCurrentCode.lang],
            volumes={
                    filepath: {'bind': ContainerVolume[InCurrentCode.lang], 'mode': 'ro'}
                    },
            network_disabled=True,
            mem_limit="128m",
            stdout=True,
            stderr=True,
            detach=True,
            cpu_period=100000,
            cpu_quota=50000,
            pids_limit=50
        )

        # Ideia:
        # Usar bitwise para capturar e definir erros ao invés de um booleano (flag: bool)

        try:
            result = instancia.wait(timeout=10) #Espera-se N segundos, se exceder o tempo é dado uma exception e a instância é parada
            stdout = instancia.logs(stdout=True, stderr=False).decode("utf-8") #Captura o output
            stderr = instancia.logs(stdout=False, stderr=True).decode("utf-8")

            if(result["StatusCode"] == 0): # Sem erros
                print(stdout)
                OutCurrentCode.output = stdout
            else: # Erro de compilação
                print("Erro de compilaçao")
                print(stderr)
                OutCurrentCode.flag = True;
                OutCurrentCode.errout = stderr
        except Exception:
            instancia.kill()
            print("Tempo Limite Excedido")
            OutCurrentCode.flag = True;
            OutCurrentCode.errout = "Tempo Limite Excedido"
        finally:
            instancia.remove() #Por fim a instância é removida, afinal marcamos "remove=false"(padrão), e "detach=true"


    #Retorna o objeto de OutCodeAreaText
    print(OutCurrentCode)
    return OutCurrentCode

app.mount("/", StaticFiles(directory=os.path.join(BASE, "Frontend"), html=True), name="static")#