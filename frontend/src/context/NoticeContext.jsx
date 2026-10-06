import { createContext, useContext, useState } from 'react'

const NoticeContext = createContext(null)
export function NoticeProvider({ children }) {
  const [notice, setNotice] = useState(null)
  return <NoticeContext.Provider value={{ notify: (message, type = 'error') => setNotice({ message, type }), clearNotice: () => setNotice(null) }}>
    {notice && <div className={`toast ${notice.type}`} role={notice.type === 'error' ? 'alert' : 'status'}>
      <span>{notice.message}</span><button aria-label="Cerrar aviso" onClick={() => setNotice(null)}>×</button>
    </div>}
    {children}
  </NoticeContext.Provider>
}
export const useNotice = () => useContext(NoticeContext)
