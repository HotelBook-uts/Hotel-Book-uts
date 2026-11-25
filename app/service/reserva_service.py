from datetime import date
from typing import Optional

from app.domain.errores import (FechasInvalidasError, HabitacionNoDisponibleError,
                                HabitacionNoEncontradaError, ReservaNoEncontradaError,
                                ReservaYaCanceladaError, UsuarioNoEncontradoError)
from app.domain.reserva import (EstadoHistorial, EstadoReserva, HistorialReservas, Reserva,
                                ReservaCreate, ReservaHistorial)
from app.repositories.habitacion_repository import HabitacionRepository
from app.repositories.hotel_repository import HotelRepository
from app.repositories.reserva_repository import ReservaRepository
from app.repositories.usuario_repository import UsuarioRepository


class ReservaService:
    def __init__(
        self,
        repo: ReservaRepository,
        habitacion_repo: HabitacionRepository,
        usuario_repo: UsuarioRepository,
        hotel_repo: HotelRepository,
    ):
        # Inyección de dependencias: recibe los repositorios, no los crea
        self.repo = repo
        self.habitacion_repo = habitacion_repo
        self.usuario_repo = usuario_repo
        self.hotel_repo = hotel_repo

    # HU-013: realizar una reserva de una habitación
    def crear(self, data: ReservaCreate) -> Reserva:
        # Regla de negocio: fechas coherentes
        if data.fechaSalida <= data.fechaEntrada:
            raise FechasInvalidasError(
                "La fecha de salida debe ser posterior a la fecha de entrada")
        if data.fechaEntrada < date.today():
            raise FechasInvalidasError(
                "La fecha de entrada no puede ser anterior a la fecha actual")

        # Regla de negocio: el cliente y la habitación deben existir
        if not self.usuario_repo.get_by_id(data.usuarioId):
            raise UsuarioNoEncontradoError(data.usuarioId)
        habitacion = self.habitacion_repo.get_by_id(data.habitacionId)
        if not habitacion:
            raise HabitacionNoEncontradaError(data.habitacionId)

        # Regla de negocio: la habitación debe estar habilitada y libre en esas fechas
        if not habitacion.disponible or self.repo.get_activas_que_se_cruzan(
            data.habitacionId, data.fechaEntrada, data.fechaSalida
        ):
            raise HabitacionNoDisponibleError(data.habitacionId)

        return self.repo.create(data)

    # HU-014: cancelar una reserva registrada
    # TODO HU-002: validar que quien cancela sea el dueño de la reserva o un administrador
    def cancelar(self, reserva_id: int) -> Reserva:
        reserva = self.repo.get_by_id(reserva_id)
        if not reserva:
            raise ReservaNoEncontradaError(reserva_id)

        # Regla de negocio: solo se cancelan reservas activas
        if reserva.estado == EstadoReserva.cancelada:
            raise ReservaYaCanceladaError(reserva_id)

        # Al quedar cancelada, deja de contar para la disponibilidad:
        # la habitación queda libre para esas fechas
        return self.repo.update_estado(reserva_id, EstadoReserva.cancelada)

    # HU-005: historial de reservas del cliente, de la más reciente a la más antigua
    # TODO HU-002: validar que el cliente consulte solo sus propias reservas (403)
    def historial(
        self, usuario_id: int, estado: Optional[EstadoHistorial] = None
    ) -> HistorialReservas:
        if not self.usuario_repo.get_by_id(usuario_id):
            raise UsuarioNoEncontradoError(usuario_id)

        hoy = date.today()
        reservas = self.repo.get_by_usuario(usuario_id)

        # Filtro opcional por estado (CONFIRMADA, FINALIZADA o CANCELADA)
        if estado is not None:
            reservas = [r for r in reservas if r.estado_historial(hoy) == estado]

        # Regla de negocio: ordenadas por fecha de entrada, la más reciente primero
        reservas.sort(key=lambda r: (r.fechaEntrada, r.id), reverse=True)

        items = [
            ReservaHistorial(
                reservaId=r.codigo,
                hotel=self._nombre_hotel(r.habitacionId),
                fechaEntrada=r.fechaEntrada,
                estado=r.estado_historial(hoy),
            )
            for r in reservas
        ]
        return HistorialReservas(
            usuarioId=usuario_id,
            totalReservas=len(items),
            ultimaReserva=items[0].reservaId if items else None,
            reservas=items,
        )

    def _nombre_hotel(self, habitacion_id: int) -> str:
        # Si la habitación o el hotel fueron eliminados, el historial no se rompe
        habitacion = self.habitacion_repo.get_by_id(habitacion_id)
        hotel = self.hotel_repo.get_by_id(habitacion.hotel_id) if habitacion else None
        return hotel.nombre if hotel else "Hotel no disponible"
