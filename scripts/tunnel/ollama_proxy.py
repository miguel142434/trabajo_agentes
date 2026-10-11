#!/usr/bin/env python3
"""Proxy inverso ligero y seguro para exponer Ollama localmente a través de un túnel.

Requisito de seguridad (Fase 15):
Ollama no posee autenticación nativa. Este proxy se interpone entre el túnel
público (e.g. Cloudflare Tunnel / cloudflared) y la instancia local de Ollama (11434),
exigiendo un Bearer token o header X-Ollama-Key compartido.

Cualquier petición no autorizada es rechazada con HTTP 401 antes de tocar Ollama,
impidiendo el acceso público no autorizado sin necesidad de abrir puertos en el router.

Uso:
    python scripts/tunnel/ollama_proxy.py --secret MI_TOKEN_SECRETO
    # O bien generar uno automáticamente:
    python scripts/tunnel/ollama_proxy.py
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from typing import ClassVar

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
}


class AuthenticatedOllamaProxy(http.server.BaseHTTPRequestHandler):
    secret: ClassVar[str] = ""
    upstream: ClassVar[str] = "http://127.0.0.1:11434"

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write(f"[{self.log_date_time_string()}] {self.address_string()} - {format % args}\n")

    def _is_authorized(self) -> bool:
        if not self.secret:
            return True

        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if secrets.compare_digest(token, self.secret):
                return True

        api_key = self.headers.get("X-Ollama-Key", "").strip()
        if api_key and secrets.compare_digest(api_key, self.secret):
            return True

        return False

    def _send_json_error(self, status: int, message: str) -> None:
        payload = json.dumps({"error": message}).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_request(self) -> None:
        # Endpoint de health check público para verificar estado del túnel
        if self.path in ("/health", "/ping") and self.command == "GET":
            payload = json.dumps({"status": "ok", "proxy": "ollama-secure-proxy"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        # Verificación estricta de autenticación
        if not self._is_authorized():
            self._send_json_error(401, "No autorizado. Token de autenticacion invalido o ausente.")
            return

        # Lectura del body si existe
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        upstream_url = f"{self.upstream.rstrip('/')}{self.path}"

        req = urllib.request.Request(upstream_url, data=body, method=self.command)

        # Copiar headers permitidos
        for header, value in self.headers.items():
            if header.lower() not in HOP_BY_HOP_HEADERS:
                req.add_header(header, value)

        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                self.send_response(response.status)
                for header, value in response.headers.items():
                    if header.lower() not in HOP_BY_HOP_HEADERS:
                        self.send_header(header, value)
                self.end_headers()

                # Reenviar contenido en streaming
                while chunk := response.read(64 * 1024):
                    self.wfile.write(chunk)
                    self.wfile.flush()

        except urllib.error.HTTPError as exc:
            self.send_response(exc.code)
            for header, value in exc.headers.items():
                if header.lower() not in HOP_BY_HOP_HEADERS:
                    self.send_header(header, value)
            self.end_headers()
            self.wfile.write(exc.read())

        except urllib.error.URLError as exc:
            self._send_json_error(
                503,
                f"No se pudo conectar con Ollama en {self.upstream}. Verifica que este ejecutandose: {exc}",
            )
        except Exception as exc:
            self._send_json_error(500, f"Error interno en el proxy: {exc}")

    do_GET = _handle_request
    do_POST = _handle_request
    do_PUT = _handle_request
    do_DELETE = _handle_request
    do_HEAD = _handle_request
    do_OPTIONS = _handle_request


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Proxy seguro con autenticacion token para Ollama",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("OLLAMA_PROXY_PORT", 11435)),
        help="Puerto en el que escuchara este proxy (default: 11435)",
    )
    parser.add_argument(
        "--upstream",
        default=os.environ.get("OLLAMA_UPSTREAM_URL", "http://127.0.0.1:11434"),
        help="URL de Ollama local (default: http://127.0.0.1:11434)",
    )
    parser.add_argument(
        "--secret",
        default=os.environ.get("OLLAMA_PROXY_SECRET"),
        help="Token secreto requerido para autenticar peticiones (si se omite, se genera uno)",
    )

    args = parser.parse_args()

    secret = args.secret or secrets.token_hex(24)

    AuthenticatedOllamaProxy.secret = secret
    AuthenticatedOllamaProxy.upstream = args.upstream

    server_address = ("127.0.0.1", args.port)
    server = http.server.ThreadingHTTPServer(server_address, AuthenticatedOllamaProxy)

    print("=" * 70)
    print("  PROXY SEGURO DE OLLAMA PARA TÚNEL (Fase 15 - Costo $0 COP)")
    print("=" * 70)
    print(f"Escuchando localmente en: http://127.0.0.1:{args.port}")
    print(f"Redirigiendo hacia Ollama: {args.upstream}")
    print(f"Token de autenticacion:  {secret}")
    print("-" * 70)
    print("Configuracion para tu backend en la nube:")
    print("  1. En otra terminal, levanta el tunel gratuito de Cloudflare:")
    print(f"     cloudflared tunnel --url http://localhost:{args.port}")
    print("  2. Copia la URL https://xxxx.trycloudflare.com asignada por cloudflared.")
    print("  3. En las variables de entorno de tu backend (e.g. Render):")
    print("     OLLAMA_BASE_URL=https://xxxx.trycloudflare.com")
    print(f"     OLLAMA_API_KEY={secret}")
    print("=" * 70)
    print("Presiona Ctrl+C para detener el proxy.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDeteniendo proxy...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
