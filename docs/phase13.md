# Fase 13: Docker Compose

Documentación de la fase 13. El objetivo es orquestar todos los componentes de la solución en contenedores Docker estándar mediante un único comando, manteniendo Ollama ejecutándose en el host local para aprovechar la aceleración de hardware sin problemas de compatibilidad de drivers GPU.

---

## 1. Arquitectura de Contenedores

```
                          [ NAVEGADOR WEB ]
                      /           |           \
                     / (Puerto    | (Puerto    \ (Puerto
                    /   3000)     |   8000)     \   8080)
                   v              v              v
            +------------+  +------------+  +------------+
            |  FRONTEND  |  |  BACKEND   |  |  KEYCLOAK  |
            |  (Nginx)   |  | (FastAPI)  |  |  (Auth)    |
            +------------+  +------------+  +------------+
                                  |   ^           ^
                           SQL /  |   |           | JWKS
                         Vectores |   | Certs     |
                                  v   +-----------+
                            +------------+
                            |  POSTGRES  |
                            | (pgvector) |
                            +------------+
                                  |
                                  | (host.docker.internal:11434)
                                  v
                        [ OLLAMA EN EL HOST ]
                        (qwen3:8b + nomic-embed)
```

### Servicios configurados en `docker-compose.yml`:

| Servicio | Imagen / Build | Puerto Host | Puerto Contenedor | Propósito |
|---|---|---|---|---|
| **`postgres`** | `pgvector/pgvector:pg16` | `5432` / `5433` | `5432` | Base de datos relacional (historial, documentos) y almacenamiento vectorial con `pgvector`. |
| **`keycloak`** | `quay.io/keycloak/keycloak:24.0.0` | `8080` | `8080` | Servidor de identidad y acceso OIDC. Realm `rag-agent` auto-importado y datos persistidos. |
| **`backend`** | Build `backend/Dockerfile` (Python 3.11-slim) | `8000` | `8000` | API FastAPI con Uvicorn, LangGraph RAG y sincronización automática de la base de conocimiento global. |
| **`frontend`** | Build `frontend/Dockerfile` (Node 20 + Nginx) | `3000` | `80` | SPA React servida en producción con Nginx y proxy fallback para enrutamiento interno. |

---

## 2. Decisiones Técnicas Clave

### A. Ollama en el Host Local
* **Motivación:** Ejecutar modelos LLM de 8B parámetros dentro de contenedores en entornos mixtos (Windows/Linux/Mac) suele causar problemas de asignación de GPU, compatibilidad con drivers WSL2 o consumo excesivo de memoria.
* **Solución:** Ollama se ejecuta directamente en la máquina anfitriona en el puerto `11434`.
* **Conectividad:** El contenedor `backend` se conecta a través de `http://host.docker.internal:11434`. Para garantizar compatibilidad tanto en Windows como en entornos Linux nativos, se configuró:
  ```yaml
  extra_hosts:
    - "host.docker.internal:host-gateway"
  ```

### B. Desacoplamiento de URLs de Keycloak (Frontchannel vs Backchannel)
* **Problema:** El navegador del usuario accede a Keycloak desde fuera en `http://localhost:8080`, por lo que Keycloak emite tokens con el claim `iss: "http://localhost:8080/realms/rag-agent"`. Sin embargo, dentro de la red interna de Docker, el contenedor backend no puede consultar `localhost:8080` (apuntaría a sí mismo).
* **Solución:**
  1. El backend consulta los certificados públicos JWKS directamente al contenedor Keycloak: `KEYCLOAK_URL=http://keycloak:8080`.
  2. Valida la firma contra el emisor público esperado mediante `KEYCLOAK_ISSUER_OVERRIDE=http://localhost:8080/realms/rag-agent`.
  3. Esto permite validación criptográfica instantánea sin requerir exposición de red compleja ni hacks de DNS.

### C. Soporte Multi-puerto para Frontend y CORS
* `frontend/Dockerfile` compila los assets de Vite con las URLs públicas del backend (`http://localhost:8000`) y Keycloak (`http://localhost:8080`).
* `keycloak/realm-export.json` autoriza explícitamente tanto el entorno de desarrollo Vite (`http://localhost:5173/*`) como el entorno contenerizado (`http://localhost:3000/*`).
* `backend/app/core/config.py` admite por defecto orígenes CORS para ambos puertos (`5173` y `3000`), evitando bloqueos entre contenedor y navegador.

### D. Volúmenes Persistentes
Se definen tres volúmenes nombrados para evitar pérdida de información:
1. `postgres_data`: Persiste tablas SQL y vectores calculados.
2. `keycloak_data`: Persiste usuarios creados, credenciales y configuración del realm.
3. `uploaded_documents_data`: Persiste los archivos físicos subidos por los usuarios en `/app/data/documents`.

### E. Optimización de Construcción con `.dockerignore`
Se agregaron archivos `.dockerignore` en la raíz, `backend/` y `frontend/` para excluir carpetas pesadas (`.venv/`, `node_modules/`, `__pycache__/`, `dist/`). Esto redujo el contexto de construcción de más de 100 MB a apenas **60 KB**, acelerando el build a menos de 3 segundos.

---

## 3. Comandos de Uso

```powershell
# 1. Asegurar que Docker Desktop y Ollama estén activos en el host

# 2. Levantar toda la solución construyendo imágenes
docker compose up --build -d

# 3. Comprobar estado de los servicios
docker compose ps

# 4. Inspeccionar logs
docker compose logs -f backend
docker compose logs -f frontend

# 5. Detener la solución
docker compose down
```

---

## 4. Evidencia de Funcionamiento

* **Build:** Backend y frontend compilan limpiamente sin advertencias críticas (`docker compose build` exitoso).
* **Arranque:** Los 4 contenedores inician en orden de dependencias (`postgres` con healthcheck activo → `keycloak` → `backend` → `frontend`).
* **Base global:** El contenedor `backend` se conectó a PostgreSQL y sincronizó la base global `Mundiales_documento_RAG.pdf` al iniciar.
* **Healthchecks:**
  * `GET http://localhost:8000/health` → `{"status": "ok"}`
  * `GET http://localhost:3000` → `200 OK` (Nginx sirviendo SPA React)
  * `GET http://localhost:8080/realms/rag-agent` → `200 OK` (Keycloak)
* **Seguridad:**
  * `GET http://localhost:8000/api/documents` sin token → `401 Unauthorized`.
