# Fase 14 — Pruebas del sistema

Ejecución del 10 de octubre de 2026 en Windows, Python 3.13 y pytest 8.3.5.
Se reutilizan las clases `unittest` existentes: pytest las descubre y ejecuta,
incluidos los casos asíncronos de `IsolatedAsyncioTestCase`. No se duplicaron
las pruebas ni se modificó la lógica del agente.

## Separación y dependencias

La separación es por marcadores registrados en `backend/pytest.ini`:

- **`unit`:** 82 pruebas aisladas, incluyendo contratos HTTP con TestClient,
  extracción de archivos y servicios externos simulados. No requieren iniciar
  PostgreSQL, Ollama ni Keycloak.
- **`integration`:** 6 pruebas en `test_documents_integration.py`,
  `test_vector_integration.py` y `test_history_integration.py`. Requieren PostgreSQL
  con pgvector; las dos primeras también usan embeddings reales de Ollama.
  Las de historial usan JWT firmados y validación real de firma/claims, con JWKS,
  generación y embeddings simulados. No requieren un usuario real de Keycloak.

`tests/conftest.py` habilita integraciones solo con `--run-integration`, incluso
si existen variables TEST_* antiguas en la terminal. La sincronización automática
de la biblioteca común se desactiva durante las pruebas. Las integraciones usan
tablas/esquemas con nombres aleatorios y limpian sus propios datos al terminar.
No ejecutarlas en una base de producción. El `.env` de la raíz define la conexión;
desde Windows debe usar el puerto publicado de PostgreSQL, no el nombre Docker
`postgres`. No es necesario detener el backend ni el frontend para probar.

## Instalación y comandos

Desde `backend/`, instalar una vez las dependencias de desarrollo:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Pruebas aisladas, sin servicios externos:

```powershell
.venv\Scripts\python.exe -m pytest -m unit -q --junitxml=test-results/unit.xml
```

Con PostgreSQL y Ollama activos, y `nomic-embed-text` descargado:

```powershell
.venv\Scripts\python.exe -m pytest -m integration --run-integration -q --junitxml=test-results/integration.xml
```

Toda la suite en una ejecución:

```powershell
.venv\Scripts\python.exe -m pytest --run-integration -q
```

Sin `--run-integration`, las integraciones se omiten; no cuentan como aprobadas.
Seleccionar `-m unit` o `-m integration` muestra el resto como `deselected`,
que significa que pertenece al otro grupo. Para investigar un fallo usar `-vv`
y el nombre de archivo/prueba. Los XML JUnit quedan en `backend/test-results/`,
fuera de Git, y contienen los resultados individuales.

`requirements-dev.txt` incluye las dependencias del backend y pytest. La imagen
de ejecución sigue instalando solo `requirements.txt`; no necesita pytest.

## Casos mínimos del plan

Todos los nombres siguientes se encuentran en `backend/tests/`. «Obtenido»
describe lo comprobado por las aserciones de esta ejecución, no una prueba manual.

