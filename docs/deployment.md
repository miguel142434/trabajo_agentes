# Guía de Preparación para Despliegue Gratuito ($0 COP) — Fase 15

Este documento define la arquitectura, preparación técnica e instrucciones paso a paso para desplegar la aplicación RAG en la nube manteniendo un costo total estricto de **$0 COP**, sin contratar máquinas virtuales, sin activar periodos de prueba facturables y ejecutando los modelos de lenguaje locales (Ollama) en el computador personal del desarrollador.

---

## 1. Filosofía de Costo $0 COP y Evaluación de Plataformas

Para garantizar $0 COP sin riesgo de facturación imprevista, no basta con elegir servicios que tengan un botón "Free". Es fundamental auditar las políticas vigentes de los proveedores:

| Proveedor / Servicio | ¿Plan Gratuito Real? | ¿Requiere Tarjeta? | Límite / Condición Crítica | Veredicto para este Proyecto |
| :--- | :---: | :---: | :--- | :--- |
| **Vercel** (Frontend) | **Sí** (Hobby) | **No** | 100 GB ancho de banda/mes, HTTPS automático, CDN global. | **Seleccionado (Frontend)** |
| **Netlify** (Frontend) | **Sí** (Starter) | **No** | 100 GB ancho de banda/mes, 300 min de build. | **Alternativa válida** |
| **Render** (Backend) | **Sí** (Free Web Service) | **No** | 512 MB RAM, 0.1 CPU, duerme tras 15 min de inactividad, 750 horas/mes gratis. | **Seleccionado (Backend)** |
| **Railway** (Backend) | **No permanente** | **Sí** | El plan gratuito es un trial con crédito limitado que caduca. | **Descartado** |
| **AWS / Azure / GCP** | **No permanente** | **Sí** | Capas gratuitas temporales (12 meses o $200 USD) que pasan a cobro automático. | **Descartado** |
| **Render PostgreSQL** | **No permanente** | No | La base de datos gratuita de Render se **elimina automáticamente a los 30 días**. | **Descartado para DB** |
| **Neon.tech** (PostgreSQL) | **Sí** (Free Tier) | **No** | 0.5 GB almacenamiento, Postgres 16 con extensión `pgvector` nativa, SSL obligatorio. | **Seleccionado (Vector DB)** |
| **Cloudflare Tunnel** | **Sí** (Zero Trust / Quick) | **No** | Conexión saliente segura sin abrir puertos en el router, sin límite de ancho de banda. | **Seleccionado (Túnel Ollama)** |

---

## 2. Arquitectura Propuesta (Híbrida Nube - Local)

El agente inteligente requiere GPUs/CPUs intensivas para Ollama (`qwen3:8b` y `nomic-embed-text`), lo cual en la nube implicaría servidores de $30 a $100 USD mensuales. La solución adoptada mantiene la inferencia en el computador personal del desarrollador sin costo, comunicándose con el backend público de forma estrictamente segura.

```
       [ Usuario Final ]
               │
       (HTTPS) │
               ▼
┌──────────────────────────────┐
│  Frontend (Vercel / Netlify) │  <-- SPA React + Vite + Tailwind/CSS
│  https://rag-app.vercel.app  │
└──────────────┬───────────────┘
               │ (HTTPS + JWT Bearer)
               ▼
┌──────────────────────────────┐
│    Backend (Render Free)     │  <-- FastAPI + LangGraph + Uvicorn
│   https://rag-api.onrender   │
└──────────┬──────────────┬────┘
           │              │
  (SSL SQL)│              │ (HTTPS + Token Secreto en Headers)
           ▼              ▼
┌──────────────────┐  ┌──────────────────────────────────────────────┐
│    Base de Datos │  │              TÚNEL SEGURO                    │
│    (Neon.tech)   │  │   Cloudflare Tunnel (cloudflared)            │
│  Postgres 16 +   │  │   https://xxxx.trycloudflare.com             │
│     pgvector     │  └──────────────────────┬───────────────────────┘
└──────────────────┘                         │ (Túnel saliente cifrado)
                                             ▼
                      ┌──────────────────────────────────────────────┐
                      │        COMPUTADOR PERSONAL LOCAL             │
                      │                                              │
                      │ ┌──────────────────────────────────────────┐ │
                      │ │ Proxy Seguro (scripts/tunnel/proxy.py)   │ │
                      │ │ Puerto local: 11435                      │ │
                      │ │ Valida Header: Authorization: Bearer ... │ │
                      │ └────────────────────┬─────────────────────┘ │
                      │                      │ (HTTP localhost)      │
                      │                      ▼                       │
                      │ ┌──────────────────────────────────────────┐ │
                      │ │ Ollama Daemon (Puerto 11434)             │ │
                      │ │ Modelos: qwen3:8b + nomic-embed-text     │ │
                      │ └──────────────────────────────────────────┘ │
                      └──────────────────────────────────────────────┘
```

