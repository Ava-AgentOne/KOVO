import { useState, useEffect } from 'react'

function Section({ title, children }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 space-y-3">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">{title}</h2>
      {children}
    </div>
  )
}

function ConfigEditor() {
  const [content, setContent] = useState('')
  const [original, setOriginal] = useState('')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    fetch('/api/settings')
      .then(r => r.json())
      .then(d => { setContent(d.content || ''); setOriginal(d.content || '') })
  }, [])

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
        setMsg('✅ Saved — restart service to apply changes')
      } else {
        setMsg(`❌ ${d.detail || 'Save failed'}`)
      }
    } catch (e) {
      setMsg(`❌ ${e.message}`)
    }
    setSaving(false)
  }

  const isDirty = content !== original

  return (
    <div className="space-y-2">
      <textarea
        className="w-full h-72 p-3 bg-gray-800 border border-gray-700 rounded text-sm text-gray-300 font-mono leading-relaxed resize-none focus:outline-none focus:border-brand-500"
        value={content}
        onChange={e => setContent(e.target.value)}
        spellCheck={false}
      />
      <div className="flex items-center gap-3">
        {msg && <span className="text-xs text-green-400 flex-1">{msg}</span>}
        <button
          onClick={save}
          disabled={saving || !isDirty}
          className="text-sm bg-brand-700 hover:bg-brand-600 text-white px-4 py-1.5 rounded disabled:opacity-40 transition-colors"
        >
          {saving ? 'Saving…' : '💾 Save settings.yaml'}
        </button>
      </div>
    </div>
  )
}

function EnvViewer() {
  const [entries, setEntries] = useState([])
  const [revealed, setRevealed] = useState({})

  useEffect(() => {
    fetch('/api/env')
      .then(r => r.json())
      .then(d => setEntries(d.entries || []))
  }, [])

  const toggle = (key) => setRevealed(prev => ({ ...prev, [key]: !prev[key] }))

  return (
    <div className="space-y-1 font-mono text-sm">
      {entries.length === 0 && <p className="text-gray-600 italic text-sm">No .env file found.</p>}
      {entries.map((e, i) => {
        if (e.type === 'comment') {
          return <div key={i} className="text-gray-600">{e.raw || ''}</div>
        }
        return (
          <div key={i} className="flex items-center gap-2">
            <span className="text-blue-400 flex-shrink-0">{e.key}</span>
            <span className="text-gray-600">=</span>
            <span className="text-yellow-300 flex-1">
              {revealed[e.key] ? e.value : e.masked}
            </span>
            <button
              onClick={() => toggle(e.key)}
              className="text-xs text-gray-500 hover:text-gray-300 px-1"
              title={revealed[e.key] ? 'Hide' : 'Reveal'}
            >
              {revealed[e.key] ? '🙈' : '👁'}
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

  const fetchStatus = () => {
    fetch('/api/service/status').then(r => r.json()).then(setStatus).catch(() => {})
  }

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
      setRestartMsg(d.restarted ? `✅ Restarted ${d.service}` : `❌ ${d.error || 'Failed'}`)
    } catch (e) {
      setRestartMsg(`❌ ${e.message}`)
    }
    setRestarting(false)
    setTimeout(fetchStatus, 2000)
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${status?.active ? 'bg-green-400' : 'bg-red-400'}`} />
        <span className="text-sm text-gray-300">
          {status ? `${status.service} — ${status.state}` : 'Checking…'}
        </span>
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={restart}
          disabled={restarting}
          className="text-sm bg-red-900/50 hover:bg-red-800/60 text-red-300 border border-red-700 px-4 py-1.5 rounded disabled:opacity-50 transition-colors"
        >
          {restarting ? 'Restarting…' : '🔄 Restart MiniClaw'}
        </button>
        {restartMsg && <span className="text-xs text-green-400">{restartMsg}</span>}
      </div>
    </div>
  )
}

function SystemInfo() {
  const [info, setInfo] = useState(null)

  useEffect(() => {
    fetch('/api/system/info').then(r => r.json()).then(setInfo).catch(() => {})
  }, [])

  if (!info) return <p className="text-gray-600 text-sm italic">Loading…</p>

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
      {[
        { label: 'Python', value: info.python },
        { label: 'Node', value: info.node },
        { label: 'Disk used', value: info.disk_used_gb != null ? `${info.disk_used_gb} / ${info.disk_total_gb} GB (${info.disk_pct}%)` : '—' },
        { label: 'Disk free', value: info.disk_free_gb != null ? `${info.disk_free_gb} GB` : '—' },
        { label: 'RAM used', value: info.ram_used_gb != null ? `${info.ram_used_gb} / ${info.ram_total_gb} GB (${info.ram_pct}%)` : '—' },
        { label: 'RAM free', value: info.ram_free_gb != null ? `${info.ram_free_gb} GB` : '—' },
      ].map(({ label, value }) => (
        <div key={label} className="bg-gray-800 rounded p-2.5">
          <p className="text-xs text-gray-500 mb-1">{label}</p>
          <p className="text-sm text-gray-200 font-mono">{value ?? '—'}</p>
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
        className="text-sm bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-600 px-4 py-1.5 rounded disabled:opacity-50 transition-colors"
      >
        {testing ? 'Testing…' : 'Test Ollama connection'}
      </button>
      {result && (
        <span className={`text-sm ${result.ok ? 'text-green-400' : 'text-red-400'}`}>
          {result.ok ? `✅ Online (${result.url})` : `❌ ${result.error || 'Offline'}`}
        </span>
      )}
    </div>
  )
}

function CredentialsSection() {
  const [status, setStatus] = useState(null)

  useEffect(() => {
    fetch('/api/setup/status')
      .then(r => r.json())
      .then(setStatus)
      .catch(() => {})
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
          status === null ? 'bg-gray-600' : status.configured ? 'bg-green-400' : 'bg-yellow-400'
        }`} />
        <span className="text-sm text-gray-300">
          {status === null
            ? 'Checking…'
            : status.configured
            ? 'Core credentials configured'
            : 'Not configured — setup required'}
        </span>
      </div>
      {status?.services && (
        <div className="flex flex-wrap gap-2">
          {svcItems.map(({ key, label }) => (
            <span
              key={key}
              className={`text-xs px-2 py-0.5 rounded-full border ${
                status.services[key]
                  ? 'border-green-700 text-green-400 bg-green-900/20'
                  : 'border-gray-700 text-gray-600'
              }`}
            >
              {label} {status.services[key] ? '✓' : '—'}
            </span>
          ))}
        </div>
      )}
      <a
        href="/dashboard/setup"
        className="inline-block text-sm bg-brand-700 hover:bg-brand-600 text-white px-4 py-1.5 rounded transition-colors"
      >
        {status?.configured ? '✏️ Edit Credentials' : '🔧 Configure Credentials'}
      </a>
    </div>
  )
}

export default function Settings() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Settings</h1>

      <Section title="Credentials">
        <CredentialsSection />
      </Section>

      <Section title="Configuration — settings.yaml">
        <ConfigEditor />
      </Section>

      <Section title="Environment — .env">
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
