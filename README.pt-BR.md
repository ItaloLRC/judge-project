# JudgeProject

[English](README.md) | Português (Brasil)

JudgeProject é um executor de código C e C++ para uma plataforma de programação competitiva. O usuário envia um programa e sua entrada; a API compila o código em um contêiner Docker, executa o binário e devolve a saída ou a classificação do erro.

O projeto estuda o fluxo de uma submissão, desde o formulário no navegador até o registro no banco de dados. A inspiração são plataformas como Beecrowd, Codeforces e DOMjudge.

## O que está implementado

- Envio de código C/C++ e entrada padrão pelo navegador ou por uma API JSON.
- Compilação com GCC ou G++ e execução em um contêiner por submissão.
- Retorno de stdout e indicação de erro de compilação, erro de execução ou limite de tempo excedido.
- Registro de metadados e resultados no PostgreSQL.
- Histórico de submissões e páginas para consultar código, entrada e saída salvos.

## Fluxo de uma submissão

1. O formulário envia `code`, `input` e `lang` para `POST /submit`.
2. A API grava os arquivos temporários e abre o registro da submissão no banco.
3. Um contêiner recebe os arquivos por volumes somente de leitura e compila o programa.
4. O executável lê a entrada fornecida. A API coleta a saída, o código de retorno e a informação de tempo.
5. O contêiner é removido, o resultado fica no PostgreSQL e os arquivos são preservados em `Submissions/<id>/`.

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

O backend usa Python 3.10+, FastAPI, Uvicorn, SQLAlchemy e o SDK Python do Docker. É necessário ter PostgreSQL e um daemon Docker em execução, com suporte a contêineres Linux. Os caminhos dos templates funcionam em Windows e Linux.

### Dependências Python

Na raiz do repositório, crie um ambiente virtual:

```bash
python -m venv .venv
```

Ative com `source .venv/Scripts/activate` no Git Bash do Windows ou `source .venv/bin/activate` em Linux. Depois:

```bash
python -m pip install -r requirements.txt
```

### Banco e imagens

Crie um banco PostgreSQL e defina a variável de ambiente `DATABASE_URL` com a conexão do seu ambiente. Exemplo em PowerShell:

```powershell
$env:DATABASE_URL = "postgresql://judge_user:senha@localhost:5432/judge_db"
```

Em Linux/Git Bash, use `export DATABASE_URL="postgresql://judge_user:senha@localhost:5432/judge_db"`. Sem essa variável, a API utiliza o endereço de desenvolvimento definido em `Backend/constants.py`. A inicialização cria as tabelas `submissions`, `submissions_result` e `problems` quando elas ainda não existem.

Construa as imagens a partir da raiz:

```bash
docker build -t judge/c:latest Images/c
docker build -t judge/cpp:latest Images/cpp
```

As imagens incluem GCC/G++, `sh`, `timeout` e `/usr/bin/time`. Reconstrua ambas após atualizar os Dockerfiles.

### Iniciar a API

```bash
cd Backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Abra [a interface local](http://127.0.0.1:8000/) ou [a documentação da API](http://127.0.0.1:8000/docs). A interface envia requisições para o mesmo endereço e porta usados para abrir a página.

## Rotas

| Método e caminho | Uso |
|---|---|
| `POST /submit` | Recebe JSON com `code`, `input` e `lang`, que deve ser `C` ou `C++` |
| `GET /submissions` | Exibe o histórico de submissões |
| `GET /submission/{id}` | Exibe uma submissão e seus arquivos |
| `POST /problem/new` | Cadastra enunciado, descrições de entrada/saída, tempo e ZIP dos casos de teste |

A resposta de execução contém `output`, `errout`, `flag` e `time`. O campo `flag` indica que o fluxo classificou um erro, enquanto `errout` contém sua descrição.

O formulário de cadastro está em `/problem/new/`. O ZIP deve conter pares `1.in`/`1.out`, `2.in`/`2.out`, etc., sem lacunas, pastas ou arquivos duplicados. São aceitos até 2000 arquivos e 50 MiB descompactados. Os casos ficam em `Problems/<id>/`; os campos `title`, `etext`, `time` (ms), `input` e `output` são enviados junto com o arquivo `file`. O cadastro retorna o ID salvo. O executor `/submit` continua executando o código com a entrada fornecida; a comparação automática com esses casos ainda não está implementada.

## Configuração dos contêineres

Cada submissão utiliza um contêiner sem privilégios de root, com rede desativada, sistema de arquivos somente de leitura, `/tmp` de 64 MiB, memória de 256 MB, limite de 50 processos e quota de CPU equivalente a metade de um núcleo. A compilação tem limite de 30 segundos e o programa, de dez segundos, com encerramento forçado após mais um segundo caso ignore o sinal de término. A saída é limitada a 1 MiB; o tempo é coletado separadamente das mensagens de erro do programa.

## Testes

Na raiz do repositório:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Os testes da API usam Docker simulado e SQLite temporário para verificar persistência, classificações de erro, limpeza, páginas e validação dos ZIPs, sem precisar dos serviços externos. Para executar também os testes com as imagens Docker construídas, defina `JUDGE_DOCKER_TESTS=1` (`$env:JUDGE_DOCKER_TESTS = "1"` em PowerShell ou `export JUDGE_DOCKER_TESTS=1` em Linux/Git Bash) e repita o comando. Eles verificam C/C++, erro de compilação, erro de execução, limite de tempo e saída ilimitada.
