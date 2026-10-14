# Documento técnico — RAG Sports Agent

**Fase 18 · Borrador para revisión del equipo**  
Fecha de elaboración: 13 de octubre de 2026.  
Base de revisión: commit `b0e52f0` y archivos presentes en el repositorio al elaborar
este documento. No se realizaron nuevos despliegues ni ejecuciones de la suite en
esta fase; los resultados citados corresponden a los registros indicados.

## 1. Nombre del proyecto e integrantes

**RAG Sports Agent: asistente documental deportivo con modelos locales.**

- Miguel Zuleta.
- Sebastián Giraldo.
- Martín Restrepo.

Asignatura: Implementación e Integración de Software. La distribución formal de
responsabilidades individuales, si se requiere para la entrega, está
**[PENDIENTE DE DOCUMENTAR]**. No se deduce autoría individual de funcionalidades
a partir de nombres de archivos o del orden de los commits.

## 2. Tema seleccionado

El dominio es la consulta de documentación deportiva: mundiales de fútbol,
Fórmula 1 y otros deportes. La biblioteca común incluida en
`backend/knowledge_base/Mundiales_documento_RAG.pdf` está orientada a mundiales;
los ejemplos en `docs/examples/deportes/` incluyen fútbol y Fórmula 1.

Cada usuario puede aportar PDF, TXT o DOCX a su biblioteca privada. El agente
combina el contenido común con el autorizado para esa cuenta. La procedencia
bibliográfica completa y fecha de actualización del corpus común están
**[PENDIENTE DE DOCUMENTAR]**; incluirlo en el repositorio no demuestra su exactitud.

## 3. Problema

La información de interés puede estar repartida entre documentos extensos y en
formatos diferentes. Buscarla manualmente requiere localizar pasajes y comprobar
su pertinencia. Un modelo generativo por sí solo puede producir afirmaciones sin
respaldo en los documentos disponibles.

El problema abordado por la implementación es ofrecer consultas en lenguaje
natural sobre ese corpus con referencias y separación de datos personales. Esta
formulación describe la finalidad del sistema; no deriva de una encuesta o estudio
de usuarios. La evaluación de necesidades con usuarios está **[PENDIENTE DE DOCUMENTAR]**.

## 4. Objetivo

Construir un asistente que recupere fragmentos relevantes, evalúe si permiten
responder y devuelva una respuesta en español con fuentes, o un rechazo explícito
cuando falte respaldo. El sistema debe permitir cargar documentos, conservar
conversaciones y proteger el acceso mediante autenticación.

Los objetivos verificables son: procesar los formatos admitidos, recuperar contenido
autorizado, citar fragmentos existentes, controlar errores de dependencias externas
y persistir el historial por usuario. No se plantea como resultado demostrado una
exactitud factual absoluta ni un tiempo de respuesta garantizado.

## 5. Arquitectura general

El navegador ejecuta React, inicia sesión en Keycloak y envía peticiones autenticadas
a FastAPI. El backend coordina LangGraph, PostgreSQL con pgvector y Ollama. Tras
recuperar contexto y generar o rechazar la respuesta, guarda la interacción y la
devuelve a la interfaz.

Hay una base PostgreSQL de la aplicación para datos vectoriales y relacionales.
Keycloak mantiene su almacenamiento separado. En Compose, frontend, backend,
PostgreSQL y Keycloak son contenedores; Ollama corre en el anfitrión.

La [arquitectura de fase 17](architecture.md) contiene los cinco diagramas de
componentes, RAG, LangGraph, carga y autenticación. Esas representaciones se basan
en código, no en un despliegue público supuesto.

## 6. Tecnologías utilizadas

