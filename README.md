#  RAG Agent — Agente Inteligente con Retrieval-Augmented Generation

Proyecto académico de un agente inteligente basado en **RAG** (Retrieval-Augmented Generation) que utiliza modelos de lenguaje locales para responder preguntas exclusivamente a partir de documentos cargados por el usuario.

## Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Backend | Python, FastAPI |
| Frontend | React, Vite, JavaScript |
| LLM Local | Ollama, Qwen |
| Orquestación IA | LangChain, LangGraph |
| Base Vectorial | PostgreSQL + pgvector |
| Contenedores | Docker, Docker Compose |

## Estructura del Repositorio

```
trabajo_agentes/
├── backend/           # API REST con FastAPI
│   ├── app/
│   │   ├── api/           # Endpoints / rutas
│   │   ├── agents/        # Agente LangGraph
│   │   ├── core/          # Configuración, excepciones, logging
│   │   ├── models/        # Modelos SQLAlchemy
│   │   ├── schemas/       # Schemas Pydantic
│   │   ├── services/      # Lógica de negocio
│   │   ├── repositories/  # Acceso a datos
│   │   └── vectorstore/   # Integración pgvector
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/          # Interfaz React + Vite
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── data/
│   └── documents/     # Documentos cargados
├── docs/
│   └── diagrams/      # Diagramas de arquitectura
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

## Requisitos Previos

- **Python** 3.11+
- **Node.js** 18+
- **Docker** y **Docker Compose** (opcional para desarrollo)

## Inicio Rápido

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

El backend estará disponible en: **http://localhost:8000**

Verifica con: `GET http://localhost:8000/health`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

El frontend estará disponible en: **http://localhost:5173**

### Docker Compose

```bash
docker compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000

## Fase 2 — Ollama + Qwen

El backend permite enviar un prompt a Ollama mediante `ChatOllama` de LangChain.
Este endpoint es una prueba de generación libre: todavía no consulta documentos ni implementa RAG.

### Instalar y ejecutar Ollama

1. Instala Ollama desde [la página oficial](https://ollama.com/download) y vuelve a abrir la terminal.
2. Abre la aplicación Ollama. Si el servidor no está activo, ejecuta `ollama serve` en una terminal aparte.
   Si indica que el puerto 11434 ya está ocupado, comprueba `ollama list`: puede que Ollama ya esté activo.
3. Descarga el modelo y comprueba su instalación:

```powershell
ollama pull qwen3:8b
ollama list
```

La descarga ocupa varios GB. Opcionalmente prueba el modelo en consola con `ollama run qwen3:8b`;
usa `/bye` para salir del chat. Estos comandos siguen la [guía de Ollama](https://docs.ollama.com/quickstart).

### Configurar y ejecutar el backend

Desde la raíz del repositorio, crea `.env` si aún no existe:

```powershell
Copy-Item .env.example .env
```

Si ya tienes `.env`, añade o actualiza estas variables sin reemplazar tus otros valores:

```dotenv
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
OLLAMA_TEMPERATURE=0
OLLAMA_TIMEOUT=120
```

`OLLAMA_TIMEOUT` limita la generación completa en segundos. La temperatura debe estar entre 0 y 2.
El backend carga el `.env` de la raíz aunque lo ejecutes desde `backend/`; las variables del proceso tienen prioridad.
Reinicia el backend después de cambiar la configuración. Para otro modelo, descárgalo con `ollama pull`
y cambia `OLLAMA_MODEL` por su nombre exacto.

```powershell
cd backend
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

En Linux/macOS utiliza `.venv/bin/python` en lugar de `.venv\Scripts\python.exe`.
Si usas el Docker Compose existente en Docker Desktop, establece en `.env`
`OLLAMA_BASE_URL=http://host.docker.internal:11434` para acceder al Ollama del host.

### Probar el endpoint

Abre http://localhost:8000/docs, selecciona `POST /api/test-llm`, pulsa **Try it out** y envía:

```json
{"prompt": "Responde en una frase: ¿qué es una API?"}
```

Respuesta esperada (el texto generado puede variar):

```json
{"response": "Una API es una interfaz que permite que distintas aplicaciones se comuniquen."}
```

