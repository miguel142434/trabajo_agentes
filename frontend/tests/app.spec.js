import { test, expect } from '@playwright/test'

const cid = '00000000-0000-0000-0000-000000000123'
const source = { document: 'mundial-2022.txt', page: null, chunk_index: 0 }
const origin = 'http://localhost:5173'

// Servidor OIDC simulado a nivel HTTP. El navegador ejecuta el adaptador real,
// incluyendo redirección, callback, intercambio de código PKCE y renovación.
async function setup(page, { ttl = 300 } = {}) {
  let signedIn = false
  let nonce = ''
  let refreshes = 0
  let tokenCalls = 0
  let sessionRejected = false
  const documents = []
  const conversations = []
  const messages = []
  const requests = []
  const claims = () => ({ sub: 'test-subject', preferred_username: 'estudiante',
    iat: Math.floor(Date.now() / 1000), exp: Math.floor(Date.now() / 1000) + (tokenCalls > 1 ? 300 : ttl),
    session_state: 'test-session', nonce, iss: 'http://localhost:8080/realms/rag-agent', aud: 'account' })
  const jwt = () => `${Buffer.from('{"alg":"RS256"}').toString('base64url')}.${Buffer.from(JSON.stringify(claims())).toString('base64url')}.test-signature`
  await page.route('http://localhost:8080/**', async route => {
    const url = new URL(route.request().url())
    const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true' }
    if (url.pathname.endsWith('/auth')) {
      nonce = url.searchParams.get('nonce')
      const callback = new URL(url.searchParams.get('redirect_uri'))
      callback.searchParams.set('state', url.searchParams.get('state'))
      if (url.searchParams.get('prompt') === 'none' && !signedIn) {
        callback.searchParams.set('error', 'login_required')
        return route.fulfill({ status: 302, headers: { location: callback.href } })
      }
      expect(url.searchParams.get('code_challenge_method')).toBe('S256')
      expect(url.searchParams.get('code_challenge')).toBeTruthy()
      signedIn = true; callback.searchParams.set('code', 'test-code')
      return route.fulfill({ status: 302, headers: { location: callback.href } })
    }
    if (url.pathname.endsWith('/token')) {
      const body = new URLSearchParams(route.request().postData())
      if (body.get('grant_type') === 'refresh_token') {
        refreshes++
        if (sessionRejected) return route.fulfill({ status: 400, headers, json: { error: 'invalid_grant' } })
      } else expect(body.get('code_verifier')?.length).toBeGreaterThan(20)
      tokenCalls++
      return route.fulfill({ headers, json: { access_token: jwt(), id_token: jwt(), refresh_token: jwt(), expires_in: ttl, token_type: 'Bearer' } })
    }
    if (url.pathname.endsWith('/logout')) {
      signedIn = false
      return route.fulfill({ status: 302, headers: { location: url.searchParams.get('post_logout_redirect_uri') } })
    }
    return route.fulfill({ status: 404, headers })
  })
  await page.route('http://127.0.0.1:8000/api/**', async route => {
    const request = route.request()
    const headers = { 'access-control-allow-origin': origin, 'access-control-allow-headers': 'authorization,content-type', 'access-control-allow-methods': 'GET,POST,OPTIONS' }
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers })
    expect(request.headers().authorization).toMatch(/^Bearer /)
    requests.push({ path: new URL(request.url()).pathname, body: request.postData() })
    if (sessionRejected) return route.fulfill({ status: 401, headers, json: { detail: 'Token expirado' } })
    if (request.url().includes('/documents/upload')) {
      const doc = { document_id: 'doc-1', filename: 'mundial-2022.txt', file_type: 'txt', chunks_created: 1,
        size_bytes: 40, created_at: '2026-10-06T10:00:00', status: 'processed' }
      documents.push(doc)
      return route.fulfill({ status: 201, headers, json: doc })
    }
    if (request.url().includes('/documents?')) return route.fulfill({ headers, json: documents })
    if (request.url().includes('/conversations?')) return route.fulfill({ headers, json: conversations })
    if (request.url().endsWith(`/conversations/${cid}`)) return route.fulfill({ headers, json: { id: cid, messages } })
    if (request.url().endsWith('/chat/rag')) {
      const body = request.postDataJSON()
      messages.push({ id: `u-${messages.length}`, role: 'user', content: body.question },
        { id: `a-${messages.length}`, role: 'assistant', content: 'Argentina ganó el Mundial de 2022.', sources: JSON.stringify([source]) })
      if (!conversations.length) conversations.push({ id: cid, title: body.question, updated_at: '2026-10-06T12:00:00' })
      return route.fulfill({ headers, json: { answer: 'Argentina ganó el Mundial de 2022.', sources: [source], conversation_id: cid } })
    }
    return route.fulfill({ status: 404, headers, json: { detail: 'No se encontró la conversación.' } })
  })
  return { documents, requests, refreshes: () => refreshes, rejectSession: () => { sessionRejected = true } }
}