| Área | Dependencias o configuración declaradas |
|---|---|
| API | FastAPI 0.115.0, Uvicorn 0.30.6, Pydantic Settings 2.7.0 |
| Orquestación | LangGraph 1.2.12, langchain-ollama 1.1.0 |
| Modelos | Ollama; `qwen3:8b` y `nomic-embed-text` |
| Persistencia | PostgreSQL 16, extensión pgvector, psycopg 3.3.6, SQLAlchemy 2.0.35 |
| Extracción | pypdf 6.19.0, python-docx 1.2.0 |
| Fragmentación | langchain-text-splitters 1.1.2 |
| Identidad | Keycloak; PyJWT 2.8.0 y cryptography 42.0.5 |
| Interfaz | React 18, React Router, Vite, keycloak-js y fetch |
| Servidor del frontend | Nginx en Docker |
| Pruebas | pytest 8.3.5, unittest y Playwright |

Fuentes de versiones: [requirements.txt](../backend/requirements.txt),
[requirements-dev.txt](../backend/requirements-dev.txt),
[package.json](../frontend/package.json), [lockfile](../frontend/package-lock.json)
y [Compose](../docker-compose.yml). El paquete Python `pgvector` no es la versión
de la extensión del servidor. No se asume que todos los entornos instalados sean iguales.

## 7. Backend

FastAPI separa rutas, esquemas, servicios, seguridad y almacenamiento. La configuración
se carga desde variables del proceso y el `.env` de la raíz. El lifespan inicializa
las tablas relacionales y, si está habilitado, lanza la sincronización de la biblioteca
común en segundo plano. La documentación interactiva se sirve en `/docs`.

| Ruta | Función | Acceso |
|---|---|---|
| GET `/health`, `/api/health` | Estado de la API | Público |
| POST `/api/test-llm` | Prueba de generación | Autenticado |
| POST `/api/documents/upload` | Carga e indexación | Autenticado |
| GET `/api/documents` | Listado propio y global | Autenticado |
| POST `/api/vector/test-add`, `/api/vector/test-search` | Operaciones de prueba vectorial | Autenticado |
| POST `/api/chat/rag` | Pregunta, respuesta y fuentes | Autenticado |
| GET/POST `/api/conversations` | Listar o crear conversaciones | Autenticado |
| GET `/api/conversations/{id}` | Leer conversación propia | Autenticado |

Los handlers distinguen validación, autorización, indisponibilidad y timeout.
Por ejemplo, conexión a Ollama fallida produce 503 y tiempo excedido produce 504;
estos errores no se convierten en una respuesta de falta de conocimiento.
Health no comprueba exhaustivamente todos los servicios.

Código: [main](../backend/app/main.py), [router](../backend/app/api/router.py),
[configuración](../backend/app/core/config.py) y [errores](../backend/app/core/exceptions.py).

## 8. Frontend

La aplicación React contiene vistas de login, chat, documentos e historial. React
Router protege las vistas privadas. Los contextos administran autenticación,
avisos y conversación activa. La capa API comparte envío de tokens, manejo de
errores y cancelación de peticiones.

El chat muestra pregunta, respuesta y fuentes; permite nueva conversación y reabrir
historial. Durante una consulta se evita duplicar el envío y se conserva el trabajo
al navegar entre secciones. El listado distingue documentos comunes de personales.
Una expiración de sesión limpia el estado privado.

La capa fetch tiene una espera de cinco minutos y no reintenta automáticamente POST:
una respuesta perdida podría corresponder a una operación ya guardada. Las variables
`VITE_*` se incorporan al compilar y son públicas, por lo que no deben contener secretos.

Código: [App.jsx](../frontend/src/App.jsx), [páginas](../frontend/src/pages),
[contextos](../frontend/src/context) y [apiService](../frontend/src/services/apiService.js).

## 9. Agente

El agente es un flujo controlado de recuperación, evaluación y respuesta. No navega
por Internet, no delega en otros agentes y no decide ejecutar herramientas arbitrarias.
`RAGService.answer` comprueba primero el acceso a la conversación y luego invoca el grafo.

La entrada contiene `question` y `conversation_id` opcional; el propietario se obtiene
del token. La salida exitosa de la API contiene `answer`, `sources` y el ID de conversación.
Cada petición reinicia los datos derivados del estado, evitando reutilizar un borrador
de otra consulta. Ver [servicio RAG](../backend/app/services/rag_service.py) y
[contratos](../backend/app/schemas/rag.py).

