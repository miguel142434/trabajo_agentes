# 🤖 RAG Agent — Agente Inteligente con Retrieval-Augmented Generation

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

## Estado del Proyecto

- [x] Fase 1 — Estructura inicial
- [ ] Fase 2 — Integrar Ollama + Qwen
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