async function login(page) {
  await page.goto('/chat')
  await expect(page.getByRole('heading', { name: 'Entra a tu espacio' })).toBeVisible()
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Hablemos de deportes' })).toBeVisible()
}

test('muestra biblioteca global junto a documentos personales', async ({ page }) => {
  const fixture = await setup(page)
  fixture.documents.push({ document_id: 'global-1', filename: 'mundiales-global.pdf', file_type: 'pdf',
    chunks_created: 3, size_bytes: 100, created_at: '2026-10-08T12:00:00Z', status: 'processed', is_global: true })
  await login(page)
  await page.getByRole('link', { name: 'Documentos', exact: true }).click()
  await expect(page.getByText('Global · siempre disponible', { exact: true })).toBeVisible()
  await page.getByLabel('Seleccionar documento').setInputFiles({ name: 'mundial-2022.txt', mimeType: 'text/plain', buffer: Buffer.from('Argentina ganó el Mundial de 2022.') })
  await page.getByRole('button', { name: 'Subir documento' }).click()
  await expect(page.getByText('Listo para consultar', { exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'mundiales-global.pdf' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'mundial-2022.txt' })).toBeVisible()
})

test('protege rutas, inicia sesión con PKCE, muestra chat y cierra sesión', async ({ page }) => {
  await setup(page)
  await login(page)
  await expect(page.locator('.user-name')).toContainText('estudiante')
  await page.screenshot({ path: 'test-results/chat-desktop.png', fullPage: true })
  await page.getByRole('button', { name: 'Cerrar sesión' }).click()
  await expect(page.getByRole('heading', { name: 'Entra a tu espacio' })).toBeVisible()
  await page.goto('/documents')
  await expect(page.getByRole('heading', { name: 'Entra a tu espacio' })).toBeVisible()
  const stored = await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))
  expect(stored).not.toContain('test-signature')
})