## 10. LangChain

LangChain aporta los adaptadores `ChatOllama` y `OllamaEmbeddings`, los mensajes de
prompt y `RecursiveCharacterTextSplitter`. Estos componentes se integran dentro de
servicios propios; no sustituyen el filtro de usuarios ni la persistencia SQL.

La selección de fuentes, los límites y el control de errores se implementan en el
proyecto. No se ha añadido una memoria conversacional de LangChain al prompt.

## 11. LangGraph

`StateGraph` utiliza `AgentState` y siete nodos:

| Nodo | Responsabilidad |
|---|---|
| `receive_question` | Reiniciar el estado derivado de la petición |
| `validate_question` | Validar y normalizar la pregunta |
| `retrieve_context` | Recuperar fragmentos autorizados |
| `grade_context` | Filtrar, limitar y evaluar contexto |
| `generate_answer` | Generar o reutilizar borrador y validar fuentes |
| `reject_question` | Establecer rechazo y fuentes vacías |
| `save_interaction` | Guardar la interacción antes de finalizar |

`context_sufficient` selecciona la rama de generación o rechazo. El generador
también puede derivar a rechazo. Las excepciones técnicas interrumpen el flujo;
no se garantiza guardar una interacción que falla antes del nodo de persistencia.

Código y representación: [graph.py](../backend/app/agents/graph.py),
[rag_nodes.py](../backend/app/agents/nodes/rag_nodes.py) y
[agent-graph.mmd](diagrams/agent-graph.mmd).

## 12. Modelo local Qwen

El modelo predeterminado es `qwen3:8b`. La integración configura `reasoning=False`
y temperatura cero en RAG. La ventana se configura en 8192 tokens; el límite
predeterminado de salida es 512 tokens. El presupuesto de contexto documental
de 6000 caracteres es un límite diferente de la ventana en tokens.

Qwen recibe fragmentos recuperados y devuelve JSON. El sistema no entrena ni
ajusta los pesos del modelo con los archivos subidos. La adecuación a deportes
procede del corpus y las instrucciones. El código detecta salida truncada y la
trata como error, en vez de aceptar JSON parcial.

Ver [LLMService](../backend/app/services/llm_service.py). Las mediciones disponibles
corresponden a CPU y no permiten afirmar rendimiento equivalente en otros equipos.

## 13. Ollama

Ollama ejecuta generación y embeddings por HTTP. En modo nativo se usa normalmente
`localhost:11434`; desde Compose, `host.docker.internal:11434`. Los modelos deben
descargarse previamente. El backend controla timeout y registra tiempos de carga,
procesamiento del prompt y generación cuando el proveedor los devuelve.

`RAG_KEEP_ALIVE=15m` solicita mantener el modelo en memoria; no garantiza que siempre
permanezca cargado. El modo híbrido puede añadir autenticación Bearer mediante
`OLLAMA_API_KEY` y un proxy. No es una clave de un servicio de IA de pago.

## 14. Base vectorial

PostgreSQL con pgvector almacena fragmentos y embeddings en `document_chunks`;
el catálogo se encuentra en `uploaded_documents` (nombres configurables). Se
conservan identificador, documento, nombre, página, índice, texto, modelo,
metadatos y propietario.

La implementación ejecuta búsqueda exacta ordenada por distancia coseno, no un
índice aproximado HNSW declarado por la aplicación. Filtra modelo de embeddings
y propietario antes del límite Top-K. Permite datos propios y `system:global`;
NULL identifica registros anteriores, no documentos compartidos automáticamente.

Al conectar se verifica la dimensión esperada. Cambiar dimensión o modelo requiere
gestionar la reindexación; los vectores de modelos distintos no se intercambian
como si fueran equivalentes. Ver [PostgresVectorStore](../backend/app/vectorstore/postgres.py).

## 15. Embeddings

`nomic-embed-text` produce vectores de 768 dimensiones según la configuración actual.
El servicio añade `search_document: ` a los fragmentos y `search_query: ` a preguntas.
Verifica número de resultados, dimensión, valores finitos y vectores no nulos.

