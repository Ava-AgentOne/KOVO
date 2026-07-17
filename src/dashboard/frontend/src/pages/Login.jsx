import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Send, ShieldCheck, ShieldX, Clock, RefreshCw } from 'lucide-react'
import KovoLogo from '../components/KovoLogo'

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" fill="#34A853"/>
      <path d="M3.964 10.706A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.706V4.962H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.038l3.007-2.332z" fill="#FBBC05"/>
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.962L3.964 7.294C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
    </svg>
  )
}

// Friendly text for ?error= codes set by the Google OAuth redirects
const GOOGLE_ERRORS = {
  google_denied: 'Google sign-in was cancelled.',
  google_state: 'That sign-in link expired — please try again.',
  google_error: 'Google sign-in failed — please try again.',
  google_forbidden: 'That Google account is not authorized for this dashboard.',
  google_unconfigured: 'Google login is not set up on this server — use Telegram login below.',
}

// idle → waiting (code shown, polling) → approved | denied | expired | error
export default function Login() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [state, setState] = useState('idle')
  const [code, setCode] = useState(null)
  const [error, setError] = useState(GOOGLE_ERRORS[searchParams.get('error')] || null)
  const [googleEnabled, setGoogleEnabled] = useState(false)
  const pollRef = useRef(null)

  // Already authenticated (or setup mode)? Skip login.
  useEffect(() => {
    fetch('/api/auth/me').then(r => { if (r.ok) navigate('/', { replace: true }) })
    fetch('/api/auth/methods')
      .then(r => r.json())
      .then(d => setGoogleEnabled(d.google === true))
      .catch(() => {})
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

  const loginWithGoogle = () => {
    window.location.href = '/api/auth/google/login'
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
      <div className="w-full max-w-sm text-center">
        <div className="flex justify-center mb-4"><KovoLogo size={72} /></div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">KOVO Dashboard</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-8">Sign in to continue</p>

        {(state === 'idle' || state === 'requesting' || state === 'error') && (
          <>
            {/* Google — primary / permanent (only when the server offers it) */}
            {googleEnabled && (
              <>
                <button
                  onClick={loginWithGoogle}
                  className="w-full flex items-center justify-center gap-2.5 px-4 py-3 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200 font-medium shadow-sm transition-colors mb-3"
                >
                  <GoogleIcon />
                  Continue with Google
                </button>

                {/* Divider */}
                <div className="flex items-center gap-3 mb-3">
                  <div className="flex-1 h-px bg-gray-200 dark:bg-gray-800" />
                  <span className="text-xs text-gray-400 dark:text-gray-600">or</span>
                  <div className="flex-1 h-px bg-gray-200 dark:bg-gray-800" />
                </div>
              </>
            )}

            {/* Telegram — fallback */}
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