Con PowerShell:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/test-llm -Method Post -ContentType 'application/json' -Body '{"prompt":"Saluda en una frase."}'
```

Con curl en Bash:

```bash
curl -X POST http://localhost:8000/api/test-llm \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Saluda en una frase."}'
```

Con `curl.exe` en Windows PowerShell, usa un archivo para evitar problemas de comillas:

```powershell
'{"prompt":"Saluda en una frase."}' | Set-Content -Encoding ascii prompt.json
curl.exe http://localhost:8000/api/test-llm -H "Content-Type: application/json" --data-binary "@prompt.json"
```

| Código HTTP | Significado | Qué revisar |
|---|---|---|
| 200 | Respuesta generada | Campo `response` |
| 422 | Prompt ausente, vacío o mayor de 16000 caracteres | Body JSON |
| 503 | Ollama inaccesible o modelo no disponible | `ollama list`, URL y `ollama pull qwen3:8b` |
| 504 | Tiempo de generación excedido | Recursos del equipo o aumentar `OLLAMA_TIMEOUT` |
| 502 | Error del proveedor o respuesta vacía | Estado y registros de Ollama |

Los errores contienen un campo `detail` con una explicación. `GET /health` sigue comprobando únicamente
que el backend está activo; no depende de que Ollama esté disponible.

### Archivos y pruebas

- `backend/app/core/config.py`: configuración validada por entorno.
- `backend/app/services/llm_service.py`: generación asíncrona, timeout y errores de Ollama.
- `backend/app/schemas/llm.py`: validación de entrada y respuesta.
- `backend/app/api/routes/llm.py`: endpoint y traducción de errores a HTTP.
- `backend/tests/test_llm.py`: contrato HTTP, configuración y casos de error sin requerir un modelo real.

La integración utiliza la [API oficial de ChatOllama](https://reference.langchain.com/python/langchain-ollama/chat_models/ChatOllama).
Ejecuta las pruebas desde `backend/`:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Para verificar manualmente los errores, configura temporalmente un modelo inexistente (503),
un puerto de Ollama sin servidor (503) o un timeout muy pequeño (504), reiniciando el backend en cada caso.
Restaura después los valores anteriores.

### Verificación de cierre de la fase 2

Verificada localmente el 22 de septiembre de 2026 con `qwen3:8b` instalado en Ollama.
Se inició una instancia temporal de Uvicorn y se hicieron solicitudes HTTP reales,
sin sustituir el modelo ni el servicio por mocks en esta prueba de integración.

| Comprobación | Resultado |
|---|---|
| `GET /health` | 200, `{"status":"ok"}` |
| `GET /docs` | 200 |
| `POST /api/test-llm` con Qwen real | 200, respuesta en 12,67 segundos |
| Prompt con solo espacios | 422 |
| `python -m unittest discover -s tests -v` desde `backend/` | 8 pruebas aprobadas |
| `python -m pip check` | Sin conflictos de dependencias |

Prompt enviado: `Responde en una sola frase en espanol: que es una API?`

Respuesta obtenida:

```json
{"response":"Una API es un conjunto de protocolos y herramientas que permite a diferentes aplicaciones comunicarse y compartir datos."}
```

La fase 2 queda cerrada. La fase 3 puede continuar conservando el contrato de
`POST /api/test-llm` y el funcionamiento de `GET /health`. Cada integrante necesita
su propio `.env`, Ollama y el modelo descargado para repetir la prueba real.

## Fase 3 — Arquitectura de FastAPI y verificación

`app/main.py` construye la aplicación mediante `create_app()`. El router
`app/api/router.py` agrupa las rutas `/api`; `core/config.py` centraliza la
configuración con Pydantic Settings, `core/exceptions.py` registra los manejadores
globales de errores y `core/logging.py` configura los mensajes de consola.
El servicio LLM conserva la integración de la fase 2.

Se mantienen `GET /health` y su alias `GET /api/health`, ambos con
`{"status":"ok"}`. La configuración carga el `.env` de la raíz mediante una ruta
absoluta basada en el archivo de código, independiente del directorio de ejecución.

Variables adicionales opcionales en `.env`:

```dotenv
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:5173"]
```

`CORS_ORIGINS` debe ser un array JSON. Reinicia el backend después de modificar `.env`.
Para observar el mensaje del health check, usa temporalmente `LOG_LEVEL=DEBUG`.

Desde la raíz del repositorio:

```powershell
cd backend
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Abre http://localhost:8000/docs y prueba `POST /api/test-llm` como en la fase 2.
Las pruebas automatizadas simulan fallos intencionados y pueden imprimir mensajes
`ERROR`; el resultado final esperado de unittest es `OK`.

Verificación del 1 de octubre de 2026:

- 12 pruebas automatizadas aprobadas: rutas, contrato LLM, errores globales,
  timeout, validación, configuración y CORS.
- Dependencias sin conflictos (`pip check`).
- Arranque real de Uvicorn desde la raíz con `--app-dir backend`.
- `/health`, `/api/health` y `/docs`: HTTP 200.
- Qwen real (`qwen3:8b`) mediante `POST /api/test-llm`: HTTP 200 en 13,12 segundos.
  Respondió: “Una API es un conjunto de protocolos y herramientas que permite a
  diferentes aplicaciones comunicarse y compartir datos de manera estructurada.”

