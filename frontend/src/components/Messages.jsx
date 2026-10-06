export function parseSources(sources) {
  try { const items = typeof sources === 'string' ? JSON.parse(sources) : sources
    return Array.isArray(items) ? items.filter(item => item && typeof item.document === 'string') : []
  } catch { return [] }
}

export default function Messages({ messages }) {
  return <div className="messages">{messages.map((message, index) => <article key={message.id || index} className={`message ${message.role === 'user' ? 'user-message' : 'assistant-message'}`}>
    <div className="message-heading"><span className="avatar">{message.role === 'user' ? 'Tú' : 'R'}</span><strong>{message.role === 'user' ? 'Tu pregunta' : 'Agente de deportes'}</strong>{message.pending && <span className="muted">Enviando</span>}</div>
    <p className="message-content">{message.content}</p>
    {parseSources(message.sources).length > 0 && <div className="sources"><span className="eyebrow">Fuentes consultadas</span><ul>{parseSources(message.sources).map((source, i) => <li key={i}><span>{source.document}</span><small>{source.page != null ? `Página ${source.page} · ` : ''}Fragmento {Number.isInteger(source.chunk_index) ? source.chunk_index + 1 : '—'}</small></li>)}</ul></div>}
  </article>)}</div>
}
