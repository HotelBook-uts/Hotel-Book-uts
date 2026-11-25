"""Pruebas de la HU-005: historial de reservas del cliente."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.api import reserva_router
from app.domain.errores import RepositorioNoDisponibleError, UsuarioNoEncontradoError
from app.domain.habitacion import HabitacionCreate
from app.domain.hotel import HotelCreate
from app.domain.reserva import EstadoHistorial, EstadoReserva, Reserva
from app.domain.usuario import UsuarioCreate
from app.repositories.habitacion_repository import HabitacionRepository
from app.repositories.hotel_repository import HotelRepository
from app.repositories.reserva_repository import ReservaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.service.reserva_service import ReservaService
from main import app
from tests.test_reservas import _crear_cliente, _crear_habitacion, _reservar

client = TestClient(app)


def _url(usuario_id: int) -> str:
    return f"/api/v1/usuarios/{usuario_id}/reservas"


# =========================== Pruebas funcionales (API) ===========================

def test_caso1_cliente_con_2_reservas_retorna_historial_200():
    cliente = _crear_cliente()
    _reservar(cliente, _crear_habitacion(), 10, 12)
    mas_reciente = _reservar(cliente, _crear_habitacion(), 40, 42).json()["reservaId"]

    respuesta = client.get(_url(cliente))

    assert respuesta.status_code == 200
    body = respuesta.json()
    assert "Historial de reservas consultado" in body["mensaje"]
    assert body["success"] is True
    assert body["data"]["usuarioId"] == cliente
    assert body["data"]["totalReservas"] == 2
    assert body["data"]["ultimaReserva"] == f"RSV-{date.today().year}-{mas_reciente:06d}"


def test_caso2_cliente_sin_reservas_retorna_200_vacio():
    cliente = _crear_cliente()

    respuesta = client.get(_url(cliente))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "mensaje": "El cliente no tiene reservas registradas",
        "data": {"usuarioId": cliente, "totalReservas": 0,
                 "ultimaReserva": None, "reservas": []},
        "success": False,
    }


def test_caso3_respuesta_exitosa_cumple_el_contrato():
    cliente = _crear_cliente()
    _reservar(cliente, _crear_habitacion(), 5, 7)

    body = client.get(_url(cliente)).json()

    assert set(body.keys()) == {"mensaje", "data", "success"}
    assert set(body["data"].keys()) == {"usuarioId", "totalReservas", "ultimaReserva", "reservas"}
    assert isinstance(body["mensaje"], str)
    assert isinstance(body["data"]["totalReservas"], int)
    assert isinstance(body["data"]["ultimaReserva"], str)
    assert isinstance(body["data"]["reservas"], list)
    assert set(body["data"]["reservas"][0].keys()) == {"reservaId", "hotel", "fechaEntrada", "estado"}


@pytest.mark.skip(reason="Requiere HU-002 (inicio de sesión con token) para identificar al cliente")
def test_caso4_cliente_consulta_reservas_de_otro_retorna_403():
    respuesta = client.get(_url(1030))  # con el token del cliente 1024

    assert respuesta.status_code == 403
    assert "No fue posible consultar el historial de reservas." in respuesta.json()["mensaje"]
    assert "Un cliente solo puede consultar sus propias reservas" in respuesta.json()["mensaje"]


def test_caso5_bd_no_disponible_retorna_503(monkeypatch):
    def falla(*_):
        raise RepositorioNoDisponibleError("sin conexión")

    monkeypatch.setattr(reserva_router.repo, "get_by_usuario", falla)

    respuesta = client.get(_url(_crear_cliente()))

    assert respuesta.status_code == 503
    assert "No fue posible consultar el historial de reservas" in respuesta.json()["mensaje"]


def test_cliente_inexistente_retorna_404():
    respuesta = client.get(_url(99999))

    assert respuesta.status_code == 404
    assert respuesta.json()["mensaje"] == "No existe un cliente con el identificador indicado"


def test_filtro_por_estado_desde_la_api():
    cliente = _crear_cliente()
    _reservar(cliente, _crear_habitacion(), 5, 7)
    cancelada = _reservar(cliente, _crear_habitacion(), 9, 11).json()["reservaId"]
    client.put(f"/api/v1/reservas/{cancelada}")

    confirmadas = client.get(_url(cliente), params={"estado": "CONFIRMADA"}).json()["data"]
    canceladas = client.get(_url(cliente), params={"estado": "CANCELADA"}).json()["data"]

    assert confirmadas["totalReservas"] == 1
    assert confirmadas["reservas"][0]["estado"] == "CONFIRMADA"
    assert canceladas["totalReservas"] == 1
    assert canceladas["reservas"][0]["estado"] == "CANCELADA"


def test_estado_invalido_es_rechazado():
    assert client.get(_url(_crear_cliente()), params={"estado": "OTRO"}).status_code == 422


def test_historial_muestra_el_nombre_del_hotel():
    cliente = _crear_cliente()
    _reservar(cliente, _crear_habitacion(), 5, 7)

    reserva = client.get(_url(cliente)).json()["data"]["reservas"][0]

    assert reserva["hotel"].startswith("Hotel ")


# ======================= Pruebas unitarias (servicio) =======================

@pytest.fixture
def entorno():
    """Servicio con repositorios nuevos y vacíos, aislado de la API."""
    hoteles, habitaciones = HotelRepository(), HabitacionRepository()
    usuarios, reservas = UsuarioRepository(), ReservaRepository()
    service = ReservaService(reservas, habitaciones, usuarios, hoteles)

    cliente = usuarios.create(
        UsuarioCreate(nombre="Laura Gómez", email="laura@correo.com", password="clave1234"),
        "hash").id
    chicamocha = hoteles.create(HotelCreate(nombre="Hotel Chicamocha", ciudad="Bucaramanga",
                                            direccion="Calle 1 # 2-3", estrellas=4,
                                            precio_noche=200000)).id
    bonita = hoteles.create(HotelCreate(nombre="Hotel Ciudad Bonita", ciudad="Bucaramanga",
                                        direccion="Calle 4 # 5-6", estrellas=5,
                                        precio_noche=300000)).id
    hab_a = habitaciones.create(HabitacionCreate(hotel_id=chicamocha, numero="101", tipo="doble",
                                                 capacidad=2, precio_noche=150000)).id
    hab_b = habitaciones.create(HabitacionCreate(hotel_id=bonita, numero="201", tipo="suite",
                                                 capacidad=2, precio_noche=250000)).id

    def agregar(habitacion_id: int, entrada: int, salida: int,
                estado: EstadoReserva = EstadoReserva.activa, usuario_id: int = cliente) -> Reserva:
        hoy = date.today()
        reserva = Reserva(id=reservas._next_id, usuarioId=usuario_id, habitacionId=habitacion_id,
                          fechaEntrada=hoy + timedelta(days=entrada),
                          fechaSalida=hoy + timedelta(days=salida), estado=estado)
        reservas._db[reserva.id] = reserva
        reservas._next_id += 1
        return reserva

    return service, cliente, hab_a, hab_b, agregar, habitaciones


def test_unit_ordena_de_la_mas_reciente_a_la_mas_antigua(entorno):
    service, cliente, hab_a, hab_b, agregar, _ = entorno
    vieja = agregar(hab_b, -120, -117)
    nueva = agregar(hab_a, 20, 23)
    media = agregar(hab_a, 5, 7)

    historial = service.historial(cliente)

    assert [r.reservaId for r in historial.reservas] == [nueva.codigo, media.codigo, vieja.codigo]
    assert historial.ultimaReserva == nueva.codigo
    assert historial.totalReservas == 3


def test_unit_estados_confirmada_finalizada_y_cancelada(entorno):
    service, cliente, hab_a, hab_b, agregar, _ = entorno
    agregar(hab_a, 10, 12)                                  # futura
    agregar(hab_b, -30, -28)                                # ya pasó
    agregar(hab_a, 40, 42, estado=EstadoReserva.cancelada)  # cancelada

    estados = {r.fechaEntrada: r.estado for r in service.historial(cliente).reservas}

    hoy = date.today()
    assert estados[hoy + timedelta(days=10)] == EstadoHistorial.CONFIRMADA
    assert estados[hoy + timedelta(days=-30)] == EstadoHistorial.FINALIZADA
    assert estados[hoy + timedelta(days=40)] == EstadoHistorial.CANCELADA


def test_unit_filtra_por_estado(entorno):
    service, cliente, hab_a, hab_b, agregar, _ = entorno
    agregar(hab_a, 10, 12)
    finalizada = agregar(hab_b, -30, -28)

    historial = service.historial(cliente, EstadoHistorial.FINALIZADA)

    assert historial.totalReservas == 1
    assert historial.ultimaReserva == finalizada.codigo
    assert historial.reservas[0].hotel == "Hotel Ciudad Bonita"


def test_unit_solo_muestra_reservas_del_cliente(entorno):
    service, cliente, hab_a, _, agregar, _ = entorno
    agregar(hab_a, 10, 12)
    agregar(hab_a, 20, 22, usuario_id=999)  # reserva de otro cliente

    assert service.historial(cliente).totalReservas == 1


def test_unit_sin_reservas_retorna_historial_vacio(entorno):
    service, cliente, *_ = entorno

    historial = service.historial(cliente)

    assert historial.totalReservas == 0
    assert historial.ultimaReserva is None
    assert historial.reservas == []


def test_unit_cliente_inexistente_lanza_error(entorno):
    service, *_ = entorno

    with pytest.raises(UsuarioNoEncontradoError):
        service.historial(99999)


def test_unit_habitacion_eliminada_no_rompe_el_historial(entorno):
    service, cliente, hab_a, _, agregar, habitaciones = entorno
    agregar(hab_a, 10, 12)
    habitaciones.delete(hab_a)

    assert service.historial(cliente).reservas[0].hotel == "Hotel no disponible"


def test_unit_codigo_de_reserva_tiene_formato_rsv():
    reserva = Reserva(id=148, usuarioId=1, habitacionId=1, fechaEntrada=date(2026, 12, 12),
                      fechaSalida=date(2026, 12, 14), fechaCreacion=date(2026, 11, 25))

    assert reserva.codigo == "RSV-2026-000148"
