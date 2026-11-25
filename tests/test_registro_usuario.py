"""Pruebas de la HU-001: registro de usuario."""

import pytest

from app.api import dependencias, usuario_router
from app.domain.errores import RepositorioNoDisponibleError
from app.domain.usuario import EstadoCuenta, Rol
from tests.helpers import client, correo_unico

URL = "/api/v1/usuarios/"


def _datos(**cambios) -> dict:
    return {"nombre": "  laura gómez ", "email": correo_unico(), "password": "clave1234",
            "telefono": "3109876543", **cambios}


def test_registro_exitoso_retorna_201_con_formato_estandar():
    datos = _datos(email="Laura.Registro@Correo.com")

    respuesta = client.post(URL, json=datos)

    assert respuesta.status_code == 201
    body = respuesta.json()
    assert body["mensaje"] == "Usuario registrado correctamente"
    assert body["success"] is True
    assert set(body.keys()) == {"mensaje", "data", "success"}
    assert set(body["data"].keys()) == {"id", "nombre", "email", "telefono"}
    assert body["data"]["nombre"] == "Laura Gómez"                     # limpio y con formato
    assert body["data"]["email"] == "laura.registro@correo.com"        # en minúsculas
    assert isinstance(body["data"]["id"], int)


def test_registro_no_devuelve_la_contrasena():
    texto = client.post(URL, json=_datos()).text

    assert "password" not in texto
    assert "clave1234" not in texto


def test_usuario_nuevo_queda_como_cliente_activo_con_contrasena_cifrada():
    usuario_id = client.post(URL, json=_datos()).json()["data"]["id"]

    guardado = dependencias.usuario_repo.get_by_id(usuario_id)

    assert guardado.rol == Rol.CLIENTE
    assert guardado.estado == EstadoCuenta.ACTIVA
    assert guardado.password_hash != "clave1234"


def test_telefono_es_opcional():
    datos = _datos()
    del datos["telefono"]

    respuesta = client.post(URL, json=datos)

    assert respuesta.status_code == 201
    assert respuesta.json()["data"]["telefono"] is None


def test_correo_repetido_retorna_409():
    correo = correo_unico()
    client.post(URL, json=_datos(email=correo))

    respuesta = client.post(URL, json=_datos(email=correo.upper()))

    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "mensaje": "No fue posible registrar el usuario. Ya existe un usuario registrado con ese correo",
        "data": None,
        "success": False,
    }


@pytest.mark.parametrize("correo", ["laura.gomez", "laura@", "@correo.com"])
def test_correo_con_formato_incorrecto_retorna_400(correo):
    respuesta = client.post(URL, json=_datos(email=correo))

    assert respuesta.status_code == 400
    body = respuesta.json()
    assert body["mensaje"] == ("No fue posible registrar el usuario. "
                               "Formato de correo no válido. Debe ser usuario@dominio.com")
    assert body["data"] is None
    assert body["success"] is False


@pytest.mark.parametrize("password", ["solotexto", "12345678"])
def test_contrasena_sin_letra_o_sin_numero_retorna_400(password):
    respuesta = client.post(URL, json=_datos(password=password))

    assert respuesta.status_code == 400
    assert "La contraseña debe contener al menos una letra y un número" in respuesta.json()["mensaje"]


def test_contrasena_corta_retorna_400():
    respuesta = client.post(URL, json=_datos(password="abc1"))

    assert respuesta.status_code == 400
    assert respuesta.json()["mensaje"].startswith("No fue posible registrar el usuario.")
    assert "password" in respuesta.json()["mensaje"]


def test_telefono_invalido_retorna_400():
    respuesta = client.post(URL, json=_datos(telefono="abc"))

    assert respuesta.status_code == 400
    assert "telefono" in respuesta.json()["mensaje"]


def test_bd_no_disponible_retorna_503(monkeypatch):
    def falla(*_):
        raise RepositorioNoDisponibleError("sin conexión")

    monkeypatch.setattr(usuario_router.service.repo, "get_by_email", falla)

    respuesta = client.post(URL, json=_datos())

    assert respuesta.status_code == 503
    assert respuesta.json()["success"] is False


def test_varios_errores_salen_juntos_y_en_espanol():
    respuesta = client.post(URL, json={"nombre": "x", "email": "malo", "password": "1"})

    assert respuesta.status_code == 400
    assert respuesta.json()["mensaje"] == (
        "No fue posible registrar el usuario. nombre: debe tener al menos 2 caracteres. "
        "Formato de correo no válido. Debe ser usuario@dominio.com. "
        "password: debe tener al menos 8 caracteres")


def test_campos_obligatorios_faltantes_retorna_400():
    respuesta = client.post(URL, json={"nombre": "Laura Gómez"})

    assert respuesta.status_code == 400
    assert respuesta.json()["mensaje"] == (
        "No fue posible registrar el usuario. email: es obligatorio. password: es obligatorio")
