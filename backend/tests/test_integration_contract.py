"""Contrato del navegador: preflight real de FastAPI y configuración del cliente."""
import json
from pathlib import Path
import unittest
from fastapi.testclient import TestClient
from app.main import app


class BrowserContractTests(unittest.TestCase):
    def test_cors_allows_authenticated_upload_and_chat(self):
        client = TestClient(app)
        self.addCleanup(client.close)
        for path in ['/api/documents/upload', '/api/chat/rag']:
            response = client.options(path, headers={
                'Origin': 'http://localhost:5173',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'authorization,content-type',
            })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['access-control-allow-origin'], 'http://localhost:5173')

    def test_export_supports_login_logout_and_swagger(self):
        root = Path(__file__).resolve().parents[2]
        realm = json.loads((root / 'keycloak/realm-export.json').read_text(encoding='utf-8'))
        client = next(c for c in realm['clients'] if c['clientId'] == 'rag-frontend')
        self.assertTrue(client['publicClient'])
        self.assertTrue(client['standardFlowEnabled'])
        self.assertIn('http://localhost:5173/*', client['redirectUris'])
        self.assertIn('http://127.0.0.1:8000/docs/oauth2-redirect', client['redirectUris'])
        self.assertIn('http://localhost:5173/login', client['attributes']['post.logout.redirect.uris'].split('##'))
        self.assertNotIn('*', client['webOrigins'])
