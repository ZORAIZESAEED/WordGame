import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# SQLite for local dev and tests. In AWS this will point at RDS Postgres,
# e.g. postgresql+psycopg://user:pass@host:5432/wordgame
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./wordgame.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True)
if DATABASE_URL.startswith("sqlite"):
    # SQLite ignores FOR UPDATE, and Python's driver starts transactions lazily, so two
    # requests could both read a game before either writes. BEGIN IMMEDIATE takes SQLite's
    # write lock at the start of every transaction instead, which serialises them.
    # (This is SQLAlchemy's documented recipe for pysqlite transaction control.)
    @event.listens_for(engine, "connect")
    def _sqlite_no_autobegin(dbapi_connection, _record):
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _sqlite_begin_immediate(conn):
        conn.exec_driver_sql("BEGIN IMMEDIATE")


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
