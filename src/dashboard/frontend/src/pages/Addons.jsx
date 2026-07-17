import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  PackagePlus, ExternalLink, Download, CheckCircle2, Circle, Loader2,
  Terminal, RefreshCw, Link as LinkIcon, Upload, KeyRound, HardDriveDownload,
} from 'lucide-react'
import PageHeader from '../components/PageHeader'
import ConfirmModal from '../components/ConfirmModal'
import useApi from '../hooks/useApi'

// Add-ons (v3.0 Phase 3.5) — guided companion setup. Every install shows
// its exact commands before running; installs stream a live log.

const STATUS_META = {
  ready:         { label: 'Ready',         cls: 'text-emerald-600 dark:text-emerald-400 bg-emerald-500/10' },
  installed:     { label: 'Needs setup',   cls: 'text-amber-600 dark:text-amber-400 bg-amber-500/10' },
  not_installed: { label: 'Not installed', cls: 'text-gray-500 bg-gray-500/10' },
  unknown:       { label: 'Unknown',       cls: 'text-gray-400 bg-gray-500/10' },
}

function InstallLog({ onDone }) {
  const [job, setJob] = useState(null)
  useEffect(() => {
    const id = setInterval(async () => {
      try {
        const d = await fetch('/api/addons/job').then(r => r.json())
        setJob(d)
        if (d.state === 'done' || d.state === 'failed') {
          clearInterval(id)
          setTimeout(onDone, 1200)
        }
      } catch {}
    }, 1500)
    return () => clearInterval(id)
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps
  if (!job || job.state === 'idle') return null
  return (
    <div className="mt-3">
      <div className="flex items-center gap-2 text-xs mb-1.5">
        {job.state === 'running' ? <Loader2 size={12} className="animate-spin text-brand-500" />
          : job.state === 'done' ? <CheckCircle2 size={12} className="text-emerald-500" />
          : <Circle size={12} className="text-red-500" />}
        <span className="text-gray-500">install {job.state}</span>
      </div>
      <pre className="text-[11px] text-gray-600 dark:text-gray-400 font-mono bg-gray-50 dark:bg-gray-800 rounded-lg p-2 overflow-auto max-h-40 whitespace-pre-wrap">
        {(job.log || []).join('\n')}
      </pre>
    </div>
  )
}

function TailscaleFlow({ onRefresh }) {
  const [authUrl, setAuthUrl] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const start = async () => {
    setBusy(true); setError('')
    try {
      const r = await fetch('/api/addons/tailscale/login', { method: 'POST' })
      const d = await r.json()
      if (d.auth_url) setAuthUrl(d.auth_url)
      else if (d.already) onRefresh()
      else setError(d.detail || 'Could not get the login link')
    } catch (e) { setError(e.message) }
    setBusy(false)
  }

  // While a login link is showing, poll status so joining flips the card
  useEffect(() => {
    if (!authUrl) return
    const id = setInterval(onRefresh, 5000)
    return () => clearInterval(id)
  }, [authUrl])  // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="mt-2">
      {!authUrl ? (
        <button onClick={start} disabled={busy}
          className="flex items-center gap-1.5 text-xs bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-white px-3 py-1.5 rounded-lg">
          {busy ? <Loader2 size={12} className="animate-spin" /> : <KeyRound size={12} />}
          Connect to your tailnet
        </button>
      ) : (
        <div className="text-xs space-y-1.5">
          <a href={authUrl} target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-1.5 bg-brand-500 hover:bg-brand-600 text-white px-3 py-1.5 rounded-lg">
            <ExternalLink size={12} /> Authorize this machine
          </a>
          <p className="text-gray-400">Sign in (Google works), click Connect — this card turns green by itself.</p>
        </div>
      )}
      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
    </div>
  )
}

function GoogleFlow({ status, onRefresh }) {
  const [authUrl, setAuthUrl] = useState(null)
  const [paste, setPaste] = useState('')
  const [msg, setMsg] = useState('')
  const fileRef = useRef(null)

  const upload = async (file) => {
    const fd = new FormData()
    fd.append('file', file)
    const r = await fetch('/api/addons/google/credentials', { method: 'POST', body: fd })
    const d = await r.json()
    setMsg(d.saved ? 'Credentials saved ✓' : (d.detail || 'Upload failed'))
    onRefresh()
  }

  const startAuth = async () => {
    setMsg('')
    const r = await fetch('/api/addons/google/auth/start', { method: 'POST' })
    const d = await r.json()
    if (d.auth_url) setAuthUrl(d.auth_url)
    else setMsg(d.detail || 'Could not start sign-in')
  }

  const complete = async () => {
    const r = await fetch('/api/addons/google/auth/complete', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code_or_url: paste }),
    })
    const d = await r.json()
    setMsg(d.message || d.detail || '')
    if (d.ok) { setAuthUrl(null); setPaste(''); onRefresh() }
  }

  return (
    <div className="mt-2 space-y-2 text-xs">
      {status === 'not_installed' && (
        <>
          <input ref={fileRef} type="file" accept=".json,application/json" className="hidden"
            onChange={e => e.target.files?.[0] && upload(e.target.files[0])} />
          <button onClick={() => fileRef.current?.click()}
            className="flex items-center gap-1.5 bg-brand-500 hover:bg-brand-600 text-white px-3 py-1.5 rounded-lg">
            <Upload size={12} /> Upload credentials.json
          </button>
          <p className="text-gray-400">From Google Cloud Console → Credentials → OAuth client (Desktop app).</p>
        </>
      )}
      {status !== 'not_installed' && !authUrl && (
        <button onClick={startAuth}
          className="flex items-center gap-1.5 bg-brand-500 hover:bg-brand-600 text-white px-3 py-1.5 rounded-lg">
          <KeyRound size={12} /> {status === 'ready' ? 'Re-connect Google' : 'Sign in with Google'}
        </button>
      )}
      {authUrl && (
        <div className="space-y-1.5">
          <a href={authUrl} target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-1.5 bg-brand-500 hover:bg-brand-600 text-white px-3 py-1.5 rounded-lg">
            <ExternalLink size={12} /> Open Google consent
          </a>
          <p className="text-gray-400">
            Approve, land on the broken “localhost” page, copy that page's full URL, paste it here:
          </p>
          <div className="flex gap-1.5">
            <input value={paste} onChange={e => setPaste(e.target.value)}
              placeholder="http://localhost:53682/?state=…&code=…"
              className="flex-1 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1.5 text-xs text-gray-900 dark:text-white focus:outline-none focus:border-brand-500" />
            <button onClick={complete} disabled={!paste.trim()}
              className="bg-emerald-500 hover:bg-emerald-600 disabled:opacity-40 text-white px-3 py-1.5 rounded-lg">
              Finish
            </button>
          </div>
        </div>
      )}
      {msg && <p className="text-gray-500">{msg}</p>}
    </div>
  )
}

