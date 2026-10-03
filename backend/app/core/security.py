"""Autenticación y Seguridad."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt import PyJWKClient

# Configuración fija (luego vamos a sacarla de config.py, pero pa hacerlo más fácil, así de momento)
KEYCLOAK_URL = "http://localhost:8080/realms/rag-agent"
ALGORITHMS = ["RS256"]
AUDIENCE = "account"

# Configuración OAuth2 para Swagger UI
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="http://localhost:8080/realms/rag-agent/protocol/openid-connect/token"
)

# Cliente para obtener las llaves públicas de Keycloak
jwks_client = PyJWKClient(f"{KEYCLOAK_URL}/protocol/openid-connect/certs")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Dependencia para validar el token JWT y retornar el ID de usuario."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Obtenemos la llave pública correcta cogiendo en el header del token
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Validamos el token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=ALGORITHMS,
            audience=AUDIENCE,
            options={"verify_aud": False} 
        )
        
        username: str = payload.get("preferred_username")
        if username is None:
            raise credentials_exception
            
        return username
        
    except jwt.PyJWTError:
        raise credentials_exception

