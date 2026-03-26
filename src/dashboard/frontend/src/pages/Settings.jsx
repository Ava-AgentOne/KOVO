import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useTheme } from '../context/ThemeContext'
import { Sun, Moon, RefreshCw } from 'lucide-react'

function Section({ title, children }) {
  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 space-y-3">
      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">{title}</h2>
      {children}
    </div>
  )
}

function ThemeToggle() {
  const { theme, toggle } = useTheme()
  return (
    <div className="flex items-center gap-4">
      <p className="text-sm text-gray-600 dark:text-gray-400">Current theme: <strong className="text-gray-900 dark:text-white capitalize">{theme}</strong></p>
      <button
        onClick={toggle}
        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm transition-colors"
      >
        {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
        Switch to {theme === 'dark' ? 'light' : 'dark'} mode
      </button>
    </div>
  )
}

function ConfigEditor() {
  const [content, setContent] = useState('')
  const [original, setOriginal] = useState('')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [loadError, setLoadError] = useState(null)

  useEffect(() => {
    fetch('/api/settings')
      .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json() })
      .then(d => { setContent(d.content || ''); setOriginal(d.content || '') })
      .catch(e => setLoadError(e.message))
  }, [])

  if (loadError) return <p className="text-sm text-red-500">Failed to load settings: {loadError}</p>

  const save = async () => {
    setSaving(true)
    setMsg('')
    try {
      const r = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      })
      const d = await r.json()
      if (r.ok) {
        setOriginal(content)
        setMsg('Saved \u2014 restart service to apply changes')
      } else {
        setMsg(d.detail || 'Save failed')
      }
    } catch (e) {
      setMsg(e.message)
    }
    setSaving(false)
  }

  const isDirty = content !== original

  return (
    <div className="space-y-2">
      <textarea
        className="w-full h-72 p-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm text-gray-700 dark:text-gray-300 font-mono leading-relaxed resize-none focus:outline-none focus:border-brand-500"
        value={content}
        onChange={e => setContent(e.target.value)}
        spellCheck={false}
      />
      <div className="flex items-center gap-3">
        {msg && <span className="text-xs text-gray-500 flex-1">{msg}</span>}
        <button
          onClick={save}
          disabled={saving || !isDirty}
          className="text-sm bg-brand-500 hover:bg-brand-600 text-white px-4 py-1.5 rounded-lg disabled:opacity-40 transition-colors"
        >
          {saving ? 'Saving\u2026' : 'Save settings.yaml'}
        </button>
      </div>
    </div>
  )
}

function EnvViewer() {
  const [entries, setEntries] = useState([])
  const [revealed, setRevealed] = useState({})
  const [loadError, setLoadError] = useState(null)

  useEffect(() => {
    fetch('/api/env')
      .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json() })
      .then(d => setEntries(d.entries || []))
      .catch(e => setLoadError(e.message))
  }, [])

  if (loadError) return <p className="text-sm text-red-500">Failed to load .env: {loadError}</p>

  const toggle = (key) => setRevealed(prev => ({ ...prev, [key]: !prev[key] }))

  return (
    <div className="space-y-1 font-mono text-sm">
      {entries.length === 0 && <p className="text-gray-400 italic text-sm">No .env file found.</p>}
      {entries.map((e, i) => {
        if (e.type === 'comment') return <div key={i} className="text-gray-400 dark:text-gray-600">{e.raw || ''}</div>
        return (
          <div key={i} className="flex items-center gap-2">
            <span className="text-blue-600 dark:text-blue-400 flex-shrink-0">{e.key}</span>
            <span className="text-gray-400">=</span>
            <span className="text-yellow-600 dark:text-yellow-300 flex-1">{revealed[e.key] ? e.value : e.masked}</span>
            <button onClick={() => toggle(e.key)} className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 px-1">
              {revealed[e.key] ? 'hide' : 'show'}
            </button>
          </div>
        )
      })}
    </div>
  )
}

