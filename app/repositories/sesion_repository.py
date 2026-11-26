from datetime import datetime, timezone


class SesionRepository:
    """HU-002: tokens invalidados al cerrar sesión (base de datos simulada en memoria).

    Se guarda el identificador (jti) de cada token cerrado junto con su
    expiración; los que ya expiraron se limpian porque no hace falta recordarlos.
    """

    def __init__(self):
        self._revocados: dict[str, datetime] = {}

    def revocar(self, jti: str, expira: datetime) -> None:
        self._limpiar_expirados()
        self._revocados[jti] = expira

    def esta_revocado(self, jti: str) -> bool:
        return jti in self._revocados

    def _limpiar_expirados(self) -> None:
        ahora = datetime.now(timezone.utc)
        self._revocados = {j: e for j, e in self._revocados.items() if e > ahora}
