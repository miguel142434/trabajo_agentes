import { useEffect, useRef, useState } from 'react'
import { api } from '../services/apiService'
import { usePageData } from '../hooks/usePageData'
import { useNotice } from '../context/NoticeContext'
import { Empty, ErrorPanel, Loading, Pagination, formatDate } from '../components/Shared'
import Icon from '../components/Icon'

export default function Documents() {
  const [offset, setOffset] = useState(0)
  const [revision, setRevision] = useState(0)
  const { items, loading, error, reload } = usePageData(api.documents, offset, revision)
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const input = useRef(null)
  const active = useRef(null)
  const { notify } = useNotice()
  useEffect(() => () => active.current?.abort(), [])
  function choose(selected) {
    if (!selected) return
    if (!/\.(pdf|txt|docx)$/i.test(selected.name)) { notify('Selecciona un documento PDF, TXT o DOCX.'); return }
    if (selected.size === 0) { notify('El archivo está vacío.'); return }
    setFile(selected)
  }
  async function upload(event) {
    event.preventDefault()
    if (!file || uploading) return
    const controller = new AbortController(); active.current = controller; setUploading(true)
    try {
      const result = await api.upload(file, controller.signal)
      if (controller.signal.aborted) return
      notify(`${result.filename} está listo para consultar (${result.chunks_created} fragmentos).`, 'success')
      setFile(null); input.current.value = ''; setOffset(0); setRevision(value => value + 1)
    } catch (e) { if (!controller.signal.aborted) notify(e.message) }
    finally { if (!controller.signal.aborted) setUploading(false) }
  }
  return <section className="content-page"><div className="page-heading"><div><span className="eyebrow">TU BIBLIOTECA PRIVADA</span><h1>Documentos</h1><p>El punto de partida de cada respuesta.</p></div></div>
    <form onSubmit={upload} className="upload-card"><div className="upload-icon"><Icon name="upload" size={28}/></div><div className="upload-copy"><h2>Añade conocimiento al agente</h2><p>Sube reglamentos, resultados o archivos deportivos en PDF, TXT o DOCX.</p><label className="file-label" htmlFor="document-file">Seleccionar documento</label><input ref={input} id="document-file" type="file" accept=".pdf,.txt,.docx" disabled={uploading} onChange={event => { setFile(null); choose(event.target.files?.[0]) }}/>{file && <p className="selected-file">{file.name} · {(file.size / 1024).toFixed(1)} KB</p>}</div><button className="button primary" type="submit" disabled={!file || uploading}>{uploading ? 'Procesando…' : 'Subir documento'}<Icon name="upload" size={17}/></button>
      {uploading && <div className="upload-status"><Loading text="Subiendo y preparando el documento…"/><small>Espera en esta página hasta que termine. Si sales, revisa después el listado antes de volver a subirlo.</small></div>}
    </form>
    <div className="section-heading"><h2>Tu biblioteca</h2><button className="text-button" disabled={loading} onClick={reload}>Actualizar listado</button></div>
    {loading ? <Loading text="Cargando documentos…"/> : error ? <ErrorPanel message={error} retry={reload}/> : items.length === 0 ? <Empty title={offset ? 'No hay más documentos' : 'Tu biblioteca empieza aquí'}>Los archivos que cargues aparecerán aquí y solo estarán disponibles para tu cuenta.</Empty> : <div className="document-list">{items.map(doc => <article className="document-row" key={doc.document_id}><span className="file-type">{doc.file_type.toUpperCase()}</span><div className="document-info"><h3>{doc.filename}</h3><p>{doc.is_global ? 'Base de conocimiento global · ' : ''}{formatDate(doc.created_at)} · {(doc.size_bytes / 1024).toFixed(1)} KB · {doc.chunks_created} fragmentos</p></div><span className="badge">{doc.is_global ? 'Global · siempre disponible' : 'Listo para consultar'}</span></article>)}</div>}
    <Pagination offset={offset} count={items.length} onChange={setOffset} disabled={loading}/>
    <p className="page-note"><Icon name="shield" size={16}/>Se consultan tus documentos junto con la base de conocimiento global del proyecto. Lo que subas solo es visible para tu cuenta. Los archivos antiguos sin propietario deben cargarse de nuevo.</p>
  </section>
}
