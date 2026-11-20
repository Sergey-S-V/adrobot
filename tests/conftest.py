import os
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import httpx
import psycopg
import pytest
from adrobot.keitaro import Settings
from adrobot.main import create_app
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy.engine import make_url

from tests.keitaro import KeitaroStub


@pytest.fixture(autouse=True)
def no_live_keitaro(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Tests must use the simulated Keitaro")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)


@contextmanager
def application():
    dsn = os.environ.get(
        "ADROBOT_TEST_DATABASE_URL",
        "postgresql://adrobot_test:adrobot_test@127.0.0.1:55433/adrobot_test",
    )
    url = make_url(dsn)
    if url.database != "adrobot_test" or url.host not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("Tests require the isolated local adrobot_test database")
    schema = "spec_" + uuid4().hex
    with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    app_url = (
        url.set(drivername="postgresql+psycopg")
        .update_query_dict({"options": f"-csearch_path={schema}"})
        .render_as_string(hide_password=False)
    )
    config = Config(str(Path(__file__).resolve().parents[1] / "backend/alembic.ini"))
    config.set_main_option("sqlalchemy.url", app_url.replace("%", "%%"))
    remote = KeitaroStub()
    try:
        command.upgrade(config, "head")
        app = create_app(
            Settings(database_url=app_url, keitaro_base_url="http://keitaro.test"),
            keitaro_transport=remote.transport,
        )
        yield app, remote
    finally:
        with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


@pytest.fixture
def client():
    with application() as (app, remote), TestClient(app) as client:
        client.remote = remote
        yield client
