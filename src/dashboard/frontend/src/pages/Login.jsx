import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Send, ShieldCheck, ShieldX, Clock, RefreshCw } from 'lucide-react'
import KovoLogo from '../components/KovoLogo'

// idle → waiting (code shown, polling) → approved | denied | expired | error
export default function Login() {
  const navigate = useNavigate()
  const [state, setState] = useState('idle')
  const [code, setCode] = useState(null)
  const [error, setError] = useState(null)
  const pollRef = useRef(null)

  // Already authenticated (or setup mode)? Skip login.
  useEffect(() => {
    fetch('/api/auth/me').then(r => { if (r.ok) navigate('/', { replace: true }) })
  }, [navigate])

  useEffect(() => () => clearInterval(pollRef.current), [])

  const start = async () => {
    setError(null)
    setState('requesting')
    try {
      const r = await fetch('/api/auth/request', { method: 'POST' })
      if (!r.ok) {
        const body = await r.json().catch(() => ({}))
        setError(body.detail || `Login unavailable (${r.status})`)
        setState('error')
        return
      }
      const d = await r.json()
      setCode(d.code)
      setState('waiting')
      pollRef.current = setInterval(async () => {
        const s = await fetch(`/api/auth/status/${d.request_id}`)
        if (!s.ok) return
        const { status } = await s.json()
        if (status === 'pending') return
        clearInterval(pollRef.current)
        if (status === 'approved') {
          setState('approved')
          setTimeout(() => navigate('/', { replace: true }), 800)
        } else {
          setState(status) // denied | expired
        }
      }, 2000)
    } catch {
      setError('Cannot reach KOVO — is the service running?')
      setState('error')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
      <div className="w-full max-w-sm text-center">
        <div className="flex justify-center mb-4"><KovoLogo size={72} /></div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">KOVO Dashboard</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-8">Login is approved from your Telegram</p>

        {(state === 'idle' || state === 'requesting' || state === 'error') && (
          <>
            <button
              onClick={start}
              disabled={state === 'requesting'}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-brand-500 hover:bg-brand-600 disabled:opacity-60 text-white font-medium transition-colors"
            >
              <Send size={17} />
              {state === 'requesting' ? 'Sending…' : 'Login with Telegram'}
            </button>
            {error && <p className="mt-4 text-sm text-red-500">{error}</p>}
          </>
        )}

        {state === 'waiting' && (
          <div className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6">
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
              KOVO sent you a message. Approve it only if the code matches:
            </p>
            <div className="text-3xl font-mono font-bold tracking-widest text-brand-500 mb-3">{code}</div>
            <p className="text-xs text-gray-400 dark:text-gray-500 flex items-center justify-center gap-1">
              <Clock size={13} /> Waiting for approval — expires in 5 minutes
            </p>
          </div>
        )}

        {state === 'approved' && (
          <div className="flex items-center justify-center gap-2 text-green-500 font-medium">
            <ShieldCheck size={20} /> Approved — opening dashboard…
          </div>
        )}

        {(state === 'denied' || state === 'expired') && (
          <div className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6">
            <div className="flex items-center justify-center gap-2 text-red-500 font-medium mb-4">
              <ShieldX size={20} /> {state === 'denied' ? 'Login denied' : 'Request expired'}
            </div>
            <button
              onClick={start}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            >
              <RefreshCw size={15} /> Try again
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
