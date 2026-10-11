"""Arranque local y en la nube compatible con psycopg asíncrono en Windows."""
import asyncio
import os
import sys

import uvicorn

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    port = int(os.environ.get("PORT", os.environ.get("BACKEND_PORT", 8000)))
    # En plataformas en la nube (Render, Railway, contenedores) $PORT está definido y se escucha en 0.0.0.0.
    default_host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    host = os.environ.get("HOST", default_host)

    uvicorn.run("app.main:app", host=host, port=port)
