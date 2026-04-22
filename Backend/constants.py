import os

CompileCMD = {
    "C++":["sh", "-c", "g++ /codigo/newfile.cpp -o /tmp/newfile"],
    "C":["sh", "-c", "gcc /codigo/newfile.c -o /tmp/newfile"]
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

RunCMD = "sh -c 'timeout 10 /usr/bin/time -f \"%e\" /tmp/newfile < /codigo/input.txt'"

DATABASE_URL = "postgresql://judge_user:senha@localhost:5432/judge_db"

BASE = os.path.dirname(__file__) # Pega o endereço do arquivo atual

submissionDir = os.path.join(BASE, "..", "Submissions")

problemsDir = os.path.join(BASE, "..", "Problems")