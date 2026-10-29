# JudgeProject

JudgeProject é um protótipo de executor de código C e C++ para uma plataforma de programação competitiva. O usuário envia um programa e sua entrada; a API compila o código em um contêiner Docker, executa o binário e devolve a saída ou a classificação do erro.

O projeto estuda o fluxo de uma submissão, desde o formulário no navegador até o registro no banco de dados. A inspiração são plataformas como Beecrowd, Codeforces e DOMjudge. A comparação automática com gabaritos e a integração com um catálogo de problemas ainda estão em desenvolvimento.

## O que está implementado

- Envio de código C/C++ e entrada padrão pelo navegador ou por uma API JSON.
- Compilação com GCC ou G++ e execução em um contêiner por submissão.
- Retorno de stdout e indicação de erro de compilação, erro de execução ou limite de tempo excedido.
- Registro de metadados e resultados no PostgreSQL.
- Histórico de submissões e páginas para consultar código, entrada e saída salvos.
- Estrutura inicial de cadastro de problemas com upload de pares de arquivos `.in` e `.out` em ZIP.

O cadastro de problemas ainda inspeciona os nomes dos arquivos e não conclui sua persistência ou a execução dos casos de teste. Uma submissão que executa sem erro recebe sua saída; a API ainda não a classifica como Accepted ou Wrong Answer por comparação com um gabarito.

## Fluxo de uma submissão

1. O formulário envia `code`, `input` e `lang` para `POST /submit`.
2. A API grava os arquivos temporários e abre o registro da submissão no banco.
3. Um contêiner recebe os arquivos por volumes somente de leitura e compila o programa.
4. O executável lê a entrada fornecida. A API coleta a saída, o código de retorno e a informação de tempo.
5. O contêiner é removido, o resultado fica no PostgreSQL e os arquivos são preservados em `Submissions/<id>/`.

As rotas são declaradas como assíncronas no FastAPI, mas as chamadas ao SDK do Docker executam o trabalho dentro da própria requisição. O projeto ainda não possui uma fila de workers para processar submissões em segundo plano.

## Organização

| Caminho | Responsabilidade |
|---|---|
| [Backend/main.py](Backend/main.py) | API, páginas de consulta e fluxo das submissões |
| [Backend/container.py](Backend/container.py) | Criação e configuração dos contêineres |
| [Backend/constants.py](Backend/constants.py) | Imagens, comandos de compilação, diretórios e conexão com o banco |
| [Backend/models.py](Backend/models.py) | Modelos de entrada/saída e criação das tabelas |
| [Backend/crud.py](Backend/crud.py) | Consultas e gravações no PostgreSQL via SQLAlchemy |
| [Backend/filesystem.py](Backend/filesystem.py) | Leitura, gravação e diretórios temporários |
| [Frontend/](Frontend/) | Formulários HTML, JavaScript e templates Jinja2 |
| [Images/](Images/) | Dockerfiles das imagens de C e C++ |
| [Submissions/](Submissions/) | Código, entrada e saída de submissões registradas |

## Ambiente de desenvolvimento

O backend usa Python, FastAPI, Uvicorn, SQLAlchemy e o SDK Python do Docker. É necessário ter PostgreSQL e um daemon Docker em execução, com suporte às imagens Linux usadas pelo projeto. Os caminhos dos templates em `Backend/main.py` incluem separadores de Windows; confira esse trecho se for executar em Linux.

### Dependências Python

Na raiz do repositório, crie um ambiente virtual:

```bash
python -m venv .venv
```

Ative com `source .venv/Scripts/activate` no Git Bash do Windows ou `source .venv/bin/activate` em Linux. Depois:

```bash
python -m pip install fastapi uvicorn sqlalchemy psycopg2-binary docker python-multipart jinja2
```

O repositório ainda não fixa as versões dessas dependências em um arquivo de instalação.

### Banco e imagens

Crie um banco PostgreSQL e configure `DATABASE_URL` em `Backend/constants.py` com a conexão do seu ambiente. A inicialização da API cria as tabelas `submissions`, `submissions_result` e `problems` quando elas ainda não existem.

Construa as imagens a partir da raiz:

```bash
docker build -t judge/c:latest Images/c
docker build -t judge/cpp:latest Images/cpp
```

O comando de execução em `Backend/constants.py` depende de `sh`, `timeout` e `/usr/bin/time`. Os Dockerfiles atuais instalam os compiladores e `musl-dev`; confirme e complete as ferramentas de execução nas imagens antes de usar o fluxo de submissão, especialmente `/usr/bin/time`.

### Iniciar a API

```bash
cd Backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Abra [a interface local](http://127.0.0.1:8000/) ou [a documentação da API](http://127.0.0.1:8000/docs). O JavaScript da interface também aponta para `127.0.0.1:8000`.

## Rotas

| Método e caminho | Uso |
|---|---|
| `POST /submit` | Recebe JSON com `code`, `input` e `lang`, que deve ser `C` ou `C++` |
| `GET /submissions` | Exibe o histórico de submissões |
| `GET /submission/{id}` | Exibe uma submissão e seus arquivos |
| `POST /problem/new` | Recebe ZIP e campos do formulário de problemas; fluxo em desenvolvimento |

A resposta de execução contém `output`, `errout`, `flag` e `time`. O campo `flag` indica que o fluxo classificou um erro, enquanto `errout` contém sua descrição.

## Limites atuais

O contêiner tem rede desativada, memória limitada a 256 MB, até 50 processos e quota de CPU equivalente a metade de um núcleo. O comando limita a execução do programa a dez segundos. Esses controles não constituem uma validação completa de isolamento para executar código hostil.

O protótipo é voltado à experimentação local. Ainda faltam autenticação, validação completa das linguagens e dos uploads, integração com os casos de teste e uma suíte automatizada para o fluxo inteiro. A pasta `Submissions/` contém registros de execução, não um benchmark ou uma prova de aceitação em um online judge.