La fase 3 queda verificada. La fase 4 pendiente incorpora embeddings locales,
PostgreSQL con pgvector y los endpoints de prueba de almacenamiento y búsqueda
semántica definidos en `plan_desarrollo.md`.

## Fase 4 — Embeddings locales y pgvector

Se guardan fragmentos manuales y se recuperan por similitud semántica. Todavía no
hay carga de archivos ni respuestas RAG. Qwen sigue atendiendo `/api/test-llm`;
`nomic-embed-text` convierte textos y consultas en vectores de 768 dimensiones.

### Preparación

Abre Docker Desktop y Ollama. Desde la raíz del proyecto:

```powershell
ollama pull nomic-embed-text
docker compose up -d postgres
docker compose ps postgres
```

Antes de levantar PostgreSQL, revisa estas variables de `.env` (añádelas sin
sobrescribir tu configuración existente; `.env.example` incluye los valores):

```dotenv
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSION=768
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ragdb
POSTGRES_USER=raguser
POSTGRES_PASSWORD=ragpassword
VECTOR_TABLE=document_chunks
POSTGRES_CONNECT_TIMEOUT=5
POSTGRES_STATEMENT_TIMEOUT=30000
```

En el equipo donde se verificó esta fase, Windows bloqueaba el puerto 5432:
se configuró **`POSTGRES_PORT=55432` en el `.env` local** y `POSTGRES_HOST=127.0.0.1`
para conectar directamente por IPv4. Si ocurre lo mismo,
usa ese puerto y vuelve a ejecutar `docker compose up -d postgres`.
El puerto interno del contenedor siempre es 5432.

También puedes definir `DATABASE_URL=postgresql+psycopg://raguser:ragpassword@localhost:5432/ragdb`.
Cuando no está vacía, tiene prioridad sobre `POSTGRES_*`; ajusta su puerto si usas 55432.
Se aceptan URI `postgresql://` y el formato `postgresql+psycopg://` del plan.
En Docker Compose el backend utiliza los campos `POSTGRES_*` y el host `postgres`.
Las credenciales iniciales de PostgreSQL se aplican al crear el volumen por primera vez.

Después, inicia el backend:

