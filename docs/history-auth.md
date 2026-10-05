# Historial y acceso por usuario (fases 9 y 10)

## Ejecutar en Windows

Con Docker Desktop, PostgreSQL y Keycloak activos, y Ollama abierto:

```powershell
# Desde la raíz
docker compose up -d postgres
docker start rag-keycloak
cd backend
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe run.py
```

`docker start rag-keycloak` supone que ya se creó ese contenedor. `run.py` selecciona
el event loop compatible con psycopg asíncrono en Windows. El backend crea las tablas
relacionales al iniciar. Usa PostgreSQL y Keycloak como servicios locales; el Compose
actual no configura Keycloak automáticamente.

Configuración disponible en `.env`, con los valores de la instalación actual:

```dotenv
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=rag-agent
KEYCLOAK_CLIENT_ID=rag-frontend
KEYCLOAK_AUDIENCE=account
```

`KEYCLOAK_URL` es la URL base, sin `/realms/...`. El emisor esperado se construye
con el realm. La audiencia `account` corresponde a la configuración local de Keycloak;
también se exige `azp=rag-frontend`. Si se configura una audiencia dedicada a esta API,
hay que añadirla a los access tokens en Keycloak y actualizar `KEYCLOAK_AUDIENCE`.
No desactivar la validación para hacer coincidir tokens de otra aplicación.

En Swagger (`http://127.0.0.1:8000/docs`), pulsa **Authorize** y usa el usuario del
realm `rag-agent`, su contraseña y client ID `rag-frontend`; client secret vacío para
el cliente público actual. Deben estar habilitados Direct access grants y Web origins
`http://127.0.0.1:8000`, sin contraseña temporal ni acciones pendientes en el usuario.
No es necesario crear de nuevo el realm ni el cliente que ya funcionan.

## Continuar una conversación

Primera pregunta:

```json
{"question":"¿Qué selección ganó el Mundial de fútbol de 2022?"}
```

La respuesta ahora incluye `conversation_id`, además de `answer` y `sources`.
Copiar ese ID en la siguiente petición:

```json
{
  "question":"¿En qué país se disputó el Mundial de 2022?",
  "conversation_id":"UUID_DEVUELTO_EN_LA_PRIMERA_RESPUESTA"
}
```

Sin ID (o con null) se crea una nueva conversación. También se puede crear una vacía
con `POST /api/conversations` y `{"title":"Mundiales"}`, y enviar su `id` al chat.
`GET /api/conversations` lista solo las propias; admite `limit` y `offset`.
`GET /api/conversations/{id}` devuelve sus mensajes, incluso después de reiniciar.
El historial conserva las fuentes serializadas en el campo `sources` de los mensajes.

La propiedad se comprueba antes de embeddings/LLM y nuevamente al guardar. Una
conversación inexistente o ajena devuelve 404, sin revelar si pertenece a otra persona.
La pareja pregunta/respuesta y la fecha de actualización se guardan en una transacción;
si falla, no se publica una conversación ni un mensaje parcial de esa operación.
También se guardan los rechazos por falta de información.

**Alcance:** continuar una conversación agrupa y conserva sus mensajes. Todavía no
se envía el historial anterior al prompt ni se resuelven preguntas como «¿y él?»
usando memoria conversacional; cada pregunta debe ser autosuficiente.

## Documentos privados y datos anteriores

El propietario procede exclusivamente del token validado (`sub`, UUID estable),
no de un campo del formulario ni de `preferred_username`, que puede cambiar.
Carga, listado, búsqueda vectorial y recuperación RAG usan ese mismo propietario.
El filtro se ejecuta en PostgreSQL **antes** del Top-K: no se recuperan documentos
ajenos para filtrarlos posteriormente en Python. Compartir un mismo servicio en memoria
no comparte identidad; esta viaja explícitamente con cada petición.

La migración de las tablas vectoriales es aditiva: añade `owner_id` si no existe.
Los documentos antiguos conservan NULL y permanecen guardados, pero no son visibles
para usuarios autenticados. **Vuelve a cargar los archivos con tu usuario**, desde
`POST /api/documents/upload`, para usarlos en las consultas privadas. No se adjudica
automáticamente el antiguo corpus global a la primera persona que se conecte.

