# Fase 11 — Interfaz React

El frontend permite iniciar sesión, consultar el agente, cargar documentos y abrir
conversaciones guardadas. Usa React, React Router, Vite y `fetch`, con una capa API
compartida y el adaptador oficial `keycloak-js`. La interfaz está en español y se
adapta a escritorio y móvil. No modifica la lógica RAG del backend.

## Ejecutar

Se recomienda Node.js 22 (probado con 22.13). Con Docker Desktop y Ollama abiertos,
desde la raíz del repositorio:

```powershell
docker compose up -d postgres
docker start rag-keycloak
cd backend
.venv\Scripts\python.exe run.py
```

En otra terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Abrir **http://localhost:5173**. El puerto es fijo: Vite avisa si 5173 está ocupado
en vez de elegir otro que Keycloak no tenga autorizado.

El frontend utiliza por defecto `http://127.0.0.1:8000` para la API y
`http://localhost:8080` para Keycloak, realm `rag-agent`, cliente `rag-frontend`.
Para modificarlos, copiar `frontend/.env.example` a `frontend/.env.local` y reiniciar Vite:

```dotenv
VITE_API_URL=http://127.0.0.1:8000
VITE_KEYCLOAK_URL=http://localhost:8080
VITE_KEYCLOAK_REALM=rag-agent
VITE_KEYCLOAK_CLIENT_ID=rag-frontend
```

Vite lee las variables de la carpeta `frontend`, no el `.env` del backend en la raíz.
Las variables `VITE_*` son públicas: no colocar contraseñas ni secretos allí. Se
incorporan a la compilación; cambiar el entorno de nginx no modifica un build existente.

## Configuración de Keycloak

El acceso del frontend usa **Authorization Code + PKCE S256**, con redirección a
Keycloak. No captura contraseñas ni almacena tokens en localStorage/sessionStorage.
Los tokens se mantienen en memoria; el adaptador consulta la sesión de Keycloak al
recargar y renueva el acceso antes de las peticiones y al expirar. El cierre de sesión
limpia el estado privado y redirige al logout de Keycloak.

En `rag-agent → Clients → rag-frontend`, conservar la configuración de Swagger y añadir:

| Campo | Valor para desarrollo |
|---|---|
| Client authentication | Off (cliente público) |
| Standard flow | On |
| Valid redirect URIs | `http://localhost:5173/*` |
| Valid post logout redirect URIs | `http://localhost:5173/login` |
| Web origins | `http://localhost:5173` |

Si se abre con `127.0.0.1`, añadir también las tres direcciones equivalentes y ese
origen a `CORS_ORIGINS` del backend. Para el acceso recomendado con `localhost`, el
backend ya tiene ese origen permitido por defecto. `Direct access grants` puede
permanecer habilitado para Swagger; el nuevo frontend no utiliza ese flujo.

Para configurar ambos nombres locales preservando las direcciones existentes,
desde `backend/` hay un asistente que pide las credenciales del administrador:

```powershell
# Primero muestra el cambio:
.venv\Scripts\python.exe scripts/configure_frontend_client.py
# Aplicar explícitamente:
.venv\Scripts\python.exe scripts/configure_frontend_client.py --apply
```

