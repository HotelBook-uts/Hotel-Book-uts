"""Pruebas de la HU-002: inicio y cierre de sesión con control de intentos."""

from datetime import datetime
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.api import dependencias
from app.core.config import settings
from app.core.security import crear_token, hash_password
from app.domain.auth import LoginRequest
from app.domain.errores import (CredencialesInvalidasError, CuentaBloqueadaError,
                                CuentaNoActivaError, RepositorioNoDisponibleError,
                                TokenInvalidoError)
from app.domain.usuario import EstadoCuenta, Rol, UsuarioCreate
from app.repositories.intento_acceso_repository import IntentoAccesoRepository
from app.repositories.sesion_repository import SesionRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.service.auth_service import AuthService
from main import app

client = TestClient(app)
LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
CLAVE = "clave1234"


def _registrar() -> dict:
    correo = f"cliente.{uuid4().hex[:8]}@correo.com"
    respuesta = client.post("/api/v1/usuarios/", json={
        "nombre": "Laura Gómez", "email": correo, "password": CLAVE})
    assert respuesta.status_code == 201
    return respuesta.json()


def _login(correo: str, contrasena: str = CLAVE):
    return client.post(LOGIN, json={"correo": correo, "contrasena": contrasena})


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# =========================== Casos de la historia ===========================

def test_caso1_login_correcto_retorna_token_jwt_con_rol_cliente():
    usuario = _registrar()

    respuesta = _login(usuario["email"])

    assert respuesta.status_code == 200
    body = respuesta.json()
    assert "Inicio de sesión exitoso" in body["mensaje"]
    assert body["success"] is True
    assert body["data"]["correo"] == usuario["email"]
    assert body["data"]["rol"] == "CLIENTE"
    payload = jwt.decode(body["data"]["token"], settings.SECRET_KEY, algorithms=["HS256"])
    assert payload["sub"] == str(usuario["id"])
    assert payload["rol"] == "CLIENTE"


def test_caso2_correo_sin_cuenta_activa_retorna_401():
    respuesta = _login("sin.cuenta@correo.com")

    assert respuesta.status_code == 401
    assert respuesta.json() == {
        "mensaje": "No existe una cuenta activa con el correo indicado",
        "data": {"correo": "sin.cuenta@correo.com", "token": None, "rol": None, "expiraEn": None},
        "success": False,
    }


def test_caso3_respuesta_exitosa_cumple_el_contrato():
    body = _login(_registrar()["email"]).json()

    assert set(body.keys()) == {"mensaje", "data", "success"}
    assert set(body["data"].keys()) == {"correo", "token", "rol", "expiraEn"}
    for campo in ("token", "rol", "expiraEn"):
        assert isinstance(body["data"][campo], str)
    assert isinstance(body["mensaje"], str)
    # expiraEn en formato ISO 8601 UTC, ej. 2026-11-09T18:00:00Z
    datetime.strptime(body["data"]["expiraEn"], "%Y-%m-%dT%H:%M:%SZ")


def test_caso4_correo_con_formato_incorrecto_retorna_400():
    respuesta = _login("laura.gomez")

    assert respuesta.status_code == 400
    body = respuesta.json()
    assert "No fue posible iniciar sesión." in body["mensaje"]
    assert "Formato de correo no válido. Debe ser usuario@dominio.com" in body["mensaje"]
    assert body["success"] is False
    assert body["data"] == {"correo": "laura.gomez", "token": None, "rol": None, "expiraEn": None}


def test_caso5_bd_no_disponible_retorna_503(monkeypatch):
    def falla(*_):
        raise RepositorioNoDisponibleError("sin conexión")

    monkeypatch.setattr(dependencias.usuario_repo, "get_by_email", falla)

    respuesta = _login("laura.gomez@correo.com")

    assert respuesta.status_code == 503
    assert "No fue posible iniciar la sesión" in respuesta.json()["mensaje"]


# ======================= Intentos fallidos y bloqueo =======================

def test_contrasena_incorrecta_retorna_401_con_intentos_restantes():
    usuario = _registrar()

    respuesta = _login(usuario["email"], "otraClave99")

    assert respuesta.status_code == 401
    assert "Correo o contraseña incorrectos" in respuesta.json()["mensaje"]
    assert f"Intentos restantes: {settings.MAX_INTENTOS_FALLIDOS - 1}" in respuesta.json()["mensaje"]
    assert respuesta.json()["data"]["token"] is None


def test_cuenta_se_bloquea_al_superar_intentos_fallidos():
    usuario = _registrar()
    for _ in range(settings.MAX_INTENTOS_FALLIDOS - 1):
        assert _login(usuario["email"], "otraClave99").status_code == 401

    respuesta = _login(usuario["email"], "otraClave99")

    assert respuesta.status_code == 403
    assert "bloqueada" in respuesta.json()["mensaje"]
    assert dependencias.usuario_repo.get_by_id(usuario["id"]).estado == EstadoCuenta.BLOQUEADA


def test_cuenta_bloqueada_no_entra_ni_con_la_contrasena_correcta():
    usuario = _registrar()
    for _ in range(settings.MAX_INTENTOS_FALLIDOS):
        _login(usuario["email"], "otraClave99")

    respuesta = _login(usuario["email"], CLAVE)

    assert respuesta.status_code == 403
    assert respuesta.json()["data"]["token"] is None


def test_login_exitoso_reinicia_el_contador_de_intentos():
    usuario = _registrar()
    for _ in range(settings.MAX_INTENTOS_FALLIDOS - 1):
        _login(usuario["email"], "otraClave99")

    assert _login(usuario["email"]).status_code == 200

    assert dependencias.usuario_repo.get_by_id(usuario["id"]).intentos_fallidos == 0
    assert _login(usuario["email"], "otraClave99").status_code == 401  # no se bloquea aún


