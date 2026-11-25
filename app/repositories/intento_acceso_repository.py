from datetime import datetime, timezone
from typing import List, Optional

from app.domain.auth import IntentoAcceso


class IntentoAccesoRepository:
    """HU-002: tabla intentos_acceso (base de datos simulada en memoria)."""

    def __init__(self):
        self._db: dict[int, IntentoAcceso] = {}
        self._next_id: int = 1

    def registrar(
        self, correo: str, usuario_id: Optional[int], exitoso: bool, motivo: str
    ) -> IntentoAcceso:
        intento = IntentoAcceso(
            id=self._next_id, correo=correo, usuarioId=usuario_id, exitoso=exitoso,
            motivo=motivo, fecha=datetime.now(timezone.utc),
        )
        self._db[self._next_id] = intento
        self._next_id += 1
        return intento

    def get_by_correo(self, correo: str) -> List[IntentoAcceso]:
        return [i for i in self._db.values() if i.correo == correo.lower()]
