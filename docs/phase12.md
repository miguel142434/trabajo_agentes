# Fase 12: integración completa

Revisión del 8 de octubre de 2026. Se conserva la arquitectura y el modo local
de una inferencia configurado en `.env`. Esta fase no cambia la velocidad de Qwen.

## Flujo integrado

Login en Keycloak → React con token en memoria → FastAPI valida firma y claims →
LangGraph recupera documentos personales y globales desde pgvector → filtro de
relevancia y evaluación de suficiencia → respuesta con fuentes o rechazo →
persistencia del par pregunta/respuesta → React e historial privado.

Los documentos globales tienen propietario `system:global`; los personales usan
el UUID `sub` de Keycloak. Los antiguos sin propietario no pasan a ser globales.
El historial no se incorpora al prompt: cada pregunta debe ser completa.

## Correcciones y comprobaciones

- El export de Keycloak incluye retorno después del logout y la dirección real de
  Swagger (`127.0.0.1:8000`). Sus orígenes son explícitos, sin comodín general.
- `is_global` siempre es booleano, incluso para registros antiguos con propietario
  nulo; evita incompatibilidad con el esquema de documentos en usos internos.
- Prueba HTTP del preflight CORS con Authorization y Content-Type para chat y carga.
- Integración con dos usuarios: carga privada, listado mixto, búsqueda, contexto,
  fuentes, persistencia y denegación del historial ajeno. Actualizar o retirar un
  global conserva documentos personales del mismo nombre.
- Prueba del navegador para visualizar un global y subir un documento privado.

El export solo se importa al crear un realm nuevo: no actualiza un realm existente.
Si el login/logout ya funciona, no hay que recrearlo. Para ajustar un cliente
existente, el asistente `backend/scripts/configure_frontend_client.py --apply`
pide las credenciales administrativas y preserva la configuración previa.

## Evidencia automatizada

| Comprobación | Resultado y alcance |
|---|---|
| Backend | 88 pruebas aprobadas, sin omisiones, con ambas integraciones activadas |
| PostgreSQL/pgvector | Reales, tablas y esquema aislados; limpieza de los datos de prueba |
| Embeddings | Ollama real en las pruebas de documentos y búsqueda |
| Chat/historial/aislamiento | HTTP ASGI, JWT firmado y PostgreSQL reales; LLM y embeddings simulados en esa prueba |
| Navegador | 8 pruebas aprobadas en Edge; React y adaptador Keycloak reales, HTTP de API/OIDC simulado |
| Frontend | `npm run build` aprobado |
| Servicios locales | `/health`: 200; `/api/documents` sin token: 401; discovery Keycloak: 200; login PKCE presenta formulario: 200 |

En la suite apareció un `ResourceWarning` de transporte asíncrono no cerrado,
sin fallos de pruebas. No se introdujeron credenciales de un usuario real ni se
ejecutó una pregunta completa desde el navegador contra Qwen en esta revisión.
La aceptación manual siguiente queda para comprobar esa combinación con tu cuenta.
Las mediciones reales previas de Qwen están en `performance/colombia-latency.md`.

Comandos desde `backend/` (PostgreSQL y Ollama activos):

```powershell
$env:TEST_AUTH_INTEGRATION='1'
$env:TEST_VECTOR_INTEGRATION='1'
.venv\Scripts\python.exe -m unittest discover -s tests -t .
```

Desde `frontend/`:

```powershell
npm run build
npm run test:e2e
```

## Arranque local

Abre Docker Desktop y Ollama. Desde la raíz, para el entorno existente:

```powershell
docker compose up -d postgres
docker start rag-keycloak
cd backend
.venv\Scripts\python.exe run.py
```

En otra terminal desde la raíz:

```powershell
cd frontend
npm run dev
```

Usar `http://localhost:5173`. Si cambiaron dependencias, ejecutar antes `npm ci`.
No iniciar a la vez el Keycloak antiguo y el de Compose: ambos usan 8080 y el nuevo
no contiene automáticamente los usuarios existentes. Para instalaciones nuevas,
Compose puede levantar `postgres keycloak`; hay que crear los usuarios del realm.
No borrar volúmenes ni recrear cuentas para resolver un problema de arranque.

El arranque completo en contenedores pertenece a fase 13: aún deben alinearse el
puerto 3000, CORS, las URLs internas/externas de Keycloak y su almacenamiento persistente.

## Checklist de aceptación manual

Preparación: dos usuarios distintos A y B en `rag-agent`, sin contraseñas temporales
ni acciones requeridas. Usar sesiones separadas o cerrar sesión entre usuarios.
Esperar `Base de conocimiento global sincronizada` antes de probar el PDF común.

- [ ] **Login y rutas:** abrir `/chat` sin sesión lleva al login. Entrar como A muestra
  su nombre. No hay errores CORS en la consola del navegador.
- [ ] **Base común:** en Documentos aparece `Mundiales_documento_RAG.pdf` con etiqueta
  global. Elegir una pregunta cuya respuesta esté explícitamente en ese PDF.
- [ ] **Carga/indexación:** crear `fase12-a.txt` con «La copa de prueba Aurora 2040
  la ganó el equipo Cóndor Azul». Subirlo como A. Aparece listo para consultar.
- [ ] **Respuesta:** preguntar «¿Qué equipo ganó la copa de prueba Aurora 2040?».
  Debe responder Cóndor Azul con la fuente `fase12-a.txt`. Revisar documento,
  página si corresponde y fragmento. No asumir que una respuesta rápida es correcta.
- [ ] **Rechazo:** preguntar por el salario exacto del entrenador de Cóndor Azul,
  dato ausente del corpus. Debe rechazar por falta de información, sin fuentes inventadas.
- [ ] **Historial:** abrir ambas conversaciones, recargar la página y comprobar que
  persisten preguntas, respuesta/rechazo y fuentes. Continuar una conversación
  conserva su ID; Nueva conversación crea otra al enviar la siguiente pregunta.
- [ ] **Separación:** copiar la URL de la conversación de A. Entrar como B: ve la
  base común, pero no `fase12-a.txt` ni el historial de A. Abrir la URL copiada
  muestra error de acceso/recurso inexistente. B no obtiene el dato privado de A.
- [ ] **Logout:** cerrar sesión devuelve al login. Atrás/recargar no permite consultar
  documentos ni conversaciones sin autenticación.
- [ ] **Error recuperable:** con sesión activa detener solo el backend y actualizar
  Documentos. Se muestra error; arrancarlo y reintentar recupera el listado.
- [ ] **Espera:** durante una pregunta lenta no se puede duplicar el envío. Cambiar
  a Documentos/Historial y regresar conserva la respuesta en curso.

Registrar fecha, usuario de prueba y resultado; no guardar contraseñas ni tokens.
