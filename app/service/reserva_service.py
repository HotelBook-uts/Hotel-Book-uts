from datetime import date

from app.domain.errores import (FechasInvalidasError, HabitacionNoDisponibleError,
                                HabitacionNoEncontradaError, ReservaNoEncontradaError,
                                ReservaYaCanceladaError, UsuarioNoEncontradoError)
from app.domain.reserva import EstadoReserva, Reserva, ReservaCreate
from app.repositories.habitacion_repository import HabitacionRepository
from app.repositories.reserva_repository import ReservaRepository
from app.repositories.usuario_repository import UsuarioRepository


class ReservaService:
    def __init__(
        self,
        repo: ReservaRepository,
        habitacion_repo: HabitacionRepository,
        usuario_repo: UsuarioRepository,
    ):
        # Inyección de dependencias: recibe los repositorios, no los crea
        self.repo = repo
        self.habitacion_repo = habitacion_repo
        self.usuario_repo = usuario_repo

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
