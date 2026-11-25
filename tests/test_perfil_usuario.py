"""Pruebas de la HU-004: consulta y actualización del perfil del cliente."""

import pytest

from app.api import usuario_router
from app.domain.errores import RepositorioNoDisponibleError
from tests.helpers import client, correo_unico, crear_admin, crear_cliente

URL = "/api/v1/usuarios"


def _datos(correo: str | None = None, **extra) -> dict:
    return {"nombres": "Laura Gómez", "correo": correo or correo_unico(),
            "telefono": "3109876543", **extra}


# ------------------------------- Consulta (GET) -------------------------------

def test_caso1_cliente_consulta_su_perfil_con_su_token_retorna_200():
    cliente = crear_cliente(email="laura.gomez@correo.com")

    respuesta = client.get(f"{URL}/{cliente.id}", headers=cliente.headers)

    assert respuesta.status_code == 200
    body = respuesta.json()
    assert "Perfil consultado correctamente" in body["mensaje"]
    assert body["success"] is True
    assert body["data"] == {
        "usuarioId": cliente.id,
        "nombres": "Laura Gómez",
        "correo": "laura.gomez@correo.com",
        "telefono": "3109876543",
    }


def test_caso2_perfil_inexistente_retorna_404():
    admin = crear_admin()

    respuesta = client.get(f"{URL}/99999", headers=admin.headers)

    assert respuesta.status_code == 404
    assert respuesta.json() == {
        "mensaje": "No existe un cliente con el identificador indicado",
        "data": {"usuarioId": 99999, "nombres": None, "correo": None, "telefono": None},
        "success": False,
    }


def test_caso3_respuesta_contiene_exactamente_los_campos_del_contrato():
    cliente = crear_cliente()

    body = client.get(f"{URL}/{cliente.id}", headers=cliente.headers).json()

    assert set(body.keys()) == {"mensaje", "data", "success"}
    assert set(body["data"].keys()) == {"usuarioId", "nombres", "correo", "telefono"}
    for campo in ("nombres", "correo", "telefono"):
        assert isinstance(body["data"][campo], str)
    assert isinstance(body["mensaje"], str)


def test_consulta_no_expone_datos_sensibles():
    cliente = crear_cliente()

    texto = client.get(f"{URL}/{cliente.id}", headers=cliente.headers).text

    assert "password" not in texto
    assert "clave1234" not in texto


def test_caso5_bd_no_disponible_en_consulta_retorna_503(monkeypatch):
    cliente = crear_cliente()

    def falla(*_):
        raise RepositorioNoDisponibleError("sin conexión")

    # Falla solo la consulta del perfil; la validación del token usa otra ruta
    monkeypatch.setattr(usuario_router.service, "repo", _RepoCaido(falla))

    respuesta = client.get(f"{URL}/{cliente.id}", headers=cliente.headers)

    assert respuesta.status_code == 503
    assert "No fue posible consultar el perfil del cliente" in respuesta.json()["mensaje"]
    assert respuesta.json()["success"] is False


class _RepoCaido:
    """Repositorio simulado que falla en cualquier operación."""

    def __init__(self, falla):
        self._falla = falla

    def __getattr__(self, _):
        return self._falla


# ------------------------- Permisos de sesión (HU-002) -------------------------

def test_consultar_sin_token_retorna_401():
    cliente = crear_cliente()

    respuesta = client.get(f"{URL}/{cliente.id}")

    assert respuesta.status_code == 401
    assert respuesta.json()["success"] is False


def test_cliente_no_puede_consultar_el_perfil_de_otro_403():
    cliente, otro = crear_cliente(), crear_cliente()

    respuesta = client.get(f"{URL}/{otro.id}", headers=cliente.headers)

    assert respuesta.status_code == 403
    assert "Un cliente solo puede consultar su propio perfil" in respuesta.json()["mensaje"]


def test_administrador_puede_consultar_cualquier_perfil():
    admin, cliente = crear_admin(), crear_cliente()

    assert client.get(f"{URL}/{cliente.id}", headers=admin.headers).status_code == 200


