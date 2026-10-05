import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import validate_token
from app.main import app
from tests.auth_helpers import USER_ID


class SecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        self.settings = Settings(_env_file=None)
        self.payload = {'iss': self.settings.keycloak_issuer, 'aud': 'account', 'azp': 'rag-frontend',
                        'typ': 'Bearer', 'sub': USER_ID, 'preferred_username': 'mutable-name',
                        'iat': int(time.time())-1, 'exp': int(time.time())+120}
        self.jwks = Mock()
        self.jwks.get_signing_key_from_jwt.return_value = SimpleNamespace(key=self.key.public_key())
        for target, result in [('app.core.security.get_jwks_client', self.jwks),
                               ('app.core.security.get_settings', self.settings)]:
            mocker = patch(target, return_value=result)
            mocker.start()
            self.addCleanup(mocker.stop)

    def token(self):
        return jwt.encode(self.payload, self.key, algorithm='RS256')

    def test_valid_token_uses_subject_not_username(self):
        self.assertEqual(validate_token(self.token()), USER_ID)

    def test_rejects_wrong_claims(self):
        for key, value in [('iss','http://attacker/realms/rag-agent'), ('aud','another-api'),
                           ('azp','another-client'), ('exp',1), ('iat',int(time.time())+600),
                           ('sub',''), ('sub','estudiante'), ('typ','ID')]:
            with self.subTest(claim=key, value=value):
                original = self.payload[key]
                self.payload[key] = value
                with self.assertRaises(HTTPException) as error:
                    validate_token(self.token())
                self.assertEqual(error.exception.status_code, 401)
                self.payload[key] = original

    def test_missing_claims_signature_and_algorithm(self):
        for claim in ['exp','iat','sub','iss','aud','azp']:
            value = self.payload.pop(claim)
            with self.assertRaises(HTTPException):
                validate_token(self.token())
            self.payload[claim] = value
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        for token in [jwt.encode(self.payload, other, algorithm='RS256'),
                      jwt.encode(self.payload, 'wrong-key', algorithm='HS256'), 'bad-token']:
            with self.assertRaises(HTTPException) as error:
                validate_token(token)
            self.assertEqual(error.exception.status_code, 401)

    def test_keycloak_unavailable_is_503(self):
        self.jwks.get_signing_key_from_jwt.side_effect = jwt.PyJWKClientConnectionError('offline')
        with self.assertRaises(HTTPException) as error:
            validate_token(self.token())
        self.assertEqual(error.exception.status_code, 503)

    def test_all_functional_routes_require_authentication(self):
        client = TestClient(app)
        try:
            for method, path in [('POST','/api/test-llm'), ('POST','/api/chat/rag'),
                                 ('POST','/api/documents/upload'), ('GET','/api/documents'),
                                 ('POST','/api/vector/test-search'), ('POST','/api/vector/test-add'),
                                 ('GET','/api/conversations'), ('POST','/api/conversations'),
                                 ('GET','/api/conversations/00000000-0000-0000-0000-000000000001')]:
                with self.subTest(path=path, method=method):
                    response = client.request(method, path)
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.headers['www-authenticate'], 'Bearer')
            self.assertEqual(client.get('/health').status_code, 200)
        finally:
            client.close()
