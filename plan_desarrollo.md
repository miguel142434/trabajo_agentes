# Plan de desarrollo por fases — Agente RAG con Ollama, Qwen, LangChain, LangGraph y pgvector

Este documento reúne prompts listos para copiar y pegar en Codex, organizados por fases de desarrollo.

---

## Fase 0 — Definición técnica del proyecto

```text
Quiero desarrollar un proyecto académico de un agente inteligente basado en RAG.

El proyecto debe utilizar:

- Python
- FastAPI para el backend
- React + Vite para el frontend
- LangChain
- LangGraph
- Ollama
- Qwen como modelo LLM local
- PostgreSQL con pgvector como base de datos vectorial
- Embeddings ejecutados localmente
- Autenticación de usuarios
- Historial de conversaciones
- Carga y procesamiento de documentos
- Docker
- Git/GitHub

El agente debe responder exclusivamente con información obtenida de los documentos almacenados en su base vectorial.

Cuando no exista información suficiente, debe rechazar la pregunta explícitamente y responder:

"No tengo suficiente información en mi base de conocimiento para responder esa pregunta."

Todavía NO escribas código.

Primero genera:

1. Una arquitectura propuesta del sistema.
2. Los principales componentes.
3. El flujo de información desde el frontend hasta el modelo.
4. Las responsabilidades de cada componente.
5. La estructura recomendada del repositorio.
6. Las dependencias principales.
7. Los riesgos técnicos principales.
8. Un roadmap de implementación.

No implementes nada todavía.
```

---

## Fase 1 — Crear estructura inicial del proyecto

```text
Vamos a comenzar la implementación del proyecto RAG definido anteriormente.

Crea solamente la estructura inicial del repositorio.

Stack:

Backend:
- Python
- FastAPI

Frontend:
- React
- Vite
- JavaScript

IA:
- LangChain
- LangGraph
- Ollama
- Qwen

Base vectorial:
- PostgreSQL con pgvector

El repositorio debe ser un monorepo con una estructura similar a:

proyecto-agente/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── agents/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   └── vectorstore/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
│
├── data/
│   └── documents/
│
├── docs/
│   └── diagrams/
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md

Requisitos:

1. Crear todas las carpetas necesarias.
2. Crear un backend FastAPI mínimo.
3. Crear únicamente un endpoint GET /health.
4. Crear un frontend React + Vite mínimo.
5. Crear .gitignore.
6. Crear .env.example.
7. Crear un README inicial.
8. Crear requirements.txt.
9. Crear Dockerfile básico para backend.
10. Crear Dockerfile básico para frontend.

NO implementar todavía:

- Ollama
- Qwen
- LangChain
- LangGraph
- PostgreSQL con pgvector
- RAG
- autenticación
- carga de documentos

Al terminar:

- muestra la estructura creada,
- explica qué archivos generaste,
- indica cómo ejecutar backend y frontend localmente.
```

---

## Fase 2 — Integrar Ollama + Qwen

```text
Ahora implementaremos únicamente la integración entre el backend FastAPI y Ollama.

No implementes RAG todavía.

Objetivo:

FastAPI debe poder enviar un prompt a un modelo Qwen ejecutado localmente mediante Ollama.

Implementa:

1. Añadir las dependencias necesarias para integrar LangChain con Ollama.
2. Crear una configuración para:
   - URL de Ollama
   - nombre del modelo
   - temperatura
3. Usar variables de entorno.
4. Crear un servicio separado para el modelo LLM.
5. Utilizar ChatOllama.
6. Crear un endpoint:

POST /api/test-llm

Body:

{
  "prompt": "texto de prueba"
}

Respuesta:

{
  "response": "respuesta generada por Qwen"
}

7. Manejar errores si:
   - Ollama no está disponible.
   - el modelo no está instalado.
   - existe timeout.

Usar una estructura limpia y separada.

No colocar toda la lógica dentro del endpoint.

Crear archivos del estilo:

services/llm_service.py
schemas/llm.py
api/routes/llm.py

Usar inicialmente:

OLLAMA_MODEL=qwen3:8b

pero permitir cambiar el modelo mediante .env.

Actualizar:

- requirements.txt
- .env.example
- README.md

Al finalizar indicar:

1. cómo instalar Ollama,
2. cómo descargar Qwen,
3. cómo ejecutar Ollama,
4. cómo probar el endpoint,
5. ejemplo usando curl.
```

