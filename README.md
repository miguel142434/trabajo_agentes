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

## Fase 5 — Carga de documentos deportivos

Dominio elegido por el equipo: **deportes**, con Mundiales de fútbol y Fórmula 1
como ejemplos iniciales. Consulta [la guía del dominio](docs/dominio-deportivo.md).
El contenido lo aportan los documentos cargados; esta fase aún no redacta respuestas RAG.

Flujo: archivo → validación → archivo temporal → extracción → fragmentos → embeddings
locales → PostgreSQL/pgvector → confirmación.

### Ejecución y configuración

Desde la raíz, con Docker Desktop y Ollama abiertos:

```powershell
docker compose up -d postgres
cd backend
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Los valores predeterminados funcionan sin modificar tu `.env`; `.env.example` incluye:

```dotenv
CHUNK_SIZE=800
CHUNK_OVERLAP=120
MAX_UPLOAD_BYTES=10485760
MAX_DOCUMENT_CHARS=2000000
MAX_DOCUMENT_CHUNKS=3000
DOCUMENT_TABLE=uploaded_documents
```

El tamaño y solapamiento se miden en caracteres. El solapamiento debe ser menor que
el tamaño, que tiene un máximo de 8000 caracteres. El splitter puede generar
fragmentos menores según los separadores y los límites de página. El archivo tiene
un máximo predeterminado de 10 MiB. Reinicia el backend tras cambiar la configuración.

### Prueba desde Swagger

1. Abre http://localhost:8000/docs.
2. En `POST /api/documents/upload`, pulsa **Try it out** y selecciona un PDF, TXT o DOCX.
   Puedes comenzar con `docs/examples/deportes/mundial-2022.txt`.
3. Pulsa **Execute**. Espera un **201** con esta estructura:

```json
{
  "document_id": "<UUID generado>",
  "filename": "mundial-2022.txt",
  "chunks_created": 1,
  "status": "processed"
}
```

La cantidad de fragmentos depende del texto y de la configuración.

4. Ejecuta `GET /api/documents`. Devuelve una lista de documentos procesados, con
   identificador, nombre, tipo, tamaño, fecha, modelo y número de fragmentos.
5. Prueba `POST /api/vector/test-search`:

```json
{"query":"¿Qué selección ganó el Mundial de fútbol de 2022?","k":1}
```

El fragmento recuperado aparece en `results[0].content`; los datos de procedencia
están en sus columnas y en `metadata`. Puedes repetir el proceso con `f1-2024.txt`.

### Ejemplos curl

Desde la raíz del repositorio, en otra terminal:

```powershell
curl.exe http://localhost:8000/api/documents/upload -F "file=@docs/examples/deportes/mundial-2022.txt"
curl.exe http://localhost:8000/api/documents/upload -F "file=@docs/examples/deportes/f1-2024.txt"
curl.exe "http://localhost:8000/api/documents?limit=100&offset=0"
```

En Bash usa `curl`. No añadas manualmente `Content-Type`: curl genera el multipart
con su delimitador. `limit` admite 1–500; `offset` permite recorrer el listado,
ordenado del más reciente al más antiguo.

### Persistencia, validaciones y límites

- PDF: texto por página con numeración desde 1. No se realiza OCR y se rechazan
  archivos protegidos por contraseña. Un PDF sin texto extraíble produce 422.
- TXT: UTF-8, con o sin BOM. Se rechazan contenidos binarios o vacíos.
- DOCX: párrafos y tablas del cuerpo en orden. No se procesan imágenes, encabezados,
  pies de página ni contenido multimedia; `page` es `null`, igual que en TXT.
- Cada fragmento guarda `document_id`, `filename`, `file_type`, `page` y `chunk_index`
  en JSONB, además de las columnas de búsqueda existentes.
- Los embeddings se solicitan en lotes de hasta 32 fragmentos. Solo al terminar
  se guardan el registro del documento y todos sus fragmentos en una transacción.
- Si falla la extracción, Ollama o PostgreSQL, no se publica un documento parcialmente
  procesado. Los archivos temporales se eliminan al terminar o fallar la petición.
- Los originales no se conservan: lo persistido es el texto fragmentado, sus vectores
  y el registro del documento. `UPLOAD_DIR` permite cambiar la carpeta temporal;
  por defecto se utiliza `data/documents/`, ignorada por Git.
- Subir el mismo archivo otra vez crea un documento con UUID nuevo. Esta fase no
  incluye deduplicación, eliminación, historial ni autenticación.
- El listado incluye archivos subidos para `VECTOR_TABLE`, aunque se haya cambiado
  después el modelo. La búsqueda sigue filtrando por el modelo configurado.
  Los textos manuales de la fase 4 no aparecen como archivos en `/api/documents`.

| Código | Situación |
|---|---|
| 201 | Documento procesado e indexado |
| 413 | Límite de tamaño, texto extraído, DOCX descomprimido o cantidad de fragmentos excedido |
| 415 | Extensión distinta de PDF, TXT o DOCX |
| 422 | Archivo vacío, inválido, sin texto, cifrado o nombre no válido |
| 409/502/503/504 | Errores de dimensión, embeddings o PostgreSQL documentados en la fase 4 |

### Arquitectura y pruebas

Se añadieron `services/file_storage.py`, `services/text_extraction.py`,
`services/chunking_service.py` y `services/document_service.py`, junto con
`schemas/document.py` y `api/routes/documents.py`. Se reutilizan `EmbeddingService`
y `PostgresVectorStore`; este último registra también los archivos en `DOCUMENT_TABLE`.

La división utiliza [RecursiveCharacterTextSplitter](https://reference.langchain.com/python/langchain-text-splitters/character/RecursiveCharacterTextSplitter).
La extracción utiliza pypdf y [python-docx](https://python-docx.readthedocs.io/en/latest/).

Desde `backend/`, pruebas sin servicios externos:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Para incluir la integración real (Ollama y PostgreSQL encendidos):

```powershell
$env:TEST_VECTOR_INTEGRATION="1"
.venv\Scripts\python.exe -m unittest discover -s tests -v
Remove-Item Env:TEST_VECTOR_INTEGRATION
```

Las pruebas generan PDF, TXT y DOCX en temporales, comprueban la limpieza y los
errores y usan tablas de integración aisladas. Esas tablas se eliminan al terminar.

### Verificación de cierre (2 de octubre de 2026)

- 37 pruebas aprobadas, incluidas las integraciones reales de las fases 4 y 5.
- Sin conflictos de dependencias (`pip check`).
- Carga real de PDF, TXT y DOCX con Ollama y PostgreSQL, listado mediante conexiones
  nuevas, metadatos correctos y búsqueda del fragmento deportivo esperado.
- Reversión verificada: una inserción vectorial inválida no deja el documento
  registrado ni sus fragmentos parcialmente guardados.
- Uvicorn y HTTP real: carga de `mundial-2022.txt` y `f1-2024.txt` con 201,
  listado con 200 y búsqueda de ambos con 200. Distancias del primer resultado:
  `0.172077` para el campeón del Mundial 2022 y `0.281785` para el cuarto título de Verstappen.
- Ambos ejemplos deportivos quedaron indexados en la base local. No quedaron
  archivos temporales TXT tras esas cargas. El servidor temporal de verificación se cerró.

## Fase 6 — RAG básico con respuestas y fuentes

`POST /api/chat/rag` conecta la recuperación documental con Qwen:
pregunta → embeddings → Top-K en pgvector → contexto → prompt de LangChain
→ Qwen a temperatura 0 → respuesta y fuentes.

### Probar desde Swagger

Con PostgreSQL y Ollama encendidos, inicia el backend como en la fase 5 y abre
http://localhost:8000/docs. Primero carga los documentos deportivos de ejemplo si
aún no aparecen en `GET /api/documents`. Después ejecuta `POST /api/chat/rag`:

```json
{"question":"¿Qué selección ganó el Mundial de fútbol de 2022?"}
```

La respuesta tiene este formato (el texto exacto puede variar):

```json
{
  "answer": "Argentina ganó el Mundial masculino de fútbol de 2022.",
  "sources": [{"document":"mundial-2022.txt","page":null,"chunk_index":0}]
}
```

`answer` es la respuesta redactada por Qwen. `sources` identifica los fragmentos
que el modelo citó entre los que recibió; sus nombres y páginas los completa el
backend desde la base, no desde nombres inventados por el modelo. TXT y DOCX
conservan `page: null`; PDF conserva el número de página.

Prueba también una pregunta sin información en esos documentos:

```json
{"question":"¿Cuál es la composición química de la atmósfera de Venus?"}
```

Resultado esperado para ese corpus:

```json
{
  "answer":"No tengo suficiente información en mi base de conocimiento para responder esa pregunta.",
  "sources":[]
}
```

Ambos son resultados HTTP 200: el rechazo por falta de información es una respuesta
válida. Una base sin fragmentos del modelo configurado se rechaza sin llamar a Qwen.
Los fallos de Ollama o PostgreSQL conservan sus códigos de error y no se confunden
con falta de conocimiento.

Desde la raíz del repositorio:

```powershell
curl.exe http://localhost:8000/api/chat/rag -H "Content-Type: application/json" --data-binary "@docs/examples/rag-question.json"
curl.exe http://localhost:8000/api/chat/rag -H "Content-Type: application/json" --data-binary "@docs/examples/rag-outside-domain.json"
```

### Configuración y alcance

```dotenv
RAG_TOP_K=4
RAG_MAX_CONTEXT_CHARS=6000
```

La pregunta admite hasta 2000 caracteres. `RAG_TOP_K` admite 1–20 fragmentos y
`RAG_MAX_CONTEXT_CHARS` limita el texto documental enviado (100–12000 caracteres).
Si un fragmento excede el presupuesto restante, se envía solo su inicio.
Para RAG se fuerza temperatura 0, salida JSON y una ventana de 8192 tokens.
`/api/test-llm` conserva su configuración y generación libre anterior.

El prompt exige responder solo con el contexto y tratar las instrucciones dentro
de los documentos como datos. Una respuesta sin referencias se convierte en rechazo;
JSON inválido o referencias inexistentes producen 502. Se eliminan referencias repetidas.
Esto verifica la procedencia de las referencias, no demuestra automáticamente que
todas las afirmaciones del modelo estén respaldadas. La fase 7 incorpora el grader
básico del grafo; la fase 8 reforzará la evaluación y añadirá umbrales de relevancia.

La especialización deportiva depende de los documentos almacenados. Este endpoint
no busca en internet ni filtra automáticamente documentos por deporte. No incluye
memoria conversacional ni autenticación. Desde la fase 7 se ejecuta mediante LangGraph.

### Separación de responsabilidades

- `services/rag_retriever.py`: recupera fragmentos usando el servicio vectorial existente.
- `services/rag_prompt.py`: construye contexto e instrucciones con `ChatPromptTemplate`.
- `services/rag_service.py`: coordina la generación con el servicio LLM existente.
- `services/rag_sources.py`: valida y formatea las referencias.
- `schemas/rag.py` y `api/routes/chat.py`: contrato y endpoint.
- `tests/test_rag.py`: respuesta, rechazo, base vacía, fuentes, formato, errores y límites.

Ejecuta las pruebas con el comando de la fase 5. Los ejemplos curl anteriores
constituyen las pruebas manuales de pregunta respondible y fuera del dominio.

### Verificación de cierre (2 de octubre de 2026)

- 46 pruebas aprobadas, incluidas las integraciones de documentos y pgvector.
- Sin conflictos de dependencias (`pip check`).
- Endpoint probado mediante TestClient con PostgreSQL, embeddings y Qwen reales,
  sin sustituir el retriever ni el LLM: temperatura efectiva 0.
- Pregunta: “Que seleccion gano el Mundial de futbol de 2022?” → HTTP 200,
  “Argentina ganó el Mundial de fútbol de 2022.”, fuente `mundial-2022.txt`,
  `page: null`, `chunk_index: 0`.
- Pregunta: “Cual es la composicion quimica de la atmosfera de Venus?” → HTTP 200,
  rechazo exacto y `sources: []`.

Esta comprobación valida esos casos del corpus local; no garantiza ausencia de
alucinaciones para cualquier pregunta. El control adicional está previsto en la fase 8.

## Fase 7 — Agente RAG con LangGraph

El endpoint `POST /api/chat/rag` conserva el contrato `{question}` → `{answer, sources}`,
pero `RAGService` delega ahora su ejecución a un `StateGraph` compilado.
Se reutilizan el retriever, el prompt, el servicio de Ollama y el formateo de fuentes.

```mermaid
flowchart TD
    START --> receive_question
    receive_question --> validate_question
    validate_question --> retrieve_context
    retrieve_context --> grade_context
    grade_context -->|Suficiente| generate_answer
    grade_context -->|Insuficiente| reject_question
    generate_answer -->|Respuesta con fuentes| save_interaction
    generate_answer -->|Rechazo del generador| reject_question
    reject_question --> save_interaction
    save_interaction --> END
