from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

Base = declarative_base()

_engine = None
_SessionLocal = None


def get_database_url():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        USER = os.getenv("user")
        PASSWORD = os.getenv("password")
        HOST = os.getenv("host")
        PORT = os.getenv("port")
        DBNAME = os.getenv("dbname")
        if all([USER, PASSWORD, HOST, PORT, DBNAME]):
            DATABASE_URL = f"postgresql+psycopg://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"
    return DATABASE_URL


def get_engine():
    global _engine
    if _engine is None:
        DATABASE_URL = get_database_url()
        if DATABASE_URL:
            _engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
    return _engine


def _get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        if engine:
            _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


class _SessionLocalProxy:
    def __call__(self):
        factory = _get_session_factory()
        if factory is None:
            raise RuntimeError("Database not configured")
        return factory()


SessionLocal = _SessionLocalProxy()


def get_db():
    factory = _get_session_factory()
    if factory is None:
        raise RuntimeError("Database not configured")
    db = factory()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    try:
        engine = get_engine()
        if engine is None:
            return False
        with engine.connect() as connection:
            print("SQLAlchemy connection successful!")
            return True
    except Exception as e:
        print(f"Failed to connect: {e}")
        return False