```powershell
cd backend
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Al primer uso de los endpoints vectoriales se ejecuta `CREATE EXTENSION IF NOT EXISTS vector`
y se crea la tabla si hace falta. La imagen de Docker ya contiene pgvector; una instalación
externa de PostgreSQL necesita esa extensión y un usuario con permisos para crearla.
El backend y `/health` pueden arrancar aunque PostgreSQL u Ollama estén apagados.

### Prueba manual en Swagger o curl

Abre http://localhost:8000/docs. En `POST /api/vector/test-add`, pega el contenido de
[`docs/examples/vector-add.json`](docs/examples/vector-add.json) y pulsa **Execute**.
Debe devolver **201**, `document_id`, tres `ids` y `chunks_created: 3`.

Después prueba `POST /api/vector/test-search`:

```json
{"query":"¿Qué mascota ronronea y atrapa ratones?","k":2}
```

Debe devolver **200** con `results`: el primer fragmento debe ser `gatos.txt`.
Cada resultado incluye `id`, `document_id`, `filename`, `page`, `chunk_index`,
`content`, `metadata` y `distance`. Una distancia coseno menor significa mayor similitud;
no es una probabilidad de que el texto sea correcto. Una tabla vacía devuelve `results: []`.

Desde otra terminal en la raíz del repositorio, los mismos ejemplos con curl:

```powershell
curl.exe http://localhost:8000/api/vector/test-add -H "Content-Type: application/json" --data-binary "@docs/examples/vector-add.json"
curl.exe http://localhost:8000/api/vector/test-search -H "Content-Type: application/json" --data-binary "@docs/examples/vector-search.json"
```

En Bash sustituye `curl.exe` por `curl`. Los archivos evitan problemas de comillas
y conservan el texto UTF-8. Cada llamada a `test-add` agrega nuevos registros;
repetirla crea otro lote. Puedes enviar un `document_id` UUID; si se omite, se genera uno.
`chunk_index` se numera desde cero dentro de cada lote.

### Almacenamiento y errores

La tabla configurable contiene `id`, `document_id`, `filename`, `page`, `chunk_index`,
`content`, `embedding VECTOR(768)`, `embedding_model` y `metadata JSONB`.
Los lotes se insertan en una transacción: si falla una fila no se guarda parte del lote.
La búsqueda Top-K usa el operador `<=>` de pgvector, con orden ascendente y `LIMIT`.
Solo se consultan registros del modelo de embeddings configurado. No se mantiene una copia en memoria.

Si cambias de modelo, ajusta `EMBEDDING_DIMENSION` y usa otra `VECTOR_TABLE` para reindexar
los textos. La aplicación no redimensiona ni elimina los vectores existentes.
Para Nomic se aplican los prefijos `search_document:` y `search_query:` que recomienda
su [ficha oficial](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5).
La conexión sigue el [adaptador oficial de pgvector para Psycopg](https://github.com/pgvector/pgvector-python).

| Código | Situación |
|---|---|
| 422 | Texto vacío, lote fuera de 1–50 fragmentos, texto mayor de 8000 caracteres o `k` fuera de 1–50 |
| 409 | Dimensión del modelo o de la tabla incompatible con la configuración |
| 502 | Respuesta de embeddings inválida o error del proveedor |
| 503 | Ollama/modelo no disponible o error de conexión, permisos o esquema de PostgreSQL |
| 504 | Tiempo de espera de embeddings excedido |

El volumen `postgres_data` conserva los datos al reiniciar o recrear el contenedor.
Puedes detener PostgreSQL con `docker compose stop postgres` y levantarlo de nuevo con
`docker compose up -d postgres`. `docker compose down -v` elimina el volumen y sus datos.

### Pruebas y archivos

Desde `backend/`, las pruebas normales no requieren servicios externos:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

La prueba real necesita Ollama con `nomic-embed-text` y PostgreSQL en ejecución:

```powershell
$env:TEST_VECTOR_INTEGRATION="1"
.venv\Scripts\python.exe -m unittest tests.test_vector_integration -v
Remove-Item Env:TEST_VECTOR_INTEGRATION
```

Esta prueba utiliza una tabla con nombre único y la elimina al terminar; comprueba
base vacía, recuperación semántica, metadatos, persistencia con nuevas conexiones,
dimensiones, separación por modelo y reversión de lotes inválidos.

Archivos añadidos:

- `app/services/embedding_service.py`: embeddings y errores de Ollama.
- `app/vectorstore/postgres.py`: conexión, tabla, transacciones y búsqueda SQL.
- `app/services/vector_service.py`: coordinación entre embeddings y PostgreSQL.
- `app/schemas/vector.py` y `app/api/routes/vector.py`: contratos y endpoints.
- `tests/test_vector.py` y `tests/test_vector_integration.py`: pruebas unitarias e integración.
- `docs/examples/vector-*.json`: ejemplos reproducibles.

### Verificación de cierre (1 de octubre de 2026)

- 22 pruebas unitarias aprobadas y una prueba de integración real aprobada.
- FastAPI ejecutado con Uvicorn: `/health`, `/api/health` y `/docs` respondieron 200.
- Inserción HTTP de tres fragmentos: 201 y `chunks_created: 3`.
- Consulta HTTP “¿Qué mascota ronronea y atrapa ratones?”: 200 y `gatos.txt`
  en primer lugar, distancia `0.296633`; segundo resultado `pan.txt`, distancia `0.438418`.
- PostgreSQL confirmó tres filas con vectores de 768 dimensiones en la prueba aislada.
- Se verificaron conexiones nuevas, metadatos, lote inválido sin inserción parcial,
  separación por modelo y rechazo de dimensión incompatible.
- Dependencias sin conflictos mediante `pip check`.

Los tres textos de los ejemplos se dejaron en `document_chunks` de la base local para
repetir la búsqueda desde Swagger. Las tablas aisladas de integración se eliminan al finalizar.
PostgreSQL queda ejecutándose; el servidor temporal de verificación de FastAPI se cerró.

## Estado del Proyecto

- [x] Fase 1 — Estructura inicial
- [x] Fase 2 — Integrar Ollama + Qwen
- [x] Fase 3 — Arquitectura profesional FastAPI
- [x] Fase 4 — Embeddings y PostgreSQL con pgvector
- [ ] Fase 5 — Carga y procesamiento de documentos
- [ ] Fase 6 — RAG básico
- [ ] Fase 7 — Agente con LangGraph
- [ ] Fase 8 — Control de alucinaciones
- [ ] Fase 9 — Base de datos para historial
- [ ] Fase 10 — Autenticación y seguridad
- [ ] Fase 11 — Frontend React
- [ ] Fase 12 — Integración completa
- [ ] Fase 13 — Docker Compose
- [ ] Fase 14 — Testing
- [ ] Fase 15 — Preparación para despliegue