---

## Fase 3 — Estructura profesional de FastAPI

```text
Quiero mejorar la arquitectura del backend FastAPI antes de implementar RAG.

Reorganiza el backend siguiendo separación de responsabilidades.

Crear:

app/main.py

app/api/
app/api/routes/

app/core/
- config.py
- exceptions.py
- logging.py

app/schemas/

app/services/

app/models/

app/repositories/

app/agents/

app/vectorstore/

Requisitos:

1. Configuración mediante variables de entorno.
2. Pydantic Settings si resulta conveniente.
3. Manejo global de excepciones.
4. Logging básico.
5. Health endpoint.
6. Router principal /api.
7. Mantener funcional el endpoint de prueba de Ollama.
8. Añadir CORS preparado para el frontend React.

No implementar todavía:

- RAG
- documentos
- embeddings
- LangGraph
- autenticación

No cambies innecesariamente código que ya funciona.

Al finalizar:

- explica la arquitectura,
- muestra el árbol de archivos,
- prueba que la aplicación arranque.
```

---

## Fase 4 — Embeddings y PostgreSQL con pgvector

```text
Ahora implementaremos exclusivamente la capa de embeddings y base vectorial.

Usaremos:

- PostgreSQL con pgvector
- embeddings locales
- preferiblemente OllamaEmbeddings con nomic-embed-text

No implementar aún el chatbot RAG completo.

Objetivo:

Poder almacenar fragmentos de texto y recuperarlos mediante búsqueda semántica.

Implementar:

1. Configurar el modelo de embeddings mediante .env:

OLLAMA_EMBEDDING_MODEL=nomic-embed-text

Configurar también la conexión a PostgreSQL:

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ragdb
POSTGRES_USER=raguser
POSTGRES_PASSWORD=ragpassword
DATABASE_URL=postgresql+psycopg://raguser:ragpassword@localhost:5432/ragdb

Asegurar que la extensión pgvector esté habilitada con:

CREATE EXTENSION IF NOT EXISTS vector;

2. Crear un servicio de embeddings.

3. Crear un servicio para PostgreSQL con pgvector.

4. La base vectorial debe persistir en PostgreSQL utilizando la extensión pgvector.

5. Crear una tabla configurable para almacenar los chunks, embeddings y metadata.

6. Cada fragmento almacenado debe persistirse en PostgreSQL con pgvector e incluir al menos:

- id
- document_id
- filename
- page
- chunk_index
- content
- embedding VECTOR(...)
- metadata JSONB

Usar una dimensión de vector compatible con el modelo de embeddings seleccionado.

7. Crear un endpoint temporal de prueba:

POST /api/vector/test-add

que permita guardar algunos textos manualmente.

8. Crear:

POST /api/vector/test-search

Body:

{
  "query": "texto de búsqueda",
  "k": 4
}

Debe devolver:

- fragmento
- metadata
- score o distancia

La búsqueda debe realizarse mediante operadores de similitud de pgvector, por ejemplo distancia coseno, y debe permitir recuperar los Top-K resultados.

9. Mantener la lógica separada del controlador.

10. Manejar errores de conexión con Ollama.

Actualizar:

- requirements.txt
- .env.example
- README.md

Todavía NO implementar:

- subida de archivos
- LangGraph
- RAG completo
- autenticación

Al finalizar incluye una prueba sencilla demostrando que una búsqueda recupera el texto semánticamente más relacionado.
```

