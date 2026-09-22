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

## Estado del Proyecto

- [x] Fase 1 — Estructura inicial
- [x] Fase 2 — Integrar Ollama + Qwen
- [ ] Fase 3 — Arquitectura profesional FastAPI
- [ ] Fase 4 — Embeddings y PostgreSQL con pgvector
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

