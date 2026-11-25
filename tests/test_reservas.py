"""Pruebas de la HU-013: realizar una reserva de una habitación."""

from tests.helpers import client, crear_admin, crear_cliente, crear_habitacion, dia, reservar

URL = "/api/v1/reservas/"


# ------------------------- Casos de la historia -------------------------

def test_caso1_reserva_habitacion_disponible_retorna_201():
    respuesta = reservar(crear_cliente(), crear_habitacion(), 5, 8)

    assert respuesta.status_code == 201
    body = respuesta.json()
    assert body["mensaje"] == "Reserva creada correctamente"
    assert body["success"] is True
    assert isinstance(body["reservaId"], int)


def test_caso2_habitacion_con_reserva_activa_retorna_400():
    habitacion = crear_habitacion()
    assert reservar(crear_cliente(), habitacion, 10, 15).status_code == 201

    respuesta = reservar(crear_cliente(), habitacion, 12, 14)

    assert respuesta.status_code == 400
    assert respuesta.json() == {
        "mensaje": "La habitación no se encuentra disponible",
        "success": False,
    }


def test_caso3_respuesta_exitosa_contiene_reservaId_mensaje_success():
    body = reservar(crear_cliente(), crear_habitacion(), 5, 6).json()

    assert set(body.keys()) == {"reservaId", "mensaje", "success"}


# ----------------------- Reglas de disponibilidad -----------------------

def test_cada_reserva_tiene_identificador_unico():
    cliente, habitacion = crear_cliente(), crear_habitacion()

    r1 = reservar(cliente, habitacion, 5, 7).json()["reservaId"]
    r2 = reservar(cliente, habitacion, 7, 9).json()["reservaId"]

    assert r1 != r2


def test_dia_de_salida_puede_ser_dia_de_entrada_de_otra_reserva():
    habitacion = crear_habitacion()
    assert reservar(crear_cliente(), habitacion, 20, 22).status_code == 201

    respuesta = reservar(crear_cliente(), habitacion, 22, 25)

    assert respuesta.status_code == 201


def test_reserva_que_envuelve_a_otra_no_esta_disponible():
    habitacion = crear_habitacion()
    assert reservar(crear_cliente(), habitacion, 30, 32).status_code == 201

    assert reservar(crear_cliente(), habitacion, 28, 35).status_code == 400


def test_misma_fecha_en_otra_habitacion_si_esta_disponible():
    cliente = crear_cliente()
    assert reservar(cliente, crear_habitacion(), 5, 8).status_code == 201

    assert reservar(cliente, crear_habitacion(), 5, 8).status_code == 201


def test_habitacion_deshabilitada_no_esta_disponible():
    respuesta = reservar(crear_cliente(), crear_habitacion(disponible=False), 5, 8)

    assert respuesta.status_code == 400
    assert respuesta.json()["mensaje"] == "La habitación no se encuentra disponible"


# --------------------------- Validaciones ---------------------------

def test_fecha_salida_anterior_o_igual_a_entrada_retorna_400():
    cliente, habitacion = crear_cliente(), crear_habitacion()

    for entrada, salida in [(5, 5), (8, 5)]:
        respuesta = reservar(cliente, habitacion, entrada, salida)
        assert respuesta.status_code == 400
        assert "posterior a la fecha de entrada" in respuesta.json()["mensaje"]


def test_fecha_entrada_en_el_pasado_retorna_400():
    respuesta = reservar(crear_cliente(), crear_habitacion(), -2, 3)

    assert respuesta.status_code == 400
    assert "anterior a la fecha actual" in respuesta.json()["mensaje"]


def test_habitacion_inexistente_retorna_404():
    respuesta = reservar(crear_cliente(), 99999, 5, 8)

    assert respuesta.status_code == 404
    assert respuesta.json() == {"mensaje": "La habitación indicada no existe", "success": False}


def test_cliente_inexistente_retorna_404():
    respuesta = reservar(crear_admin(), crear_habitacion(), 5, 8, usuario_id=99999)

    assert respuesta.status_code == 404
    assert respuesta.json() == {"mensaje": "El cliente indicado no existe", "success": False}


# ------------------------- Permisos de sesión (HU-002) -------------------------

def test_reservar_sin_token_retorna_401():
    respuesta = client.post(URL, json={"usuarioId": 1, "habitacionId": 1,
                                       "fechaEntrada": dia(5), "fechaSalida": dia(8)})

    assert respuesta.status_code == 401


def test_cliente_no_puede_reservar_a_nombre_de_otro_403():
    cliente, otro = crear_cliente(), crear_cliente()

    respuesta = reservar(cliente, crear_habitacion(), 5, 8, usuario_id=otro.id)

    assert respuesta.status_code == 403
    assert "Un cliente solo puede reservar a su propio nombre" in respuesta.json()["mensaje"]


def test_administrador_puede_reservar_por_un_cliente():
    admin, cliente = crear_admin(), crear_cliente()

    respuesta = reservar(admin, crear_habitacion(), 5, 8, usuario_id=cliente.id)

    assert respuesta.status_code == 201
