from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _registrar_usuario(email: str) -> dict:
    respuesta = client.post(
        "/api/v1/usuarios/",
        json={"nombre": "laura gómez", "email": email, "password": "clave1234"},
    )
    assert respuesta.status_code == 201
    return respuesta.json()


def test_consultar_usuario_existente_retorna_200():
    """Caso 1: existe un usuario registrado y se consulta por su ID."""
    usuario = _registrar_usuario("laura.gomez@correo.com")

    respuesta = client.get(f"/api/v1/usuarios/{usuario['id']}")

    assert respuesta.status_code == 200
    body = respuesta.json()
    assert body["mensaje"] == "Usuario encontrado"
    assert body["success"] is True
    assert body["data"] == {
        "id": usuario["id"],
        "nombre": "Laura Gómez",
        "correo": "laura.gomez@correo.com",
    }


def test_consultar_usuario_inexistente_retorna_404():
    """Caso 2: se consulta un ID que no existe."""
    respuesta = client.get("/api/v1/usuarios/99999")

    assert respuesta.status_code == 404
    assert respuesta.json() == {
        "mensaje": "Usuario no encontrado",
        "data": None,
        "success": False,
    }


def test_consulta_exitosa_solo_contiene_id_nombre_correo():
    """Caso 3: la respuesta contiene id, nombre y correo (y nunca la contraseña)."""
    usuario = _registrar_usuario("otro.usuario@correo.com")

    data = client.get(f"/api/v1/usuarios/{usuario['id']}").json()["data"]

    assert set(data.keys()) == {"id", "nombre", "correo"}
