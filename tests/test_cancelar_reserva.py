"""Pruebas de la HU-014: cancelar una reserva registrada."""

from app.api import reserva_router
from app.domain.reserva import EstadoReserva
from tests.helpers import Cuenta, client, crear_admin, crear_cliente, crear_habitacion, reservar

URL = "/api/v1/reservas"


def _crear_reserva(cliente: Cuenta, habitacion_id: int | None = None) -> int:
    respuesta = reservar(cliente, habitacion_id or crear_habitacion(), 5, 8)
    assert respuesta.status_code == 201
    return respuesta.json()["reservaId"]


def _cancelar(cuenta: Cuenta, reserva_id: int):
    return client.put(f"{URL}/{reserva_id}", headers=cuenta.headers)


# ------------------------- Casos de la historia -------------------------

def test_caso1_cancelar_reserva_activa_retorna_200():
    cliente = crear_cliente()

    respuesta = _cancelar(cliente, _crear_reserva(cliente))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"mensaje": "Reserva cancelada correctamente", "success": True}


def test_caso2_cancelar_reserva_inexistente_retorna_404():
    respuesta = _cancelar(crear_cliente(), 999999)

    assert respuesta.status_code == 404
    assert respuesta.json() == {"mensaje": "Reserva no encontrada", "success": False}


def test_caso3_respuesta_exitosa_contiene_mensaje_y_success():
    cliente = crear_cliente()

    body = _cancelar(cliente, _crear_reserva(cliente)).json()

    assert set(body.keys()) == {"mensaje", "success"}


# --------------------------- Reglas de negocio ---------------------------

def test_reserva_queda_en_estado_cancelada():
    cliente = crear_cliente()
    reserva_id = _crear_reserva(cliente)

    _cancelar(cliente, reserva_id)

    assert reserva_router.repo.get_by_id(reserva_id).estado == EstadoReserva.cancelada


def test_cancelar_libera_la_habitacion_para_esas_fechas():
    cliente, otro = crear_cliente(), crear_cliente()
    habitacion = crear_habitacion()
    reserva_id = _crear_reserva(cliente, habitacion)
    assert reservar(otro, habitacion, 5, 8).status_code == 400

    _cancelar(cliente, reserva_id)

    assert reservar(otro, habitacion, 5, 8).status_code == 201


def test_cancelar_reserva_ya_cancelada_retorna_400():
    cliente = crear_cliente()
    reserva_id = _crear_reserva(cliente)
    _cancelar(cliente, reserva_id)

    respuesta = _cancelar(cliente, reserva_id)

    assert respuesta.status_code == 400
    assert respuesta.json() == {"mensaje": "La reserva ya se encuentra cancelada", "success": False}


# ------------------------- Permisos de sesión (HU-002) -------------------------

def test_cancelar_sin_token_retorna_401():
    reserva_id = _crear_reserva(crear_cliente())

    assert client.put(f"{URL}/{reserva_id}").status_code == 401


def test_cliente_no_puede_cancelar_reserva_de_otro_403():
    dueno, otro = crear_cliente(), crear_cliente()
    reserva_id = _crear_reserva(dueno)

    respuesta = _cancelar(otro, reserva_id)

    assert respuesta.status_code == 403
    assert "Un cliente solo puede cancelar sus propias reservas" in respuesta.json()["mensaje"]
    assert reserva_router.repo.get_by_id(reserva_id).estado == EstadoReserva.activa


def test_administrador_puede_cancelar_cualquier_reserva():
    reserva_id = _crear_reserva(crear_cliente())

    assert _cancelar(crear_admin(), reserva_id).status_code == 200
