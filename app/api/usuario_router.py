from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.domain.usuario import RespuestaUsuario, Usuario, UsuarioCreate
from app.repositories.usuario_repository import UsuarioRepository
from app.service.usuario_service import UsuarioService

# Instancias: un solo repositorio, así los datos se comparten entre peticiones
repo = UsuarioRepository()
service = UsuarioService(repo)

router = APIRouter(prefix="/api/v1/usuarios", tags=["Usuarios"])


@router.post("/", response_model=Usuario, status_code=status.HTTP_201_CREATED)
def registrar_usuario(data: UsuarioCreate):
    """HU-001: registra un usuario nuevo."""
    return service.registrar(data)


@router.get(
    "/{usuario_id}",
    response_model=RespuestaUsuario,
    summary="Consultar información personal de un usuario",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": RespuestaUsuario,
            "description": "Usuario no encontrado",
            "content": {
                "application/json": {
                    "example": {"mensaje": "Usuario no encontrado", "data": None, "success": False}
                }
            },
        }
    },
)
def consultar_usuario(usuario_id: int):
    """HU-003: consulta la información personal (id, nombre y correo) de un usuario por su ID."""
    usuario = service.consultar(usuario_id)
    if usuario is None:
        respuesta = RespuestaUsuario(mensaje="Usuario no encontrado", data=None, success=False)
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=respuesta.model_dump())
    return RespuestaUsuario(mensaje="Usuario encontrado", data=usuario, success=True)