---

## Fase 5 — Carga y procesamiento de documentos

```text
Ahora implementaremos la carga y procesamiento de documentos.

Objetivo:

Permitir cargar archivos desde FastAPI y convertirlos en documentos indexados dentro de PostgreSQL con pgvector.

Soportar inicialmente solamente:

- PDF
- TXT
- DOCX

No implementar todavía multimedia.

Flujo obligatorio:

archivo
→ validación
→ almacenamiento temporal
→ extracción de texto
→ división en chunks
→ embeddings
→ PostgreSQL con pgvector
→ confirmación

Implementar:

POST /api/documents/upload

Debe aceptar multipart/form-data.

Crear servicios separados para:

1. almacenamiento del archivo,
2. extracción de texto,
3. chunking,
4. embeddings,
5. almacenamiento en PostgreSQL con pgvector.

Para dividir texto utilizar RecursiveCharacterTextSplitter.

Configurar mediante .env:

CHUNK_SIZE
CHUNK_OVERLAP

Valores iniciales sugeridos:

CHUNK_SIZE=800
CHUNK_OVERLAP=120

Cada chunk debe guardar metadata:

- document_id
- filename
- file_type
- page, cuando aplique
- chunk_index

Validar:

- tipos permitidos,
- archivos vacíos,
- tamaño máximo,
- errores de extracción.

Respuesta esperada:

{
  "document_id": "...",
  "filename": "...",
  "chunks_created": 25,
  "status": "processed"
}

Crear también:

GET /api/documents

que permita listar los documentos cargados.

No implementar todavía autenticación ni LangGraph.

Actualizar README con ejemplos curl.
```

---

## Fase 6 — Implementar RAG básico

```text
Ahora implementaremos un RAG básico usando LangChain.

Todavía NO utilizar LangGraph.

Objetivo:

Pregunta
→ búsqueda vectorial
→ recuperación de contexto
→ prompt
→ Qwen vía Ollama
→ respuesta

Crear un servicio RAG separado.

Endpoint:

POST /api/chat/rag

Body:

{
  "question": "pregunta del usuario"
}

El sistema debe:

1. convertir la pregunta a embedding,
2. consultar PostgreSQL con pgvector,
3. recuperar los chunks más relevantes,
4. construir el contexto,
5. enviarlo a Qwen,
6. devolver la respuesta,
7. devolver también las fuentes utilizadas.

La respuesta debería tener aproximadamente esta estructura:

{
  "answer": "...",
  "sources": [
    {
      "document": "...",
      "page": 3,
      "chunk_index": 12
    }
  ]
}

Crear un prompt estricto:

El modelo debe responder únicamente utilizando la información incluida en CONTEXTO.

No debe utilizar conocimiento externo.

Si el contexto no permite responder, debe indicar:

"No tengo suficiente información en mi base de conocimiento para responder esa pregunta."

Usar temperature=0.

Separar:

- retriever
- prompt
- generación
- formateo de fuentes

No implementar todavía LangGraph ni autenticación.

Añadir pruebas manuales:

1. pregunta respondible,
2. pregunta fuera del dominio.
```

---

## Fase 7 — Crear el agente con LangGraph

