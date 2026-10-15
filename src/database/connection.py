import logging
from typing import Optional, Tuple, Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from src.database.config import get_db_settings

logger = logging.getLogger(__name__)

_DEFAULT_ENGINE: Optional[Engine] = None

def get_engine(custom_url: Optional[str] = None, echo: bool = False) -> Engine:
    """
    Creates and returns a SQLAlchemy Engine.
    Configured with connection pooling and pre-ping validation for reliability.
    Automatically refreshes if database settings have changed.
    """
    global _DEFAULT_ENGINE
    if custom_url is not None:
        return create_engine(custom_url, echo=echo)

    settings = get_db_settings()
    url = settings.sqlalchemy_url

    if _DEFAULT_ENGINE is None or str(_DEFAULT_ENGINE.url) != url:
        # Check if SQLite in-memory or PostgreSQL
        if "sqlite" in url:
            _DEFAULT_ENGINE = create_engine(url, echo=echo)
        else:
            _DEFAULT_ENGINE = create_engine(
                url,
                echo=echo,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=1800,
            )
    return _DEFAULT_ENGINE

def get_session_factory(engine: Optional[Engine] = None) -> sessionmaker:
    """Returns a configured sessionmaker bound to the given or default engine."""
    eng = engine or get_engine()
    return sessionmaker(bind=eng, autoflush=False, autocommit=False)

@contextmanager
def get_db_session(engine: Optional[Engine] = None) -> Generator[Session, None, None]:
    """Context manager that yields an active database session and handles commit/rollback."""
    session_factory = get_session_factory(engine)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session rolled back due to error: {e}")
        raise
    finally:
        session.close()

def check_database_connection(engine: Optional[Engine] = None) -> Tuple[bool, str]:
    """
    Performs a lightweight health check (SELECT 1) against the database engine.
    Returns (status: bool, message: str).
    """
    eng = engine or get_engine()
    settings = get_db_settings()

    if "sqlite" not in str(eng.url) and not settings.is_configured():
        return False, (
            "PostgreSQL credentials are not configured in .env. "
            "Please create a .env file with your local DB credentials: "
            "DB_HOST=localhost, DB_PORT=5432, DB_NAME=travelwise_db, DB_USER=postgres, DB_PASSWORD=your_password"
        )

    try:
        with eng.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            if result == 1:
                db_type = "PostgreSQL" if "postgresql" in str(eng.url) else "SQLite"
                db_name = eng.url.database or "in-memory"
                return True, f"Successfully connected to {db_type} database '{db_name}' at {eng.url.host or 'local'}."
            return False, f"Unexpected health check response from database: {result}"
    except Exception as e:
        err_msg = str(e)
        logger.warning(f"Database health check failed: {err_msg}")
        if "fe_sendauth" in err_msg or "password authentication failed" in err_msg:
            return False, (
                "PostgreSQL authentication failed. Please verify your DB_USER and DB_PASSWORD "
                "in your .env file."
            )
        elif "could not connect to server" in err_msg or "Connection refused" in err_msg:
            return False, (
                "Could not reach PostgreSQL server on port 5432. "
                "Please ensure the PostgreSQL service is running."
            )
        elif "database" in err_msg and "does not exist" in err_msg:
            return False, (
                f"Database '{settings.name}' does not exist on PostgreSQL server. "
                f"Create it using: CREATE DATABASE {settings.name};"
            )
        return False, f"Database connection error: {err_msg}"