function OllamaFlow({ onStarted }) {
  const [model, setModel] = useState('llama3.2:3b')
  const [msg, setMsg] = useState('')
  const pull = async () => {
    setMsg('')
    const r = await fetch('/api/addons/ollama/pull', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model }),
    })
    const d = await r.json()
    if (d.started) { setMsg(`Pulling ${d.model}…`); onStarted() }
    else setMsg(d.detail || 'Pull failed')
  }
  return (
    <div className="mt-2 text-xs space-y-1.5">
      <div className="flex gap-1.5">
        <input value={model} onChange={e => setModel(e.target.value)}
          className="flex-1 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1.5 font-mono text-xs text-gray-900 dark:text-white focus:outline-none focus:border-brand-500" />
        <button onClick={pull}
          className="flex items-center gap-1.5 bg-brand-500 hover:bg-brand-600 text-white px-3 py-1.5 rounded-lg">
          <HardDriveDownload size={12} /> Pull model
        </button>
      </div>
      {msg && <p className="text-gray-500">{msg}</p>}
    </div>
  )
}

function AddonCard({ addon, onRefresh, onInstallStarted, installing }) {
  const meta = STATUS_META[addon.status] || STATUS_META.unknown
  const [confirm, setConfirm] = useState(false)
  const [commands, setCommands] = useState([])

  const askInstall = async () => {
    const d = await fetch(`/api/addons/${addon.id}/commands`).then(r => r.json())
    setCommands(d.commands || [])
    setConfirm(true)
  }
  const doInstall = async () => {
    setConfirm(false)
    try {
      await fetch(`/api/addons/${addon.id}/install`, { method: 'POST' })
      onInstallStarted()
    } catch {}
  }

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
      <div className="flex items-start justify-between gap-2 mb-1">
        <div className="flex items-center gap-2 min-w-0">
          <div className="p-1.5 rounded-lg bg-orange-500/10 text-orange-500 flex-shrink-0">
            <PackagePlus size={14} />
          </div>
          <h3 className="font-semibold text-gray-900 dark:text-white text-sm truncate">{addon.label}</h3>
        </div>
        <span className={`text-[10px] px-2 py-0.5 rounded-full flex-shrink-0 ${meta.cls}`}>{meta.label}</span>
      </div>
      <p className="text-xs text-gray-500 mb-1">{addon.desc}</p>
      {addon.detail && <p className="text-[11px] text-gray-400 font-mono mb-1">{addon.detail}</p>}

      {/* State-appropriate action */}
      {addon.status === 'not_installed' && addon.installable && !installing && (
        <button onClick={askInstall}
          className="mt-1 flex items-center gap-1.5 text-xs bg-brand-500 hover:bg-brand-600 text-white px-3 py-1.5 rounded-lg">
          <Download size={12} /> Install
        </button>
      )}
      {addon.configure_kind === 'tailscale' && addon.status === 'installed' && (
        <TailscaleFlow onRefresh={onRefresh} />
      )}
      {addon.configure_kind === 'google' && addon.status !== 'ready' && (
        <GoogleFlow status={addon.status} onRefresh={onRefresh} />
      )}
      {addon.configure_kind === 'ollama' && addon.status === 'installed' && !installing && (
        <OllamaFlow onStarted={onInstallStarted} />
      )}
      {addon.configure_kind === 'link' && addon.status !== 'ready' && (
        <Link to={addon.link}
          className="mt-1 inline-flex items-center gap-1.5 text-xs bg-brand-500 hover:bg-brand-600 text-white px-3 py-1.5 rounded-lg">
          <LinkIcon size={12} /> Open the MCP Store
        </Link>
      )}

      <div className="flex items-center justify-end mt-2">
        <a href={addon.docs} target="_blank" rel="noreferrer"
          className="flex items-center gap-1 text-xs text-gray-400 hover:text-brand-500">
          Docs <ExternalLink size={11} />
        </a>
      </div>

      <ConfirmModal open={confirm} title={`Install ${addon.label}?`}
        message={
          <span>
            These exact commands will run on the server:
            <pre className="mt-2 text-[11px] font-mono bg-gray-50 dark:bg-gray-900 rounded-lg p-2 overflow-auto max-h-40 whitespace-pre-wrap text-left">
              {commands.join('\n')}
            </pre>
          </span>
        }
        confirmLabel="Run install" confirmColor="brand"
        onConfirm={doInstall} onCancel={() => setConfirm(false)} />
    </div>
  )
}

export default function Addons() {
  const { data, loading, reload } = useApi('/api/addons', 30000)
  const [installing, setInstalling] = useState(false)
  const list = data?.addons || []
  const ready = list.filter(a => a.status === 'ready').length

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <PageHeader title="Add-ons" icon={PackagePlus} accent="orange"
          subtitle={!loading ? `${ready}/${list.length} ready · guided setup for KOVO's companions` : undefined} />
        <button onClick={reload} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800" title="Re-detect">
          <RefreshCw size={14} />
        </button>
      </div>

      {installing && <InstallLog onDone={() => { setInstalling(false); reload() }} />}

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 animate-pulse">
          {[1, 2, 3, 4].map(i => <div key={i} className="h-36 bg-gray-200 dark:bg-gray-800 rounded-xl" />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {list.map(a => (
            <AddonCard key={a.id} addon={a} onRefresh={reload}
              installing={installing}
              onInstallStarted={() => setInstalling(true)} />
          ))}
        </div>
      )}

      <p className="text-[11px] text-gray-400 flex items-center gap-1.5">
        <Terminal size={11} />
        Installs always show their exact commands before running, and stream a live log.
      </p>
    </div>
  )
}