```text
Ahora reemplazaremos el flujo RAG lineal por un agente construido explícitamente con LangGraph.

Este es uno de los componentes principales del proyecto.

Crear un AgentState usando TypedDict o equivalente.

Debe incluir al menos:

- user_id
- conversation_id
- question
- retrieved_documents
- context_score
- answer
- sources
- status

Construir los siguientes nodos:

1. receive_question
2. validate_question
3. retrieve_context
4. grade_context
5. generate_answer
6. reject_question
7. save_interaction

Flujo esperado:

START
↓
validate_question
↓
retrieve_context
↓
grade_context
↓
si contexto suficiente → generate_answer
si contexto insuficiente → reject_question
↓
save_interaction
↓
END

El nodo grade_context debe controlar una transición condicional.

El nodo reject_question debe devolver:

"No tengo suficiente información en mi base de conocimiento para responder esa pregunta."

Crear el grafo en un módulo separado:

app/agents/graph.py

Los nodos pueden organizarse dentro de:

app/agents/nodes/

Actualizar el endpoint del chat para utilizar LangGraph.

No poner lógica completa dentro del endpoint.

Incluir comentarios claros mostrando:

- nodos,
- edges,
- conditional edges,
- START,
- END.

Crear también una función que permita generar o visualizar el diagrama del grafo si LangGraph lo soporta.

No implementar todavía autenticación.
```

---

## Fase 8 — Control de alucinaciones

```text
Ahora quiero reforzar el control de alucinaciones del agente.

El objetivo es impedir que Qwen responda utilizando conocimiento que no proviene de la base documental.

Implementar al menos estas cuatro estrategias:

1. similarity threshold,
2. context relevance grader,
3. prompt estricto,
4. rechazo explícito.

Requisitos:

A. Similarity threshold

Definir en .env:

RAG_MIN_RELEVANCE_SCORE

El sistema debe rechazar documentos que no superen el umbral.

B. Context grader

El nodo grade_context debe determinar si los documentos recuperados contienen información suficiente para contestar.

Debe devolver únicamente una clasificación estructurada como:

SUFFICIENT
INSUFFICIENT

C. Prompt estricto

Qwen debe recibir una instrucción explícita indicando que:

- solo puede utilizar CONTEXTO,
- no debe utilizar conocimiento externo,
- no debe inferir información no presente,
- si existe duda debe rechazar.

D. Rechazo

Cuando no haya contexto suficiente devolver exactamente:

"No tengo suficiente información en mi base de conocimiento para responder esa pregunta."

E. Fuentes

Cada respuesta válida debe devolver:

- documento
- página
- chunk

F. Logging

Registrar:

- número de chunks recuperados,
- scores,
- resultado del grader,
- ruta tomada por LangGraph.

No mostrar razonamiento interno del modelo.

Añadir tests para:

1. pregunta claramente documentada,
2. pregunta parcialmente documentada,
3. pregunta no relacionada,
4. base vectorial vacía.
```

---

## Fase 9 — Base de datos para historial

```text
Ahora implementaremos persistencia tradicional para usuarios, conversaciones e historial.

No mezclar el historial conversacional con la tabla vectorial. Puede usarse la misma instancia de PostgreSQL, pero en tablas relacionales separadas de las tablas de embeddings.

Usar inicialmente:

- SQLAlchemy
- PostgreSQL para desarrollo y producción

Diseñar los modelos:

User
- id
- username o email
- created_at

Conversation
- id
- user_id
- title
- created_at
- updated_at

Message
- id
- conversation_id
- role
- content
- created_at

Document
- id
- user_id
- filename
- file_type
- created_at
- status

Crear:

GET /api/conversations

GET /api/conversations/{conversation_id}

POST /api/conversations

El agente debe guardar automáticamente:

- pregunta del usuario,
- respuesta,
- fuentes utilizadas.

El nodo save_interaction de LangGraph debe encargarse de esta operación mediante un servicio independiente.

No implementar todavía autenticación real.

Crear migraciones si se considera conveniente usar Alembic.

Actualizar README.
```

---

## Fase 10 — Autenticación y seguridad

