from contextlib import asynccontextmanager
import logging
import os
import re
import shutil
import zipfile
import zlib

import docker
from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import filesystem
import container
import models
import constants
import crud

logger = logging.getLogger(__name__)
client = None


@asynccontextmanager
async def lifespan(app):
    global client
    client = docker.from_env()
    try:
        models.create_table()
        yield
    finally:
        client.close()


app = FastAPI(lifespan=lifespan)


@app.post("/submit")
def Submit(InCurrentCode: models.InCodeAreaText):
    OutCurrentCode = models.OutCodeAreaText()

    with filesystem.create_dir() as tmpdir:
        filepath = filesystem.create_filepath(tmpdir, constants.langPath[InCurrentCode.lang])
        inputpath = filesystem.create_filepath(tmpdir, "input.txt")
        filesystem.write_file(filepath, InCurrentCode.code)
        filesystem.write_file(inputpath, InCurrentCode.input)
        currentID = crud.insert_submission_register(InCurrentCode.lang)

        instancia = None
        scode = -1
        try:
            instancia = container.container_run(client, InCurrentCode.lang, filepath, inputpath)
            scode, _ = instancia.exec_run(constants.CompileCMD[InCurrentCode.lang])
            if scode != 0:
                OutCurrentCode.flag = True
                OutCurrentCode.errout = "Compilation Error"
            else:
                scode, (stdout, elapsed) = instancia.exec_run(constants.RunCMD, demux=True)
                OutCurrentCode.output = (stdout or b"").decode("utf-8", errors="replace")
                elapsed = (elapsed or b"").decode("utf-8", errors="replace").strip()
                if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", elapsed):
                    OutCurrentCode.time = elapsed

                # SIGKILL também pode indicar falta de memória; só é timeout após o limite.
                timed_out = scode == 124 or (scode == 137 and bool(OutCurrentCode.time) and float(OutCurrentCode.time) >= 10)
                if timed_out:
                    OutCurrentCode.flag = True
                    OutCurrentCode.errout = "Time Limit Exceeded"
                elif scode != 0:
                    OutCurrentCode.flag = True
                    OutCurrentCode.errout = "Runtime Error"
        except docker.errors.DockerException:
            logger.exception("Falha no executor da submissão %s", currentID)
            scode = -1
            OutCurrentCode.flag = True
            OutCurrentCode.errout = "Executor indisponível"
        finally:
            if instancia is not None:
                try:
                    instancia.remove(force=True)
                except docker.errors.DockerException:
                    logger.exception("Falha ao remover o contêiner da submissão %s", currentID)

        subpath = os.path.join(constants.submissionDir, str(currentID))
        os.makedirs(subpath, exist_ok=True)
        filesystem.write_file(os.path.join(subpath, "cf.txt"), InCurrentCode.code)
        filesystem.write_file(os.path.join(subpath, "out.txt"), OutCurrentCode.output)
        filesystem.write_file(os.path.join(subpath, "in.txt"), InCurrentCode.input)
        crud.insert_result_register(currentID, OutCurrentCode.time, OutCurrentCode.flag, scode, OutCurrentCode.errout)

    if OutCurrentCode.errout == "Executor indisponível":
        raise HTTPException(status_code=503, detail=OutCurrentCode.errout)
    return OutCurrentCode


@app.get("/submissions")
def Submissions(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="submissions.html",
        context={"submissions": crud.get_submissions()}
    )


def validate_testcases(archive):
    files = archive.infolist()
    if not files or len(files) > 2000 or sum(f.file_size for f in files) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="ZIP vazio ou acima do limite de 2000 arquivos e 50 MiB descompactados.")

    infiles, outfiles = set(), set()
    for entry in files:
        match = re.fullmatch(r"([1-9][0-9]*)\.(in|out)", entry.filename)
        if match is None or entry.flag_bits & 1:
            raise HTTPException(status_code=400, detail="O ZIP deve conter apenas pares 1.in/1.out, 2.in/2.out, etc., sem pastas ou senha.")
        number, extension = match.groups()
        target = infiles if extension == "in" else outfiles
        if number in target:
            raise HTTPException(status_code=400, detail="O ZIP contém casos de teste duplicados.")
        target.add(number)

    expected = {str(i) for i in range(1, len(infiles) + 1)}
    if infiles != outfiles or infiles != expected:
        raise HTTPException(status_code=400, detail="Os casos devem formar pares .in/.out numerados de 1 até N, sem lacunas.")


@app.post("/problem/new")
def ProblemSubmissions(
    file: UploadFile = File(...), etext: str = Form(...),
    time: int = Form(..., gt=0), title: str = Form(...),
    input: str = Form(...), output: str = Form(...)
):
    if not all(value.strip() for value in (title, etext, input, output)):
        raise HTTPException(status_code=422, detail="Preencha todos os campos do problema.")

    os.makedirs(constants.problemsDir, exist_ok=True)
    with filesystem.create_dir() as tmpdir:
        try:
            with zipfile.ZipFile(file.file, "r") as archive:
                validate_testcases(archive)
                for entry in archive.infolist():
                    with archive.open(entry) as source, open(os.path.join(tmpdir, entry.filename), "wb") as target:
                        # Os nomes e o tamanho descompactado já foram validados.
                        shutil.copyfileobj(source, target)
        except (zipfile.BadZipFile, zlib.error, RuntimeError, NotImplementedError, EOFError) as exc:
            raise HTTPException(status_code=400, detail="Arquivo ZIP inválido ou não suportado.") from exc
        finally:
            file.file.close()

        current_id = crud.insert_problem_register(time, title, etext, input, output)
        shutil.copytree(tmpdir, os.path.join(constants.problemsDir, str(current_id)))

    return {"message": "Ok", "id": current_id}


@app.get("/submission/{id}")
def current_submission(id: int, request: Request):
    record = crud.get_submission_by_id(id)
    if record is None:
        raise HTTPException(status_code=404, detail="Submissão não encontrada.")
    submission = dict(record)
    try:
        for field, filename in (("code", "cf.txt"), ("output", "out.txt"), ("input", "in.txt")):
            submission[field] = filesystem.read_file(os.path.join(constants.submissionDir, str(id), filename))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Arquivos da submissão não encontrados.") from exc

    return templates.TemplateResponse(
        request=request,
        name="currentsubmission.html",
        context={"submission": submission}
    )


templates = Jinja2Templates(directory=os.path.join(constants.BASE, "..", "Frontend", "Templates"))
app.mount("/", StaticFiles(directory=os.path.join(constants.BASE, "..", "Frontend"), html=True), name="static")
