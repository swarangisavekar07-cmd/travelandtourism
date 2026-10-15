import os
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote_plus
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Search paths for .env file: project root, then venv folder as fallback
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ROOT_ENV = _PROJECT_ROOT / ".env"
_VENV_ENV = _PROJECT_ROOT / "venv" / ".env"

if _ROOT_ENV.exists():
    load_dotenv(dotenv_path=_ROOT_ENV, override=True)
elif _VENV_ENV.exists():
    load_dotenv(dotenv_path=_VENV_ENV, override=True)
else:
    load_dotenv(override=True)


@dataclass(frozen=True)
class DatabaseSettings:
    """Database configuration parsed from environment variables."""
    host: str = "localhost"
    port: int = 5432
    name: str = "travelwise_db"
    user: str = "postgres"
    password: str = ""
    database_url_override: Optional[str] = None

    @property
    def sqlalchemy_url(self) -> str:
        """Constructs the SQLAlchemy connection URL with properly escaped credentials."""
        if self.database_url_override:
            url = self.database_url_override
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg2://", 1)
            return url

        encoded_password = quote_plus(self.password) if self.password else ""
        return f"postgresql+psycopg2://{self.user}:{encoded_password}@{self.host}:{self.port}/{self.name}"

    def is_configured(self) -> bool:
        """Checks if credentials appear configured rather than blank or placeholder."""
        if self.database_url_override:
            return True
        if not self.password or self.password in ("change_me_in_dotenv", "your_password"):
            return False
        return True


def get_db_settings() -> DatabaseSettings:
    """
    Returns DatabaseSettings instance loaded from current environment.
    Always re-checks .env files dynamically to ensure latest values are picked up.
    """
    if _ROOT_ENV.exists():
        load_dotenv(dotenv_path=_ROOT_ENV, override=True)
    elif _VENV_ENV.exists():
        load_dotenv(dotenv_path=_VENV_ENV, override=True)

    return DatabaseSettings(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        name=os.getenv("DB_NAME", "travelwise_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        database_url_override=os.getenv("DATABASE_URL"),
    )