```text
Ahora debemos implementar autenticación y proteger la API.

Requisito fundamental:

ningún endpoint funcional de la aplicación debe quedar accesible sin autenticación.

Podemos utilizar Keycloak.

Diseñar la integración de forma limpia.

Implementar:

1. autenticación mediante JWT,
2. validación del access token en FastAPI,
3. identificación del usuario actual,
4. protección mediante dependency injection,
5. asociación entre user_id y:
   - conversaciones,
   - documentos,
   - historial.

Mantener públicos únicamente endpoints técnicos estrictamente necesarios como /health si se considera apropiado.

Proteger:

/api/chat/*
/api/documents/*
/api/conversations/*

El usuario A no debe poder consultar conversaciones ni documentos pertenecientes al usuario B.

Configurar mediante .env:

KEYCLOAK_URL
KEYCLOAK_REALM
KEYCLOAK_CLIENT_ID

Crear manejo para:

- token ausente,
- token inválido,
- token expirado,
- usuario no autorizado.

No poner secretos en el código.

Actualizar .env.example y README.

Incluir instrucciones para configurar Keycloak localmente.
```

---

## Fase 11 — Frontend React

```text
Ahora construiremos el frontend de la aplicación.

Tecnologías:

- React
- Vite
- React Router
- fetch o Axios

Crear una interfaz clara y funcional.

Vistas:

1. Login
2. Chat
3. Documents
4. History

Layout principal:

Sidebar:
- Chat
- Documents
- History
- Logout

Área principal:
- contenido de la vista seleccionada

CHAT:

Debe mostrar:

- mensajes del usuario,
- respuestas del agente,
- fuentes utilizadas,
- loading,
- errores.

Debe permitir iniciar una conversación nueva.

DOCUMENTS:

Debe permitir:

- seleccionar archivo,
- subirlo,
- visualizar estado de procesamiento,
- listar documentos cargados.

HISTORY:

Debe permitir:

- listar conversaciones,
- abrir conversación,
- visualizar mensajes anteriores.

AUTH:

- guardar correctamente el token,
- enviarlo como Bearer token,
- manejar expiración,
- impedir acceder a rutas privadas sin login.

No implementar diseño excesivamente complejo.

Priorizar funcionalidad, claridad y buena estructura.

Separar:

components/
pages/
services/
hooks/
context/

Crear una capa apiService o equivalente.

No duplicar lógica de llamadas HTTP en cada componente.

Usar variables de entorno para la URL del backend.

Crear manejo global de errores.
```

---

## Fase 12 — Integración completa

```text
Ahora revisa e integra todos los componentes existentes.

El flujo final debe ser:

Usuario
→ Login
→ React
→ FastAPI protegido
→ LangGraph
→ Retriever
→ PostgreSQL con pgvector
→ Context grader
→ Qwen mediante Ollama
→ respuesta + fuentes
→ almacenamiento en historial
→ frontend

Haz una revisión integral.

Verificar:

1. login,
2. protección de rutas,
3. chat,
4. retrieval,
5. rechazo,
6. fuentes,
7. subida de documentos,
8. indexación,
9. historial,
10. separación por usuario.

No agregar funcionalidades innecesarias.

Corrige:

- imports,
- manejo de excepciones,
- endpoints inconsistentes,
- schemas,
- tipos,
- variables de entorno,
- CORS.

Crear una checklist de pruebas manuales.

No modificar arquitectura sin necesidad.
```

---

## Fase 13 — Docker Compose

```text
Ahora quiero dockerizar el proyecto.

Crear Dockerfile correcto para:

- backend,
- frontend.

Crear docker-compose.yml.

Incluir servicios necesarios según la arquitectura actual.

Posibles servicios:

- backend
- frontend
- keycloak
- postgres con pgvector

PostgreSQL con pgvector puede mantenerse embebido/persistido si esa es la arquitectura actual.

Ollama inicialmente puede correr en el host local para evitar problemas de GPU y compatibilidad.

Configurar el backend para poder acceder a Ollama ejecutándose en el host.

Usar variables de entorno.

Crear volúmenes para datos persistentes.

El objetivo debe ser que:

docker compose up --build

levante la mayor parte del sistema.

Actualizar README incluyendo:

- requisitos,
- configuración,
- comandos,
- troubleshooting.
```

---

