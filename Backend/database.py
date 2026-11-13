from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from constants import DATABASE_URL

url = make_url(DATABASE_URL)
if url.drivername == "postgresql":
    url = url.set(drivername="postgresql+psycopg2")
engine = create_engine(url)

