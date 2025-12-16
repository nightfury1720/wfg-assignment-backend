from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

load_dotenv()

Base = declarative_base()

_engine = None
_SessionLocal = None


def is_ipv6(address):
    try:
        import ipaddress
        ipaddress.IPv6Address(address)
        return True
    except (ValueError, AttributeError):
        return False


def fix_database_url(url):
    if not url:
        return url
    
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        
        if host and is_ipv6(host):
            host_clean = host.replace('[', '').replace(']', '')
            if not (host.startswith('[') and host.endswith(']')):
                host = f'[{host_clean}]'
            
            auth_part = ''
            if parsed.username:
                if parsed.password:
                    auth_part = f"{parsed.username}:{parsed.password}@"
                else:
                    auth_part = f"{parsed.username}@"
            
            port_part = f":{parsed.port}" if parsed.port else ""
            netloc = f"{auth_part}{host}{port_part}"
            
            query_params = parse_qs(parsed.query)
            if 'sslmode' not in query_params:
                query_params['sslmode'] = ['require']
            query = urlencode(query_params, doseq=True)
            
            fixed_url = urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                query,
                parsed.fragment
            ))
            return fixed_url
    except Exception:
        pass
    
    return url


def get_database_url():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL:
        DATABASE_URL = fix_database_url(DATABASE_URL)
    else:
        USER = os.getenv("user")
        PASSWORD = os.getenv("password")
        HOST = os.getenv("host")
        PORT = os.getenv("port")
        DBNAME = os.getenv("dbname")
        if all([USER, PASSWORD, HOST, PORT, DBNAME]):
            if is_ipv6(HOST) and not (HOST.startswith('[') and HOST.endswith(']')):
                HOST = f'[{HOST}]'
            DATABASE_URL = f"postgresql+psycopg://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"
    return DATABASE_URL


def get_engine():
    global _engine
    if _engine is None:
        DATABASE_URL = get_database_url()
        if DATABASE_URL:
            connect_args = {}
            parsed = urlparse(DATABASE_URL)
            hostname_clean = parsed.hostname.replace('[', '').replace(']', '') if parsed.hostname else None
            
            if hostname_clean and is_ipv6(hostname_clean):
                connect_args['connect_timeout'] = 30
                connect_args['sslmode'] = 'require'
            
            _engine = create_engine(
                DATABASE_URL, 
                pool_pre_ping=True, 
                pool_recycle=300,
                pool_size=5,
                max_overflow=10,
                connect_args=connect_args
            )
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