def test_cliente_no_puede_actualizar_el_perfil_de_otro_403():
    cliente, otro = crear_cliente(), crear_cliente()

    respuesta = client.put(f"{URL}/{otro.id}", headers=cliente.headers, json=_datos())

    assert respuesta.status_code == 403
    assert "Un cliente solo puede actualizar su propio perfil" in respuesta.json()["mensaje"]


def test_administrador_puede_actualizar_cualquier_perfil():
    admin, cliente = crear_admin(), crear_cliente()

    respuesta = client.put(f"{URL}/{cliente.id}", headers=admin.headers, json=_datos())

    assert respuesta.status_code == 200


# ----------------------------- Actualización (PUT) ----------------------------

def test_actualizar_perfil_correctamente_retorna_200():
    cliente = crear_cliente()
    nuevo_correo = correo_unico()

    respuesta = client.put(f"{URL}/{cliente.id}", headers=cliente.headers, json={
        "nombres": "laura gómez pérez", "correo": nuevo_correo.upper(), "telefono": "3001234567",
    })

    assert respuesta.status_code == 200
    body = respuesta.json()
    assert body["mensaje"] == "Perfil actualizado correctamente"
    assert body["success"] is True
    assert body["data"] == {
        "usuarioId": cliente.id,
        "nombres": "Laura Gómez Pérez",
        "correo": nuevo_correo,
        "telefono": "3001234567",
    }
    # Los cambios quedan guardados
    guardado = client.get(f"{URL}/{cliente.id}", headers=cliente.headers).json()["data"]
    assert guardado == body["data"]


@pytest.mark.parametrize("correo", ["laura.gomez@", "sin-arroba.com", "a@b"])
def test_caso4_actualizar_con_correo_invalido_retorna_400(correo):
    cliente = crear_cliente()

    respuesta = client.put(f"{URL}/{cliente.id}", headers=cliente.headers, json=_datos(correo))

    assert respuesta.status_code == 400
    body = respuesta.json()
    assert "No fue posible actualizar el perfil." in body["mensaje"]
    assert "Formato de correo no válido. Debe ser usuario@dominio.com" in body["mensaje"]
    assert body["success"] is False


def test_actualizar_con_correo_de_otro_usuario_retorna_409():
    otro, cliente = crear_cliente(), crear_cliente()

    respuesta = client.put(f"{URL}/{cliente.id}", headers=cliente.headers,
                           json=_datos(otro.email))

    assert respuesta.status_code == 409
    assert "El correo ya está registrado por otro usuario" in respuesta.json()["mensaje"]


def test_actualizar_manteniendo_su_propio_correo_retorna_200():
    cliente = crear_cliente()

    respuesta = client.put(f"{URL}/{cliente.id}", headers=cliente.headers,
                           json=_datos(cliente.email))

    assert respuesta.status_code == 200


def test_actualizar_perfil_inexistente_retorna_404():
    admin = crear_admin()

    respuesta = client.put(f"{URL}/99999", headers=admin.headers, json=_datos())

    assert respuesta.status_code == 404
    assert respuesta.json()["mensaje"] == "No existe un cliente con el identificador indicado"


def test_actualizar_no_modifica_la_contrasena():
    cliente = crear_cliente()
    hash_antes = usuario_router.repo.get_by_id(cliente.id).password_hash

    client.put(f"{URL}/{cliente.id}", headers=cliente.headers, json=_datos())

    assert usuario_router.repo.get_by_id(cliente.id).password_hash == hash_antes


def test_caso5_bd_no_disponible_en_actualizacion_retorna_503(monkeypatch):
    cliente = crear_cliente()

    def falla(*_):
        raise RepositorioNoDisponibleError("sin conexión")

    monkeypatch.setattr(usuario_router.service, "repo", _RepoCaido(falla))

    respuesta = client.put(f"{URL}/{cliente.id}", headers=cliente.headers, json=_datos())

    assert respuesta.status_code == 503
    assert "No fue posible actualizar el perfil del cliente" in respuesta.json()["mensaje"]


def test_registro_sigue_respondiendo_422_con_datos_invalidos():
    """La validación 400 personalizada aplica solo a los endpoints que lo piden."""
    respuesta = client.post(f"{URL}/", json={"nombre": "x", "email": "malo", "password": "1"})

    assert respuesta.status_code == 422
