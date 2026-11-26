"""Funciones de apoyo compartidas por las pruebas."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import dependencias
from app.domain.auth import SesionUsuario
from app.domain.usuario import Rol
from main import app

client = TestClient(app)
CLAVE = "clave1234"


@dataclass
class Cuenta:
    id: int
    email: str
    token: str

    @property
    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}


def correo_unico() -> str:
    return f"cliente.{uuid4().hex[:8]}@correo.com"


def registrar(nombre: str = "laura gómez", email: str | None = None,
              telefono: str | None = "3109876543") -> dict:
    respuesta = client.post("/api/v1/usuarios/", json={
        "nombre": nombre, "email": email or correo_unico(),
        "password": CLAVE, "telefono": telefono,
    })
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["data"]


def iniciar_sesion(email: str) -> str:
    respuesta = client.post("/api/v1/auth/login", json={"correo": email, "contrasena": CLAVE})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["data"]["token"]


def crear_cliente(**datos) -> Cuenta:
    """Registra un cliente nuevo e inicia sesión con él."""
    usuario = registrar(**datos)
    return Cuenta(usuario["id"], usuario["email"], iniciar_sesion(usuario["email"]))


def crear_admin() -> Cuenta:
    """Registra un usuario, le asigna el rol ADMINISTRADOR e inicia sesión."""
    usuario = registrar(nombre="admin hotelbook")
    repo = dependencias.usuario_repo
    repo._db[usuario["id"]] = repo.get_by_id(usuario["id"]).model_copy(
        update={"rol": Rol.ADMINISTRADOR})
    return Cuenta(usuario["id"], usuario["email"], iniciar_sesion(usuario["email"]))


def sesion(usuario_id: int, rol: Rol = Rol.CLIENTE) -> SesionUsuario:
    """Sesión simulada para pruebas unitarias de los servicios."""
    return SesionUsuario(usuarioId=usuario_id, rol=rol, jti="prueba",
                         expira=datetime.now(timezone.utc) + timedelta(minutes=30))


def dia(dias: int) -> str:
    return (date.today() + timedelta(days=dias)).isoformat()


def crear_habitacion(disponible: bool = True) -> int:
    hotel = client.post("/hoteles/", json={
        "nombre": f"Hotel {uuid4().hex[:8]}", "ciudad": "Bucaramanga",
        "direccion": "Calle 10 # 20-30", "estrellas": 4, "precio_noche": 250000,
    })
    assert hotel.status_code == 201, hotel.text
    habitacion = client.post("/habitaciones/", json={
        "hotel_id": hotel.json()["id"], "numero": "101", "tipo": "doble",
        "capacidad": 2, "precio_noche": 180000, "disponible": disponible,
    })
    assert habitacion.status_code == 201, habitacion.text
    return habitacion.json()["id"]


def reservar(cuenta: Cuenta, habitacion_id: int, entrada: int, salida: int,
             usuario_id: int | None = None):
    """Crea una reserva con la sesión de `cuenta` (por defecto a su propio nombre)."""
    return client.post("/api/v1/reservas/", headers=cuenta.headers, json={
        "usuarioId": usuario_id or cuenta.id, "habitacionId": habitacion_id,
        "fechaEntrada": dia(entrada), "fechaSalida": dia(salida),
    })
