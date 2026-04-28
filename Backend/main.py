from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import zipfile
import os
import docker
import filesystem
import container
import models
import constants
import crud

app = FastAPI()

client = docker.from_env()
models.create_table()

@app.post("/submit")
async def Submit(InCurrentCode: models.InCodeAreaText):

    OutCurrentCode = models.OutCodeAreaText()

    tmpDirObject = filesystem.create_dir() # Crio o objeto do diretório temporário

    filepath = filesystem.create_filepath(tmpDirObject.name, "newfile.c") # Crio o caminho do arquivo que posteriormente será escrito
    inputpath = filesystem.create_filepath(tmpDirObject.name, "input.txt") # Crio o caminho do arquivo de input

    filesystem.write_file(filepath, InCurrentCode.code) # Escrevo o código enviado no arquivo criado
    filesystem.write_file(inputpath, InCurrentCode.input) # Escrevo o input no arquivo .txt criado

    currentID =  crud.insert_submission_register(InCurrentCode.lang) # Insere no banco de dados os metadados da submissão

    #Criação do arquivos persistentes para o banco de dados e controle de dados
    #Código fonte e o output e o input (talvez)

    #Container
    instancia = container.container_run(client, InCurrentCode.lang, filepath, inputpath) # Inicio o container com os dados necessários
    scode = 0 # Status code

    try:

        compilacao = instancia.exec_run(constants.CompileCMD[InCurrentCode.lang]) #Compilo o código enviado

        if compilacao[0] != 0:
            OutCurrentCode.flag = True
            OutCurrentCode.errout = "Compilation Error"
            return OutCurrentCode

        exec = instancia.exec_run(constants.RunCMD, demux=True) #Executo o código que fora compilado

        scode = exec[0] # Guardo o exitcode
        stdout, stderr = exec[1] # Guardo a saída padrão e de erro

        if scode in (124, 143):
            OutCurrentCode.flag = True
            OutCurrentCode.errout = "Time Limit Exceeded"
        elif scode != 0:
            OutCurrentCode.flag = True
            OutCurrentCode.errout = "Runtime Error"
        else:
            OutCurrentCode.output = stdout.decode("utf-8") if stdout else ""

        OutCurrentCode.time = stderr.decode("utf-8").strip() # Parse na string de erro (nesse caso, seria o tempo de execução)

    except Exception as e:
        instancia.kill()
        OutCurrentCode.flag = True;
        OutCurrentCode.errout = "Erro"
    finally:
        instancia.stop()
        instancia.remove() #Por fim a instância é removida, afinal marcamos "remove=false"(padrão), e "detach=true"
        crud.insert_result_register(currentID, OutCurrentCode.time, OutCurrentCode.flag, scode, OutCurrentCode.errout)


        #Crio os arquivos persistentes da submissão atual
        #Consiste em código fonte, output e input
        subpath = os.path.join(constants.submissionDir, str(currentID))
        os.makedirs(subpath)
        filesystem.write_file(os.path.join(subpath, "cf.txt"), InCurrentCode.code) # Salvo o código fonte
        filesystem.write_file(os.path.join(subpath, "out.txt"), OutCurrentCode.output) # Salvo o output
        filesystem.write_file(os.path.join(subpath, "in.txt"), InCurrentCode.input) # Salvo o input

    filesystem.delete_dir(tmpDirObject) # O diretório temporário é excluido

    #Retorna o objeto de OutCodeAreaText

    return OutCurrentCode

@app.get("/submissions")
async def Submissions(request: Request):

    submissions = crud.get_submissions()
    print(submissions)

    return templates.TemplateResponse(
        request=request,
        name="submissions.html",
        context={"submissions": submissions}
    )

@app.post("/problem/new")
async def ProblemSubmissions(file: UploadFile = File(...), etext: str = Form(...), time : int = Form(...)):
    print(file)
    print(etext)
    print(time)

    with zipfile.ZipFile(file.file, "r") as current_zip_file:

        current_zip_file_namelist = current_zip_file.namelist()
        k = len(current_zip_file_namelist)
        print(k)


    print("abc")
    ##ok, eu faço o parsing, se der tudo "Ok" eu crio uma pasta e coloco tudo la, se nao retorno erro

    return {'message': "Ok"}


@app.get("/submission/{id}")
async def current_submission(id: int, request: Request):
    
    submission = dict(crud.get_submission_by_id(id))

    strid = str(id)

    submission["code"] = filesystem.read_file(os.path.join(constants.submissionDir, strid, "cf.txt"))
    submission["output"] = filesystem.read_file(os.path.join(constants.submissionDir, strid, "out.txt"))
    submission["input"] = filesystem.read_file(os.path.join(constants.submissionDir, strid, "in.txt"))

    print(submission)

    return templates.TemplateResponse(
        request=request,
        name="currentsubmission.html",
        context={"submission": submission}
    )



templates = Jinja2Templates(directory=os.path.join(constants.BASE, "..\\Frontend\\Templates"))
app.mount("/", StaticFiles(directory=os.path.join(constants.BASE, "../Frontend"), html=True), name="static")#