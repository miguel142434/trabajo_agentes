"""Tokens de Keycloak: firma, emisor, audiencia, cliente y sujeto estable."""
from functools import lru_cache
from uuid import UUID
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWKClient
from starlette.concurrency import run_in_threadpool
from app.core.config import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{get_settings().keycloak_issuer}/protocol/openid-connect/token")

@lru_cache
def get_jwks_client():
    return PyJWKClient(get_settings().keycloak_jwks_uri, timeout=5)

def get_signing_key(token: str):
    settings = get_settings()
    if settings.keycloak_jwks_json:
        try:
            jwk_set = jwt.PyJWKSet.from_json(settings.keycloak_jwks_json)
            kid = jwt.get_unverified_header(token).get("kid")
            return jwk_set[kid]
        except Exception as exc:
            raise HTTPException(401, "Token no válido o firma no reconocida.") from exc
    return get_jwks_client().get_signing_key_from_jwt(token)

def validate_token(token: str) -> str:
    settings = get_settings()
    try:
        key = get_signing_key(token)
        payload = jwt.decode(token, key.key, algorithms=["RS256"],
            audience=settings.keycloak_audience, issuer=settings.keycloak_issuer,
            options={"require": ["exp", "iat", "sub", "iss", "aud", "azp"]})
        if payload["azp"] != settings.keycloak_client_id or payload.get("typ") != "Bearer":
            raise ValueError("Cliente o tipo de token incorrecto")
        return str(UUID(payload["sub"]))
    except jwt.PyJWKClientConnectionError as exc:
        raise HTTPException(503, "No se pudo consultar Keycloak.") from exc
    except (jwt.PyJWTError, ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(401, "Credenciales inválidas o token expirado",
                            headers={"WWW-Authenticate": "Bearer"}) from exc

async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    # JWKS usa HTTP síncrono; ejecutarlo fuera del event loop.
    return await run_in_threadpool(validate_token, token)
