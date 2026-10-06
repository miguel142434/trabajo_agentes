import { useEffect, useState } from 'react'

export function usePageData(loader, offset, revision = 0) {
  const [state, setState] = useState({ items: [], loading: true, error: '' })
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setState({ items: [], loading: true, error: '' })
    loader(offset, controller.signal).then(items => {
      if (!controller.signal.aborted) setState({ items, loading: false, error: '' })
    }).catch(error => {
      if (!controller.signal.aborted) setState({ items: [], loading: false, error: error.message })
    })
    return () => controller.abort()
  }, [loader, offset, revision, attempt])
  return { ...state, reload: () => setAttempt(value => value + 1) }
}
