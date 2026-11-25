"""Pruebas de la HU-014: cancelar una reserva registrada."""

from fastapi.testclient import TestClient

from app.api import reserva_router
from app.domain.reserva import EstadoReserva
from main import app
from tests.test_reservas import _crear_cliente, _crear_habitacion, _reservar

client = TestClient(app)
URL = "/api/v1/reservas"


def _crear_reserva(habitacion_id: int | None = None) -> int:
    respuesta = _reservar(_crear_cliente(), habitacion_id or _crear_habitacion(), 5, 8)
    assert respuesta.status_code == 201
    return respuesta.json()["reservaId"]


# ------------------------- Casos de la historia -------------------------

def test_caso1_cancelar_reserva_activa_retorna_200():
    reserva_id = _crear_reserva()

    respuesta = client.put(f"{URL}/{reserva_id}")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"mensaje": "Reserva cancelada correctamente", "success": True}


def test_caso2_cancelar_reserva_inexistente_retorna_404():
    respuesta = client.put(f"{URL}/999999")

    assert respuesta.status_code == 404
    assert respuesta.json() == {"mensaje": "Reserva no encontrada", "success": False}


def test_caso3_respuesta_exitosa_contiene_mensaje_y_success():
    body = client.put(f"{URL}/{_crear_reserva()}").json()

    assert set(body.keys()) == {"mensaje", "success"}


# --------------------------- Reglas de negocio ---------------------------

def test_reserva_queda_en_estado_cancelada():
    reserva_id = _crear_reserva()

    client.put(f"{URL}/{reserva_id}")

    assert reserva_router.repo.get_by_id(reserva_id).estado == EstadoReserva.cancelada


def test_cancelar_libera_la_habitacion_para_esas_fechas():
    habitacion = _crear_habitacion()
    reserva_id = _crear_reserva(habitacion)
    assert _reservar(_crear_cliente(), habitacion, 5, 8).status_code == 400

    client.put(f"{URL}/{reserva_id}")

    assert _reservar(_crear_cliente(), habitacion, 5, 8).status_code == 201


def test_cancelar_reserva_ya_cancelada_retorna_400():
    reserva_id = _crear_reserva()
    client.put(f"{URL}/{reserva_id}")

    respuesta = client.put(f"{URL}/{reserva_id}")

    assert respuesta.status_code == 400
    assert respuesta.json() == {"mensaje": "La reserva ya se encuentra cancelada", "success": False}
