import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useNotice } from '../context/NoticeContext'
import { Brand } from './Shared'
import Icon from './Icon'

export default function Layout() {
  const auth = useAuth()
  const { notify } = useNotice()
  const location = useLocation()
  const title = location.pathname.startsWith('/documents') ? 'Documentos' : location.pathname.startsWith('/history') ? 'Historial' : 'Chat'
  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Ir al contenido</a>
    <aside className="sidebar"><Brand/><p className="sidebar-caption">TU ESPACIO DE CONSULTA</p>
      <nav aria-label="Navegación principal">
        <NavLink to="/chat"><Icon name="chat"/>Chat</NavLink>
        <NavLink to="/documents"><Icon name="file"/>Documentos</NavLink>
        <NavLink to="/history"><Icon name="history"/>Historial</NavLink>
      </nav>
      <div className="sidebar-bottom"><div className="privacy-note"><Icon name="shield"/><p>Tus documentos.<br/><strong>Solo en tu cuenta.</strong></p></div>
        <div className="user-block"><span className="user-initial">{auth.name.slice(0, 1).toUpperCase()}</span><span className="user-name">{auth.name}<small>Espacio personal</small></span></div>
        <button className="logout" onClick={() => auth.logout().catch(() => notify('No se pudo completar el cierre de sesión. Recarga e inténtalo nuevamente.'))}><Icon name="logout"/>Cerrar sesión</button>
      </div>
    </aside>
    <div className="workspace"><header className="topbar"><span>Mi espacio <span className="breadcrumb">/</span> <strong>{title}</strong></span><span className="topbar-note">Conocimiento con fuentes</span></header>
      <main id="main-content" tabIndex={-1}><Outlet/></main>
    </div>
  </div>
}