```

`AgentState` contiene `user_id`, `conversation_id`, `question`, `retrieved_documents`,
`context_score`, `answer`, `sources` y `status`, además del prompt limitado y el resultado
de evaluación. `user_id` y `conversation_id` son `None` en el endpoint actual; no se ha
añadido autenticación ni memoria conversacional.

| Nodo | Responsabilidad |
|---|---|
| `receive_question` | Inicializa los datos de esta ejecución sin reutilizar respuestas anteriores |
| `validate_question` | Valida la pregunta incluso si se invoca el grafo directamente |
| `retrieve_context` | Recupera Top-K fragmentos de PostgreSQL |
| `grade_context` | Evalúa suficiencia y, en modo de una llamada, prepara la respuesta |
| `generate_answer` | Valida el borrador y sus referencias; en modo de dos llamadas también lo genera |
| `reject_question` | Devuelve la frase de rechazo exacta y fuentes vacías |
| `save_interaction` | Registra el resultado en el estado de la ejecución actual |

El grader devuelve un JSON con `classification: SUFFICIENT | INSUFFICIENT`. Su decisión controla una
arista condicional real del grafo. Si no hay contexto, no se invoca al modelo.
En el modo opcional `RAG_SINGLE_PASS=true`, la misma llamada prepara un borrador cuando hay respaldo; el nodo
`generate_answer` valida su estructura y referencias antes de publicarlo.
Con `RAG_SINGLE_PASS=false` (por defecto desde la fase 8), se conserva la evaluación seguida de una segunda
llamada para generar; esta también puede rechazar aunque el grader haya aprobado.

`context_score` es la mayor similitud coseno (`1 - distance`) entre los fragmentos
seleccionados: es diagnóstico, no una probabilidad ni un umbral de aceptación.
La fase 8 filtra cada fragmento por similitud antes de construir el contexto.
Los errores técnicos mantienen los handlers existentes: no se convierten en rechazos
por falta de información.

**Alcance de `save_interaction`:** utiliza `InteractionService` y deja un registro
con `persisted: false` dentro del resultado interno del grafo. No escribe conversaciones
en PostgreSQL, no comparte historial entre peticiones y no crea una lista global en memoria.
El historial persistente corresponde a la fase 9. El endpoint continúa devolviendo
únicamente `answer` y `sources`.

### Ejecutar y comprobar

Desde `backend/`:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Con Ollama y PostgreSQL activos, usa los ejemplos de la fase 6 en `/docs`.
En la terminal aparecen los nodos de recuperación y evaluación, la ruta elegida y el
registro final. En fase 8, por defecto se hacen dos llamadas si hay contexto suficiente;
ninguna si ningún fragmento supera el umbral. `RAG_SINGLE_PASS=true` es el modo
alternativo de una llamada, sin clasificación independiente.
`OLLAMA_TIMEOUT` se aplica
a cada llamada, no a la duración completa del grafo.

### Optimización de latencia (3 de octubre de 2026)

Se conserva Qwen `qwen3:8b`, el endpoint y la recuperación de documentos. La evaluación
y el borrador comparten una llamada para evitar procesar el mismo contexto dos veces.
Las referencias siguen validándose en Python y un veredicto insuficiente devuelve el
rechazo establecido. Esto no sustituye los controles y umbrales previstos para la fase 8.

Configuración de la optimización anterior a fase 8 (ahora el modo por defecto es `false`):

```dotenv
RAG_SINGLE_PASS=true
RAG_MAX_OUTPUT_TOKENS=512
RAG_KEEP_ALIVE=15m
```

El límite de salida favorece respuestas breves; si el modelo agota ese límite se
devuelve un error explícito en lugar de aceptar JSON truncado. Puede aumentarse
hasta 2048. `RAG_KEEP_ALIVE` solicita mantener el modelo cargado durante 15 minutos
después de usarlo, consumiendo memoria mientras permanece cargado. Reinicia el backend
para aplicar cambios. Para recuperar el flujo de dos llamadas, usa `RAG_SINGLE_PASS=false`.

Los logs separan recuperación, carga del modelo, procesamiento del contexto y generación.
Las mediciones y los comandos para repetirlas están en
[`docs/performance/README.md`](docs/performance/README.md). En CPU todavía pueden
transcurrir decenas de segundos; no se cachean respuestas ni se omite la búsqueda.

La suite se ejecuta igual que en las fases anteriores. `tests/test_agent.py` verifica
las ramas, el estado por ejecución, la validación, el rechazo posterior a generación,
la propagación de errores y el diagrama.

### Archivos y diagrama

- `app/agents/state.py`: estado tipado del agente.
- `app/agents/graph.py`: nodos, edges, conditional edges, START y END.
- `app/agents/nodes/rag_nodes.py`: implementación de los siete nodos.
- `app/services/context_grader.py`: evaluación básica de suficiencia.
- `app/services/interaction_service.py`: registro por ejecución.
- `app/services/rag_service.py`: fachada compatible que invoca el grafo.

El diagrama generado desde el grafo real está en
[`docs/diagrams/agent-graph.mmd`](docs/diagrams/agent-graph.mmd).
Para regenerarlo sin conectar a Ollama ni PostgreSQL, desde `backend/`:

```powershell
.venv\Scripts\python.exe -m app.agents.graph | Set-Content -Encoding utf8 ../docs/diagrams/agent-graph.mmd
```

La función `graph_mermaid(graph)` usa `get_graph().draw_mermaid()` y no requiere
un servicio externo de imágenes. La implementación usa la
[API oficial de StateGraph](https://reference.langchain.com/python/langgraph/graph/state/StateGraph).

### Verificación de cierre (2 de octubre de 2026)

- 56 pruebas aprobadas, incluidas las integraciones de las fases anteriores.
- Dependencias sin conflictos y exportación Mermaid comprobada.
- Endpoint probado mediante TestClient, con Qwen, Ollama y PostgreSQL reales.
- Mundial 2022: `grade_context` aprobó el contexto, `generate_answer` respondió
  “Argentina ganó el Mundial de fútbol de 2022.” con fuente `mundial-2022.txt`,
  página `null`, fragmento 0; HTTP 200. Tiempo total observado: 134,97 segundos.
- Atmósfera de Venus: `grade_context` devolvió insuficiente y pasó directamente
  por `reject_question` y `save_interaction`, sin generar una respuesta libre;
  rechazo exacto, fuentes vacías y HTTP 200. Tiempo observado: 55,80 segundos.
- Ambas ramas finalizaron con un registro interno `persisted: false`.

Los tiempos corresponden al equipo local con Qwen ejecutándose en CPU; no son una
garantía de latencia. Los casos probados no garantizan que el evaluador acierte siempre;
la fase 8 reforzará el control de alucinaciones.

## Fase 8 — Control de alucinaciones

El agente aplica cuatro controles: filtro de similitud por fragmento, clasificación
de suficiencia, prompt estricto y rechazo explícito. Las respuestas aceptadas mantienen
las fuentes con `document`, `page` y `chunk_index`.

```dotenv
RAG_MIN_RELEVANCE_SCORE=0.65
RAG_SINGLE_PASS=false
```

El score es `1 - distancia_coseno`, no una probabilidad. Solo se admiten fragmentos
con score **mayor** que el umbral; los demás no llegan a Qwen ni se pueden citar.
Si ninguno pasa, se rechaza sin invocar al LLM. El valor 0.65 es inicial y configurable,
no universal: debe calibrarse al cambiar documentos o modelo de embeddings.

El evaluador recibe exactamente el contexto filtrado y limitado y devuelve únicamente
`{"classification":"SUFFICIENT"}` o `{"classification":"INSUFFICIENT"}`. Coincidir
en tema no basta: todas las partes de la pregunta deben estar documentadas. Los prompts
prohíben usar conocimiento externo, inferir hechos ausentes y obedecer instrucciones
dentro de documentos o preguntas; ante dudas o contradicciones deben rechazar.

El rechazo devuelve exactamente:

```json
{"answer":"No tengo suficiente información en mi base de conocimiento para responder esa pregunta.","sources":[]}
```

Los logs muestran número de chunks, scores, umbral, clasificación y ruta del grafo;
no muestran el razonamiento del modelo. JSON inválido, referencias inventadas o errores
de Ollama siguen siendo errores técnicos, no rechazos por falta de conocimiento.

**Tiempo de respuesta:** la clasificación independiente exige dos llamadas cuando se
responde. Se mantienen el límite de salida y keep-alive de la optimización anterior,
y el filtro puede reducir el contexto. El modo `RAG_SINGLE_PASS=true` sigue disponible
con filtro, pero combina evaluación y borrador y no cumple el requisito de clasificación
independiente de esta fase. El modo estricto queda configurado en `.env` local.

Para ejecutar desde `backend/`:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

En `http://127.0.0.1:8000/docs`, usar `POST /api/chat/rag` con los casos de
[`docs/phase8.md`](docs/phase8.md). Ese documento incluye archivos modificados,
comandos de pruebas y limitaciones. Los controles reducen el riesgo de alucinaciones;
no garantizan que Qwen siempre evalúe correctamente el respaldo documental.

## Estado del Proyecto

- [x] Fase 1 — Estructura inicial
- [x] Fase 2 — Integrar Ollama + Qwen
- [x] Fase 3 — Arquitectura profesional FastAPI
- [x] Fase 4 — Embeddings y PostgreSQL con pgvector
- [x] Fase 5 — Carga y procesamiento de documentos
- [x] Fase 6 — RAG básico
- [x] Fase 7 — Agente con LangGraph
- [x] Fase 8 — Control de alucinaciones
- [ ] Fase 9 — Base de datos para historial
- [ ] Fase 10 — Autenticación y seguridad
- [ ] Fase 11 — Frontend React
- [ ] Fase 12 — Integración completa
- [ ] Fase 13 — Docker Compose
- [ ] Fase 14 — Testing
- [ ] Fase 15 — Preparación para despliegue


