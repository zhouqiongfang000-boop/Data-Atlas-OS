from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base

from config import (
    get_bool_env,
    get_int_env,
    get_env,
    is_production_env,
    load_env_file,
    require_env,
)


load_env_file()


def _build_database_url():
    database_url = get_env("DATABASE_URL")
    if database_url:
        return database_url

    drivername = get_env("DB_DRIVER", "mysql+pymysql")
    port = get_int_env("DB_PORT", 3306)

    if is_production_env():
        return URL.create(
            drivername=drivername,
            username=require_env("DB_USER"),
            password=require_env("DB_PASSWORD"),
            host=require_env("DB_HOST"),
            port=port,
            database=require_env("DB_NAME"),
        )

    return URL.create(
        drivername=drivername,
        username=get_env("DB_USER", "root"),
        password=get_env("DB_PASSWORD", "123456yXr!"),
        host=get_env("DB_HOST", "localhost"),
        port=port,
        database=get_env("DB_NAME", "dataplatform"),
    )


DATABASE_URL = _build_database_url()

engine = create_engine(
    DATABASE_URL,
    echo=get_bool_env("SQLALCHEMY_ECHO", False),
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()
