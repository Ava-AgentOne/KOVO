import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useTheme } from '../context/ThemeContext'
import { Sun, Moon, RefreshCw, ChevronDown, ChevronUp, Save, Download, Trash2, Archive } from 'lucide-react'

function Section({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center justify-between w-full px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
      >
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">{title}</h2>
        {open ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
      </button>
      {open && <div className="px-4 pb-4 space-y-3">{children}</div>}
    </div>
  )
}

function FieldRow({ label, hint, children }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-4">
      <div className="sm:w-48 flex-shrink-0">
        <p className="text-sm text-gray-700 dark:text-gray-300">{label}</p>
        {hint && <p className="text-xs text-gray-400">{hint}</p>}
      </div>
      <div className="flex-1">{children}</div>
    </div>
  )
}

const inputCls = 'w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-900 dark:text-gray-200 focus:outline-none focus:border-brand-500'
const selectCls = 'bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-900 dark:text-gray-200 focus:outline-none focus:border-brand-500'

// ── Appearance ──────────────────────────────────────────
function ThemeToggle() {
  const { theme, toggle } = useTheme()
  return (
    <div className="flex items-center gap-4">
      <p className="text-sm text-gray-600 dark:text-gray-400">Current: <strong className="text-gray-900 dark:text-white capitalize">{theme}</strong></p>
      <button onClick={toggle}
        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm transition-colors">
        {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
        Switch to {theme === 'dark' ? 'light' : 'dark'}
      </button>
    </div>
  )
}

// ── Structured Config ───────────────────────────────────
function StructuredConfig() {
  const [config, setConfig] = useState(null)
  const [raw, setRaw] = useState('')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [showRaw, setShowRaw] = useState(false)
  const [loadError, setLoadError] = useState(null)

  useEffect(() => {
    fetch('/api/settings')
      .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json() })
      .then(d => {
        setRaw(d.content || '')
        try {
          // Parse YAML-like content into structured fields
          const lines = (d.content || '').split('\n')
          const parsed = {}
          let currentSection = null
          for (const line of lines) {
            const sectionMatch = line.match(/^(\w[\w_]*):/)
            if (sectionMatch && !line.includes('${')) {
              currentSection = sectionMatch[1]
              parsed[currentSection] = parsed[currentSection] || {}
              continue
            }
            if (currentSection) {
              const kvMatch = line.match(/^\s+(\w[\w_]*)\s*:\s*(.+)/)
              if (kvMatch) {
                const val = kvMatch[2].trim().replace(/^["']|["']$/g, '')
                parsed[currentSection][kvMatch[1]] = val
              }
            }
          }
          setConfig(parsed)
        } catch { setConfig(null) }
      })
      .catch(e => setLoadError(e.message))
  }, [])

  const updateField = (section, key, value) => {
    // Update the raw YAML string
    const regex = new RegExp(`(^\\s+${key}\\s*:\\s*)(.+)$`, 'm')
    // Find the section first, then the key within it
    const lines = raw.split('\n')
    let inSection = false
    const newLines = lines.map(line => {
      if (line.match(new RegExp(`^${section}:`))) { inSection = true; return line }
      if (line.match(/^\w/) && inSection) { inSection = false }
      if (inSection && line.match(new RegExp(`^\\s+${key}\\s*:`))) {
        return line.replace(/:\s*.+$/, `: ${value}`)
      }
      return line
    })
    setRaw(newLines.join('\n'))
    setConfig(prev => ({ ...prev, [section]: { ...(prev?.[section] || {}), [key]: value } }))
  }

  const save = async () => {
    setSaving(true)
    setMsg('')
    try {
      const r = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: raw }),
      })
      const d = await r.json()
      if (r.ok) setMsg('Saved \u2014 restart service to apply')
      else setMsg(d.detail || 'Save failed')
    } catch (e) { setMsg(e.message) }
    setSaving(false)
  }

  if (loadError) return <p className="text-sm text-red-500">Failed to load: {loadError}</p>
  if (!config) return <div className="animate-pulse h-40 bg-gray-100 dark:bg-gray-800 rounded-lg" />

  return (
    <div className="space-y-4">
      {/* Ollama */}
      <div className="space-y-2">
        <p className="text-xs font-semibold text-gray-400 uppercase">Ollama (Local LLM)</p>
        <FieldRow label="URL" hint="Ollama API endpoint">
          <input className={inputCls} value={config.ollama?.url || ''} onChange={e => updateField('ollama', 'url', e.target.value)} />
        </FieldRow>
        <FieldRow label="Model" hint="Default model for cheap tasks">
          <input className={inputCls} value={config.ollama?.default_model || ''} onChange={e => updateField('ollama', 'default_model', e.target.value)} />
        </FieldRow>
        <FieldRow label="Enabled">
          <select className={selectCls} value={config.ollama?.enabled || 'false'} onChange={e => updateField('ollama', 'enabled', e.target.value)}>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </FieldRow>
      </div>

      {/* Claude */}
      <div className="space-y-2">
        <p className="text-xs font-semibold text-gray-400 uppercase">Claude</p>
        <FieldRow label="Default model">
          <select className={selectCls} value={config.claude?.default_model || 'sonnet'} onChange={e => updateField('claude', 'default_model', e.target.value)}>
            <option value="sonnet">Sonnet (fast, balanced)</option>
            <option value="opus">Opus (deep reasoning)</option>
            <option value="haiku">Haiku (quick, cheap)</option>
          </select>
        </FieldRow>
        <FieldRow label="Timeout" hint="Seconds before Claude CLI times out">
          <input type="number" className={inputCls} value={config.claude?.timeout || '300'} onChange={e => updateField('claude', 'timeout', e.target.value)} />
        </FieldRow>
      </div>

      {/* Heartbeat */}
      <div className="space-y-2">
        <p className="text-xs font-semibold text-gray-400 uppercase">Heartbeat</p>
        <FieldRow label="Quick check" hint="Minutes between health checks">
          <input type="number" className={inputCls} value={config.heartbeat?.quick_interval || '30'} onChange={e => updateField('heartbeat', 'quick_interval', e.target.value)} />
        </FieldRow>
        <FieldRow label="Full report" hint="Hours between full reports">
          <input type="number" className={inputCls} value={config.heartbeat?.full_interval || '6'} onChange={e => updateField('heartbeat', 'full_interval', e.target.value)} />
        </FieldRow>
        <FieldRow label="Morning briefing" hint="Time in 24h format">
          <input className={inputCls} value={config.heartbeat?.morning_time || '08:00'} onChange={e => updateField('heartbeat', 'morning_time', e.target.value)} placeholder="08:00" />
        </FieldRow>
      </div>

      {/* Gateway */}
      <div className="space-y-2">
        <p className="text-xs font-semibold text-gray-400 uppercase">Gateway</p>
        <FieldRow label="Port">
          <input type="number" className={inputCls} value={config.gateway?.port || '8080'} onChange={e => updateField('gateway', 'port', e.target.value)} />
        </FieldRow>
      </div>

      {/* Save + Raw toggle */}
      <div className="flex items-center gap-3 pt-2 border-t border-gray-100 dark:border-gray-800">
        <button onClick={save} disabled={saving}
          className="flex items-center gap-2 text-sm bg-brand-500 hover:bg-brand-600 text-white px-4 py-1.5 rounded-lg disabled:opacity-40 transition-colors">
          <Save size={14} /> {saving ? 'Saving\u2026' : 'Save'}
        </button>
        {msg && <span className="text-xs text-gray-500 flex-1">{msg}</span>}
        <button onClick={() => setShowRaw(!showRaw)}
          className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 ml-auto transition-colors">
          {showRaw ? 'Hide raw YAML' : 'Edit raw YAML'}
        </button>
      </div>

      {/* Raw YAML editor (advanced) */}
      {showRaw && (
        <div className="space-y-2">
          <p className="text-xs text-amber-600 dark:text-amber-400">Be careful with indentation. Invalid YAML will be rejected.</p>
          <textarea
            className="w-full h-64 p-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm text-gray-700 dark:text-gray-300 font-mono leading-relaxed resize-none focus:outline-none focus:border-brand-500"
            value={raw}
            onChange={e => setRaw(e.target.value)}
            spellCheck={false}
          />
        </div>
      )}
    </div>
  )
}