def test_cada_intento_queda_registrado_en_intentos_acceso():
    usuario = _registrar()
    _login(usuario["email"], "otraClave99")
    _login(usuario["email"])

    intentos = dependencias.intento_repo.get_by_correo(usuario["email"])

    assert [i.exitoso for i in intentos] == [False, True]
    assert all(i.usuarioId == usuario["id"] for i in intentos)


def test_cuenta_inactiva_no_puede_iniciar_sesion():
    usuario = _registrar()
    dependencias.usuario_repo.update_seguridad(usuario["id"], 0, EstadoCuenta.INACTIVA)

    respuesta = _login(usuario["email"])

    assert respuesta.status_code == 401
    assert respuesta.json()["mensaje"] == "No existe una cuenta activa con el correo indicado"


def test_login_acepta_correo_en_mayusculas():
    usuario = _registrar()

    assert _login(usuario["email"].upper()).status_code == 200


# ============================= Cierre de sesión =============================

def test_logout_invalida_el_token():
    token = _login(_registrar()["email"]).json()["data"]["token"]

    respuesta = client.post(LOGOUT, headers=_bearer(token))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"mensaje": "Sesión cerrada correctamente", "success": True}
    # El mismo token ya no sirve
    segunda = client.post(LOGOUT, headers=_bearer(token))
    assert segunda.status_code == 401
    assert "Inicie sesión nuevamente" in segunda.json()["mensaje"]


def test_logout_sin_token_retorna_401():
    respuesta = client.post(LOGOUT)

    assert respuesta.status_code == 401
    assert respuesta.json()["mensaje"] == "Debe iniciar sesión para realizar esta operación"


def test_token_alterado_retorna_401():
    token = _login(_registrar()["email"]).json()["data"]["token"]

    assert client.post(LOGOUT, headers=_bearer(token[:-3] + "abc")).status_code == 401


def test_token_expirado_retorna_401():
    usuario = _registrar()
    token, _, _ = crear_token(usuario["id"], "CLIENTE", minutos=-1)

    assert client.post(LOGOUT, headers=_bearer(token)).status_code == 401


def test_nuevo_login_despues_de_logout_funciona():
    usuario = _registrar()
    token = _login(usuario["email"]).json()["data"]["token"]
    client.post(LOGOUT, headers=_bearer(token))

    nuevo = _login(usuario["email"]).json()["data"]["token"]

    assert client.post(LOGOUT, headers=_bearer(nuevo)).status_code == 200


# ======================= Pruebas unitarias (servicio) =======================

@pytest.fixture
def auth():
    usuarios, intentos, sesiones = UsuarioRepository(), IntentoAccesoRepository(), SesionRepository()
    service = AuthService(usuarios, intentos, sesiones, max_intentos=3)
    usuario = usuarios.create(
        UsuarioCreate(nombre="Laura Gómez", email="laura@correo.com", password=CLAVE),
        hash_password(CLAVE))
    return service, usuarios, intentos, usuario


def _req(contrasena: str = CLAVE, correo: str = "laura@correo.com") -> LoginRequest:
    return LoginRequest(correo=correo, contrasena=contrasena)


def test_unit_credenciales_correctas_entregan_token_con_rol(auth):
    service, usuarios, _, usuario = auth
    usuarios._db[usuario.id] = usuario.model_copy(update={"rol": Rol.ADMINISTRADOR})

    sesion = service.login(_req())

    assert sesion.rol == Rol.ADMINISTRADOR
    assert service.validar_token(sesion.token).rol == Rol.ADMINISTRADOR


def test_unit_cuenta_inexistente(auth):
    service, *_ = auth

    with pytest.raises(CuentaNoActivaError):
        service.login(_req(correo="nadie@correo.com"))


def test_unit_cuenta_el_numero_de_intentos_fallidos(auth):
    service, usuarios, _, usuario = auth

    with pytest.raises(CredencialesInvalidasError) as primero:
        service.login(_req("mala1234"))
    with pytest.raises(CredencialesInvalidasError) as segundo:
        service.login(_req("mala1234"))

    assert primero.value.intentos_restantes == 2
    assert segundo.value.intentos_restantes == 1
    assert usuarios.get_by_id(usuario.id).intentos_fallidos == 2


def test_unit_bloquea_al_llegar_al_maximo(auth):
    service, usuarios, intentos, usuario = auth
    for _ in range(2):
        with pytest.raises(CredencialesInvalidasError):
            service.login(_req("mala1234"))

    with pytest.raises(CuentaBloqueadaError):
        service.login(_req("mala1234"))

    assert usuarios.get_by_id(usuario.id).estado == EstadoCuenta.BLOQUEADA
    assert intentos.get_by_correo("laura@correo.com")[-1].motivo == "Cuenta bloqueada por intentos fallidos"


def test_unit_token_revocado_no_es_valido(auth):
    service, *_ = auth
    token = service.login(_req()).token
    sesion = service.validar_token(token)

    service.logout(sesion)

    with pytest.raises(TokenInvalidoError):
        service.validar_token(token)


def test_unit_token_de_cuenta_bloqueada_deja_de_servir(auth):
    service, usuarios, _, usuario = auth
    token = service.login(_req()).token
    usuarios.update_seguridad(usuario.id, 3, EstadoCuenta.BLOQUEADA)

    with pytest.raises(TokenInvalidoError):
        service.validar_token(token)
