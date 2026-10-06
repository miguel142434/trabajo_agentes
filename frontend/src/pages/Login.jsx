import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { Brand } from '../components/Shared'
import Icon from '../components/Icon'

export default function Login() {
  const auth = useAuth()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function enter() {
    setBusy(true); setError('')
    try { await auth.login() } catch { setError('No se pudo abrir el inicio de sesión. Comprueba que Keycloak esté disponible.'); setBusy(false) }
  }
  return <div className="login-page"><section className="login-story"><Brand/>
    <div className="login-copy"><span className="eyebrow">FÚTBOL · FÓRMULA 1 · DEPORTES</span><h1>Detrás de cada<br/>respuesta,<br/><em>una fuente.</em></h1><p>Explora tus documentos deportivos. Haz preguntas y encuentra respuestas con el respaldo de tu propia biblioteca.</p></div>
    <div className="field-art" aria-hidden="true"><div className="field-center"/><span className="field-line"/><span className="field-dot"/></div>
    <span className="login-foot">Tu archivo. Tu contexto. Tu conversación.</span>
  </section><main className="login-form"><div><span className="section-number">01 / BIENVENIDO</span><h2>Entra a tu espacio</h2><p>Usa la misma cuenta con la que accedes al agente. Tus documentos e historial permanecerán privados.</p>
    {(error || auth.error) && <div className="error-panel" role="alert">{error || auth.error}</div>}
    <button className="button primary login-button" disabled={busy} onClick={enter}>{busy ? 'Abriendo acceso…' : 'Iniciar sesión'}<Icon name="arrow"/></button>
    <p className="login-help">Continuarás en Keycloak para ingresar tus credenciales y luego volverás aquí.</p>
    {auth.error && <button className="text-button" onClick={() => location.reload()}>Volver a comprobar conexión</button>}
    <div className="login-trust"><Icon name="shield"/><span>Acceso a tu cuenta personal</span></div>
  </div></main></div>
}
