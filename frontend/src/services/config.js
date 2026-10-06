const env = import.meta.env

export const config = {
  apiUrl: (env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, ''),
  keycloakUrl: env.VITE_KEYCLOAK_URL || 'http://localhost:8080',
  realm: env.VITE_KEYCLOAK_REALM || 'rag-agent',
  clientId: env.VITE_KEYCLOAK_CLIENT_ID || 'rag-frontend',
}
