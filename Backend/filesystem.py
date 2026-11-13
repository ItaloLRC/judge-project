import tempfile
import os

def create_dir():

    tmpdir = tempfile.TemporaryDirectory() 

    return tmpdir #Preciso pegar o tmpdir.name para caminho em string


def delete_dir(dirpath):
    dirpath.cleanup() # Deleto o diretório


def create_filepath(tmpdir: str, filename: str):

    filepath = os.path.join(tmpdir, filename)  # Crio o caminho do arquivo

    return filepath # Retorno o caminho criado

def read_file(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def write_file(filepath: str, data: str):

    with open(filepath, "w", encoding="utf-8", newline="") as f: # Abro o arquivo em modo escrita

        f.write(data) # Escrevo os dados
