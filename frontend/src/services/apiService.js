import { authService } from './authService'
import { config } from './config'

const pending = new Set()
authService.subscribe(() => {
  if (!authService.snapshot().authenticated) pending.forEach(controller => controller.abort())
})

export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status }
}

export async function request(path, { method = 'GET', body, signal } = {}) {
  const controller = new AbortController()
  const abort = () => controller.abort()
  signal?.addEventListener('abort', abort, { once: true })
  if (signal?.aborted) controller.abort()
  pending.add(controller)
  // Una respuesta puede necesitar dos inferencias locales. No repetir POST automáticamente.
  const timeout = setTimeout(abort, 300000)
  try {
    const token = await authService.token()
    const headers = { Authorization: `Bearer ${token}` }
    if (body && !(body instanceof FormData)) headers['Content-Type'] = 'application/json'
    const response = await fetch(`${config.apiUrl}/api${path}`, { method, headers,
      signal: controller.signal, body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined })
    if (response.status === 401) {
      authService.expire()
      throw new ApiError('Tu sesión expiró. Vuelve a iniciar sesión.', 401)
    }
    const data = response.status === 204 ? null : await response.json().catch(() => null)
    if (!response.ok) {
      const fallback = response.status === 404 ? 'No se encontró el recurso o no tienes acceso.' :
        response.status === 403 ? 'No tienes permiso para realizar esta acción.' :
        response.status >= 500 ? 'El servicio no pudo completar la operación. Inténtalo más tarde.' : 'Revisa los datos e inténtalo nuevamente.'
      throw new ApiError(typeof data?.detail === 'string' ? data.detail : fallback, response.status)
    }
    if (data === null && response.status !== 204) throw new ApiError('El servidor devolvió una respuesta inesperada.', 502)
    return data
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (controller.signal.aborted) throw new ApiError('La espera terminó. La operación puede haberse guardado; revisa el historial o los documentos antes de repetirla.', 0)
    throw new ApiError(error instanceof TypeError ? 'No se pudo conectar con el backend. Comprueba que esté funcionando.' : error.message, 0)
  } finally {
    clearTimeout(timeout)
    pending.delete(controller)
    signal?.removeEventListener('abort', abort)
  }
}

export const api = {
  ask: (question, conversationId, signal) => request('/chat/rag', { method: 'POST',
    body: { question, conversation_id: conversationId || null }, signal }),
  conversations: (offset = 0, signal) => request(`/conversations?limit=20&offset=${offset}`, { signal }),
  conversation: (id, signal) => request(`/conversations/${encodeURIComponent(id)}`, { signal }),
  documents: (offset = 0, signal) => request(`/documents?limit=20&offset=${offset}`, { signal }),
  upload: (file, signal) => {
    const body = new FormData(); body.append('file', file)
    return request('/documents/upload', { method: 'POST', body, signal })
  },
}