El historial anterior utilizaba nombres de usuario como ID. Se conserva, pero ya no
se asocia automáticamente a un usuario con el mismo nombre. Para recuperarlo, un
administrador debe comprobar el **User ID** de esa cuenta en Keycloak y ejecutar:

```powershell
# Desde backend, primero revisar. Sustituir el UUID por el ID verificado.
.venv\Scripts\python.exe scripts/migrate_legacy_history.py --legacy-user estudiante --subject UUID_DE_KEYCLOAK
# Después de verificar el destino, aplicar explícitamente:
.venv\Scripts\python.exe scripts/migrate_legacy_history.py --legacy-user estudiante --subject UUID_DE_KEYCLOAK --apply
```

El script transfiere las conversaciones y registros relacionales de documentos
del usuario indicado, conservando los mensajes. No reasigna el corpus vectorial.
No se ejecuta automáticamente durante el login. El modelo `documents_history`
heredado no es el catálogo de cargas: ese sigue siendo `uploaded_documents`.

## Autenticación

Se comprueban firma RS256 con JWKS, expiración, emisión, emisor exacto, audiencia,
cliente autorizado, tipo Bearer y sujeto UUID. Se requieren `exp`, `iat`, `iss`, `aud`,
`azp` y `sub`; PyJWT también valida `nbf` cuando existe. No se registran tokens.
La consulta JWKS se realiza fuera del event loop y tiene timeout.

Chat, documentos, vectores, conversaciones y `/api/test-llm` requieren autenticación.
Health y documentación técnica siguen públicos. Token inválido/ausente/expirado: 401;
fallo al consultar claves de Keycloak: 503. La validación es local con claves públicas,
no introspección por petición: un token revocado puede seguir válido hasta expirar.

## Verificación

Verificado el 5 de octubre de 2026: **80 pruebas aprobadas**, incluidas las integraciones
de PostgreSQL, documentos y embeddings; `pip check` sin conflictos. Las claves públicas
del Keycloak local estaban accesibles. No se inició sesión con credenciales de usuarios
reales durante estas pruebas. La suite emitió un `ResourceWarning` de transporte sin
cerrar en una integración anterior de Ollama; no hubo fallos de pruebas.

1. Autoriza usuario A y carga `docs/examples/deportes/mundial-2022.txt`.
2. Haz dos preguntas usando el mismo `conversation_id`; consulta su detalle: cuatro mensajes.
3. Autoriza usuario B: no debe ver documentos ni conversaciones de A; el ID de A devuelve 404.
4. Una consulta RAG de B no debe usar las fuentes de A. Carga documentos propios para probar su respuesta.
5. Sin autorizarte, `/api/test-llm` también devuelve 401.

Suite, desde `backend/`, con PostgreSQL y Ollama activos para las integraciones anteriores:

```powershell
$env:TEST_VECTOR_INTEGRATION="1"
$env:TEST_AUTH_INTEGRATION="1"
.venv\Scripts\python.exe -m unittest discover -s tests -v
Remove-Item Env:TEST_VECTOR_INTEGRATION
Remove-Item Env:TEST_AUTH_INTEGRATION
```

Las pruebas nuevas firman JWT RSA reales con claves de prueba y comprueban firma,
claims y rutas HTTP. El test de aislamiento usa PostgreSQL real en un esquema exclusivo
y tablas vectoriales exclusivas, con embeddings y generación simulados para comprobar
qué documentos llegan al modelo. Prueba continuidad, propiedad, rollback, rechazo y
migración administrativa del historial. No usa credenciales de usuarios reales de Keycloak.
Las integraciones anteriores siguen probando embeddings y carga con Ollama real.

Los scripts de benchmark/fase 8 usan un registrador de pruebas para no escribir historial.
`benchmark_rag.py --user-id UUID` selecciona los documentos de ese usuario; sin él solo
selecciona el corpus histórico sin propietario. `verify_phase8.py` usa un usuario
simulado y una tabla aislada; no sustituye las pruebas de autenticación.
