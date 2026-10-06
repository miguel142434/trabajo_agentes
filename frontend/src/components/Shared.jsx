import Icon from './Icon'

export function Brand() { return <span className="brand"><span className="brand-symbol">R<span>↗</span></span><span>RAG<span className="brand-light"> / deportes</span></span></span> }
export function Loading({ text = 'Cargando…' }) { return <div className="loading" role="status"><span className="spinner"/>{text}</div> }
export function Empty({ title, children, icon = 'file' }) { return <div className="empty"><span className="empty-icon"><Icon name={icon} size={28}/></span><h2>{title}</h2><p>{children}</p></div> }
export function ErrorPanel({ message, retry }) { return <div className="error-panel" role="alert"><p>{message}</p>{retry && <button className="button secondary" onClick={retry}>Volver a intentar</button>}</div> }
export function Pagination({ offset, count, onChange, disabled }) { return <div className="pagination"><span>Página {offset / 20 + 1}</span><div><button className="button secondary" disabled={disabled || offset === 0} onClick={() => onChange(Math.max(0, offset - 20))}>Anterior</button><button className="button secondary" disabled={disabled || count < 20} onClick={() => onChange(offset + 20)}>Siguiente</button></div></div> }
export function formatDate(value) {
  if (!value) return ''
  const date = new Date(/[Zz]|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' })
}
