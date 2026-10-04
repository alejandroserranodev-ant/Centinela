# Sign-in against the profiles of the root .env, replaced here by two profiles hashed with few
# iterations so the suite stays fast, and the signed token every other route reads its person from.
import pytest
from fastapi.testclient import TestClient

from centinela_api import auth
from centinela_api.main import app

CLAVE = "Andina2026!"


@pytest.fixture
def perfiles(monkeypatch):
    monkeypatch.setattr(auth, "ITERACIONES", 1000)
    cifrada = auth.cifrar(CLAVE, iteraciones=1000)
    monkeypatch.setattr(auth, "FICTICIA", auth.cifrar("nadie", iteraciones=1000))
    monkeypatch.setattr(auth, "PERFILES", auth.cargar(
        '[{"correo": "Gerente@andina.test", "nombre": "Mariana Restrepo", "rol": "gerente", "area": null, "clave": "%s"},'
        ' {"correo": "cartera@andina.test", "nombre": "Lucía Ospina", "rol": "lider_proceso", "area": "Analista de cartera", "clave": "%s"}]'
        % (cifrada, cifrada)
    ))
    return TestClient(app)


def _entrar(cliente, correo=" GERENTE@andina.test", clave=CLAVE):
    return cliente.post("/auth/login", json={"email": correo, "password": clave})


def test_cifrar_y_comprobar_son_un_viaje_de_ida_y_vuelta():
    cifrada = auth.cifrar(CLAVE, iteraciones=1000)
    assert cifrada.startswith("pbkdf2_sha256$1000$")
    assert auth.coincide(CLAVE, cifrada)
    assert not auth.coincide("otra", cifrada)
    assert auth.cifrar(CLAVE, iteraciones=1000) != cifrada


def test_el_alta_de_los_perfiles_rechaza_una_lista_mal_formada():
    with pytest.raises(RuntimeError, match="CENTINELA_USUARIOS"):
        auth.cargar('[{"correo": "a@b", "nombre": "A", "rol": "gerente", "clave": "Andina2026!"}]')
    with pytest.raises(RuntimeError, match="CENTINELA_USUARIOS"):
        auth.cargar("no es json")
    otra_cuenta = auth.cifrar(CLAVE, iteraciones=1000)
    with pytest.raises(RuntimeError, match="CENTINELA_USUARIOS"):
        auth.cargar('[{"correo": "a@b", "nombre": "A", "rol": "gerente", "clave": "%s"}]' % otra_cuenta)


def test_los_perfiles_del_env_cargan_con_la_clave_cifrada():
    assert {p.rol for p in auth.PERFILES.values()} == {"gerente", "lider_proceso", "analista", "auditor"}
    assert all(p.clave.startswith("pbkdf2_sha256$600000$") for p in auth.PERFILES.values())


def test_entrar_devuelve_un_token_y_la_persona(perfiles):
    respuesta = _entrar(perfiles)
    assert respuesta.status_code == 200
    assert respuesta.json()["persona"] == {"email": "gerente@andina.test", "name": "Mariana Restrepo", "role": "gerente", "area": None}
    sesion = perfiles.get("/auth/sesion", headers={"Authorization": f"Bearer {respuesta.json()['token']}"})
    assert sesion.status_code == 200
    assert sesion.json()["email"] == "gerente@andina.test"


def test_clave_errada_y_correo_desconocido_responden_igual(perfiles):
    errada = _entrar(perfiles, clave="otra")
    desconocido = _entrar(perfiles, correo="nadie@andina.test")
    assert errada.status_code == desconocido.status_code == 401
    assert errada.json() == desconocido.json() == {"detail": "Correo o contraseña incorrectos"}


def test_un_token_alterado_es_401(perfiles):
    token = _entrar(perfiles).json()["token"]
    carga, firma = token.split(".")
    otra = auth._b64(b'{"correo":"cartera@andina.test","exp":9999999999}')
    for alterado in (f"{otra}.{firma}", f"{carga}.{firma[:-2]}xx", carga, "basura"):
        respuesta = perfiles.get("/auth/sesion", headers={"Authorization": f"Bearer {alterado}"})
        assert respuesta.status_code == 401
        assert respuesta.headers["WWW-Authenticate"] == "Bearer"


def test_un_token_firmado_con_otra_clave_es_401(perfiles, monkeypatch):
    persona = auth.PERFILES["gerente@andina.test"].persona()
    propia = auth.AUTH_SECRET_KEY
    monkeypatch.setattr(auth, "AUTH_SECRET_KEY", b"la clave que alguien leyo en el repositorio")
    ajeno = auth.emitir(persona)
    monkeypatch.setattr(auth, "AUTH_SECRET_KEY", propia)
    assert auth.leer(ajeno) is None
    assert perfiles.get("/auth/sesion", headers={"Authorization": f"Bearer {ajeno}"}).status_code == 401


def test_sin_clave_en_el_entorno_la_firma_es_aleatoria():
    from centinela_api import config

    assert isinstance(config.AUTH_SECRET_KEY, bytes) and len(config.AUTH_SECRET_KEY) >= 32


def test_un_token_vencido_es_401(perfiles):
    persona = auth.PERFILES["gerente@andina.test"].persona()
    vencido = auth.emitir(persona, ahora=0)
    assert auth.leer(vencido) is None
    assert perfiles.get("/auth/sesion", headers={"Authorization": f"Bearer {vencido}"}).status_code == 401


def test_un_perfil_retirado_invalida_su_token(perfiles, monkeypatch):
    token = _entrar(perfiles).json()["token"]
    monkeypatch.setattr(auth, "PERFILES", {})
    assert perfiles.get("/auth/sesion", headers={"Authorization": f"Bearer {token}"}).status_code == 401


@pytest.mark.parametrize("ruta", ["/simulacion/dia-actual", "/alertas", "/alertas/x", "/bitacora", "/consultas/q"])
def test_una_ruta_protegida_sin_token_es_401(perfiles, ruta):
    respuesta = perfiles.get(ruta)
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": "Inicia sesión para continuar"}


def test_avanzar_decidir_y_preguntar_sin_token_son_401(perfiles):
    assert perfiles.post("/simulacion/avanzar").status_code == 401
    assert perfiles.post("/alertas/x/decision", json={"kind": "reject", "reason": "r"}).status_code == 401
    assert perfiles.post("/chat", json={"question": "¿Cuánto?"}).status_code == 401
