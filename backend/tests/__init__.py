import os

# Las pruebas no deben indexar la base de conocimiento global contra los servicios reales.
os.environ.setdefault("KNOWLEDGE_BASE_SEED_ON_STARTUP", "false")
