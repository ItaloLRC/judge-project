import os

CompileCMD = {
    "C++":["timeout", "-k", "1s", "30s", "g++", "/codigo/newfile.cpp", "-o", "/tmp/newfile"],
    "C":["timeout", "-k", "1s", "30s", "gcc", "/codigo/newfile.c", "-o", "/tmp/newfile"]
}

ContainerVolume = {
    "C++":"/codigo/newfile.cpp",
    "C":"/codigo/newfile.c"
}

ContainerImage = {
    "C++":"judge/cpp:latest",
    "C":"judge/c:latest"
}

langPath = {
    "C++":"cf.cpp",
    "C":"cf.c"
}

RunCMD = [
    "sh", "-c",
    "/usr/bin/time -q -f '%e' timeout -k 1s 10s sh -c "
    "'ulimit -f 1024; exec /tmp/newfile < /codigo/input.txt "
    "> /tmp/judge-stdout 2> /tmp/judge-stderr'; "
    "status=$?; timeout -k 1s 2s head -c 1048576 /tmp/judge-stdout 2>/dev/null; exit \"$status\""
]

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://judge_user:senha@localhost:5432/judge_db")

BASE = os.path.dirname(__file__) # Pega o endereço do arquivo atual

submissionDir = os.path.join(BASE, "..", "Submissions")

problemsDir = os.path.join(BASE, "..", "Problems")
