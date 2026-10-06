import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { api } from '../services/apiService'
import { useNotice } from './NoticeContext'

const ChatContext = createContext(null)
export function ChatProvider({ children }) {
  const [messages, setMessages] = useState([])
  const [id, setId] = useState(null)
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [draft, setDraft] = useState('')
  const [revision, setRevision] = useState(0)
  const controller = useRef(null)
  const locked = useRef(false)
  const loadVersion = useRef(0)
  const { notify } = useNotice()
  useEffect(() => () => { loadVersion.current++; controller.current?.abort() }, [])

  async function open(conversationId) {
    if (locked.current) return
    const version = ++loadVersion.current
    controller.current?.abort()
    const current = new AbortController(); controller.current = current
    setLoading(true); setError(''); setMessages([]); setId(null); setDraft('')
    try {
      const result = await api.conversation(conversationId, current.signal)
      if (version !== loadVersion.current || current.signal.aborted) return
      setId(result.id); setMessages(result.messages)
    } catch (e) {
      if (!current.signal.aborted && version === loadVersion.current) setError(e.message)
    } finally {
      if (version === loadVersion.current) setLoading(false)
    }
  }

  function reset() {
    if (locked.current) return
    loadVersion.current++; controller.current?.abort()
    setId(null); setMessages([]); setDraft(''); setError(''); setLoading(false)
  }

  async function send() {
    const question = draft.trim()
    if (!question || question.length > 2000 || locked.current || loading || error) return
    locked.current = true; setBusy(true)
    const current = new AbortController(); controller.current = current
    setMessages(items => [...items, { role: 'user', content: question, pending: true }])
    setDraft('')
    try {
      const result = await api.ask(question, id, current.signal)
      if (current.signal.aborted) return
      setId(result.conversation_id)
      setMessages(items => [...items.map(item => ({ ...item, pending: false })),
        { role: 'assistant', content: result.answer, sources: result.sources }])
      setRevision(value => value + 1)
    } catch (e) {
      if (!current.signal.aborted) {
        setMessages(items => items.filter(item => !item.pending)); setDraft(question)
        notify(`${e.message} Antes de repetir la pregunta, puedes comprobar el historial.`)
      }
    } finally { locked.current = false; setBusy(false) }
  }
  return <ChatContext.Provider value={{ messages, id, busy, loading, error, draft, setDraft, open, reset, send, revision }}>
    {children}
  </ChatContext.Provider>
}
export const useChat = () => useContext(ChatContext)
