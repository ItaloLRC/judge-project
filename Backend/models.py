from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from database import engine

class OutCodeAreaText(BaseModel):
    output: str = ""
    errout: str = ""
    flag: bool = False
    time: str = ""

class InCodeAreaText(BaseModel):
    input: str = ""
    code: str = ""
    lang: str = ""

def create_table():
    with engine.connect() as conn:
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS submissions(
                id SERIAL PRIMARY KEY,
                language TEXT,
                date TIMESTAMPTZ DEFAULT now()
            )
            """
        ))
        conn.commit()

        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS submissions_result(
                id SERIAL PRIMARY KEY,
                submission_id INT REFERENCES submissions(id),
                time TEXT,
                flag BOOL,
                exit_code INT,
                errout TEXT
            )

            """
        ))
        conn.commit()