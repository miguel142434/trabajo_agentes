"""Persistencia de chunks y búsqueda exacta Top-K con distancia coseno."""

from contextlib import contextmanager
from uuid import uuid4

from pgvector import Vector
from pgvector.psycopg import register_vector
from psycopg import Connection, Error, OperationalError, sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import Settings
from app.core.exceptions import AppError

# Propietario de los documentos de la base de conocimiento global. Los usuarios
# reales usan el `sub` UUID de Keycloak, así que este valor nunca colisiona; se
# evita NULL porque identifica a los registros antiguos sin propietario.
GLOBAL_OWNER_ID = "system:global"


class PostgresVectorStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.table = sql.Identifier("public", settings.vector_table)

    def _conninfo(self):
        if self.settings.database_url:
            # Aceptar la URL del plan de desarrollo y las URI nativas de PostgreSQL.
            return self.settings.database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        return make_conninfo(
            host=self.settings.postgres_host, port=self.settings.postgres_port,
            dbname=self.settings.postgres_db, user=self.settings.postgres_user,
            password=self.settings.postgres_password,
        )

    @contextmanager
    def connection(self):
        try:
            with Connection.connect(
                self._conninfo(), row_factory=dict_row,
                connect_timeout=self.settings.postgres_connect_timeout,
                options=f"-c statement_timeout={self.settings.postgres_statement_timeout}",
            ) as conn:
                # Serializa la primera creación de la extensión/tabla entre peticiones.
                with conn.transaction():
                    conn.execute("SELECT pg_advisory_xact_lock(417004)")
                    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    conn.execute(sql.SQL("""
                        CREATE TABLE IF NOT EXISTS {} (
                            id UUID PRIMARY KEY,
                            document_id UUID NOT NULL,
                            filename TEXT NOT NULL,
                            page INTEGER,
                            chunk_index INTEGER NOT NULL,
                            content TEXT NOT NULL,
                            embedding VECTOR({}) NOT NULL,
                            embedding_model TEXT NOT NULL,
                            metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb
                        )
                    """).format(self.table, sql.Literal(self.settings.embedding_dimension)))
                    # Migración aditiva: los registros anteriores conservan propietario NULL.
                    conn.execute(sql.SQL("ALTER TABLE {} ADD COLUMN IF NOT EXISTS owner_id TEXT").format(self.table))
                    cursor = conn.execute("""
                        SELECT format_type(a.atttypid, a.atttypmod) AS type
                        FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname = 'public' AND c.relname = %s
                          AND a.attname = 'embedding' AND NOT a.attisdropped
                    """, (self.settings.vector_table,))
                    row = cursor.fetchone()
                    if not row or row["type"] != f"vector({self.settings.embedding_dimension})":
                        raise AppError("La tabla tiene otra dimensión. Usa otra VECTOR_TABLE o reindexa sus datos.", 409)
                register_vector(conn)
                yield conn
        except AppError:
            raise
        except OperationalError as exc:
            raise AppError("PostgreSQL no está disponible. Revisa su conexión y credenciales.", 503) from exc
        except Error as exc:
            raise AppError("Falló la operación en PostgreSQL. Revisa pgvector, permisos y esquema de la tabla.", 503) from exc

    def _ensure_documents(self, conn):
        conn.execute("SELECT pg_advisory_xact_lock(417005)")
        conn.execute(sql.SQL("""
            CREATE TABLE IF NOT EXISTS {} (
                document_id UUID PRIMARY KEY,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                size_bytes BIGINT NOT NULL,
                chunks_created INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'processed',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                embedding_model TEXT NOT NULL,
                vector_table TEXT NOT NULL
            )
        """).format(sql.Identifier("public", self.settings.document_table)))
        conn.execute(sql.SQL("ALTER TABLE {} ADD COLUMN IF NOT EXISTS owner_id TEXT").format(
            sql.Identifier("public", self.settings.document_table)))
        # Huella SHA-256 del archivo: permite saber si un documento global cambió.
        conn.execute(sql.SQL("ALTER TABLE {} ADD COLUMN IF NOT EXISTS content_hash TEXT").format(
            sql.Identifier("public", self.settings.document_table)))

    def list_documents(self, limit=100, offset=0, *, user_id=None):
        with self.connection() as conn:
            self._ensure_documents(conn)
            return conn.execute(sql.SQL("""
                SELECT document_id, filename, file_type, size_bytes, chunks_created,
                       status, created_at, embedding_model, owner_id = %s AS is_global
                FROM {} WHERE vector_table = %s
                  AND (owner_id IS NOT DISTINCT FROM %s OR owner_id = %s)
                ORDER BY is_global DESC, created_at DESC, document_id ASC LIMIT %s OFFSET %s
            """).format(sql.Identifier("public", self.settings.document_table)),
                (GLOBAL_OWNER_ID, self.settings.vector_table, user_id, GLOBAL_OWNER_ID,
                 limit, offset)).fetchall()

    def add(self, document_id, chunks, vectors, *, document=None, user_id=None):
        with self.connection() as conn:
            return self._insert(conn, document_id, chunks, vectors, document=document, user_id=user_id)

    def _insert(self, conn, document_id, chunks, vectors, *, document=None, user_id=None):
        ids = [uuid4() for _ in chunks]
        if document is not None:
            self._ensure_documents(conn)
            conn.execute(sql.SQL("""
                INSERT INTO {} (document_id, filename, file_type, size_bytes, chunks_created,
                                embedding_model, vector_table, owner_id, content_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """).format(sql.Identifier("public", self.settings.document_table)),
                (document_id, document["filename"], document["file_type"], document["size_bytes"],
                 len(chunks), self.settings.ollama_embedding_model, self.settings.vector_table, user_id,
                 document.get("content_hash")))
        with conn.cursor() as cursor:
            cursor.executemany(sql.SQL("""
                INSERT INTO {} (id, document_id, filename, page, chunk_index,
                                content, embedding, embedding_model, metadata, owner_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """).format(self.table), [
                (chunk_id, document_id, chunk.filename, chunk.page, index,
                 chunk.content, Vector(vector), self.settings.ollama_embedding_model, Jsonb(chunk.metadata), user_id)
                for index, (chunk_id, chunk, vector) in enumerate(zip(ids, chunks, vectors, strict=True))
            ])
        return ids

    # ------------------------------------------------------------------
    # Base de conocimiento global (owner_id = GLOBAL_OWNER_ID)
    # ------------------------------------------------------------------
    def global_document_is_current(self, filename, content_hash):
        """True si el archivo global ya está indexado con el mismo contenido y modelo."""
        with self.connection() as conn:
            self._ensure_documents(conn)
            row = conn.execute(sql.SQL("""
                SELECT 1 FROM {} WHERE owner_id = %s AND filename = %s AND content_hash = %s
                  AND embedding_model = %s AND vector_table = %s LIMIT 1
            """).format(sql.Identifier("public", self.settings.document_table)),
                (GLOBAL_OWNER_ID, filename, content_hash, self.settings.ollama_embedding_model,
                 self.settings.vector_table)).fetchone()
            return row is not None

    def replace_global_document(self, document_id, chunks, vectors, *, document):
        """Sustituye, en una sola transacción, cualquier versión previa del archivo global."""
        with self.connection() as conn, conn.transaction():
            conn.execute("SELECT pg_advisory_xact_lock(417006)")
            self._delete_global(conn, "filename = %s", (document["filename"],))
            return self._insert(conn, document_id, chunks, vectors, document=document, user_id=GLOBAL_OWNER_ID)

    def prune_global_documents(self, keep_filenames):
        """Elimina documentos globales cuyo archivo ya no existe en la carpeta."""
        with self.connection() as conn, conn.transaction():
            conn.execute("SELECT pg_advisory_xact_lock(417006)")
            self._ensure_documents(conn)
            return self._delete_global(conn, "NOT (filename = ANY(%s))", (list(keep_filenames),))

    def _delete_global(self, conn, condition, params):
        self._ensure_documents(conn)
        documents = sql.Identifier("public", self.settings.document_table)
        rows = conn.execute(sql.SQL("SELECT document_id FROM {} WHERE owner_id = %s AND vector_table = %s AND ")
                            .format(documents) + sql.SQL(condition),
                            (GLOBAL_OWNER_ID, self.settings.vector_table, *params)).fetchall()
        ids = [row["document_id"] for row in rows]
        if ids:
            conn.execute(sql.SQL("DELETE FROM {} WHERE document_id = ANY(%s)").format(self.table), (ids,))
            conn.execute(sql.SQL("DELETE FROM {} WHERE document_id = ANY(%s)").format(documents), (ids,))
        return len(ids)

    def search(self, vector, k, *, user_id=None):
        # Cada usuario consulta sus propios documentos más la base de conocimiento global.
        with self.connection() as conn:
            cursor = conn.execute(sql.SQL("""
                SELECT id, document_id, filename, page, chunk_index, content, metadata,
                       embedding <=> %s AS distance
                FROM {} WHERE embedding_model = %s
                  AND (owner_id IS NOT DISTINCT FROM %s OR owner_id = %s)
                ORDER BY distance ASC, id ASC LIMIT %s
            """).format(self.table), (Vector(vector), self.settings.ollama_embedding_model, user_id,
                                      GLOBAL_OWNER_ID, k))
            return cursor.fetchall()
