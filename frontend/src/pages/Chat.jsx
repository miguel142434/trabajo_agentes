import { useEffect, useRef } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useChat } from '../context/ChatContext'
import Messages from '../components/Messages'
import Icon from '../components/Icon'
import { ErrorPanel, Loading } from '../components/Shared'

export default function Chat() {
  const chat = useChat()
  const { conversationId } = useParams()
  const navigate = useNavigate()
  const bottom = useRef(null)
  const input = useRef(null)
  useEffect(() => {
    if (conversationId && conversationId !== chat.id && !chat.busy) chat.open(conversationId)
    // El ID de la ruta dispara la carga; un mensaje enviado no vuelve a cargar el historial.
  }, [conversationId])
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [chat.messages, chat.busy])
  function fresh() { chat.reset(); navigate('/chat'); input.current?.focus() }
  return <section className="chat-page"><div className="page-heading"><div><span className="eyebrow">TU ASISTENTE DOCUMENTAL</span><h1>Hablemos de deportes</h1></div><button className="button secondary" disabled={chat.busy} onClick={fresh}><Icon name="plus"/>Nueva conversación</button></div>
    <div className="chat-feed" aria-live="polite" aria-busy={chat.busy || chat.loading}>
      {chat.loading ? <Loading text="Abriendo conversación…"/> : chat.error ? <ErrorPanel message={chat.error} retry={() => chat.open(conversationId)}/> : chat.messages.length ? <Messages messages={chat.messages}/> : <div className="chat-welcome"><span className="welcome-mark"><Icon name="chat" size={30}/></span><h2>El deporte, con fuentes.</h2><p>Pregunta sobre tus documentos de fútbol, Fórmula 1 y otros deportes. Si no hay información suficiente, te lo diré.</p><div className="suggestions">{['¿Qué selección ganó el Mundial de 2022?', '¿Dónde aseguró Verstappen su cuarto título?'].map(question => <button key={question} onClick={() => { chat.setDraft(question); input.current?.focus() }}>{question}<Icon name="arrow" size={17}/></button>)}</div><Link className="text-link" to="/documents">¿Primera vez? Carga tus documentos →</Link></div>}
      {chat.busy && <div className="thinking"><Loading text="Consultando tus documentos…"/><small>La respuesta puede tardar unos minutos. Puedes visitar otras secciones mientras esperas.</small></div>}<div ref={bottom}/>
    </div>
    <form className="composer" onSubmit={event => { event.preventDefault(); chat.send() }}>
      <label className="sr-only" htmlFor="question">Tu pregunta</label><textarea ref={input} id="question" value={chat.draft} onChange={event => chat.setDraft(event.target.value)} maxLength={2000} rows={2} placeholder="Escribe una pregunta sobre tus documentos…" disabled={chat.busy || chat.loading || Boolean(chat.error)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); chat.send() } }}/>
      <div className="composer-footer"><small>{chat.draft.length}/2000 <span>· Enter para enviar · Shift + Enter para nueva línea</span></small><button className="button primary" disabled={!chat.draft.trim() || chat.busy || chat.loading || Boolean(chat.error)} type="submit">{chat.busy ? 'Consultando…' : 'Enviar'}<Icon name="arrow" size={17}/></button></div>
    </form><p className="chat-disclaimer">Formula preguntas completas: el agente consulta documentos, pero aún no usa los mensajes anteriores como contexto.</p>
  </section>
}