function ServiceControls() {
  const [status, setStatus] = useState(null)
  const [restarting, setRestarting] = useState(false)
  const [restartMsg, setRestartMsg] = useState('')

  const fetchStatus = () => fetch('/api/service/status').then(r => r.json()).then(setStatus).catch(() => {})

  useEffect(() => {
    fetchStatus()
    const id = setInterval(fetchStatus, 10000)
    return () => clearInterval(id)
  }, [])

  const restart = async () => {
    setRestarting(true)
    setRestartMsg('')
    try {
      const r = await fetch('/api/service/restart', { method: 'POST' })
      const d = await r.json()
      setRestartMsg(d.restarted ? `Restarted ${d.service}` : d.error || 'Failed')
    } catch (e) {
      setRestartMsg(e.message)
    }
    setRestarting(false)
    setTimeout(fetchStatus, 2000)
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${status?.active ? 'bg-green-500' : 'bg-red-500'}`} />
        <span className="text-sm text-gray-700 dark:text-gray-300">
          {status ? `${status.service} \u2014 ${status.state}` : 'Checking\u2026'}
        </span>
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={restart}
          disabled={restarting}
          className="flex items-center gap-2 text-sm bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-700 px-4 py-1.5 rounded-lg disabled:opacity-50 transition-colors"
        >
          <RefreshCw size={14} className={restarting ? 'animate-spin' : ''} />
          {restarting ? 'Restarting\u2026' : 'Restart Kovo'}
        </button>
        {restartMsg && <span className="text-xs text-gray-500">{restartMsg}</span>}
      </div>
    </div>
  )
}

function SystemInfo() {
  const [info, setInfo] = useState(null)
  const [loadError, setLoadError] = useState(null)

  useEffect(() => {
    fetch('/api/system/info')
      .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json() })
      .then(setInfo)
      .catch(e => setLoadError(e.message))
  }, [])

  if (loadError) return <p className="text-sm text-red-500">Failed to load system info: {loadError}</p>
  if (!info) return (
    <div className="animate-pulse">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {[1,2,3,4,5,6].map(i => <div key={i} className="h-16 bg-gray-100 dark:bg-gray-800 rounded-lg" />)}
      </div>
    </div>
  )

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
      {[
        { label: 'Python', value: info.python },
        { label: 'Node', value: info.node },
        { label: 'Disk used', value: info.disk_used_gb != null ? `${info.disk_used_gb} / ${info.disk_total_gb} GB (${info.disk_pct}%)` : '\u2014' },
        { label: 'Disk free', value: info.disk_free_gb != null ? `${info.disk_free_gb} GB` : '\u2014' },
        { label: 'RAM used', value: info.ram_used_gb != null ? `${info.ram_used_gb} / ${info.ram_total_gb} GB (${info.ram_pct}%)` : '\u2014' },
        { label: 'RAM free', value: info.ram_free_gb != null ? `${info.ram_free_gb} GB` : '\u2014' },
      ].map(({ label, value }) => (
        <div key={label} className="bg-gray-50 dark:bg-gray-800 rounded-lg p-2.5">
          <p className="text-xs text-gray-400 mb-1">{label}</p>
          <p className="text-sm text-gray-700 dark:text-gray-200 font-mono">{value ?? '\u2014'}</p>
        </div>
      ))}
    </div>
  )
}

function OllamaTest() {
  const [result, setResult] = useState(null)
  const [testing, setTesting] = useState(false)

  const test = async () => {
    setTesting(true)
    setResult(null)
    try {
      const r = await fetch('/api/ollama/test', { method: 'POST' })
      setResult(await r.json())
    } catch (e) {
      setResult({ ok: false, error: e.message })
    }
    setTesting(false)
  }

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={test}
        disabled={testing}
        className="text-sm bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600 px-4 py-1.5 rounded-lg disabled:opacity-50 transition-colors"
      >
        {testing ? 'Testing\u2026' : 'Test Ollama connection'}
      </button>
      {result && (
        <span className={`text-sm ${result.ok ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
          {result.ok ? `Online (${result.url})` : result.error || 'Offline'}
        </span>
      )}
    </div>
  )
}

function CredentialsSection() {
  const [status, setStatus] = useState(null)

  useEffect(() => {
    fetch('/api/setup/status').then(r => r.json()).then(setStatus).catch(() => {})
  }, [])

  const svcItems = [
    { key: 'telegram_calls', label: 'Voice Calls' },
    { key: 'google_calendar', label: 'Google Calendar' },
    { key: 'groq', label: 'Groq Transcription' },
  ]

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
          status === null ? 'bg-gray-400' : status.configured ? 'bg-green-500' : 'bg-yellow-500'
        }`} />
        <span className="text-sm text-gray-700 dark:text-gray-300">
          {status === null ? 'Checking\u2026' : status.configured ? 'Core credentials configured' : 'Not configured \u2014 setup required'}
        </span>
      </div>
      {status?.services && (
        <div className="flex flex-wrap gap-2">
          {svcItems.map(({ key, label }) => (
            <span
              key={key}
              className={`text-xs px-2 py-0.5 rounded-full border ${
                status.services[key]
                  ? 'border-green-300 dark:border-green-700 text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20'
                  : 'border-gray-200 dark:border-gray-700 text-gray-400'
              }`}
            >
              {label} {status.services[key] ? '\u2713' : '\u2014'}
            </span>
          ))}
        </div>
      )}
      <Link
        to="/setup"
        className="inline-block text-sm bg-brand-500 hover:bg-brand-600 text-white px-4 py-1.5 rounded-lg transition-colors"
      >
        {status?.configured ? 'Edit Credentials' : 'Configure Credentials'}
      </Link>
    </div>
  )
}

export default function Settings() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>

      <Section title="Appearance">
        <ThemeToggle />
      </Section>

      <Section title="Credentials">
        <CredentialsSection />
      </Section>

      <Section title="Configuration &mdash; settings.yaml">
        <ConfigEditor />
      </Section>

      <Section title="Environment &mdash; .env">
        <EnvViewer />
      </Section>

      <Section title="Service Controls">
        <ServiceControls />
      </Section>

      <Section title="System Info">
        <SystemInfo />
      </Section>

      <Section title="Ollama">
        <OllamaTest />
      </Section>
    </div>
  )
}
