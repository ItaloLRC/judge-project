
> 🚧 **Status:** Em desenvolvimento ativo. Atualmente focado no registro de problemas.

---

# 🧑‍⚖️ JudgeProject - Motor de Avaliação de Código (Online Judge)

Um motor de juiz virtual focado na compilação e execução segura de código C/C++ de terceiros, inspirado em plataformas de programação competitiva (como Beecrowd, Codeforces e DOMjudge). 

## 🛠️ Tecnologias Utilizadas
* **Backend:** Python, FastAPI, Uvicorn
* **Banco de Dados:** PostgreSQL, SQLAlchemy
* **Infraestrutura/Segurança:** Docker (RCE Isolado)
* **Frontend:** HTML, Vanilla JavaScript, Jinja2 Templates

---

## 🏗️ Arquitetura do Sistema
O projeto foi desenhado focando em separação de responsabilidades e execução assíncrona:

1. **Frontend:** Coleta o código e a linguagem selecionada pelo usuário.
2. **API (FastAPI):** Recebe o *payload*, valida os dados e repassa para o Docker.
3. **Motor de Avaliação (Docker):** Um contêiner efêmero é gerado exclusivamente para compilar e executar o código do usuário de forma isolada, comparando a saída padrão (stdout) com o gabarito.
4. **Armazenamento:** Metadados e IDs são salvos no PostgreSQL, enquanto os arquivos de I/O pesados (Código Fonte, In/Out) ficam isolados no Filesystem.

---