---

## 3. Seguridad del Túnel Local de Ollama

### El problema de seguridad
Ollama **no incluye autenticación nativa**. Si se expone el puerto 11434 a Internet o se conecta directamente un túnel sin autenticación, cualquier usuario o bot que descubra o escanee la URL del túnel podría consumir el 100% de los recursos de la máquina local.

> [!CAUTION]
> Confiar únicamente en que la URL del túnel es "difícil de adivinar" (**seguridad por oscuridad**) es una vulnerabilidad grave. Las URLs pueden filtrarse en registros, cabeceras `Referer` o rastreadores web.

### La solución implementada: Proxy de Autenticación Local
Se incluye en el repositorio la herramienta `scripts/tunnel/ollama_proxy.py`:
1. Escucha exclusivamente en `127.0.0.1:11435`.
2. Intercepta todas las peticiones dirigidas a Ollama.
3. Exige la presencia de un token de autorización en la cabecera HTTP (`Authorization: Bearer <TOKEN>` o `X-Ollama-Key: <TOKEN>`).
4. Si el token no coincide, responde **401 Unauthorized** de inmediato sin transferir carga a Ollama.
5. El túnel de Cloudflare apunta **al proxy (puerto 11435)** y no a Ollama directamente.
6. El backend en Render envía el token en cada petición mediante la variable `OLLAMA_API_KEY`.

---

## 4. Requisitos y Preparación del Entorno Local

### Hardware para el PC Local
- **RAM**: Mínimo 16 GB (recomendado para alojar `qwen3:8b` y el sistema operativo fluidamente).
- **GPU (Opcional pero recomendada)**: NVIDIA GTX 1660 o superior (6GB+ VRAM). En CPU, las respuestas demoran más tiempo pero funcionan correctamente.
- **Conexión a Internet**: Acceso saliente estándar (no requiere IP pública fija ni apertura de puertos NAT).

### Software Requerido
1. **Ollama**:
   ```bash
   ollama pull qwen3:8b
   ollama pull nomic-embed-text
   ```
2. **Cloudflare Tunnel (`cloudflared`)**:
   - Descarga gratuita oficial: [https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)
   - En Windows (con winget):
     ```powershell
     winget install Cloudflare.cloudflared
     ```
3. **Python 3.11+**:
   - Ya presente en el entorno del proyecto.

---

## 5. Preparación Técnica Realizada en el Código

### 5.1. Frontend
- **Reescritura de Rutas SPA**:
  - Creado `frontend/vercel.json` con regla de reescritura hacia `/index.html` para evitar errores 404 al recargar rutas como `/chat` o `/documents`.
  - Creado `frontend/public/_redirects` con `/* /index.html 200` para compatibilidad directa con Netlify y Cloudflare Pages.
- **Configuración desacoplada**: `src/services/config.js` lee variables estándar `VITE_API_URL`, `VITE_KEYCLOAK_URL`, etc., sin secretos embebidos en el código fuente.
- **HTTPS nativo**: La aplicación utiliza URLs relativas y soporte HTTPS automático provisto por Vercel/Netlify.

### 5.2. Backend
- **Puerto y Host dinámico**:
  - `backend/run.py` actualizado para leer `PORT` o `BACKEND_PORT` (por defecto 8000) y escuchar en `0.0.0.0` cuando se detecta un entorno en la nube.
  - `backend/Dockerfile` actualizado con `CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]` para respetar la asignación dinámica de puertos de Render/Railway.
- **CORS Flexible**:
  - `backend/app/core/config.py` adaptado para admitir `CORS_ORIGINS` tanto en formato array JSON `["https://app.vercel.app"]` como lista separada por comas `https://app.vercel.app,http://localhost:5173`.
- **Autenticación con Túnel de Ollama**:
  - Añadido `ollama_api_key` en `Settings`.
  - `LLMService` y `EmbeddingService` transmiten automáticamente `Authorization: Bearer <OLLAMA_API_KEY>` cuando dicha clave está configurada.
- **Endpoint de Health Check**: `/health` responde con estado HTTP 200 para monitores de actividad de Render.
- **Resiliencia ante caídas**: Manejo estructurado de excepciones `LLMUnavailableError` y `LLMTimeoutError` que informa al usuario si el PC local pierde conexión.

---

## 6. Variables de Entorno para Producción