## Fase 14 — Testing

```text
Ahora quiero crear pruebas para el sistema.

Crear tests principalmente para el backend.

Utilizar pytest.

Cubrir como mínimo:

1. GET /health.
2. Endpoint protegido sin token → 401.
3. Usuario autenticado → acceso correcto.
4. Upload válido.
5. Upload con tipo no permitido.
6. Procesamiento de documento.
7. Retrieval con contenido existente.
8. Pregunta válida → respuesta.
9. Pregunta fuera del dominio → rechazo.
10. Base vectorial pgvector vacía → rechazo.
11. Ollama no disponible → error controlado.
12. Usuario A no puede acceder a información del usuario B.

Mockear el LLM cuando sea conveniente para evitar depender siempre de Ollama durante unit tests.

Separar:

- unit tests
- integration tests

Crear además un archivo:

docs/test-cases.md

con una tabla que incluya:

- ID
- caso
- entrada
- resultado esperado
- resultado obtenido
- estado

No intentar alcanzar cobertura artificial del 100%.

Priorizar las funciones críticas.
```

---

## Fase 15 — Preparación para despliegue

```text
Ahora prepara el proyecto para despliegue en nube.

No despliegues automáticamente todavía.

El frontend debería poder desplegarse en Vercel.

El backend debe quedar preparado para una plataforma como:

- Render
- Railway
- Azure App Service
- AWS

Revisar:

1. variables de entorno,
2. CORS,
3. puertos,
4. Dockerfile,
5. health check,
6. persistencia,
7. logs,
8. URLs configurables.

Analizar especialmente el problema de Ollama:

El proyecto exige un modelo local, pero el backend debe estar disponible públicamente.

Proponer una arquitectura viable para ejecutar Ollama en una VM o servidor propio.

Explicar:

- requisitos de RAM,
- posibles problemas de CPU/GPU,
- conexión backend → Ollama,
- seguridad del endpoint de Ollama.

Crear:

docs/deployment.md

con instrucciones paso a paso.

No realizar cambios destructivos.
```

---

## Fase 16 — README final

```text
Ahora crea o mejora el README principal del proyecto.

Debe quedar suficientemente claro para que otra persona pueda clonar y ejecutar el proyecto.

Incluir:

1. Nombre del proyecto.
2. Descripción.
3. Objetivo.
4. Arquitectura.
5. Tecnologías.
6. Estructura del repositorio.
7. Requisitos.
8. Instalación de Ollama.
9. Descarga del modelo Qwen.
10. Instalación del modelo de embeddings.
11. Variables de entorno.
12. Ejecución del backend.
13. Ejecución del frontend.
14. Ejecución con Docker.
15. Configuración de autenticación.
16. Carga de documentos.
17. Funcionamiento del RAG.
18. Explicación resumida de LangGraph.
19. Control de alucinaciones.
20. Ejemplos de uso.
21. Tests.
22. Despliegue.
23. Limitaciones conocidas.

Usar Markdown profesional.

No inventar funcionalidades que el proyecto no tenga.

Inspecciona primero el código real y documenta únicamente lo que realmente existe.
```

---

## Fase 17 — Generar diagramas técnicos

```text
Quiero documentar la arquitectura real del proyecto.

Inspecciona el código antes de hacerlo.

Crea diagramas Mermaid para:

1. Arquitectura general.
2. Flujo RAG.
3. Grafo LangGraph.
4. Flujo de carga de documentos.
5. Flujo de autenticación.

Arquitectura general aproximada:

Usuario
→ React
→ FastAPI
→ autenticación
→ LangGraph
→ PostgreSQL con pgvector
→ Ollama/Qwen
→ base de datos de historial

Pero debes ajustar el diagrama a la implementación real.

Guardar los diagramas en:

docs/diagrams/

Crear también un archivo:

docs/architecture.md

explicando cada componente.

No inventar componentes que no existan.
```

---

