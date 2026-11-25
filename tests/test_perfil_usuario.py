"""Pruebas de la HU-004: consulta y actualización del perfil del cliente."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import usuario_router
from app.domain.errores import RepositorioNoDisponibleError
from main import app

client = TestClient(app)
URL = "/api/v1/usuarios"


def _correo() -> str:
    return f"cliente.{uuid4().hex[:8]}@correo.com"


def _registrar(nombre: str = "laura gómez", email: str | None = None,
               telefono: str | None = "3109876543") -> dict:
    respuesta = client.post(f"{URL}/", json={
        "nombre": nombre, "email": email or _correo(),
        "password": "clave1234", "telefono": telefono,
    })
    assert respuesta.status_code == 201
    return respuesta.json()


# ------------------------------- Consulta (GET) -------------------------------

def test_caso1_consultar_perfil_existente_retorna_200():
    usuario = _registrar(email="laura.gomez@correo.com")

    respuesta = client.get(f"{URL}/{usuario['id']}")

    assert respuesta.status_code == 200
    body = respuesta.json()
    assert "Perfil consultado correctamente" in body["mensaje"]
    assert body["success"] is True
    assert body["data"] == {
        "usuarioId": usuario["id"],
        "nombres": "Laura Gómez",
        "correo": "laura.gomez@correo.com",
        "telefono": "3109876543",
    }


def test_caso2_consultar_perfil_inexistente_retorna_404():
    respuesta = client.get(f"{URL}/99999")

    assert respuesta.status_code == 404
    assert respuesta.json() == {
        "mensaje": "No existe un cliente con el identificador indicado",
        "data": {"usuarioId": 99999, "nombres": None, "correo": None, "telefono": None},
        "success": False,
    }


def test_caso3_respuesta_contiene_exactamente_los_campos_del_contrato():
    usuario = _registrar()

    body = client.get(f"{URL}/{usuario['id']}").json()

    assert set(body.keys()) == {"mensaje", "data", "success"}
    assert set(body["data"].keys()) == {"usuarioId", "nombres", "correo", "telefono"}
    for campo in ("nombres", "correo", "telefono"):
        assert isinstance(body["data"][campo], str)
    assert isinstance(body["mensaje"], str)


def test_consulta_no_expone_datos_sensibles():
    usuario = _registrar()

    texto = client.get(f"{URL}/{usuario['id']}").text

    assert "password" not in texto
    assert "clave1234" not in texto


def test_caso5_bd_no_disponible_en_consulta_retorna_503(monkeypatch):
    def falla(*_):
        raise RepositorioNoDisponibleError("sin conexión")

    monkeypatch.setattr(usuario_router.repo, "get_by_id", falla)

    respuesta = client.get(f"{URL}/1")

    assert respuesta.status_code == 503
    assert "No fue posible consultar el perfil del cliente" in respuesta.json()["mensaje"]
    assert respuesta.json()["success"] is False


# ----------------------------- Actualización (PUT) ----------------------------

def test_actualizar_perfil_correctamente_retorna_200():
    usuario = _registrar()
    nuevo_correo = _correo()

    respuesta = client.put(f"{URL}/{usuario['id']}", json={
        "nombres": "laura gómez pérez", "correo": nuevo_correo.upper(), "telefono": "3001234567",
    })

    assert respuesta.status_code == 200
    body = respuesta.json()
    assert body["mensaje"] == "Perfil actualizado correctamente"
    assert body["success"] is True
    assert body["data"] == {
        "usuarioId": usuario["id"],
        "nombres": "Laura Gómez Pérez",
        "correo": nuevo_correo,
        "telefono": "3001234567",
    }
    # Los cambios quedan guardados
    assert client.get(f"{URL}/{usuario['id']}").json()["data"] == body["data"]


@pytest.mark.parametrize("correo", ["laura.gomez@", "sin-arroba.com", "a@b"])
def test_caso4_actualizar_con_correo_invalido_retorna_400(correo):
    usuario = _registrar()

    respuesta = client.put(f"{URL}/{usuario['id']}", json={
        "nombres": "Laura Gómez", "correo": correo, "telefono": "3109876543",
    })

    assert respuesta.status_code == 400
    body = respuesta.json()
    assert "No fue posible actualizar el perfil." in body["mensaje"]
    assert "Formato de correo no válido. Debe ser usuario@dominio.com" in body["mensaje"]
    assert body["success"] is False


def test_actualizar_con_correo_de_otro_usuario_retorna_409():
    otro = _registrar()
    usuario = _registrar()

    respuesta = client.put(f"{URL}/{usuario['id']}", json={
        "nombres": "Laura Gómez", "correo": otro["email"], "telefono": "3109876543",
    })

    assert respuesta.status_code == 409
    assert "El correo ya está registrado por otro usuario" in respuesta.json()["mensaje"]


def test_actualizar_manteniendo_su_propio_correo_retorna_200():
    usuario = _registrar()

    respuesta = client.put(f"{URL}/{usuario['id']}", json={
        "nombres": "Laura Gómez", "correo": usuario["email"], "telefono": "3109876543",
    })

    assert respuesta.status_code == 200


def test_actualizar_perfil_inexistente_retorna_404():
    respuesta = client.put(f"{URL}/99999", json={
        "nombres": "Laura Gómez", "correo": _correo(), "telefono": "3109876543",
    })

    assert respuesta.status_code == 404
    assert respuesta.json()["mensaje"] == "No existe un cliente con el identificador indicado"


def test_actualizar_no_modifica_la_contrasena():
    usuario = _registrar()
    hash_antes = usuario_router.repo.get_by_id(usuario["id"]).password_hash

    client.put(f"{URL}/{usuario['id']}", json={
        "nombres": "Laura Gómez", "correo": _correo(), "telefono": "3109876543",
    })

    assert usuario_router.repo.get_by_id(usuario["id"]).password_hash == hash_antes


def test_caso5_bd_no_disponible_en_actualizacion_retorna_503(monkeypatch):
    def falla(*_):
        raise RepositorioNoDisponibleError("sin conexión")

    monkeypatch.setattr(usuario_router.repo, "get_by_id", falla)

    respuesta = client.put(f"{URL}/1", json={
        "nombres": "Laura Gómez", "correo": _correo(), "telefono": "3109876543",
    })

    assert respuesta.status_code == 503
    assert "No fue posible actualizar el perfil del cliente" in respuesta.json()["mensaje"]


def test_registro_sigue_respondiendo_422_con_datos_invalidos():
    """La validación 400 personalizada aplica solo al PUT del perfil."""
    respuesta = client.post(f"{URL}/", json={"nombre": "x", "email": "malo", "password": "1"})

    assert respuesta.status_code == 422
