from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings

_is_sqlite = "sqlite" in settings.DATABASE_URL

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 60} if _is_sqlite else {},
    pool_pre_ping=True,
    pool_size=10 if not _is_sqlite else 5,
)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")       # concurrent reads during writes
        cur.execute("PRAGMA synchronous=NORMAL")      # faster writes, still safe
        cur.execute("PRAGMA cache_size=-65536")       # 64 MB page cache
        cur.execute("PRAGMA busy_timeout=60000")      # wait up to 60s on lock
        cur.execute("PRAGMA temp_store=MEMORY")
        cur.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