// ── Backup Management ───────────────────────────────────
function BackupManager() {
  const [backups, setBackups] = useState(null)
  const [running, setRunning] = useState(false)
  const [msg, setMsg] = useState('')

  const loadBackups = () =>
    fetch('/api/backup/list')
      .then(r => r.json())
      .then(setBackups)
      .catch(() => setBackups({ backups: [], total_size: '0B' }))

  useEffect(() => { loadBackups() }, [])

  const runBackup = async () => {
    setRunning(true)
    setMsg('')
    try {
      const r = await fetch('/api/backup', { method: 'POST' })
      const d = await r.json()
      if (d.ok) setMsg(`Backup created (${d.size || '?'})`)
      else setMsg(d.error || 'Backup failed')
      loadBackups()
    } catch (e) { setMsg('Backup failed: ' + e.message) }
    setRunning(false)
  }

  const deleteBackup = async (filename) => {
    if (!confirm(`Delete ${filename}?`)) return
    try {
      await fetch(`/api/backup/${filename}`, { method: 'DELETE' })
      loadBackups()
    } catch {}
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <button onClick={runBackup} disabled={running}
          className="flex items-center gap-2 text-sm bg-brand-500 hover:bg-brand-600 text-white px-4 py-1.5 rounded-lg disabled:opacity-50 transition-colors">
          <Archive size={14} /> {running ? 'Backing up\u2026' : 'Backup Now'}
        </button>
        {msg && <span className="text-xs text-gray-500">{msg}</span>}
      </div>

      {backups && (
        <div className="space-y-1">
          <p className="text-xs text-gray-400">
            {backups.backups?.length || 0} backups \u00b7 {backups.total_size || '0B'} total
          </p>
          {backups.backups?.length > 0 && (
            <div className="max-h-48 overflow-y-auto space-y-1">
              {backups.backups.map(b => (
                <div key={b.name} className="flex items-center justify-between text-sm p-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="flex items-center gap-2 min-w-0">
                    <Archive size={12} className="text-gray-400 flex-shrink-0" />
                    <span className="text-gray-700 dark:text-gray-300 font-mono text-xs truncate">{b.name}</span>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-xs text-gray-400">{b.size}</span>
                    <button onClick={() => deleteBackup(b.name)} className="text-gray-400 hover:text-red-500 transition-colors p-0.5">
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          {(!backups.backups || backups.backups.length === 0) && (
            <p className="text-xs text-gray-400 italic">No backups yet. Click "Backup Now" to create one.</p>
          )}
        </div>
      )}
    </div>
  )
}

// ── .env Viewer ─────────────────────────────────────────
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

  if (loadError) return <p className="text-sm text-red-500">Failed to load: {loadError}</p>

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

// ── Service Controls ────────────────────────────────────
function ServiceControls() {
  const [status, setStatus] = useState(null)
  const [restarting, setRestarting] = useState(false)
  const [restartMsg, setRestartMsg] = useState('')

  const fetchStatus = () => fetch('/api/service/status').then(r => r.json()).then(setStatus).catch(() => {})
  useEffect(() => { fetchStatus(); const id = setInterval(fetchStatus, 10000); return () => clearInterval(id) }, [])

  const restart = async () => {
    setRestarting(true)
    setRestartMsg('')
    try {
      const r = await fetch('/api/service/restart', { method: 'POST' })
      const d = await r.json()
      setRestartMsg(d.restarted ? `Restarted ${d.service}` : d.error || 'Failed')
    } catch (e) { setRestartMsg(e.message) }
    setRestarting(false)
    setTimeout(fetchStatus, 2000)
  }

  return (
    <div className="flex items-center gap-3">
      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${status?.active ? 'bg-green-500' : 'bg-red-500'}`} />
      <span className="text-sm text-gray-700 dark:text-gray-300">
        {status ? `${status.service} \u2014 ${status.state}` : 'Checking\u2026'}
      </span>
      <button onClick={restart} disabled={restarting}
        className="flex items-center gap-2 text-sm bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-700 px-3 py-1 rounded-lg disabled:opacity-50 transition-colors ml-auto">
        <RefreshCw size={14} className={restarting ? 'animate-spin' : ''} />
        {restarting ? 'Restarting\u2026' : 'Restart'}
      </button>
      {restartMsg && <span className="text-xs text-gray-500">{restartMsg}</span>}
    </div>
  )
}

// ── System Info ─────────────────────────────────────────
function SystemInfo() {
  const [info, setInfo] = useState(null)
  const [loadError, setLoadError] = useState(null)

  useEffect(() => {
    fetch('/api/system/info')
      .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json() })
      .then(setInfo)
      .catch(e => setLoadError(e.message))
  }, [])

  if (loadError) return <p className="text-sm text-red-500">Failed to load: {loadError}</p>
  if (!info) return <div className="animate-pulse"><div className="grid grid-cols-3 gap-3">{[1,2,3].map(i => <div key={i} className="h-14 bg-gray-100 dark:bg-gray-800 rounded-lg" />)}</div></div>

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
      {[
        { label: 'Python', value: info.python },
        { label: 'Node', value: info.node },
        { label: 'Disk', value: info.disk_used_gb != null ? `${info.disk_used_gb}/${info.disk_total_gb} GB (${info.disk_pct}%)` : '\u2014' },
        { label: 'RAM', value: info.ram_used_gb != null ? `${info.ram_used_gb}/${info.ram_total_gb} GB (${info.ram_pct}%)` : '\u2014' },
      ].map(({ label, value }) => (
        <div key={label} className="bg-gray-50 dark:bg-gray-800 rounded-lg p-2.5">
          <p className="text-xs text-gray-400 mb-0.5">{label}</p>
          <p className="text-sm text-gray-700 dark:text-gray-200 font-mono">{value ?? '\u2014'}</p>
        </div>
      ))}
    </div>
  )
}

// ── Ollama Test ─────────────────────────────────────────
function OllamaTest() {
  const [result, setResult] = useState(null)
  const [testing, setTesting] = useState(false)

  const test = async () => {
    setTesting(true)
    setResult(null)
    try {
      const r = await fetch('/api/ollama/test', { method: 'POST' })
      setResult(await r.json())
    } catch (e) { setResult({ ok: false, error: e.message }) }
    setTesting(false)
  }

  return (
    <div className="flex items-center gap-3">
      <button onClick={test} disabled={testing}
        className="text-sm bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600 px-4 py-1.5 rounded-lg disabled:opacity-50 transition-colors">
        {testing ? 'Testing\u2026' : 'Test Ollama'}
      </button>
      {result && (
        <span className={`text-sm ${result.ok ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
          {result.ok ? `Online (${result.url})` : result.error || 'Offline'}
        </span>
      )}
    </div>
  )
}

// ── Credentials ─────────────────────────────────────────
function CredentialsSection() {
  const [status, setStatus] = useState(null)
  useEffect(() => { fetch('/api/setup/status').then(r => r.json()).then(setStatus).catch(() => {}) }, [])

  return (
    <div className="flex items-center gap-3 flex-wrap">
      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${status === null ? 'bg-gray-400' : status.configured ? 'bg-green-500' : 'bg-yellow-500'}`} />
      <span className="text-sm text-gray-700 dark:text-gray-300">
        {status === null ? 'Checking\u2026' : status.configured ? 'Configured' : 'Not configured'}
      </span>
      {status?.services && (
        <div className="flex gap-1.5">
          {[
            { key: 'telegram_calls', label: 'Calls' },
            { key: 'google_calendar', label: 'Google' },
            { key: 'groq', label: 'Groq' },
          ].map(({ key, label }) => (
            <span key={key} className={`text-xs px-1.5 py-0.5 rounded-full border ${
              status.services[key] ? 'border-green-300 dark:border-green-700 text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20'
                : 'border-gray-200 dark:border-gray-700 text-gray-400'
            }`}>{label} {status.services[key] ? '\u2713' : '\u2014'}</span>
          ))}
        </div>
      )}
      <Link to="/setup" className="text-sm bg-brand-500 hover:bg-brand-600 text-white px-3 py-1 rounded-lg transition-colors ml-auto">
        {status?.configured ? 'Edit' : 'Configure'}
      </Link>
    </div>
  )
}

// ── Main Settings Page ──────────────────────────────────
export default function Settings() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>

      <Section title="Service">
        <ServiceControls />
      </Section>

      <Section title="Credentials">
        <CredentialsSection />
      </Section>

      <Section title="Configuration">
        <StructuredConfig />
      </Section>

      <Section title="Backup">
        <BackupManager />
      </Section>

      <Section title="Environment (.env)" defaultOpen={false}>
        <EnvViewer />
      </Section>

      <Section title="System" defaultOpen={false}>
        <SystemInfo />
        <div className="pt-2 border-t border-gray-100 dark:border-gray-800">
          <OllamaTest />
        </div>
      </Section>

      <Section title="Appearance" defaultOpen={false}>
        <ThemeToggle />
      </Section>
    </div>
  )
}
