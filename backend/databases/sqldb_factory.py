from typing import Any, Callable, Dict

from loguru import logger
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker

from backend.config.settings import _settings

engine = create_engine(
    _settings.postgres.url,
    pool_size=_settings.postgres.pool_size,
    max_overflow=_settings.postgres.max_overflow,
    pool_timeout=_settings.postgres.pool_timeout,
    pool_recycle=_settings.postgres.pool_recycle,
    pool_use_lifo=True,
    pool_pre_ping=True,
    isolation_level="READ COMMITTED",
)


class SQLDBFactory:
    _registry: Dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, creator: Callable[[], Any]):
        cls._registry[name] = creator

    @classmethod
    def create(cls, name: str) -> Any:
        creator = cls._registry.get(name)
        if not creator:
            raise ValueError(f"No resource named '{name}' registered.")
        return creator()

    @classmethod
    def create_postgres(cls):
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        def get_db():
            session = SessionLocal()
            try:
                yield session
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"Error in get_db_session context manager: {e}")
            finally:
                session.close()

        return get_db


SQLDBFactory.register("postgres", SQLDBFactory.create_postgres)
