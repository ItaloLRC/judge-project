# JudgeProject

English | [Português (Brasil)](README.pt-BR.md)

JudgeProject is a C and C++ code runner for a competitive programming platform. Users submit a program and its input; the API compiles the code in a Docker container, runs the binary, and returns its output or an error classification.

The project explores the submission workflow, from the browser form to the database record. It draws inspiration from platforms such as Beecrowd, Codeforces, and DOMjudge.

## Implemented features

- Submit C/C++ code and standard input through the browser or a JSON API.
- Compile with GCC or G++ and run in a separate container for each submission.
- Return stdout and classify compilation errors, runtime errors, and time limit violations.
- Store metadata and results in PostgreSQL.
- Browse submission history and view saved source code, input, and output.

## Submission workflow

1. The form sends `code`, `input`, and `lang` to `POST /submit`.
2. The API writes temporary files and creates a submission record in the database.
3. A container receives the files through read-only bind mounts and compiles the program.
4. The executable reads the supplied input. The API collects its output, exit code, and elapsed time.
5. The container is removed, the result is stored in PostgreSQL, and the files are preserved in `Submissions/<id>/`.

## Project structure

| Path | Responsibility |
|---|---|
| [Backend/main.py](Backend/main.py) | API, submission pages, and submission workflow |
| [Backend/container.py](Backend/container.py) | Container creation and configuration |
| [Backend/constants.py](Backend/constants.py) | Images, compilation commands, directories, and database connection |
| [Backend/models.py](Backend/models.py) | Input/output models and table creation |
| [Backend/crud.py](Backend/crud.py) | PostgreSQL queries and writes through SQLAlchemy |
| [Backend/filesystem.py](Backend/filesystem.py) | File operations and temporary directories |
| [Frontend/](Frontend/) | HTML forms, JavaScript, and Jinja2 templates |
| [Images/](Images/) | Dockerfiles for the C and C++ images |
| [Submissions/](Submissions/) | Source code, input, and output from recorded submissions |

## Development environment

The backend uses Python 3.10+, FastAPI, Uvicorn, SQLAlchemy, and the Docker SDK for Python. PostgreSQL and a running Docker daemon with Linux container support are required. Template paths work on Windows and Linux.

### Python dependencies

Create a virtual environment at the repository root:

```bash
python -m venv .venv
```

Activate it with `source .venv/Scripts/activate` in Git Bash on Windows or `source .venv/bin/activate` on Linux. Then run:

```bash
python -m pip install -r requirements.txt
```

### Database and images

Create a PostgreSQL database and set the `DATABASE_URL` environment variable to your connection string. PowerShell example:

```powershell
$env:DATABASE_URL = "postgresql://judge_user:senha@localhost:5432/judge_db"
```

On Linux/Git Bash, use `export DATABASE_URL="postgresql://judge_user:senha@localhost:5432/judge_db"`. If the variable is unset, the API uses the development URL in `Backend/constants.py`. Startup creates the `submissions`, `submissions_result`, and `problems` tables if they do not exist.

Build the images from the repository root:

```bash
docker build -t judge/c:latest Images/c
docker build -t judge/cpp:latest Images/cpp
```

The images include GCC/G++, `sh`, `timeout`, and `/usr/bin/time`. Rebuild both images after updating the Dockerfiles.

### Start the API

```bash
cd Backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Open the [local interface](http://127.0.0.1:8000/) or the [API documentation](http://127.0.0.1:8000/docs). The interface sends requests to the same address and port used to open the page.

## Routes

| Method and path | Purpose |
|---|---|
| `POST /submit` | Accepts JSON with `code`, `input`, and `lang`, which must be `C` or `C++` |
| `GET /submissions` | Displays submission history |
| `GET /submission/{id}` | Displays a submission and its files |
| `POST /problem/new` | Registers a problem statement, input/output descriptions, time limit, and ZIP of test cases |

Execution responses contain `output`, `errout`, `flag`, and `time`. The `flag` field indicates a classified error; `errout` provides its description.

The problem registration form is at `/problem/new/`. The ZIP must contain pairs such as `1.in`/`1.out`, `2.in`/`2.out`, and so on, without gaps, folders, or duplicate files. The limits are 2000 files and 50 MiB uncompressed. Test cases are saved in `Problems/<id>/`; the `title`, `etext`, `time` (ms), `input`, and `output` fields are submitted along with the `file` upload. Registration returns the saved ID. The `/submit` runner still executes code with the supplied input; automatic comparison against these test cases is not implemented yet.

## Container configuration

Each submission runs in a container without root privileges, with networking disabled, a read-only filesystem, a 64 MiB `/tmp`, 256 MB of memory, a limit of 50 processes, and a CPU quota equivalent to half a core. Compilation has a 30-second limit and execution has a ten-second limit, followed by forced termination after one additional second if the program ignores the termination signal. Output is limited to 1 MiB; elapsed time is collected separately from the program's error messages.

## Tests

From the repository root:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

API tests use mocked Docker and a temporary SQLite database to check persistence, error classifications, cleanup, pages, and ZIP validation without external services. To also run tests against the built Docker images, set `JUDGE_DOCKER_TESTS=1` (`$env:JUDGE_DOCKER_TESTS = "1"` in PowerShell or `export JUDGE_DOCKER_TESTS=1` on Linux/Git Bash) and repeat the command. These tests cover C/C++, compilation errors, runtime errors, time limits, and unbounded output.