Documentación de referencia: [adaptador JavaScript de Keycloak](https://www.keycloak.org/securing-apps/javascript-adapter).

## Uso

1. **Iniciar sesión:** continuar en Keycloak con tu usuario de `rag-agent` y volver
   automáticamente al chat. Una sesión caducada o un 401 devuelve a la pantalla de acceso.
2. **Documentos:** elegir PDF, TXT o DOCX y pulsar **Subir documento**. Durante el
   procesamiento se bloquea el envío duplicado. Se muestra la confirmación y se actualiza
   la biblioteca, con paginación, fecha, tamaño y fragmentos. Los límites definitivos
   de tamaño y contenido los valida el backend.
3. **Chat:** escribir una pregunta completa. Enter envía; Shift + Enter añade una línea.
   La respuesta muestra documento, página cuando existe y fragmento utilizado. El
   fragmento se numera desde 1 en pantalla (el índice de la API empieza en 0).
4. **Nueva conversación:** limpia el intercambio actual; la siguiente pregunta crea
   una conversación nueva. Las siguientes preguntas conservan el ID que devuelve la API.
5. **Historial:** lista conversaciones del usuario, permite abrirlas, leer los mensajes
   previos y seguir preguntando en la misma conversación. Las fuentes antiguas guardadas
   como JSON de texto también se muestran.

Se puede navegar a documentos o historial mientras el agente responde; la consulta
permanece activa en el contexto del chat. No se permite abrir otra conversación ni
iniciar una nueva hasta que finalice. Si se cierra/recarga la página, se pierde la
espera local, pero el servidor puede haber guardado la operación: revisar el historial
antes de repetir. Lo mismo aplica al salir durante una subida de archivo.

No hay porcentaje ficticio de procesamiento ni respuestas simuladas en la aplicación.
El tiempo máximo de espera del cliente es cinco minutos. No se reintentan automáticamente
peticiones POST, para evitar duplicar documentos o mensajes. Los errores de red, validación,
permisos y servidor tienen mensajes visibles y las listas permiten volver a intentar.

## Límites actuales

- El historial conserva mensajes; no añade memoria conversacional al prompt de Qwen.
- Los documentos antiguos sin propietario se deben cargar nuevamente con una cuenta.
- Las fuentes son referencias; no hay enlace de descarga porque el backend no conserva
  los originales ni ofrece un endpoint para descargarlos.
- No se añadieron borrado/renombrado de documentos o conversaciones, registro de usuarios
  ni funcionalidades de fases posteriores.
- El frontend no sustituye la autorización del backend: este sigue filtrando por usuario.

## Archivos principales

| Carpeta | Responsabilidad |
|---|---|
| `frontend/src/pages` | Login, Chat, Documents e History |
| `frontend/src/components` | Layout, mensajes, fuentes, indicadores y navegación |
| `frontend/src/context` | Autenticación, avisos y consulta activa |
| `frontend/src/hooks` | Carga cancelable y paginada de listas |
| `frontend/src/services` | Configuración, adaptador de sesión y cliente HTTP único |
| `frontend/tests` | Flujos de navegador con Playwright |

`frontend/nginx.conf` permite recargar rutas como `/history` en la imagen Docker.
El Dockerfile instala con `npm ci` y utiliza el lockfile. La configuración completa
de despliegue y Compose con Keycloak permanece fuera de esta fase.

## Pruebas y compilación

Verificación del 6 de octubre de 2026:

- Compilación de producción completada con Vite 6.4.3.
- Siete pruebas de navegador aprobadas en Edge, con API y OIDC simulados.
- Capturas de escritorio (1440 px) y móvil (390 px) revisadas; prueba de desbordamiento horizontal aprobada.
- Dependencias actualizadas; la instalación reportó cero vulnerabilidades.
- Cliente local `rag-frontend` actualizado para los dos orígenes de desarrollo,
  conservando los de Swagger. Keycloak real aceptó una petición Authorization Code
  con PKCE para `http://localhost:5173/chat` y devolvió su formulario de acceso.
- El backend tiene permitido el origen `http://localhost:5173`. No se inició sesión
  con la contraseña del usuario ni se generó una respuesta real de Qwen desde la nueva
  interfaz durante esta verificación.

Desde `frontend/`:

```powershell
npm run build
npm run test:e2e
npm audit
```

Las pruebas usan Edge instalado en Windows, en modo sin ventana. En otro sistema,
se puede establecer `PLAYWRIGHT_CHANNEL=chromium` e instalarlo con
`npx playwright install chromium`. No requieren contraseñas ni Ollama: simulan
Keycloak y la API a nivel HTTP, ejecutando React y el adaptador OIDC reales. Comprueban
PKCE, autorización, tokens en Bearer, renovación, 401, logout, subida, errores,
continuidad, recarga de historial, estados de espera y diseño móvil.

Las pruebas simuladas no certifican una respuesta de Qwen ni el servidor real de
Keycloak; la comprobación manual de integración se hace con los pasos de Uso.
