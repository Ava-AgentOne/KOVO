import { useState, useEffect, useCallback } from 'react'

export default function useApi(url, interval = 0) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(() => {
    fetch(url)
      .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json() })
      .then(d => { setData(d); setLoading(false); setError(null) })
      .catch(e => { setLoading(false); setError(e.message) })
  }, [url])

  useEffect(() => {
    load()
    if (!interval) return
    const id = setInterval(load, interval)
    return () => clearInterval(id)
  }, [load, interval])

  return { data, loading, error, reload: load }
}