Se usa el embedding para proximidad semántica, no como una puntuación de verdad.
Una distancia baja no demuestra que el fragmento responda completamente la pregunta;
por eso existe una evaluación posterior de suficiencia.

Código: [EmbeddingService](../backend/app/services/embedding_service.py).

## 16. Proceso de carga

La carga privada sigue estos pasos:

1. Autenticar la petición y validar nombre, extensión y límite de 10 MiB por defecto.
2. Crear temporal con identificador interno; rechazar contenido vacío o inválido.
3. Extraer texto con pypdf, python-docx o decodificación TXT UTF-8.
4. Dividir con tamaño 800 y solapamiento 120 caracteres por defecto. Conservar
   página PDF y metadatos; validar límites de texto y número de fragmentos.
5. Generar embeddings por lotes de hasta 32 fragmentos.
6. Publicar catálogo y fragmentos en una transacción asociada al usuario.
7. Limpiar el temporal, también ante errores posteriores a su creación.

No se conserva un original descargable. La carga se completa dentro de la petición;
no hay cola de tareas externa. La biblioteca común se sincroniza mediante una tarea
asíncrona al arrancar: compara SHA-256 y modelo, omite archivos sin cambios, reemplaza
versiones globales y retira registros de archivos eliminados. Una carpeta inexistente
no dispara el vaciado global. Los originales versionados de esa biblioteca permanecen.

Código: [document_service](../backend/app/services/document_service.py),
[file_storage](../backend/app/services/file_storage.py),
[chunking](../backend/app/services/chunking_service.py),
[knowledge_base](../backend/app/services/knowledge_base.py).

## 17. Arquitectura RAG

La recuperación aumentada para generación combina pregunta y fragmentos autorizados
en un prompt acotado. Se recuperan hasta cuatro fragmentos por defecto y se aplica
`score = 1 - distance`, con valores válidos y estrictamente superiores a 0,65.
El prompt conserva solo el contenido que cabe en el presupuesto configurado.

| Modo | Comportamiento |
|---|---|
| `RAG_SINGLE_PASS=false` | Una llamada evalúa; si hay respaldo, otra genera |
| `RAG_SINGLE_PASS=true` | Una llamada produce suficiencia, borrador y referencias |
| Sin contexto seleccionado | Rechazo sin llamada a Qwen; la recuperación puede haber calculado el embedding |

El modo conjunto reutiliza el borrador de la misma petición. No es una caché entre
usuarios. Tras validar, se guardan respuesta y fuentes. El historial no aporta
turnos anteriores al contexto; las preguntas deben formularse completas.

Ver [diagrama RAG](diagrams/rag-flow.mmd), [prompt](../backend/app/services/rag_prompt.py)
y [retriever](../backend/app/services/rag_retriever.py).

## 18. Control de alucinaciones

Los controles presentes son: filtro de relevancia, evaluación de suficiencia,
instrucciones para usar solo hechos explícitos del contexto, rechazo de datos
parciales o contradictorios, estructura JSON estricta y validación de referencias.
Las instrucciones de los documentos se tratan como datos, no como órdenes confiables.

Cuando falta respaldo, se devuelve:

> No tengo suficiente información en mi base de conocimiento para responder esa pregunta.

Una respuesta sin fuentes o un rechazo explícito del generador deriva a la rama de
rechazo. JSON inválido, referencia inexistente o salida truncada producen error
técnico. Estas defensas no constituyen una garantía contra toda alucinación o
inyección de instrucciones. La evaluación factual sobre un conjunto amplio y
etiquetado de preguntas está **[PENDIENTE DE DOCUMENTAR]**.

Código: [evaluador](../backend/app/services/context_grader.py),
[fuentes](../backend/app/services/rag_sources.py), [esquemas](../backend/app/schemas/rag.py).

## 19. Seguridad

