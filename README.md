# RAG Sports Agent

Asistente documental en español sobre mundiales de fútbol, Fórmula 1 y otros deportes.
Consulta una biblioteca común y los documentos privados del usuario, responde con
fuentes y rechaza preguntas cuando no encuentra respaldo suficiente.

**Integrantes:** Miguel Zuleta, Sebastián Giraldo y Martín Restrepo.

Proyecto de la asignatura Implementación e Integración de Software.

## Contenido

- [Objetivo y arquitectura](#objetivo-y-arquitectura)
- [Estructura](#estructura)
- [Requisitos e instalación de modelos](#requisitos-e-instalación-de-modelos)
- [Configuración](#configuración)
- [Ejecutar con Docker](#ejecutar-con-docker)
- [Autenticación y usuarios](#autenticación-y-usuarios)
- [Ejecutar backend y frontend en desarrollo](#ejecutar-backend-y-frontend-en-desarrollo)
- [Documentos y ejemplos](#documentos-y-ejemplos)
- [RAG, LangGraph y control de alucinaciones](#rag-langgraph-y-control-de-alucinaciones)
- [Tests](#tests)
- [Despliegue](#despliegue)
- [Limitaciones y diagnóstico](#limitaciones-y-diagnóstico)
- [Estado del proyecto](#estado-del-proyecto)

## Objetivo y arquitectura

El objetivo es responder preguntas sobre documentación deportiva con referencias
consultables y acceso por cuenta. La interfaz ofrece login, chat, carga/listado de
documentos e historial. No busca información en Internet ni actualiza automáticamente
resultados deportivos. Los controles reducen respuestas sin respaldo; no garantizan
que toda afirmación del modelo sea correcta.

El navegador autentica al usuario en Keycloak. React envía el token a FastAPI, que
valida firma, emisor, audiencia, cliente y expiración. LangGraph coordina recuperación
en PostgreSQL/pgvector y llamadas a Ollama. El resultado se guarda en el historial
antes de devolver respuesta y fuentes a la interfaz.

| Componente | Tecnología |
|---|---|
| Frontend | React 18, React Router, Vite y fetch; Nginx en Docker |
| Backend | FastAPI, Pydantic Settings, Uvicorn |
| Agente | LangGraph y componentes LangChain |
| Generación | Ollama con `qwen3:8b` |
| Embeddings | `nomic-embed-text`, 768 dimensiones |
| Datos | PostgreSQL 16, pgvector, psycopg y SQLAlchemy asíncrono |
| Acceso | Keycloak, JWT y Authorization Code + PKCE |
| Pruebas | pytest, unittest y Playwright |

Versiones fijadas en [requirements.txt](backend/requirements.txt) y
[package-lock.json](frontend/package-lock.json).

## Estructura

```text
backend/
  app/
    api/           Rutas HTTP
    agents/        Estado, grafo y nodos LangGraph
    core/          Configuración, seguridad, errores y conexión SQL
    models/        Modelos de historial
    schemas/       Contratos de entrada/salida
    services/      Documentos, embeddings, RAG e historial
    vectorstore/   Persistencia y búsqueda pgvector
  knowledge_base/  Biblioteca común versionada
  scripts/         Benchmark y utilidades de configuración/migración
  tests/           Pruebas unitarias e integración
  requirements.txt
  requirements-dev.txt
  pytest.ini
  run.py
frontend/
  src/             Páginas, componentes, contextos y servicios
  tests/           Pruebas Playwright
  nginx.conf
  vercel.json
keycloak/realm-export.json
scripts/tunnel/ollama_proxy.py
docs/
docker-compose.yml
.env.example
plan_desarrollo.md
```

## Requisitos e instalación de modelos

**Docker:** Git, Docker Desktop con contenedores Linux (o Docker Engine con Compose)
y Ollama instalado en el anfitrión. Python y Node del anfitrión no son necesarios
para ejecutar los contenedores.

**Desarrollo/pruebas nativas:** Python 3.11 o superior y Node.js 22 con npm. Las pruebas
locales documentadas usaron Python 3.13; el Dockerfile del frontend compila con Node 20.
Reservar espacio para imágenes y modelos. La memoria necesaria depende del contexto,
concurrencia y hardware; ejecutar Qwen 8B en CPU puede tardar minutos.

Instalar Ollama desde la [descarga oficial](https://ollama.com/download), abrirlo y ejecutar:

```powershell
ollama --version
ollama pull qwen3:8b
ollama pull nomic-embed-text
ollama list
```

No hace falta repetir los `pull` si los modelos ya están descargados. Mantener Ollama
abierto para indexar o consultar. El modo local no requiere una API de IA de pago.

## Configuración

Clonar el repositorio del equipo y abrir una terminal en la raíz. En PowerShell,
crear `.env` solo si aún no existe, conservando la configuración previa:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

En macOS/Linux: `test -f .env || cp .env.example .env`.
Las variables del proceso tienen prioridad sobre el archivo. No versionar secretos.

| Variable | Función / valor predeterminado del backend |
|---|---|
| `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | `http://localhost:11434`, `qwen3:8b` |
| `OLLAMA_EMBEDDING_MODEL`, `EMBEDDING_DIMENSION` | `nomic-embed-text`, `768` |
| `OLLAMA_TIMEOUT` | 120 segundos por llamada |
| `POSTGRES_HOST`, `POSTGRES_PORT` | `localhost`, `5432` para ejecución nativa |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Conexión; ejemplos en `.env.example` |
| `DATABASE_URL` | Alternativa con prioridad sobre las variables PostgreSQL separadas |
| `CORS_ORIGINS` | Orígenes del frontend, lista JSON o separada por comas |
| `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID` | `http://localhost:8080`, `rag-agent`, `rag-frontend` |
| `KEYCLOAK_AUDIENCE` | `account` |
| `RAG_TOP_K`, `RAG_MAX_CONTEXT_CHARS` | Hasta 4 fragmentos y presupuesto de 6000 caracteres |
| `RAG_MIN_RELEVANCE_SCORE` | `0.65`, se conservan puntuaciones estrictamente superiores |
| `RAG_SINGLE_PASS` | `false`: evaluación y generación separadas; `true`: una inferencia conjunta |
| `RAG_MAX_OUTPUT_TOKENS`, `RAG_KEEP_ALIVE` | `512`, permanencia solicitada en memoria de `15m` |
| `CHUNK_SIZE`, `CHUNK_OVERLAP` | 800 caracteres, solapamiento de 120 |
| `MAX_UPLOAD_BYTES` | 10485760 bytes (10 MiB) |
| `KNOWLEDGE_BASE_SEED_ON_STARTUP` | `true`, sincroniza la biblioteca común al arrancar |

En CPU se puede usar `RAG_SINGLE_PASS=true`. Mantiene filtro y validación de fuentes,
pero el veredicto y el borrador proceden de la misma inferencia. Reiniciar el backend
después de cambiar su configuración.

Vite lee `frontend/.env.local`, **no** el `.env` de la raíz. Si se necesitan cambios,
copiar [frontend/.env.example](frontend/.env.example) allí:

```dotenv
VITE_API_URL=http://127.0.0.1:8000
VITE_KEYCLOAK_URL=http://localhost:8080
VITE_KEYCLOAK_REALM=rag-agent
VITE_KEYCLOAK_CLIENT_ID=rag-frontend
```

Las variables `VITE_*` son públicas y se incorporan al compilar; no poner secretos.
Docker las define como argumentos de build en Compose. `FRONTEND_PORT` en `.env`
no cambia el puerto Docker: actualmente `3000:80` está escrito en Compose.

## Ejecutar con Docker

Con Docker y Ollama abiertos, desde la raíz:

```powershell
docker compose up --build -d
docker compose ps
```

| Servicio | Dirección predeterminada |
|---|---|
| Aplicación | http://localhost:3000 |
| API / Swagger | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| Administración Keycloak | http://localhost:8080/admin |
| PostgreSQL | `127.0.0.1:POSTGRES_PORT` (5432 si no se cambia) |

No iniciar otro backend en 8000 ni otro Keycloak en 8080. Si sigue activo el contenedor
antiguo `rag-keycloak`, detenerlo con `docker stop rag-keycloak`. Sus usuarios no se
transfieren automáticamente al nuevo volumen de Keycloak; detener no significa borrar.

Compose conecta internamente con `postgres:5432`, `keycloak:8080` y Ollama mediante
`host.docker.internal:11434`. Sobrescribe `DATABASE_URL` con un valor vacío para usar
PostgreSQL local. El emisor público esperado es `http://localhost:8080/realms/rag-agent`.
Si se cambia `BACKEND_PORT`, también hay que ajustar la URL del frontend compilado.

```powershell
docker compose logs -f backend
docker compose down
```

Ctrl+C sale del seguimiento de logs. `down` conserva los volúmenes; `down -v` los
elimina con sus datos. PostgreSQL guarda catálogo, fragmentos, vectores e historial;
Keycloak guarda cuentas en su volumen. El volumen de documentos no es un archivo
permanente de subidas: el código elimina los originales temporales al procesarlos.

## Autenticación y usuarios

Compose importa el realm `rag-agent` y el cliente público `rag-frontend` al crear
Keycloak. El export no crea usuarios ni actualiza un realm que ya existe.

1. Abrir la consola de administración.
2. Entrar con `KEYCLOAK_ADMIN_USER` y `KEYCLOAK_ADMIN_PASSWORD` configurados para Compose.
   Sin configuración, Compose usa los ejemplos locales `admin` y `admin_seguro_123`;
   sustituirlos para cualquier instalación publicada.
3. Seleccionar **rag-agent**, no `master`.
4. En **Users → Add user**, completar username, nombre, apellido y correo; crear.
5. En **Credentials → Set password**, asignar contraseña y desactivar **Temporary**.
   No dejar acciones requeridas pendientes para probar desde Swagger.
6. Iniciar sesión en el frontend con esa cuenta.

React usa Authorization Code + PKCE y conserva tokens en memoria. Swagger utiliza
el flujo de contraseña: **Authorize**, username/password, client_id `rag-frontend`,
client_secret vacío. Las rutas funcionales requieren token; health y documentación
son públicos. La propiedad de documentos privados e historial usa el UUID `sub`.

Para un cliente ya existente: Standard flow activo, Client authentication desactivado,
redirect `http://localhost:3000/*`, origen `http://localhost:3000` y retorno de logout
`http://localhost:3000/login`. Para Vite usar 5173. Para Swagger autorizar
`http://localhost:8000/docs/oauth2-redirect` o su variante `127.0.0.1`, según se utilice.

El export actual también contiene comodines de nube y `webOrigins="*"`. Hay una
discrepancia con una prueba existente (ver Tests); antes de publicar, usar direcciones
concretas del proyecto. Cambiar el JSON no actualiza automáticamente un realm existente.

## Ejecutar backend y frontend en desarrollo

Esta alternativa ejecuta Python y Vite en el anfitrión. Desde la raíz:

```powershell
docker compose up -d postgres keycloak
```

Si el stack completo ya estaba activo, detener solo sus servicios backend y frontend:
`docker compose stop backend frontend`. Mantener Ollama abierto.
En `.env`, usar `POSTGRES_HOST=127.0.0.1` y el puerto publicado de PostgreSQL; revisar
que `DATABASE_URL` no esté apuntando a otra base.

**Backend en PowerShell:**

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe run.py
```

No recrear el entorno si ya existe. En macOS/Linux usar `python3 -m venv .venv` y
`.venv/bin/python`. `run.py` selecciona el event loop compatible con psycopg en Windows.
Para el puerto, lee `PORT`, luego `BACKEND_PORT` del proceso, o usa 8000. El script no
carga `.env` para elegir el puerto: en PowerShell se puede establecer
`$env:BACKEND_PORT='8001'` antes de ejecutarlo.

**Frontend, otra terminal desde la raíz:**

```powershell
cd frontend
npm ci
npm run dev
```

Abrir http://localhost:5173. En siguientes arranques basta `npm run dev` si las
dependencias no cambiaron. `npm run build` compila para producción. Si cambia la
dirección de API, ajustar Vite, CORS y Keycloak según corresponda.

## Documentos y ejemplos

La biblioteca común incluye [Mundiales_documento_RAG.pdf](backend/knowledge_base/Mundiales_documento_RAG.pdf).
Se sincroniza en segundo plano al arrancar. Esperar **Base de conocimiento global
sincronizada** y actualizar el listado. Archivos sin cambios se omiten; nuevos o
modificados se indexan. Retirar un archivo de la carpeta común retira su contenido
global al sincronizar. El propietario global es `system:global`.

Para archivos propios: **Documentos → Seleccionar archivo → Subir documento**.
Se admiten PDF con texto, TXT UTF-8 y DOCX. La extracción conserva páginas PDF,
divide texto, calcula embeddings por lotes y guarda catálogo y fragmentos en una
transacción. Los originales temporales se eliminan: no hay descarga del archivo
original. Los registros antiguos sin propietario no pasan a ser globales ni se
asignan automáticamente; consultar [historial y autenticación](docs/history-auth.md).

Prueba manual:

1. Crear `prueba.txt`: «La copa de prueba Aurora 2040 la ganó el equipo Cóndor Azul».
2. Subirlo y esperar **Listo para consultar**.
3. Preguntar «¿Qué equipo ganó la copa de prueba Aurora 2040?»; comprobar Cóndor Azul
   y la fuente `prueba.txt`.
4. Preguntar el salario exacto de su entrenador, ausente del documento. Se espera rechazo.
5. Abrir Historial y recargar. Otra cuenta no debe ver ese archivo ni conversación.

Hay también [documentos deportivos de ejemplo](docs/examples/deportes/mundial-2022.txt).
En Swagger, autenticarse y enviar a `POST /api/chat/rag`:

```json
{"question":"¿Qué equipo ganó la copa de prueba Aurora 2040?"}
```

La respuesta contiene `answer`, `sources` y `conversation_id`. Cada fuente contiene
`document`, `page` (puede ser null) y `chunk_index` (base cero en API). Para continuar
una conversación enviar su ID. Sus mensajes previos **no** se añaden al prompt;
formular cada pregunta de forma completa.

## RAG, LangGraph y control de alucinaciones

RAG recupera información antes de generar. Se calcula el embedding de la pregunta,
se buscan fragmentos por distancia coseno y se combinan documentos globales con los
del usuario, filtrando propietarios antes del límite de resultados. Se evalúa la
relevancia como `1 - distance` y se aplica el umbral configurado.

El [grafo](backend/app/agents/graph.py) recorre
`receive_question → validate_question → retrieve_context → grade_context`.
Según suficiencia, pasa a `generate_answer` o `reject_question`; ambas ramas terminan
en `save_interaction`. El generador también puede solicitar rechazo.

El evaluador recibe el contexto limitado que se usará para responder. Las instrucciones
piden ignorar órdenes de los documentos, responder hechos respaldados y rechazar
información parcial o contradictoria. Se valida JSON, pertenencia de referencias
al contexto y se eliminan citas repetidas. Sin respaldo, devuelve:

> No tengo suficiente información en mi base de conocimiento para responder esa pregunta.

Si no hay fragmentos que superen el filtro, no se llama al modelo. Un fallo técnico
de Ollama produce un error controlado, no un rechazo por falta de conocimiento.
Validar que una fuente exista no demuestra que sustente cada afirmación generada.

## Tests

Desde `backend/`:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -m unit -q
# Con PostgreSQL y Ollama activos; tablas y esquemas aislados:
.venv\Scripts\python.exe -m pytest -m integration --run-integration -q
```

No ejecutar integraciones sobre producción. El LLM se simula en pruebas de contratos;
las de documentos/búsqueda usan embeddings reales. Para el navegador, desde `frontend/`:

```powershell
npm run test:e2e
```

Playwright usa Edge en Windows. Para Chromium en otros entornos:
`npx playwright install chromium`. Las pruebas de navegador simulan API/OIDC;
no son consultas completas a Qwen con credenciales reales.

**Evidencia histórica:** fase 14 registró 82 pruebas aisladas y 6 integraciones
aprobadas; fase 12 registró 8 de navegador. Ver [casos y resultados](docs/test-cases.md).
No certifican los commits posteriores. El export modificado en fase 15 contiene
`*` en `webOrigins`, mientras
`test_integration_contract.py::BrowserContractTests::test_export_supports_login_logout_and_swagger`
lo prohíbe. Esta discrepancia está pendiente; fase 16 documenta el estado sin cambiar
la configuración ni las aserciones para ocultarla.

## Despliegue

Existe preparación para una arquitectura híbrida: frontend en Vercel/Netlify,
backend en Render, PostgreSQL/pgvector en Neon y Ollama en un computador conectado
por túnel. Keycloak necesita una dirección pública accesible al navegador. No se ha
verificado aquí una URL publicada: clonar o arrancar Compose no despliega en la nube.

La [guía de despliegue](docs/deployment.md) describe el procedimiento. Sus cifras de
planes, cuotas y costos son referencias del documento, no garantías vigentes;
verificar las condiciones del proveedor antes de publicar.

Soporte presente en el código:

- Puerto `PORT`, URLs y CORS configurables, reescrituras SPA para Vercel.
- `DATABASE_URL`: el código cambia `-pooler.` por `.` para usar conexión directa.
- `OLLAMA_API_KEY`: Bearer compartido con el proxy para generación y embeddings;
  no es una clave de un proveedor de IA de pago.
- `scripts/tunnel/ollama_proxy.py`: escucha en 127.0.0.1:11435, genera un secreto
  si no se proporciona y lo muestra en terminal. `/health` y `/ping` son públicos;
  las demás peticiones requieren autenticación. No compartir logs con ese secreto.
- `KEYCLOAK_ISSUER_OVERRIDE` separa emisor público y dirección interna.
  `KEYCLOAK_JWKS_URL` permite certificados remotos; `KEYCLOAK_JWKS_JSON` permite
  claves públicas configuradas sin consulta HTTP. Hay que actualizar esa copia
  cuando se rotan las claves; no sustituye el login de Keycloak.

Para el modo híbrido se requiere proxy y túnel, su URL/secreto en el backend remoto
y direcciones concretas en frontend/CORS/Keycloak. Compose local no requiere túneles.
Sin el equipo que ejecuta Ollama no hay chat ni indexación de nuevas subidas. Si
Keycloak también depende de ese equipo, se afecta el acceso. Los datos locales
no se migran automáticamente a Neon ni entre instancias de Keycloak.

## Limitaciones y diagnóstico

| Situación | Comprobación |
|---|---|
| Puerto ocupado | Detener backend nativo o Keycloak antiguo; revisar `docker compose ps` |
| `invalid_redirect_uri` | Autorizar la URL exacta en el cliente del realm existente |
| Cuenta incompleta | Completar perfil/acciones requeridas y revisar contraseña temporal |
| Ollama no conecta | Abrirlo, comprobar `ollama list`, logs y acceso desde Docker al host |
| Biblioteca vacía | Esperar sincronización, actualizar listado y revisar logs del backend |
| API devuelve 401 | Revisar sesión, emisor, audiencia y cliente; no compartir tokens |
| Variables Vite sin efecto | Reconstruir frontend: se incorporan al build |
| Health correcto y chat falla | Health comprueba la API, no todos los servicios externos |

La muestra local con Qwen 8B en CPU bajó de 212,8 a 111,7 segundos al usar una
inferencia. No es promedio ni garantía; ver [medición](docs/performance/colombia-latency.md).
6000 caracteres de contexto no garantizan rapidez. Publicar el backend no acelera
Qwen si sigue ejecutándose en el mismo equipo.

No hay OCR para PDFs escaneados, búsqueda web, memoria conversacional en el prompt
ni descarga de originales. Cambiar modelo/dimensión de embeddings requiere reindexar
los datos compatibles. La información del corpus puede estar desactualizada.

## Estado del proyecto

- Fases 1–13: backend, RAG, autenticación, historial, frontend, integración y Compose.
- Fase 14: organización de pruebas con pytest y matriz de resultados.
- Fase 15: preparación de despliegue; no implica publicación verificada.
- Fase 16: README contrastado con código, equipo e instrucciones de ejecución.
- Fases 17–20: pendientes según [plan_desarrollo.md](plan_desarrollo.md).

Guías: [frontend](docs/frontend.md), [integración y checklist](docs/phase12.md),
[Docker](docs/phase13.md), [autenticación e historial](docs/history-auth.md),
[control de respuestas](docs/phase8.md), [pruebas](docs/test-cases.md) y
[despliegue](docs/deployment.md). Las guías por fase son registros de su momento;
para arranque y limitaciones actuales usar este README y el código vigente.
