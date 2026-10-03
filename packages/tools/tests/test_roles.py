# The gate of the law that no agent changes a database: what centinela_lector and centinela_kernel
# can read and run, that every write either role attempts fails, and that neither can become
# centinela_propietario, the NOLOGIN owner of the functions. Needs the scratch database.
import psycopg
import pytest

pytestmark = pytest.mark.db

WRITES = [
    "INSERT INTO centinela.bodegas VALUES ('X', 'X', 'X')",
    "UPDATE centinela.pedidos SET canal = 'x'",
    "DELETE FROM centinela.pagos",
    "TRUNCATE centinela.pagos",
    "CREATE TABLE centinela.intruso (x int)",
    "CREATE TABLE public.intruso (x int)",
    "CREATE TEMP TABLE intruso (x int)",
    "DROP FUNCTION centinela.k_oc_abiertas(date)",
    "ALTER FUNCTION centinela.fecha_corte() SECURITY INVOKER",
    "GRANT SELECT ON centinela.pedidos TO centinela_lector",
]


def fails(conn, statement):
    with pytest.raises(psycopg.Error):
        conn.execute(statement)


def test_the_reader_cannot_select_a_table(connect):
    with connect("lector") as conn:
        fails(conn, "SELECT * FROM centinela.pedidos LIMIT 1")


def test_the_reader_reads_a_view_that_calls_fecha_corte(connect):
    with connect("lector") as conn:
        assert conn.execute("SELECT count(*) FROM centinela.v_cartera_cliente").fetchone()[0] > 0


def test_the_reader_executes_a_kernel_function(connect):
    with connect("lector") as conn:
        assert conn.execute("SELECT count(*) FROM centinela.k_oc_abiertas('2026-03-02')").fetchone()[0] > 0


def test_the_kernel_reads_a_readable_column_and_not_a_persons_name(connect):
    with connect("kernel") as conn:
        conn.execute("SELECT vendedor_id, region FROM centinela.vendedores LIMIT 1")
        fails(conn, "SELECT nombre FROM centinela.vendedores LIMIT 1")


def test_the_kernel_cannot_read_a_view(connect):
    with connect("kernel") as conn:
        fails(conn, "SELECT * FROM centinela.v_ventas LIMIT 1")


@pytest.mark.parametrize("role", ["lector", "kernel"])
@pytest.mark.parametrize("statement", WRITES)
def test_every_write_of_either_role_fails(connect, superuser, role, statement):
    before = superuser.execute("SELECT (SELECT count(*) FROM centinela.pagos), (SELECT count(*) FROM centinela.bodegas)").fetchone()
    with connect(role) as conn:
        fails(conn, statement)
    assert superuser.execute("SELECT (SELECT count(*) FROM centinela.pagos), (SELECT count(*) FROM centinela.bodegas)").fetchone() == before


@pytest.mark.parametrize("role", ["lector", "kernel"])
def test_neither_login_role_can_become_the_owner(connect, role):
    with connect(role) as conn:
        fails(conn, "SET ROLE centinela_propietario")