### Backend (Render / Producción)
```ini
# Configuración del servidor
PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=https://tu-frontend.vercel.app

# Base de datos vectorial persistente (Neon.tech - Postgres 16 con pgvector)
# Reemplazar con la URI real provista por Neon (mantener sslmode=require)
DATABASE_URL=postgresql://usuario:password@ep-cool-sample.us-east-2.aws.neon.tech/neondb?sslmode=require
VECTOR_TABLE=document_chunks
DOCUMENT_TABLE=uploaded_documents

# Parámetros RAG y embeddings
OLLAMA_MODEL=qwen3:8b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSION=768
OLLAMA_TIMEOUT=180
RAG_MIN_RELEVANCE_SCORE=0.65
RAG_SINGLE_PASS=true

# Conexión segura con el PC local a través del túnel
OLLAMA_BASE_URL=https://tu-tunel-generado.trycloudflare.com
OLLAMA_API_KEY=tu_token_secreto_aleatorio_de_32_caracteres

# Autenticación Keycloak (ver sección 7)
KEYCLOAK_URL=https://tu-keycloak.onrender.com
KEYCLOAK_REALM=rag-agent
KEYCLOAK_CLIENT_ID=rag-frontend
KEYCLOAK_AUDIENCE=account
```

### Frontend (Vercel / Producción)
```ini
VITE_API_URL=https://tu-backend.onrender.com
VITE_KEYCLOAK_URL=https://tu-keycloak.onrender.com
VITE_KEYCLOAK_REALM=rag-agent
VITE_KEYCLOAK_CLIENT_ID=rag-frontend
```

---

## 7. Despliegue de Keycloak en Esquema Gratuito

Keycloak requiere típicamente entre 512 MB y 1 GB de RAM al iniciar la JVM de Quarkus. Para mantener $0 COP se disponen dos alternativas:

### Opción A (Híbrida — Recomendada): Keycloak local en Docker con túnel
1. Ejecutar Keycloak localmente como hasta ahora con `docker compose up keycloak`.
2. Exponerlo mediante un segundo túnel de Cloudflare (`cloudflared tunnel --url http://localhost:8080`).
3. Ventaja: Cero consumo de RAM en la nube y tiempo de respuesta instantáneo para el realm exportado.

### Opción B (Completamente en Nube): Keycloak optimizado en contenedor gratuito
1. Desplegar la imagen `quay.io/keycloak/keycloak:24.0.0` en una cuenta gratuita de Render o Koyeb.
2. Configurar la variable de entorno para limitar la memoria de la JVM:
   ```bash
   JAVA_OPTS_APPEND="-Xms128m -Xmx384m -XX:+UseG1GC"
   ```
3. Conectar Keycloak a una base de datos PostgreSQL gratuita en Neon.tech.

---

## 8. Instrucciones Paso a Paso para el Despliegue

