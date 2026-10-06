"""Añade orígenes del frontend al cliente existente de Keycloak.

Por defecto solo muestra el cambio; --apply lo guarda. Pide credenciales de
administración de forma interactiva y nunca las guarda en el repositorio.
"""
import argparse
import getpass
from pathlib import Path
import sys

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import get_settings


def configure(username, password, *, apply=False):
    settings = get_settings()
    base = str(settings.keycloak_url).rstrip('/')
    origins = ['http://localhost:5173', 'http://127.0.0.1:5173']
    with httpx.Client(timeout=15) as client:
        token = client.post(f'{base}/realms/master/protocol/openid-connect/token', data={
            'grant_type':'password', 'client_id':'admin-cli', 'username':username, 'password':password})
        if token.status_code != 200:
            raise SystemExit('No se pudo autenticar al administrador. No se modificó Keycloak.')
        client.headers['Authorization'] = 'Bearer ' + token.json()['access_token']
        clients_url = f'{base}/admin/realms/{settings.keycloak_realm}/clients'
        response = client.get(clients_url, params={'clientId': settings.keycloak_client_id})
        response.raise_for_status()
        matches = [item for item in response.json() if item['clientId'] == settings.keycloak_client_id]
        if len(matches) != 1:
            raise SystemExit('No se encontró un único cliente con ese nombre.')
        item = matches[0]
        if not item.get('publicClient'):
            raise SystemExit('El frontend necesita un cliente público. Revisa Client authentication en Keycloak.')
        item['standardFlowEnabled'] = True
        item['redirectUris'] = list(dict.fromkeys(item.get('redirectUris', []) + [origin+'/*' for origin in origins]))
        item['webOrigins'] = list(dict.fromkeys(item.get('webOrigins', []) + origins))
        attrs = item.setdefault('attributes', {})
        logout = attrs.get('post.logout.redirect.uris', '').split('##')
        attrs['post.logout.redirect.uris'] = '##'.join(dict.fromkeys(
            [value for value in logout if value] + [origin+'/login' for origin in origins]))
        print('Cliente:', item['clientId'])
        print('Orígenes a habilitar:', ', '.join(origins))
        print('Retorno después de salir: /login. Se conservan las direcciones existentes.')
        if apply:
            saved = client.put(f"{clients_url}/{item['id']}", json=item)
            saved.raise_for_status()
            print('Configuración del frontend guardada.')
        else:
            print('Solo revisión. Ejecuta con --apply para guardar.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        configure(input('Usuario administrador de Keycloak: '), getpass.getpass('Contraseña: '), apply=args.apply)
    except httpx.RequestError:
        raise SystemExit('No se pudo conectar con Keycloak. Inicia el contenedor y vuelve a intentarlo.')
    except httpx.HTTPStatusError as exc:
        raise SystemExit(f'Keycloak rechazó la operación (HTTP {exc.response.status_code}). Revisa los permisos del administrador.')
