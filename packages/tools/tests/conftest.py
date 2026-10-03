# Fixtures for the tests marked db. They run only when CENTINELA_TEST_DSN names a scratch PostgreSQL
# loaded with data/sql/01 to 04 (packages/tools/AGENTS.md starts one); the session applies to it the
# roles, the grants, the base KPIs of data/metricas.yaml and the fixture KPIs, as the generator writes them.
import os

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from centinela_tools.generate import render, view_names
from centinela_tools.paths import METRICAS, SQL_DIR
from centinela_tools.settings import Settings
from centinela_tools.sources import load_sources
from centinela_tools.tools import load_entries

from support import fixture_entries

DSN = os.environ.get("CENTINELA_TEST_DSN")
ROLES = {"lector": "centinela_lector", "kernel": "centinela_kernel"}


def pytest_collection_modifyitems(config, items):
    if DSN:
        return
    skip = pytest.mark.skip(reason="CENTINELA_TEST_DSN is not set; packages/tools/AGENTS.md starts a scratch database")
    for item in items:
        if "db" in item.keywords:
            item.add_marker(skip)


def open_as(role: str) -> psycopg.Connection:
    name = ROLES[role]
    return psycopg.connect(make_conninfo(DSN, user=name, password=name), autocommit=True)


@pytest.fixture(scope="session")
def applied():
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute(render(load_sources(), {**load_entries(METRICAS), **fixture_entries()}, view_names(SQL_DIR), lambda query: 0.0, Settings()))
    return True


@pytest.fixture
def superuser(applied):
    with psycopg.connect(DSN, autocommit=True) as conn:
        yield conn


@pytest.fixture
def connect(applied):
    return open_as