La API exige JWT en las rutas funcionales. La propiedad se deriva de `sub`, no de
un identificador arbitrario enviado por el cliente. El SQL filtra documentos por
propietario y las conversaciones ajenas se rechazan con 404. Al guardar historial
se vuelve a comprobar propiedad dentro de la transacción.

La carga sanea nombres y usa UUID internos, limita bytes/texto/fragmentos y limpia
temporales. CORS restringe qué orígenes del navegador pueden llamar a la API, pero
no sustituye la autenticación. Las credenciales no deben introducirse en `VITE_*`.

Existe una discrepancia conocida: el export de Keycloak incorpora `*` en
`webOrigins` y comodines de dominios, mientras una prueba exige no usar ese origen
general. Antes de publicar se deben configurar direcciones concretas. Compose usa
Keycloak `start-dev` y valores administrativos de ejemplo; no se presenta como
configuración de producción endurecida.

## 20. Autenticación

React usa `keycloak-js` con Authorization Code + PKCE S256, comprobación inicial
`check-sso` y tokens en memoria. Antes de las peticiones solicita renovación si
restan menos de 30 segundos. Si falla la renovación o la API devuelve 401, limpia
la sesión. El logout redirige a Keycloak y vuelve al login.

FastAPI valida firma RS256 y claims `iss`, `aud`, `exp`, `iat`, `azp`, `typ` y `sub`
UUID. Las claves se obtienen por JWKS con caché o de `KEYCLOAK_JWKS_JSON`. Leer
`kid` sin validar solo selecciona clave; la firma se comprueba después. Una copia
JSON debe actualizarse al rotar claves. `KEYCLOAK_ISSUER_OVERRIDE` separa emisor
público de la dirección interna del servicio.

Swagger utiliza OAuth2 de contraseña, distinto del frontend PKCE. El export crea
realm/cliente, no usuarios; tampoco actualiza automáticamente un realm existente.
Ver [security.py](../backend/app/core/security.py) y
[authService](../frontend/src/services/authService.js).

## 21. Historial

SQLAlchemy administra `users`, `conversations` y `messages`. Una interacción guarda
pregunta y respuesta en una sola transacción; también guarda rechazos. La respuesta
incluye su ID de conversación. Las fuentes se serializan como JSON en una columna
de texto y la interfaz las interpreta al reabrir el historial.

Si se continúa una conversación se comprueba que pertenezca al usuario, se bloquea
su fila al guardar y se actualiza la fecha. Fallar en la creación del par provoca
rollback. El modelo heredado `documents_history` existe, pero no es el catálogo
de la carga actual. La migración del historial antiguo por username es explícita,
no automática al iniciar sesión.

Código: [modelos](../backend/app/models/domain.py),
[InteractionService](../backend/app/services/interaction_service.py) y
[guía de migración](history-auth.md).

## 22. Docker

Compose define PostgreSQL/pgvector, Keycloak, backend y frontend. El backend usa
Python 3.11-slim; el frontend se compila con Node y se sirve con Nginx, cuyo fallback
permite recargar rutas SPA. Ollama permanece fuera de los contenedores.

| Recurso | Configuración local |
|---|---|
| Frontend | Puerto 3000; Vite nativo usa 5173 |
| Backend | Puerto 8000 por defecto |
| Keycloak | Puerto 8080 |
| PostgreSQL | Puerto anfitrión configurable, 5432 interno |
| Persistencia | `postgres_data`, `keycloak_data`, `uploaded_documents_data` |

Desde la raíz, con `.env`, Docker y Ollama disponibles:

```powershell
docker compose up --build -d
docker compose ps
docker compose logs -f backend
```

La aplicación se abre en `http://localhost:3000`. `docker compose down` conserva
volúmenes; añadir `-v` los elimina. El volumen de documentos no evita la eliminación
de originales temporales realizada por el código. No ejecutar otro backend o
Keycloak simultáneamente en los mismos puertos.

Referencia: [Compose](../docker-compose.yml) y [guía de ejecución](../README.md).

## 23. Despliegue

