import Keycloak from 'keycloak-js'
import { config } from './config'

const keycloak = new Keycloak({ url: config.keycloakUrl, realm: config.realm, clientId: config.clientId })
const listeners = new Set()
let initialization
let snapshot = { ready: false, authenticated: false, name: '', subject: '', error: '' }

function publish(error = '') {
  snapshot = { ready: true, authenticated: Boolean(keycloak.authenticated),
    name: keycloak.tokenParsed?.preferred_username || 'Usuario',
    subject: keycloak.subject || '', error }
  listeners.forEach(listener => listener())
}

keycloak.onAuthSuccess = () => publish()
keycloak.onAuthRefreshSuccess = () => publish()
keycloak.onAuthLogout = () => publish('Tu sesión terminó. Vuelve a iniciar sesión.')
keycloak.onAuthRefreshError = () => authService.expire()
keycloak.onTokenExpired = () => authService.token().catch(() => {})

export const authService = {
  subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener) },
  snapshot: () => snapshot,
  initialize() {
    // Una sola inicialización, también bajo React.StrictMode.
    initialization ??= keycloak.init({ onLoad: 'check-sso', pkceMethod: 'S256',
      checkLoginIframe: false, responseMode: 'query', messageReceiveTimeout: 10000 })
      .then(() => publish())
      .catch(() => publish('No pudimos conectar con el servicio de acceso. Comprueba que Keycloak esté disponible y que esta dirección esté autorizada.'))
    return initialization
  },
  login() { return keycloak.login({ redirectUri: `${location.origin}/chat` }) },
  async token() {
    if (!keycloak.authenticated) throw new Error('Inicia sesión para continuar.')
    try {
      await keycloak.updateToken(30)
      if (!keycloak.token) throw new Error('Sesión finalizada')
      return keycloak.token
    } catch {
      this.expire()
      throw new Error('Tu sesión expiró. Vuelve a iniciar sesión.')
    }
  },
  expire() {
    keycloak.clearToken()
    publish('Tu sesión expiró o dejó de ser válida. Vuelve a iniciar sesión.')
  },
  async logout() {
    // Crear la URL mientras aún existe id_token_hint; después limpiar memoria.
    const url = keycloak.createLogoutUrl({ redirectUri: `${location.origin}/login` })
    keycloak.clearToken()
    publish()
    location.assign(url)
  },
}