test('sube documento, pregunta, cita fuentes y continúa desde historial', async ({ page }) => {
  const fixture = await setup(page)
  await login(page)
  await page.getByRole('link', { name: 'Documentos', exact: true }).click()
  await expect(page.getByText('Tu biblioteca empieza aquí')).toBeVisible()
  await page.getByLabel('Seleccionar documento').setInputFiles({ name: 'mundial-2022.txt', mimeType: 'text/plain', buffer: Buffer.from('Argentina ganó el Mundial de 2022.') })
  await page.getByRole('button', { name: 'Subir documento' }).click()
  await expect(page.getByText('Listo para consultar')).toBeVisible()
  await page.getByRole('button', { name: 'Cerrar aviso' }).click()
  await page.getByRole('link', { name: 'Chat', exact: true }).click()
  await page.getByLabel('Tu pregunta').fill('¿Quién ganó el Mundial de 2022?')
  await page.getByRole('button', { name: 'Enviar', exact: true }).click()
  await expect(page.getByText('Argentina ganó el Mundial de 2022.', { exact: true })).toBeVisible()
  await expect(page.getByText('mundial-2022.txt', { exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Historial', exact: true }).click()
  await page.getByRole('link', { name: 'Abrir', exact: true }).click()
  await page.reload()
  await expect(page.getByText('Argentina ganó el Mundial de 2022.', { exact: true })).toBeVisible()
  await expect(page.getByText('mundial-2022.txt', { exact: true })).toBeVisible()
  await page.getByLabel('Tu pregunta').fill('¿Dónde se disputó el Mundial de 2022?')
  await page.getByRole('button', { name: 'Enviar', exact: true }).click()
  await expect(page.locator('.assistant-message')).toHaveCount(2)
  const asks = fixture.requests.filter(request => request.path.endsWith('/chat/rag'))
  expect(JSON.parse(asks[0].body).conversation_id).toBeNull()
  expect(JSON.parse(asks[1].body).conversation_id).toBe(cid)
  await page.getByRole('button', { name: 'Nueva conversación' }).click()
  await expect(page.getByRole('heading', { name: 'El deporte, con fuentes.' })).toBeVisible()
})

test('renueva el token y abandona las rutas privadas cuando la API devuelve 401', async ({ page }) => {
  const fixture = await setup(page, { ttl: 20 })
  await login(page)
  await page.getByRole('link', { name: 'Documentos', exact: true }).click()
  await expect(page.getByText('Tu biblioteca empieza aquí')).toBeVisible()
  expect(fixture.refreshes()).toBeGreaterThan(0)
  fixture.rejectSession()
  await page.getByRole('button', { name: 'Actualizar listado' }).click()
  await expect(page.getByRole('heading', { name: 'Entra a tu espacio' })).toBeVisible()
  await expect(page.getByRole('alert')).toContainText('sesión')
})

test('renovación rechazada cierra la sesión antes de consultar la API', async ({ page }) => {
  const fixture = await setup(page, { ttl: 20 })
  await login(page)
  fixture.rejectSession()
  await page.getByRole('link', { name: 'Documentos', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Entra a tu espacio' })).toBeVisible()
  expect(fixture.refreshes()).toBe(1)
  expect(fixture.requests).toHaveLength(0)
})

test('conversación inexistente muestra error y permite empezar una nueva', async ({ page }) => {
  await setup(page)
  await login(page)
  await page.goto('/chat/00000000-0000-0000-0000-000000000456')
  await expect(page.getByRole('alert')).toContainText('No se encontró la conversación')
  await expect(page.getByRole('button', { name: 'Enviar', exact: true })).toBeDisabled()
  await page.getByRole('button', { name: 'Nueva conversación' }).click()
  await expect(page.getByRole('heading', { name: 'El deporte, con fuentes.' })).toBeVisible()
  await expect(page.getByLabel('Tu pregunta')).toBeEnabled()
})

test('error de carga recuperable, archivo inválido y vista móvil sin desbordamiento', async ({ page }) => {
  await setup(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await login(page)
  await page.getByRole('link', { name: 'Documentos', exact: true }).click()
  await page.getByLabel('Seleccionar documento').setInputFiles({ name: 'video.mp4', mimeType: 'video/mp4', buffer: Buffer.from('video') })
  await expect(page.getByRole('alert')).toContainText('PDF, TXT o DOCX')
  await expect(page.getByRole('button', { name: 'Subir documento' })).toBeDisabled()
  await page.getByRole('button', { name: 'Cerrar aviso' }).click()
  await page.route('**/api/documents?*', route => route.abort('failed'))
  await page.getByRole('button', { name: 'Actualizar listado' }).click()
  await expect(page.getByRole('alert')).toContainText('backend')
  await page.unroute('**/api/documents?*')
  await page.getByRole('button', { name: 'Volver a intentar' }).click()
  await expect(page.getByText('Tu biblioteca empieza aquí')).toBeVisible()
  const width = await page.evaluate(() => document.documentElement.scrollWidth)
  expect(width).toBeLessThanOrEqual(390)
  await page.screenshot({ path: 'test-results/documents-mobile.png', fullPage: true })
})

test('no duplica preguntas mientras espera y conserva el trabajo al cambiar de sección', async ({ page }) => {
  await setup(page)
  await login(page)
  let finish
  let calls = 0
  const delayed = new Promise(resolve => { finish = resolve })
  await page.route('**/api/chat/rag', async route => {
    if (route.request().method() === 'OPTIONS') return route.fallback()
    calls++; await delayed
    await route.fulfill({ headers: { 'access-control-allow-origin': origin }, json: { answer: 'Respuesta demorada', sources: [source], conversation_id: cid } })
  })
  await page.getByLabel('Tu pregunta').fill('Una pregunta documentada')
  await page.getByRole('button', { name: 'Enviar', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Nueva conversación' })).toBeDisabled()
  await page.getByRole('link', { name: 'Historial', exact: true }).click()
  await expect(page.getByText('Hay una respuesta en curso.', { exact: false })).toBeVisible()
  finish()
  await page.getByRole('link', { name: 'Chat', exact: true }).click()
  await expect(page.getByText('Respuesta demorada', { exact: true })).toBeVisible()
  expect(calls).toBe(1)
})
