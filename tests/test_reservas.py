"""Pruebas de la HU-013: realizar una reserva de una habitación."""

from datetime import date, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
URL = "/api/v1/reservas/"


def _dia(dias: int) -> str:
    return (date.today() + timedelta(days=dias)).isoformat()


def _crear_cliente() -> int:
    respuesta = client.post("/api/v1/usuarios/", json={
        "nombre": "Laura Gómez", "email": f"cliente.{uuid4().hex[:8]}@correo.com",
        "password": "clave1234",
    })
    assert respuesta.status_code == 201
    return respuesta.json()["id"]


def _crear_habitacion(disponible: bool = True) -> int:
    hotel = client.post("/hoteles/", json={
        "nombre": f"Hotel {uuid4().hex[:8]}", "ciudad": "Bucaramanga",
        "direccion": "Calle 10 # 20-30", "estrellas": 4, "precio_noche": 250000,
    })
    assert hotel.status_code == 201
    habitacion = client.post("/habitaciones/", json={
        "hotel_id": hotel.json()["id"], "numero": "101", "tipo": "doble",
        "capacidad": 2, "precio_noche": 180000, "disponible": disponible,
    })
    assert habitacion.status_code == 201
    return habitacion.json()["id"]


def _reservar(usuario_id: int, habitacion_id: int, entrada: int, salida: int):
    return client.post(URL, json={
        "usuarioId": usuario_id, "habitacionId": habitacion_id,
        "fechaEntrada": _dia(entrada), "fechaSalida": _dia(salida),
    })


# ------------------------- Casos de la historia -------------------------

def test_caso1_reserva_habitacion_disponible_retorna_201():
    respuesta = _reservar(_crear_cliente(), _crear_habitacion(), 5, 8)

    assert respuesta.status_code == 201
    body = respuesta.json()
    assert body["mensaje"] == "Reserva creada correctamente"
    assert body["success"] is True
    assert isinstance(body["reservaId"], int)


def test_caso2_habitacion_con_reserva_activa_retorna_400():
    habitacion = _crear_habitacion()
    assert _reservar(_crear_cliente(), habitacion, 10, 15).status_code == 201

    respuesta = _reservar(_crear_cliente(), habitacion, 12, 14)

    assert respuesta.status_code == 400
    assert respuesta.json() == {
        "mensaje": "La habitación no se encuentra disponible",
        "success": False,
    }


def test_caso3_respuesta_exitosa_contiene_reservaId_mensaje_success():
    body = _reservar(_crear_cliente(), _crear_habitacion(), 5, 6).json()

    assert set(body.keys()) == {"reservaId", "mensaje", "success"}


# ----------------------- Reglas de disponibilidad -----------------------

def test_cada_reserva_tiene_identificador_unico():
    cliente, habitacion = _crear_cliente(), _crear_habitacion()

    r1 = _reservar(cliente, habitacion, 5, 7).json()["reservaId"]
    r2 = _reservar(cliente, habitacion, 7, 9).json()["reservaId"]

    assert r1 != r2


def test_dia_de_salida_puede_ser_dia_de_entrada_de_otra_reserva():
    habitacion = _crear_habitacion()
    assert _reservar(_crear_cliente(), habitacion, 20, 22).status_code == 201

    respuesta = _reservar(_crear_cliente(), habitacion, 22, 25)

    assert respuesta.status_code == 201


def test_reserva_que_envuelve_a_otra_no_esta_disponible():
    habitacion = _crear_habitacion()
    assert _reservar(_crear_cliente(), habitacion, 30, 32).status_code == 201

    assert _reservar(_crear_cliente(), habitacion, 28, 35).status_code == 400


def test_misma_fecha_en_otra_habitacion_si_esta_disponible():
    cliente = _crear_cliente()
    assert _reservar(cliente, _crear_habitacion(), 5, 8).status_code == 201

    assert _reservar(cliente, _crear_habitacion(), 5, 8).status_code == 201


def test_habitacion_deshabilitada_no_esta_disponible():
    respuesta = _reservar(_crear_cliente(), _crear_habitacion(disponible=False), 5, 8)

    assert respuesta.status_code == 400
    assert respuesta.json()["mensaje"] == "La habitación no se encuentra disponible"


# --------------------------- Validaciones ---------------------------

def test_fecha_salida_anterior_o_igual_a_entrada_retorna_400():
    cliente, habitacion = _crear_cliente(), _crear_habitacion()

    for entrada, salida in [(5, 5), (8, 5)]:
        respuesta = _reservar(cliente, habitacion, entrada, salida)
        assert respuesta.status_code == 400
        assert "posterior a la fecha de entrada" in respuesta.json()["mensaje"]


def test_fecha_entrada_en_el_pasado_retorna_400():
    respuesta = _reservar(_crear_cliente(), _crear_habitacion(), -2, 3)

    assert respuesta.status_code == 400
    assert "anterior a la fecha actual" in respuesta.json()["mensaje"]


def test_habitacion_inexistente_retorna_404():
    respuesta = _reservar(_crear_cliente(), 99999, 5, 8)

    assert respuesta.status_code == 404
    assert respuesta.json() == {"mensaje": "La habitación indicada no existe", "success": False}


def test_cliente_inexistente_retorna_404():
    respuesta = _reservar(99999, _crear_habitacion(), 5, 8)

    assert respuesta.status_code == 404
    assert respuesta.json() == {"mensaje": "El cliente indicado no existe", "success": False}
