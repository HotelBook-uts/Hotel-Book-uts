from datetime import date

from app.domain.errores import (FechasInvalidasError, HabitacionNoDisponibleError,
                                HabitacionNoEncontradaError, UsuarioNoEncontradoError)
from app.domain.reserva import Reserva, ReservaCreate
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