La fase 15 preparó una arquitectura híbrida con frontend en Vercel/Netlify, backend
en Render, PostgreSQL en Neon y Ollama local mediante proxy autenticado y túnel.
El código incluye puerto dinámico, URLs configurables, reescrituras SPA y soporte
de Bearer para el proxy. Las conexiones remotas de base reemplazan `-pooler.` por
`.` para usar endpoint directo.

El proxy `scripts/tunnel/ollama_proxy.py` escucha en loopback; autentica peticiones
hacia Ollama y deja públicos sus health checks. Genera y muestra un secreto si no
se proporciona; esos logs no deben publicarse. La nube sigue dependiendo del equipo
que ejecuta Ollama y, si es local, de Keycloak.

**URL pública real, fecha de despliegue, entorno final y evidencia de acceso remoto:**
**[PENDIENTE DE DOCUMENTAR]**. El repositorio demuestra preparación, no confirma
una instalación activa. Los costos/cuotas de proveedores descritos en
[deployment.md](deployment.md) no se verificaron en esta fase ni se garantizan.

## 24. Evidencias

Se distinguen implementación inspeccionada, resultados históricos y validaciones
todavía pendientes. No se ejecutó una nueva batería de pruebas al redactar el informe.

| Evidencia | Resultado registrado | Alcance y fuente |
|---|---|---|
| Backend, fase 14 (10/10/2026) | 82 pruebas aisladas y 6 integraciones aprobadas | [test-cases.md](test-cases.md); no certifica los commits posteriores |
| Navegador, fase 12 (08/10/2026) | 8 pruebas aprobadas y build correcto | [phase12.md](phase12.md); API/OIDC simulados en navegador |
| Integración de documentos | PostgreSQL y embeddings de Ollama reales | Casos de fase 14; tablas/esquemas de prueba aislados |
| Chat/historial privado | HTTP ASGI, JWT firmado y PostgreSQL; LLM simulado | Pruebas de aislamiento e historial en fase 14 |
| Docker, fase 13 | Arranque/build y comprobaciones HTTP registrados | [phase13.md](phase13.md); registro documental, no nueva ejecución |
| Arquitectura, fase 17 | Cinco fuentes Mermaid y grafo generado desde código | [architecture.md](architecture.md) |
| Latencia, 06/10/2026 | 212,80 s con dos llamadas; 111,74 s con una | [dos llamadas](performance/colombia-two-8b.json), [una llamada](performance/colombia-single-8b.json) |

La medición de latencia usó la misma pregunta sobre Colombia y el mismo PDF personal
con Qwen 8B en CPU. Ambas respuestas señalaron cuartos de final en Brasil 2014 con
las mismas fuentes. La reducción observada fue aproximadamente 47,5 %. Es una muestra
por modo, no un promedio. No incluye navegador, login ni escritura del historial;
no debe atribuirse al PDF global actual. Ver [metodología](performance/colombia-latency.md).

Las pruebas no equivalen a medir precisión factual general. La ejecución actual de
toda la suite después de fase 15, capturas finales con cuentas reales y aceptación
manual completa están **[PENDIENTE DE DOCUMENTAR]**. La discrepancia de Keycloak
impide presentar los resultados históricos como una suite actual sin fallos.

