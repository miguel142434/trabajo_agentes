import { Component } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ChatProvider } from './context/ChatContext'
import { NoticeProvider } from './context/NoticeContext'
import Layout from './components/Layout'
import { Brand, Loading } from './components/Shared'
import Login from './pages/Login'
import Chat from './pages/Chat'
import Documents from './pages/Documents'
import History from './pages/History'

class ErrorBoundary extends Component {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    return this.state.failed ? <main className="startup"><Brand/><h1>No pudimos mostrar esta pantalla</h1><p>Recarga la aplicación para volver a intentarlo.</p><button className="button primary" onClick={() => location.reload()}>Recargar</button></main> : this.props.children
  }
}

function PrivateArea() {
  const auth = useAuth()
  if (!auth.authenticated) return <Navigate to="/login" replace/>
  return <NoticeProvider key={auth.subject}><ChatProvider><Layout/></ChatProvider></NoticeProvider>
}

function Application() {
  const auth = useAuth()
  // Keycloak debe procesar su callback y limpiar la URL antes de montar el router.
  if (!auth.ready) return <main className="startup"><Brand/><Loading text="Preparando tu espacio…"/></main>
  return <BrowserRouter><Routes>
    <Route path="/login" element={auth.authenticated ? <Navigate to="/chat" replace/> : <Login/>}/>
    <Route element={<PrivateArea/>}>
      <Route path="/chat" element={<Chat/>}/>
      <Route path="/chat/:conversationId" element={<Chat/>}/>
      <Route path="/documents" element={<Documents/>}/>
      <Route path="/history" element={<History/>}/>
    </Route>
    <Route path="*" element={<Navigate to="/chat" replace/>}/>
  </Routes></BrowserRouter>
}

export default function App() {
  return <ErrorBoundary><AuthProvider><Application/></AuthProvider></ErrorBoundary>
}
