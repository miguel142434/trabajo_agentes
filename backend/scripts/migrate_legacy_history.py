"""Reasignación administrativa explícita del historial anterior basado en username.

No deduce propietarios por el nombre de un token ni modifica documentos compartidos.
El administrador debe verificar el UUID en Keycloak antes de ejecutar --apply.
"""
import argparse
from pathlib import Path
import sys
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from psycopg import Connection
from app.core.config import get_settings
from app.vectorstore.postgres import PostgresVectorStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--legacy-user', required=True)
    parser.add_argument('--subject', required=True, type=UUID)
    parser.add_argument('--apply', action='store_true', help='Sin esta opción solo muestra cantidades.')
    args = parser.parse_args()
    source, target = args.legacy_user, str(args.subject)
    if source == target:
        parser.error('El origen y el destino deben ser diferentes.')
    with Connection.connect(PostgresVectorStore(get_settings())._conninfo(), connect_timeout=5) as conn:
        old = conn.execute('SELECT id FROM users WHERE id=%s FOR UPDATE', (source,)).fetchone()
        if not old:
            raise SystemExit('No existe ese usuario histórico.')
        count = conn.execute('SELECT count(*) FROM conversations WHERE user_id=%s', (source,)).fetchone()[0]
        print(f'Conversaciones a reasignar: {count}; destino: {target}')
        if not args.apply:
            print('Solo revisión. Verifica el User ID en Keycloak antes de añadir --apply.')
            return
        conn.execute('INSERT INTO users (id,username,created_at) VALUES (%s,%s,CURRENT_TIMESTAMP) ON CONFLICT (id) DO NOTHING', (target,target))
        conn.execute('UPDATE conversations SET user_id=%s WHERE user_id=%s', (target,source))
        conn.execute('UPDATE documents_history SET user_id=%s WHERE user_id=%s', (target,source))
        print('Historial reasignado. No se modificaron documentos ni fragmentos vectoriales.')


if __name__ == '__main__':
    main()
