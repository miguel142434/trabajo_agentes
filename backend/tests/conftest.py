"""Selección explícita de pruebas externas sin duplicar la suite unittest."""
import os

import pytest


INTEGRATION_MODULES = {
    'test_documents_integration.py',
    'test_vector_integration.py',
    'test_history_integration.py',
}


def pytest_addoption(parser):
    parser.addoption('--run-integration', action='store_true', default=False,
                     help='Habilita PostgreSQL y Ollama reales en tablas aisladas.')


def pytest_configure(config):
    # Antes de importar app/settings o evaluar los decoradores unittest.
    # Nunca sincronizar ni purgar la biblioteca real desde un lifespan de pruebas.
    os.environ['KNOWLEDGE_BASE_SEED_ON_STARTUP'] = 'false'
    enabled = '1' if config.getoption('--run-integration') else '0'
    os.environ['TEST_AUTH_INTEGRATION'] = enabled
    os.environ['TEST_VECTOR_INTEGRATION'] = enabled


def pytest_collection_modifyitems(config, items):
    for item in items:
        integration = item.path.name in INTEGRATION_MODULES
        item.add_marker(pytest.mark.integration if integration else pytest.mark.unit)
        if integration and not config.getoption('--run-integration'):
            item.add_marker(pytest.mark.skip(reason='Usar --run-integration con PostgreSQL y Ollama activos'))
