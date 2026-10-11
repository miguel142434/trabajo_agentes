# RAG Agent — Agente Inteligente Deportivo con LangGraph y Modelos Locales

Sistema inteligente de preguntas y respuestas basado en arquitectura **RAG** (*Retrieval-Augmented Generation*) que utiliza modelos de lenguaje y embeddings completamente locales mediante **Ollama**, persistencia vectorial con **PostgreSQL + pgvector**, base de datos relacional para historial conversacional, autenticación robusta mediante **Keycloak (JWT / OAuth2 / PKCE)** y una interfaz de usuario moderna en **React (Vite)**.

El sistema está diseñado para operar con un costo estricto de **$0 COP**, permitiendo tanto ejecución 100% local (vía Docker Compose o entornos nativos) como despliegue híbrido en la nube.

---

## Tabla de Contenidos

1. [Nombre del Proyecto](#1-nombre-del-proyecto)
2. [Descripción](#2-descripción)
3. [Objetivo](#3-objetivo)
4. [Arquitectura General](#4-arquitectura-general)
5. [Tecnologías Utilizadas](#5-tecnologías-utilizadas)
6. [Estructura del Repositorio](#6-estructura-del-repositorio)
7. [Requisitos Previos](#7-requisitos-previos)
8. [Instalación de Ollama](#8-instalación-de-ollama)
9. [Descarga del Modelo Qwen](#9-descarga-del-modelo-qwen)
10. [Instalación del Modelo de Embeddings](#10-instalación-del-modelo-de-embeddings)
11. [Variables de Entorno](#11-variables-de-entorno)
12. [Ejecución del Backend](#12-ejecución-del-backend)
13. [Ejecución del Frontend](#13-ejecución-del-frontend)
14. [Ejecución con Docker](#14-ejecución-con-docker)
15. [Configuración de Autenticación (Keycloak)](#15-configuración-de-autenticación-keycloak)
16. [Carga e Indexación de Documentos](#16-carga-e-indexación-de-documentos)
17. [Funcionamiento del RAG](#17-funcionamiento-del-rag)
18. [Explicación Resumida de LangGraph](#18-explicación-resumida-de-langgraph)
19. [Control de Alucinaciones](#19-control-de-alucinaciones)
20. [Ejemplos de Uso](#20-ejemplos-de-uso)
21. [Pruebas Automatizadas (Tests)](#21-pruebas-automatizadas-tests)
22. [Despliegue Gratuito en la Nube ($0 COP)](#22-despliegue-gratuito-en-la-nube-0-cop)
23. [Limitaciones Conocidas](#23-limitaciones-conocidas)

---

## 1. Nombre del Proyecto

**RAG Sports Agent API & Client** — Agente Inteligente con Recuperación Aumentada para Dominio Histórico Deportivo.

---

## 2. Descripción

Este proyecto implementa una solución integral de Inteligencia Artificial para responder consultas en lenguaje natural a partir de documentos. Incorpora:
- Una **base de conocimiento global precargada** con datos históricos de las Copas Mundiales de la FIFA (`Mundiales_documento_RAG.pdf`), accesible para todos los usuarios.
- Un módulo de **gestión de documentos de usuario**, permitiendo subir archivos adicionales (PDF, TXT, DOCX) que se segmentan, vectorizan y aíslan por usuario.
- Un flujo orquestado con **LangGraph** que implementa evaluación de suficiencia de contexto (*Context Relevance Grading*) y verificación estricta para impedir que el LLM invente respuestas.
- Autenticación federada mediante **Keycloak** para proteger todos los endpoints funcionales y garantizar el aislamiento de datos entre usuarios.

---

## 3. Objetivo

Proveer un asistente conversacional capaz de responder preguntas precisas y fundamentadas exclusivamente en la documentación disponible, citando las fuentes utilizadas (documento, página y fragmento), rechazando explícitamente cualquier consulta sobre información ausente o no documentada, y funcionando íntegramente con modelos locales y herramientas de código abierto sin incurrir en costos de licencias ni consumo de APIs de pago.

---

## 4. Arquitectura General

El sistema implementa una arquitectura desacoplada en tres capas principales:

```
[ Navegador Web ]
       │
       ▼ (HTTPS / HTTP)
┌──────────────────────────────────────────────┐
│             FRONTEND (React + Vite)          │
│  - Enrutamiento con React Router             │
│  - Cliente de autenticación Keycloak-JS      │
│  - Vistas: Login, Chat, Documentos, History  │
└──────────────────────┬───────────────────────┘
                       │ (API REST + Bearer JWT)
                       ▼
┌──────────────────────────────────────────────┐
│             BACKEND (FastAPI)                │
│  - Validación de tokens y contexto de usuario │
│  - Pipeline de carga, chunking y extracción  │
│  - Orquestación con LangGraph (StateGraph)   │
└──────────┬──────────────────────┬────────────┘
           │                      │
           ▼ (SQLAlchemy / SQL)   ▼ (HTTP API)
┌──────────────────────┐  ┌─────────────────────────────────┐
│  POSTGRESQL 16       │  │        OLLAMA (Host Local)      │
│  - pgvector:         │  │  - qwen3:8b (Generación LLM)    │
│    document_chunks   │  │  - nomic-embed-text (Embeddings)│
│  - Relacional:       │  └─────────────────────────────────┘
│    conversations     │
│    messages          │
│    uploaded_docs     │
└──────────────────────┘
```

---

## 5. Tecnologías Utilizadas

| Componente | Tecnología | Versión / Detalle |
| :--- | :--- | :--- |
| **Backend** | Python, FastAPI, Uvicorn | Python 3.11+, FastAPI 0.115+ |
| **Modelos de IA** | Ollama | `qwen3:8b`, `nomic-embed-text` (768 dim) |
| **Orquestación IA** | LangChain, LangGraph | LangGraph 1.2+, LangChain Core |
| **Procesamiento Texto** | PyPDF, python-docx | Extracción nativa estructurada por páginas |
| **Base de Datos** | PostgreSQL + pgvector | PostgreSQL 16 con extensión vectorial nativa |
| **ORM / Persistencia** | SQLAlchemy, Psycopg 3 | Conexiones asíncronas con pool pre-ping |
| **Autenticación** | Keycloak, PyJWT, Cryptography | OAuth2 / OpenID Connect, flujo PKCE |
| **Frontend** | React, Vite | React 18, React Router DOM 7 |
| **Contenedores** | Docker, Docker Compose | Imágenes optimizadas basadas en Linux |

---

## 6. Estructura del Repositorio

```text
trabajo_agentes/
├── backend/
│   ├── app/
│   │   ├── agents/            # Grafo LangGraph, nodos y estado
│   │   │   ├── graph.py       # Definición del flujo StateGraph
│   │   │   ├── state.py       # Estado tipado del agente
│   │   │   └── nodes/         # Nodos (retrieve, grade, generate, reject, save)
│   │   ├── api/               # Controladores y endpoints REST (/chat, /documents, /conversations)
│   │   ├── core/              # Configuración (Pydantic), seguridad JWT, base de datos y logs
│   │   ├── models/            # Modelos ORM relacionales (User, Conversation, Message, Document)
│   │   ├── schemas/           # Schemas de validación Pydantic
│   │   ├── services/          # Lógica de negocio (RAG, embeddings, chunking, storage, knowledge base)
│   │   └── vectorstore/       # Repositorio pgvector (distancia coseno, filtros y migración)
│   ├── knowledge_base/        # Base de conocimiento global precargada al iniciar
│   │   └── Mundiales_documento_RAG.pdf
│   ├── tests/                 # 90 tests automatizados (unitarios y de integración)
│   ├── Dockerfile             # Contenedor del backend
│   ├── requirements.txt       # Dependencias Python
│   └── run.py                 # Script de arranque con soporte de puerto dinámico
├── frontend/
│   ├── src/
│   │   ├── components/        # Componentes reutilizables (Sidebar, Layout, Navbar)
│   │   ├── context/           # Contextos de React (AuthContext)
│   │   ├── pages/             # Vistas (ChatPage, DocumentsPage, HistoryPage, LoginPage)
│   │   └── services/          # Clientes API (apiService, authService, config)
│   ├── public/                # Favicon, assets y regla de redirección SPA (_redirects)
│   ├── vercel.json            # Reescritura de rutas para despliegue en Vercel
│   ├── Dockerfile             # Contenedor del frontend con Nginx
│   └── package.json           # Dependencias Node.js
├── keycloak/
│   └── realm-export.json      # Configuración automatizada del realm rag-agent y cliente
├── scripts/
│   ├── tunnel/
│   │   └── ollama_proxy.py    # Proxy de seguridad con token para túnel de Ollama
│   ├── benchmark_rag.py       # Script de medición de latencia y evaluación
│   └── migrate_legacy_history.py
├── docs/
│   ├── deployment.md          # Guía exhaustiva de despliegue gratuito ($0 COP)
│   └── test-cases.md          # Matriz de casos de prueba formal
├── docker-compose.yml         # Orquestación local multicontenedor
├── .env.example               # Plantilla de variables de entorno documentada
└── README.md                  # Este documento
```

---

## 7. Requisitos Previos

- **Sistema Operativo**: Windows 10/11, macOS o Linux.
- **Python**: Versión 3.11 o superior.
- **Node.js**: Versión 18 o superior (con `npm`).
- **Ollama**: Instalado localmente en el sistema operativo anfitrión.
- **Docker y Docker Compose**: Recomendado para levantar la base de datos y Keycloak sin instalaciones manuales.
- **Memoria RAM**: 16 GB recomendados (mínimo 8 GB con paginación adecuada).

---

## 8. Instalación de Ollama

Ollama es el motor de inferencia que ejecuta los modelos de forma local:

- **Windows**: Descarga el instalador oficial desde [https://ollama.com/download/windows](https://ollama.com/download/windows) y ejecútalo.
- **macOS**: Descarga desde [https://ollama.com/download/mac](https://ollama.com/download/mac).
- **Linux**: Ejecuta en terminal:
  ```bash
  curl -fsSL https://ollama.ai/install.sh | sh
  ```

Verifica la instalación en tu terminal:
```bash
ollama --version
```

---

## 9. Descarga del Modelo Qwen

El sistema utiliza **Qwen 2.5 / Qwen 3 (8B)** por su excelente capacidad de razonamiento en español y cumplimiento estricto de prompts:

```bash
ollama pull qwen3:8b
```

*(Si cuentas con recursos limitados de memoria, también puedes utilizar `qwen2.5:3b` ajustando la variable `OLLAMA_MODEL` en tu `.env`).*

---

## 10. Instalación del Modelo de Embeddings

Para convertir los fragmentos de texto en vectores matemáticos de 768 dimensiones:

```bash
ollama pull nomic-embed-text
```

Verifica que ambos modelos estén disponibles:
```bash
ollama list
```

---

## 11. Variables de Entorno

Copia el archivo de ejemplo en la raíz del proyecto para crear tu archivo `.env`:

```bash
cp .env.example .env
```

Parámetros clave documentados en `.env`:

```ini
# Backend
BACKEND_PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]

# Frontend
FRONTEND_PORT=5173
VITE_API_URL=http://localhost:8000

# Ollama Local
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
OLLAMA_TEMPERATURE=0
OLLAMA_TIMEOUT=120

# Embeddings y Dimensión
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSION=768

# PostgreSQL + pgvector
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ragdb
POSTGRES_USER=raguser
POSTGRES_PASSWORD=ragpassword
VECTOR_TABLE=document_chunks
DOCUMENT_TABLE=uploaded_documents

# Parámetros RAG y Control de Alucinaciones
CHUNK_SIZE=800
CHUNK_OVERLAP=120
RAG_TOP_K=4
RAG_MAX_CONTEXT_CHARS=6000
RAG_MIN_RELEVANCE_SCORE=0.65
RAG_SINGLE_PASS=false

# Autenticación Keycloak
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=rag-agent
KEYCLOAK_CLIENT_ID=rag-frontend
KEYCLOAK_AUDIENCE=account

# Base de Conocimiento Global
KNOWLEDGE_BASE_SEED_ON_STARTUP=true
```

---

## 12. Ejecución del Backend

Para ejecutar el backend de forma nativa en tu máquina:

1. Ingresa a la carpeta `backend` y crea el entorno virtual:
   ```bash
   cd backend
   python -m venv .venv
   ```

2. Activa el entorno virtual:
   - **Windows (PowerShell)**:
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS**:
     ```bash
     source .venv/bin/activate
     ```

3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Asegúrate de que PostgreSQL con `pgvector` y Keycloak estén corriendo (puedes levantarlos con Docker: `docker compose up -d postgres keycloak`).

5. Inicia el backend:
   ```bash
   python run.py
   ```
   *El backend estará disponible en `http://localhost:8000`. Puedes verificar la documentación interactiva en `http://localhost:8000/docs`.*

---

## 13. Ejecución del Frontend

1. En una nueva terminal, ingresa a la carpeta `frontend`:
   ```bash
   cd frontend
   ```

2. Instala los paquetes de Node.js:
   ```bash
   npm install
   ```

3. Inicia el servidor de desarrollo Vite:
   ```bash
   npm run dev
   ```
   *El frontend estará disponible en `http://localhost:5173`.*

---

## 14. Ejecución con Docker

El proyecto incluye un archivo `docker-compose.yml` que permite levantar todo el ecosistema (PostgreSQL con pgvector, Keycloak, Backend y Frontend) en un solo comando:

```bash
docker compose up --build
```

### Servicios orquestados:
- **`postgres`**: PostgreSQL 16 con extensión `pgvector` preinstalada en el puerto `5432`.
- **`keycloak`**: Servidor de identidad en el puerto `8080`, importando automáticamente el realm `rag-agent`.
- **`backend`**: FastAPI en el puerto `8000`, configurado para comunicarse con Ollama en el anfitrión vía `host.docker.internal:11434`.
- **`frontend`**: Aplicación web servida mediante Nginx en el puerto `3000`.

### Comandos de gestión de Docker:
```bash
# Ver estado de los contenedores
docker compose ps

# Ver logs en tiempo real
docker compose logs -f

# Detener los servicios conservando volúmenes de datos
docker compose down
```

---

## 15. Configuración de Autenticación (Keycloak)

La aplicación utiliza **Keycloak 24** como proveedor OpenID Connect (OIDC). Ningún endpoint funcional (chat, documentos, historial) es accesible sin un token JWT válido.

- **Importación Automática**: El contenedor de Keycloak importa automáticamente `keycloak/realm-export.json`.
- **Credenciales del Administrador de Keycloak**:
  - URL de Consola: `http://localhost:8080`
  - Usuario: `admin`
  - Contraseña: `admin_seguro_123`
- **Realm**: `rag-agent`
- **Cliente**: `rag-frontend` (Público, flujo estándar con PKCE y direct access grants habilitados).
- **Aislamiento Multi-usuario**: Cada documento y conversación queda etiquetado con el `sub` (UUID del usuario) extraído del token. El Usuario A jamás puede consultar documentos ni conversaciones del Usuario B.

---

## 16. Carga e Indexación de Documentos

El pipeline de ingesta procesa documentos de forma estructurada:

1. **Formatos Soportados**: `.pdf`, `.txt`, `.docx` (hasta 10 MB por archivo).
2. **Extracción**: Lectura de texto nativo página por página (`pypdf` para PDF, `python-docx` para tablas y párrafos de DOCX, decodificación UTF-8 para TXT).
3. **División en Fragmentos (Chunking)**:
   - Tamaño: `CHUNK_SIZE=800` caracteres.
   - Solapamiento: `CHUNK_OVERLAP=120` caracteres.
   - Preservación de metadatos: cada fragmento conserva `page`, `chunk_index`, `filename` y metadatos de usuario.
4. **Embeddings**: Los fragmentos se envían por lotes al modelo `nomic-embed-text` con el prefijo `search_document: `.
5. **Persistencia Atómica**: Chunks, vectores y metadatos se guardan en una única transacción en la tabla `document_chunks`.
6. **Base de Conocimiento Global**: Los archivos en `backend/knowledge_base/` (como `Mundiales_documento_RAG.pdf`) se indexan al arrancar con el identificador especial `owner_id = 'system:global'`, quedando disponibles para todos los usuarios.

---

## 17. Funcionamiento del RAG

El flujo de Recuperación Aumentada opera de la siguiente manera:

1. La consulta del usuario se transforma en un vector semántico con el prefijo `search_query: ` usando `nomic-embed-text`.
2. Se realiza una búsqueda exacta de similitud de coseno (`<=>`) en PostgreSQL recuperando los `RAG_TOP_K=4` fragmentos más cercanos cuyo score supere el umbral `RAG_MIN_RELEVANCE_SCORE=0.65`.
3. La búsqueda consulta simultáneamente los fragmentos propios del usuario autenticado y los fragmentos de la base global (`system:global`).
4. Se ensambla un contexto estructurado donde cada fragmento está claramente delimitado:
   ```text
   [DOCUMENTO 1: Mundiales_documento_RAG.pdf | Página: 4 | Fragmento: 1]
   Contenido del fragmento...
   ```
5. El modelo genera la respuesta fundamentándose estrictamente en dicho contexto y retornando las fuentes exactas (documento, página y chunk).

---

## 18. Explicación Resumida de LangGraph

La lógica del agente conversacional no es lineal, sino un grafo de estados cíclico implementado con **LangGraph** (`backend/app/agents/graph.py`):

```
       START
         │
         ▼
 ┌───────────────┐
 │retrieve_context│  <-- Búsqueda Top-K en pgvector + filtro por score
 └───────┬───────┘
         │
         ▼
 ┌───────────────┐
 │ grade_context │  <-- ¿La información es SUFFICIENT o INSUFFICIENT?
 └───────┬───────┘
         │
     [¿Suficiente?]
     ├── SÍ  ──► [ generate_answer ] ──┐
     │                                 │
     └── NO  ──► [ reject_question ] ──┤
                                       ▼
                              ┌─────────────────┐
                              │save_interaction │  <-- Guarda pregunta, respuesta y fuentes
                              └────────┬────────┘
                                       │
                                       ▼
                                      END
```

- **`retrieve_context`**: Consulta la base vectorial y filtra por umbral de similitud.
- **`grade_context`**: Clasifica si los fragmentos contienen los hechos necesarios para responder la pregunta. Soporta modo dual o `RAG_SINGLE_PASS=true` para optimizar latencia en CPU.
- **`generate_answer`**: Genera la respuesta definitiva citando las fuentes.
- **`reject_question`**: Si el contexto es insuficiente o irrelevante, emite el rechazo estricto sin consultar al modelo.
- **`save_interaction`**: Registra la interacción y fuentes en las tablas relacionales de historial.

---

## 19. Control de Alucinaciones

Para evitar que el modelo invente datos o utilice conocimiento preentrenado no documentado, el sistema aplica cuatro barreras defensivas:

1. **Similarity Threshold**: Cualquier fragmento con una similitud inferior a `RAG_MIN_RELEVANCE_SCORE=0.65` se descarta automáticamente. Si ningún fragmento supera el umbral, la pregunta no pasa a generación.
2. **Context Relevance Grader**: El nodo evaluador clasifica el contexto como `SUFFICIENT` o `INSUFFICIENT`. Si la información no basta, el grafo transita obligatoriamente a rechazo.
3. **Prompting Estricto**: El LLM recibe instrucciones categóricas:
   - Solo puede utilizar los hechos presentes en `[CONTEXTO DOCUMENTAL]`.
   - Tiene prohibido inferir o suponer datos no mencionados explícitamente.
4. **Rechazo Explícito Canónico**: Ante cualquier duda o falta de información, el sistema emite exactamente la frase:
   > *"No tengo suficiente información en mi base de conocimiento para responder esa pregunta."*

---

## 20. Ejemplos de Uso

### Caso 1: Pregunta fundamentada en la base documental global
- **Pregunta**: `¿Quién quedó de subcampeón en el mundial de 1934?`
- **Respuesta**: `En el mundial de 1934 celebrado en Italia, el subcampeón fue Checoslovaquia tras caer en la final 2-1 ante Italia.`
- **Fuentes Citadas**:
  - Documento: `Mundiales_documento_RAG.pdf` | Página: 3 | Fragmento: 2

### Caso 2: Pregunta fuera de dominio (Control de alucinación)
- **Pregunta**: `¿Quién ganó el premio Nobel de Literatura en 1982?`
- **Respuesta**: `No tengo suficiente información en mi base de conocimiento para responder esa pregunta.`
- **Fuentes Citadas**: Ninguna (Rechazo automático sin alucinación).

### Caso 3: Pregunta sobre documento privado subido por el usuario
- El usuario sube `reglamento_torneo_local.pdf`.
- **Pregunta**: `¿Cuántas tarjetas amarillas causan suspensión en el torneo local?`
- **Respuesta**: `De acuerdo con el reglamento cargado, acumular tres tarjetas amarillas conlleva un partido de suspensión.`
- **Fuentes Citadas**:
  - Documento: `reglamento_torneo_local.pdf` | Página: 2 | Fragmento: 4

---

## 21. Pruebas Automatizadas (Tests)

El backend cuenta con una suite completa de **90 pruebas automatizadas** que validan la API sin depender de descargas pesadas de modelos mediante mocks controlados:

Para ejecutar todas las pruebas:
```bash
cd backend
python -m unittest discover -s tests -t .
```

### Cobertura de pruebas:
- `test_agent.py`: Transiciones del grafo LangGraph y evaluación de estados.
- `test_hallucinations.py`: Verificación de las cuatro defensas contra alucinaciones.
- `test_rag.py` & `test_rag_performance.py`: Recuperación Top-K, filtrado por score y modo single-pass.
- `test_security.py`: Validación de tokens JWT, claims requeridos (aud, iss, sub, azp) y rechazo 401.
- `test_documents.py`: Subida de archivos, validación de tipos (.pdf, .txt, .docx) y límites de tamaño.
- `test_vector.py`: Operaciones matemáticas de similitud y filtros de aislamiento por usuario.
- `test_llm.py`: Manejo de errores de conexión con Ollama (404, 503, timeout) y formato de `CORS_ORIGINS`.

---

## 22. Despliegue Gratuito en la Nube ($0 COP)

El proyecto está preparado para desplegarse públicamente con un costo total de **$0 COP** mediante una arquitectura híbrida:

| Componente | Servicio | Costo | Función |
| :--- | :--- | :---: | :--- |
| **Frontend** | **Vercel** / Netlify | $0 COP | Aloja la SPA de React con CDN global y HTTPS. |
| **Backend** | **Render** | $0 COP | Web Service gratuito que ejecuta FastAPI y LangGraph. |
| **Base Vectorial** | **Neon.tech** | $0 COP | PostgreSQL 16 serverless perpetuo con `pgvector`. |
| **Inferencia LLM** | **PC Personal** | $0 COP | Ejecuta Ollama sin pagar costosos servidores de GPU en la nube. |
| **Túnel Seguro** | **Cloudflare Tunnel** | $0 COP | Conecta el backend de Render con el PC local de forma cifrada. |

### Componente de seguridad del túnel:
Para evitar exponer Ollama directamente a Internet, el proyecto incluye un proxy ligero con autenticación por Bearer token:
```bash
# En el PC local:
python scripts/tunnel/ollama_proxy.py --secret MI_TOKEN_SECRETO
cloudflared tunnel --url http://localhost:11435
```
Cualquier solicitud externa sin el token es rechazada de inmediato con **401 Unauthorized**.

*(Para consultar la guía detallada de despliegue paso a paso, revisa [`docs/deployment.md`](docs/deployment.md)).*

---

## 23. Limitaciones Conocidas

1. **Dependencia de la máquina local en modo híbrido**: En el despliegue gratuito, el modelo Ollama corre en el computador del usuario. Si el computador está apagado, el backend devuelve `503 Service Unavailable` controlado para el chat (la navegación, historial y documentos continúan funcionando).
2. **Suspensión por inactividad en Render Free**: El plan gratuito de Render suspende el contenedor tras 15 minutos sin tráfico; la primera petición posterior experimenta una latencia de inicio en frío (*cold start*) de ~40 segundos.
3. **Documentos escaneados**: La extracción de texto requiere documentos digitales nativos. Los PDFs escaneados (imágenes puras) no contienen texto legible y requieren OCR (no incluido en el alcance de este agente).
4. **Límites de contexto del modelo**: El tamaño máximo de contexto está fijado en `RAG_MAX_CONTEXT_CHARS=6000` para garantizar respuestas rápidas en equipos con CPU convencional.

---

Desarrollado para la materia **Implementación e Integración de Software** (Semestre 6).