## Fase 18 — Documento técnico

```text
Quiero generar un borrador del documento técnico del proyecto basándote exclusivamente en el código real.

Debe contener:

1. Nombre del proyecto e integrantes.
2. Tema seleccionado.
3. Problema.
4. Objetivo.
5. Arquitectura general.
6. Tecnologías utilizadas.
7. Backend.
8. Frontend.
9. Agente.
10. LangChain.
11. LangGraph.
12. Modelo local Qwen.
13. Ollama.
14. Base vectorial.
15. Embeddings.
16. Proceso de carga.
17. Arquitectura RAG.
18. Control de alucinaciones.
19. Seguridad.
20. Autenticación.
21. Historial.
22. Docker.
23. Despliegue.
24. Evidencias.
25. Problemas encontrados.
26. Limitaciones.
27. Conclusiones.

Inspecciona el repositorio antes de redactar.

No inventar resultados.

Cuando falte información coloca:

[PENDIENTE DE DOCUMENTAR]

Guardar como:

docs/documento-tecnico.md
```

---

## Fase 19 — Preparar la demostración

```text
Quiero preparar una demostración de 7 a 10 minutos del proyecto.

Basándote en el sistema real, diseña un guion de demostración.

Debe incluir obligatoriamente:

1. Introducción al problema.
2. Arquitectura.
3. Login.
4. Chat.
5. Pregunta que el sistema responda correctamente.
6. Mostrar fuentes.
7. Pregunta que deba rechazar.
8. Carga de un documento nuevo.
9. Esperar procesamiento.
10. Hacer una pregunta cuya respuesta dependa del documento recién cargado.
11. Mostrar historial.
12. Mostrar brevemente LangGraph en el código.
13. Explicar los nodos.
14. Mostrar arquitectura.
15. Mostrar evidencia del despliegue.

Crear:

docs/demo-script.md

Para cada paso indicar:

- qué mostrar,
- qué decir,
- duración estimada.

La demostración completa debe durar entre 7 y 10 minutos.
```

---

## Fase 20 — Revisión final del proyecto

```text
Actúa como revisor técnico final del proyecto.

NO agregues nuevas funcionalidades todavía.

Inspecciona todo el repositorio.

Evalúa:

1. Arquitectura.
2. Backend.
3. Frontend.
4. Autenticación.
5. Seguridad.
6. LangChain.
7. LangGraph.
8. RAG.
9. PostgreSQL con pgvector.
10. Embeddings.
11. Ollama.
12. Qwen.
13. Control de alucinaciones.
14. Carga de documentos.
15. Historial.
16. Manejo de errores.
17. Variables de entorno.
18. Docker.
19. Testing.
20. README.

Identifica problemas clasificándolos como:

CRITICAL
HIGH
MEDIUM
LOW

Para cada problema indicar:

- archivo,
- problema,
- impacto,
- solución recomendada.

Después crea una checklist final.

No modifiques nada hasta mostrar primero el diagnóstico.
```

---

# Cabecera recomendada para usar antes de cada fase

```text
IMPORTANTE:

Trabaja sobre el código existente.

Antes de modificar nada:

1. inspecciona la estructura actual,
2. identifica qué componentes ya existen,
3. reutiliza el código existente cuando sea correcto,
4. no dupliques servicios,
5. no cambies nombres ni arquitectura innecesariamente,
6. no implementes funcionalidades de fases posteriores,
7. ejecuta las pruebas relevantes al finalizar.

Si necesitas modificar un archivo existente, hazlo manteniendo compatibilidad con lo ya construido.
```

---

# Cierre recomendado para cada fase

```text
Al terminar:

1. enumera los archivos creados,
2. enumera los archivos modificados,
3. explica brevemente los cambios,
4. indica los comandos que debo ejecutar,
5. indica cómo verificar manualmente que esta fase funciona,
6. no continúes con la siguiente fase.
```
