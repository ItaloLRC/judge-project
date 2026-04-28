from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from constants import DATABASE_URL
from database import engine

def insert_submission_register(lang: str):
    cid: int
    with engine.connect() as conn:
        result = conn.execute(text(
            """
            INSERT INTO submissions (language)
            VALUES(:language)   
            RETURNING id
            """),
            {"language": lang}

        )
        conn.commit()
        cid = result.fetchone().id

    return cid
    


def insert_result_register(sub_id: int, time: str, flag: bool, exit_code: int, errout: str):
    cid: int
    with engine.connect() as conn:
        result = conn.execute(text(
            """
            INSERT INTO submissions_result (submission_id, time, flag, exit_code, errout)
            VALUES(:submission_id, :time, :flag, :exit_code, :errout)
            RETURNING id
            """),

            {"submission_id": sub_id,  "time": time, "flag": flag, "exit_code": exit_code, "errout": errout}

            )
        cid = result.fetchone().id
        conn.commit()

    return cid

def insert_problem_register(time: int, title: str, text:str, input:str, output:str):
    cid: int

    with engine.connect() as conn:
        result = conn.execute(text(
            """
            INSERT INTO problems (time, title, textarea, input, output)
            VALUES(:time, :title, :text, :input, :output)
            RETURNING id
            """),
            {"time": time, "title": title, "textarea": text, "input":input, "output":output}
        )

        cid = result.fetchone().id
        conn.commit()
    
    return cid

def get_submissions_results():

    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM submissions_result"))
        return result.mappings().fetchall()
    
def get_submission_by_id(id: int):

    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM submissions WHERE id = :id"),
                              {"id": id}
                            )
        return result.mappings().fetchone()

def get_submissions():

    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM submissions"))
        return result.mappings().fetchall()