### Paso 1: Crear la Base de Datos Gratuita en Neon.tech
1. Ingresa a [https://neon.tech](https://neon.tech) e inicia sesión (con GitHub o Google, sin tarjeta).
2. Crea un proyecto gratuito (ej. `rag-agent-db`).
3. Copia el **Connection String** que tiene el formato:
   `postgresql://alex:AbCdEf@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require`
4. Abre la consola SQL de Neon y activa la extensión de vectores:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

### Paso 2: Iniciar el Proxy y el Túnel de Ollama en el PC Local
1. Genera un token secreto o deja que el script genere uno:
   ```powershell
   python scripts/tunnel/ollama_proxy.py --secret mi_clave_secreta_super_segura
   ```
   *El proxy quedará escuchando en `http://127.0.0.1:11435` y solicitará la clave para cualquier petición.*

2. En otra terminal, levanta el túnel de Cloudflare apuntando al proxy:
   ```powershell
   cloudflared tunnel --url http://localhost:11435
   ```
   *Cloudflare imprimirá una URL pública como `https://random-words.trycloudflare.com`.*

3. Verifica el funcionamiento del túnel desde un navegador o terminal:
   ```bash
   # Debe responder {"status": "ok", "proxy": "ollama-secure-proxy"}
   curl https://random-words.trycloudflare.com/health

   # Debe responder 401 Unauthorized si no hay token
   curl -X POST https://random-words.trycloudflare.com/api/generate
   ```

### Paso 3: Desplegar el Backend en Render
1. Sube tu código a GitHub.
2. Ingresa a [https://render.com](https://render.com) (inicia sesión con GitHub).
3. Haz clic en **New +** > **Web Service**.
4. Conecta tu repositorio de GitHub.
5. Configura:
   - **Root Directory**: `backend` (o déjalo en la raíz si compilas desde Dockerfile raíz).
   - **Environment**: `Python 3` (o `Docker`).
   - Si usas Python nativo:
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free ($0/month).
6. En la sección **Environment Variables**, añade las variables descritas en la Sección 6:
   - `DATABASE_URL` (obtenida de Neon.tech).
   - `OLLAMA_BASE_URL` (la URL de Cloudflare Tunnel).
   - `OLLAMA_API_KEY` (`mi_clave_secreta_super_segura`).
   - `CORS_ORIGINS` (temporalmente `*` o la futura URL de Vercel).
7. Haz clic en **Deploy Web Service**.

### Paso 4: Desplegar el Frontend en Vercel
1. Ingresa a [https://vercel.com](https://vercel.com).
2. Haz clic en **Add New...** > **Project** y selecciona el repositorio.
3. En la configuración del proyecto:
   - **Framework Preset**: Vite.
   - **Root Directory**: `frontend`.
4. En **Environment Variables**, configura:
   - `VITE_API_URL`: La URL pública de Render (ej. `https://rag-api.onrender.com`).
   - `VITE_KEYCLOAK_URL`: La URL pública de tu Keycloak.
5. Haz clic en **Deploy**.
6. Una vez desplegado, copia la URL asignada (ej. `https://rag-app.vercel.app`) y actualiza la variable `CORS_ORIGINS` en el backend de Render.

---

## 9. Procedimiento de Verificación del Sistema

1. **Prueba de Health Check del Backend**:
   Visita `https://rag-api.onrender.com/health`. Debe responder con código 200 y JSON indicando estado saludable.
2. **Prueba de Rechazo No Autorizado en Ollama**:
   Envía una petición al túnel sin cabecera de autenticación. Debe retornar `401 Unauthorized`.
3. **Prueba de Chat y RAG**:
   Inicia sesión en la interfaz web de Vercel, formula una pregunta sobre el documento precargado (e.g. *¿Quién fue el subcampeón del mundial de 1934?*).
   - El frontend enviará la consulta al backend en Render.
   - Render recuperará los embeddings y fragmentos de Neon.tech.
   - Render enviará la petición autenticada a través del túnel a tu PC.
   - Ollama generará la respuesta en tu máquina y la retornará a través del túnel hasta el navegador.
4. **Prueba de Resiliencia (PC apagado)**:
   Detén `ollama_proxy.py`. Realiza una consulta desde la aplicación web: el sistema debe mostrar un mensaje amigable indicando que el modelo no se encuentra disponible temporalmente, sin colapsar el backend.

---

## 10. Limitaciones Conocidas y Mitigaciones

| Limitación | Causa | Impacto | Mitigación |
| :--- | :--- | :--- | :--- |
| **PC Local Apagado / Suspendido** | Ollama corre en la máquina personal. | El chat no puede generar respuestas ni embeddings. | El backend responde con un error controlado `503 Service Unavailable`. La navegación, historial y documentos siguen funcionando. |
| **Suspensión por Inactividad de Render** | Plan Free de Render entra en suspensión tras 15 minutos sin tráfico. | La primera petición tras un periodo de inactividad tarda ~45 segundos (cold start). | Configurar un servicio gratuito de monitoreo como [UptimeRobot](https://uptimerobot.com) que haga ping al endpoint `/health` cada 10 minutos. |
| **URL Efímera de Cloudflare Quick Tunnel** | El comando rápido `cloudflared tunnel --url` genera un subdominio aleatorio cada vez que se reinicia. | Si se reinicia el túnel, la URL cambia y debe actualizarse en Render. | Crear un túnel permanente con nombre (**Named Tunnel**) en la consola gratuita de Cloudflare Zero Trust (también $0 COP permanente). |
| **Límite de Disco en Neon (0.5 GB)** | Plan Free de Neon.tech. | Límite para almacenar miles de documentos y vectores. | Suficiente para cientos de PDFs y más de 100,000 fragmentos con embeddings. |

---

## 11. Procedimiento para Detener o Eliminar Recursos ($0 COP Garantizado)

Para garantizar que ningún recurso persista si se desea desmontar el proyecto:

1. **Detener el PC Local**:
   - Detener el proceso del túnel presionando `Ctrl+C` en la terminal de `cloudflared`.
   - Detener el proxy local presionando `Ctrl+C` en la terminal de `ollama_proxy.py`.
2. **Eliminar el Frontend en Vercel**:
   - En el Dashboard de Vercel: `Project Settings` > `General` > `Delete Project`.
3. **Eliminar el Backend en Render**:
   - En el Dashboard de Render: Seleccionar el Web Service > `Settings` > `Delete Web Service`.
4. **Eliminar la Base de Datos en Neon.tech**:
   - En la consola de Neon: `Project Settings` > `Delete Project`.

Al seguir este procedimiento, no queda ningún servicio activo ni rastro facturable en ningún proveedor.