Para reproducir desde `backend/`:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -m unit -q
.venv\Scripts\python.exe -m pytest -m integration --run-integration -q
```

El segundo grupo requiere PostgreSQL y Ollama activos. Las pruebas de navegador
se ejecutan con `npm run test:e2e` desde `frontend/`. No usar producción para las
integraciones; consultar los prerrequisitos en [test-cases.md](test-cases.md).

## 25. Problemas encontrados

| Problema | Evidencia y tratamiento existente | Situación |
|---|---|---|
| Respuestas lentas en CPU | Medición identificó procesamiento del contexto; modo conjunto elimina una inferencia | Mejoró la muestra, pero la latencia sigue siendo alta |
| psycopg asíncrono en Windows | `run.py` selecciona WindowsSelectorEventLoopPolicy | Ajuste presente para arranque nativo |
| Dependencia asíncrona de SQLAlchemy | `SQLAlchemy[asyncio]` declarado en requirements | Dependencia incluida; verificar instalación del entorno |
| Puertos y cuentas entre Keycloak antiguo y Compose | Guías distinguen contenedores y volúmenes | Detener el servicio duplicado; no asumir migración de usuarios |
| Datos antiguos sin propietario | Migración explícita de historial y recarga de documentos documentadas | Sin reasignación automática |
| URLs internas Docker frente al emisor JWT público | Separación de URL de JWKS y emisor esperado | Soporte configurado |
| Orígenes comodín de Keycloak | Export de fase 15 contradice aserción de `test_integration_contract.py` | Pendiente de corrección y nueva validación |
| Documentación demasiado concluyente | README de fase 16 distingue costos, evidencia histórica y límites | Informe conserva esas distinciones |

Este apartado resume problemas observables/documentados. No reemplaza la revisión
final de seguridad y calidad prevista en fase 20 ni afirma que todos estén resueltos.

## 26. Limitaciones

- Dependencia de hardware y disponibilidad de Ollama; sin él no hay generación ni
  nuevos embeddings. Llevar FastAPI a la nube no acelera por sí solo Qwen local.
- Sin OCR, búsqueda web, actualización automática del corpus ni memoria de turnos
  anteriores en el prompt.
- Presupuesto limitado de contexto, Top-K y umbral pueden excluir evidencia relevante.
- Las fuentes se validan estructuralmente; no se demuestra automáticamente cada
  afirmación ni se elimina todo riesgo de alucinación o inyección de instrucciones.
- Los originales privados se eliminan después de procesarlos; no hay descarga de ellos.
- Las mediciones disponibles no son pruebas de carga, percentiles de latencia ni
  evaluación con múltiples usuarios concurrentes.
- Health informa disponibilidad de la API, no preparación de toda la infraestructura
  ni finalización de la sincronización global.
- El entorno local usa configuración de desarrollo de Keycloak; quedan ajustes para
  publicación y una discrepancia de configuración/prueba ya identificada.
- Las evidencias de pruebas son históricas y parcialmente simuladas. No existe en
  este informe una aceptación manual reciente del recorrido remoto completo.

## 27. Conclusiones

El código integra interfaz web, identidad, procesamiento documental, recuperación
vectorial, evaluación de suficiencia, generación local e historial privado. La
separación en servicios y el grafo explícito permiten seguir el recorrido de una
pregunta y distinguir rechazo por falta de respaldo de un error técnico.

La biblioteca común permite consultar contenido precargado, mientras la biblioteca
personal amplía el corpus visible sin compartir automáticamente datos de otras
cuentas. Las pruebas históricas aportan evidencia de contratos e integración, con
los límites de simulación descritos. La muestra de rendimiento respalda una mejora
al combinar inferencias, pero no una experiencia de respuesta inmediata.

El resultado es una implementación funcional documentada, no una certificación
de preparación para producción. Antes de una entrega definitiva deben completarse
las evidencias pendientes, resolver la discrepancia de Keycloak y ejecutar las
comprobaciones pertinentes. Las fases 19 y 20 del plan siguen fuera del alcance de
esta redacción.

### Fuentes internas y pendientes de entrega

Las referencias enlazadas a lo largo del documento apuntan al código y registros
del repositorio. Para operación: [README](../README.md). Para diseño:
[arquitectura](architecture.md). Para alcance: [plan de desarrollo](../plan_desarrollo.md).

| Dato pendiente | Estado |
|---|---|
| Distribución formal de responsabilidades, si la entrega la exige | [PENDIENTE DE DOCUMENTAR] |
| Procedencia y actualización bibliográfica completa del corpus común | [PENDIENTE DE DOCUMENTAR] |
| Evaluación con usuarios y conjunto de preguntas etiquetadas | [PENDIENTE DE DOCUMENTAR] |
| URL pública, entorno final y comprobación remota | [PENDIENTE DE DOCUMENTAR] |
| Resultados recientes de suite y aceptación manual con capturas | [PENDIENTE DE DOCUMENTAR] |
