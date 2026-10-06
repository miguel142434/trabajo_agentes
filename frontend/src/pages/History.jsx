import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/apiService'
import { usePageData } from '../hooks/usePageData'
import { useChat } from '../context/ChatContext'
import { Empty, ErrorPanel, Loading, Pagination, formatDate } from '../components/Shared'
import Icon from '../components/Icon'

export default function History() {
  const [offset, setOffset] = useState(0)
  const chat = useChat()
  const { items, loading, error, reload } = usePageData(api.conversations, offset, chat.revision)
  return <section className="content-page"><div className="page-heading"><div><span className="eyebrow">CONVERSACIONES GUARDADAS</span><h1>Historial</h1><p>Vuelve a tus preguntas, respuestas y fuentes.</p></div><button className="button secondary" disabled={loading} onClick={reload}>Actualizar</button></div>
    {chat.busy && <p className="info-panel" role="status">Hay una respuesta en curso. Cuando termine podrás abrir otra conversación.</p>}
    {loading ? <Loading text="Cargando conversaciones…"/> : error ? <ErrorPanel message={error} retry={reload}/> : !items.length ? <Empty title={offset ? 'No hay más conversaciones' : 'Tu próxima pregunta inicia el historial'} icon="history">Las conversaciones se guardan automáticamente cuando el agente termina de responder. <Link to="/chat">Ir al chat</Link></Empty> : <div className="history-list">{items.map(conversation => <article className="history-card" key={conversation.id}><span className="history-icon"><Icon name="chat"/></span><div><h2>{conversation.title || 'Nueva conversación'}</h2><p>Última actividad · {formatDate(conversation.updated_at)}</p></div>{chat.busy ? <span className="muted">Espera la respuesta</span> : <Link className="button secondary" to={`/chat/${conversation.id}`}>Abrir<Icon name="arrow" size={17}/></Link>}</article>)}</div>}
    <Pagination offset={offset} count={items.length} onChange={setOffset} disabled={loading}/>
  </section>
}