| ID | Caso / prueba | Entrada | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|---|
| T14-01 | Health — `test_llm.py::LLMEndpointTests::test_health_and_docs` | GET `/health` y `/api/health` | `{"status":"ok"}`; documentación accesible | Respuestas y contrato correctos | Aprobado |
| T14-02 | Protección — `test_security.py::SecurityTests::test_all_functional_routes_require_authentication` | Rutas de chat, documentos, vectores e historial sin token | HTTP 401 con Bearer | Todas las rutas protegidas rechazan el acceso | Aprobado |
| T14-03 | Acceso autenticado — `test_history_integration.py::HistoryIsolationTests::test_upload_search_rag_history_and_cross_user_denial` | JWT RS256 válido para A | Carga 201, consultas y chat 200 | Firma/claims validados y acceso autorizado | Aprobado |
| T14-04 | Upload válido — `test_documents.py::DocumentTests::test_txt_upload_metadata_and_safe_name` | TXT deportivo y nombre con ruta | 201, nombre saneado, fragmentos y metadatos | Documento procesado y temporales limpiados | Aprobado |
| T14-05 | Tipo no permitido — `test_documents.py::DocumentTests::test_invalid_files` | `video.mp4` | 415, sin embeddings ni escritura | Archivo rechazado sin efectos persistentes | Aprobado |
| T14-06 | Procesamiento — `test_documents_integration.py::DocumentIntegrationTests` | TXT, PDF y DOCX generados para pruebas | Extracción, embeddings y persistencia; listado de los tres formatos | Los tres formatos indexados y búsqueda correcta con Ollama/PostgreSQL | Aprobado |
| T14-07 | Retrieval — `test_vector_integration.py::VectorIntegrationTests::test_semantic_search_persistence_and_dimension_guard` | Pregunta sobre mascota que ronronea | `gatos.txt` primero, metadatos y persistencia correctos | Fuente esperada recuperada mediante embeddings reales | Aprobado |
| T14-08 | Respuesta respaldada — `test_rag_performance.py::SinglePassTests::test_answer_uses_exactly_one_llm_call` | Pregunta sobre Mundial 2022 y JSON simulado válido | 200, Argentina, fuente válida; una inferencia | Contrato, fuente y número de llamadas correctos | Aprobado |
| T14-09 | Fuera de dominio — `test_hallucinations.py::HallucinationTests::test_unrelated_question_skips_model` | Consulta sobre Venus, contexto no relevante | Rechazo sin llamar al modelo | Rechazo y ausencia de inferencia confirmados | Aprobado |
| T14-10 | Base vacía — `test_history_integration.py::HistoryIsolationTests::test_pair_is_atomic_and_rejections_are_saved` y `test_rag.py::RAGTests::test_empty_database_skips_llm` | Pregunta sin documentos visibles | Rechazo sin fuentes ni inferencia; historial persistido | PostgreSQL vacío produce respuesta sin fuentes y par persistido; prueba aislada confirma el texto de rechazo | Aprobado |
| T14-11 | Ollama no disponible — `test_llm.py::LLMEndpointTests::test_provider_errors` | Error de conexión simulado | HTTP 503 controlado con `detail` | 503; también se verifican timeout 504 y errores de generación | Aprobado |
| T14-12 | Separación de usuarios — `test_history_integration.py::HistoryIsolationTests::test_global_and_private_documents_remain_isolated_through_chat` | A y B, documentos privados y global compartido | Cada contexto excluye al otro usuario; historial ajeno 404 | Aislamiento, fuentes y conservación de privados tras retirar global verificados | Aprobado |

La suite también cubre límites de archivos/contexto, PDF inválido o cifrado,
fallos de embeddings, atomicidad, tokens vencidos/falsificados, CORS, JSON inválido,
fuentes inventadas, falta parcial de información y migración explícita de historial.

## Resultado de esta ejecución

| Grupo | Aprobadas | Fallidas | No seleccionadas | Duración |
|---|---:|---:|---:|---:|
| `unit` | 82 | 0 | 6 | 10,77 s |
| `integration --run-integration` | 6 | 0 | 82 | 11,46 s |

Total: **88 pruebas aprobadas**, sin pruebas omitidas dentro de los grupos
seleccionados. Aparecieron dos advertencias de deprecación en Starlette relacionadas
con multipart y AnyIO; no se ocultaron y no provocaron fallos.

Estos tiempos corresponden a las pruebas, no a la latencia del chat. La suite no
demuestra la exactitud factual de Qwen en preguntas arbitrarias ni prueba un login
real de Keycloak desde el navegador. Para aceptación manual, usar la checklist de
[fase 12](phase12.md); para mediciones reales del modelo, consultar
[el registro de latencia](performance/colombia-latency.md).

Las pruebas del frontend siguen disponibles con `npm run test:e2e` desde
`frontend/`. No se volvieron a ejecutar en fase 14 porque no se modificó la interfaz.
