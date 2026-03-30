import { useState, useEffect, useRef } from 'react'
import UpdateChecker from '../components/UpdateChecker'
import { Link } from 'react-router-dom'
import { useTheme } from '../context/ThemeContext'
import {
  Sun, Moon, RefreshCw, ChevronDown, ChevronUp, Save, Download, Upload,
  Trash2, Archive, Loader2, ExternalLink,
  MessageSquare, Phone, Cloud, Github, Mic, Settings2, Database,
  Server, HardDrive, Plug, Eye, EyeOff,
} from 'lucide-react'

// ── Tab system ──────────────────────────────────────────────────
const TABS = [
  { id: 'connections', label: 'Connections', icon: Plug },
  { id: 'config', label: 'Configuration', icon: Settings2 },
  { id: 'backup', label: 'Backup', icon: HardDrive },
  { id: 'system', label: 'System', icon: Server },
]

function TabBar({ active, onChange }) {
  return (
    <div className="flex border-b border-gray-200 dark:border-gray-800 mb-6 -mx-1">
      {TABS.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          onClick={() => onChange(id)}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors mx-1 ${
            active === id
              ? 'border-brand-500 text-brand-500'
              : 'border-transparent text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'
          }`}
        >
          <Icon size={15} />
          {label}
        </button>
      ))}
    </div>
  )
}

// ── Shared UI ───────────────────────────────────────────────────
function Section({ title, children, defaultOpen = true, actions }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center justify-between w-full px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
      >
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">{title}</h2>
        <div className="flex items-center gap-2">
          {actions}
          {open ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
        </div>
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

function ExtLink({ href, children }) {
  return (
    <a href={href} target="_blank" rel="noreferrer" className="text-brand-500 hover:text-brand-600 underline underline-offset-2 inline-flex items-center gap-1 text-xs">
      {children} <ExternalLink size={10} />
    </a>
  )
}

function StatusDot({ ok, label }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${ok ? 'bg-emerald-500' : 'bg-gray-300 dark:bg-gray-600'}`} />
      <span className={`text-xs ${ok ? 'text-emerald-600 dark:text-emerald-400' : 'text-gray-400'}`}>{label}</span>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════
// TAB 1: CONNECTIONS
// ═══════════════════════════════════════════════════════════════
function ConnectionCard({ icon: Icon, iconColor, title, description, configured, children, testFn, testLabel }) {
  const [expanded, setExpanded] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)

  const doTest = async () => {
    if (!testFn) return
    setTesting(true)
    setTestResult(null)
    try {
      const r = await testFn()
      setTestResult(r)
    } catch (e) { setTestResult({ ok: false, error: e.message }) }
    setTesting(false)
  }

  return (
    <div className={`bg-white dark:bg-gray-900 border rounded-xl overflow-hidden transition-colors ${
      configured ? 'border-gray-200 dark:border-gray-800' : 'border-dashed border-gray-300 dark:border-gray-700'
    }`}>
      <div className="flex items-center gap-4 px-4 py-3.5">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${iconColor}`}>
          <Icon size={20} className="text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-gray-900 dark:text-white">{title}</p>
            {configured ? (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-700 font-medium">Connected</span>
            ) : (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-50 dark:bg-gray-800 text-gray-400 border border-gray-200 dark:border-gray-700 font-medium">Not set up</span>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-0.5">{description}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {testFn && configured && (
            <button onClick={doTest} disabled={testing}
              className="text-xs text-gray-400 hover:text-brand-500 px-2 py-1 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors disabled:opacity-50">
              {testing ? 'Testing…' : (testLabel || 'Test')}
            </button>
          )}
          {testResult && (
            <span className={`text-xs ${testResult.ok ? 'text-emerald-500' : 'text-red-400'}`}>
              {testResult.ok ? '✓' : testResult.error || '✗'}
            </span>
          )}
          <button onClick={() => setExpanded(!expanded)}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-1 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>
      {expanded && (
        <div className="px-4 pb-4 pt-1 border-t border-gray-100 dark:border-gray-800 space-y-3">
          {children}
        </div>
      )}
    </div>
  )
}

function EnvField({ label, envKey, hint, entries, onSave, type = 'text' }) {
  const current = entries.find(e => e.key === envKey)
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState('')
  const [showValue, setShowValue] = useState(false)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  const save = async () => {
    setSaving(true)
    setMsg('')
    try {
      await onSave(envKey, value)
      setEditing(false)
      setMsg('Saved — restart to apply')
    } catch (e) { setMsg(e.message) }
    setSaving(false)
  }

  const hasValue = current && current.has_value

  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3">
      <div className="sm:w-40 flex-shrink-0">
        <p className="text-sm text-gray-700 dark:text-gray-300">{label}</p>
        {hint && <p className="text-xs text-gray-400">{hint}</p>}
      </div>
      <div className="flex-1 flex items-center gap-2">
        {editing ? (
          <>
            <input
              type={showValue ? 'text' : 'password'}
              className={inputCls + ' flex-1 font-mono text-xs'}
              value={value}
              onChange={e => setValue(e.target.value)}
              placeholder={`Enter ${label}…`}
              autoFocus
            />
            <button onClick={() => setShowValue(!showValue)} className="text-gray-400 hover:text-gray-600 p-1">
              {showValue ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
            <button onClick={save} disabled={saving} className="text-xs bg-brand-500 hover:bg-brand-600 text-white px-3 py-1.5 rounded-lg disabled:opacity-50 transition-colors">
              {saving ? '…' : 'Save'}
            </button>
            <button onClick={() => setEditing(false)} className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1.5">Cancel</button>
          </>
        ) : (
          <>
            <span className={`text-xs font-mono flex-1 ${hasValue ? 'text-gray-600 dark:text-gray-400' : 'text-gray-300 dark:text-gray-600 italic'}`}>
              {hasValue ? current.masked : 'Not configured'}
            </span>
            <button onClick={async () => {
              setEditing(true)
              if (hasValue) {
                try {
                  const r = await fetch('/api/env/reveal', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key: envKey }) })
                  const d = await r.json()
                  setValue(d.value || '')
                } catch { setValue('') }
              } else { setValue('') }
            }}
              className="text-xs text-brand-500 hover:text-brand-600 px-2 py-1 rounded-lg hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors">
              {hasValue ? 'Change' : 'Set up'}
            </button>
          </>
        )}
        {msg && <span className="text-xs text-gray-400">{msg}</span>}
      </div>
    </div>
  )
}

function ConnectionsTab() {
  const [entries, setEntries] = useState([])
  const [setupStatus, setSetupStatus] = useState(null)
  const [ollamaOk, setOllamaOk] = useState(false)

  useEffect(() => {
    fetch('/api/env').then(r => r.json()).then(d => setEntries(d.entries || [])).catch(() => {})
    fetch('/api/setup/status').then(r => r.json()).then(setSetupStatus).catch(() => {})
    fetch('/api/status').then(r => r.json()).then(d => setOllamaOk(d.ollama === true)).catch(() => {})
  }, [])

  const saveEnvKey = async (key, value) => {
    const resp = await fetch('/api/env/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key, value }),
    })
    if (!resp.ok) {
      throw new Error('Save failed — edit config/.env manually and restart')
    }
    // Refresh entries
    const r = await fetch('/api/env')
    const d = await r.json()
    setEntries(d.entries || [])
  }

  const hasKey = (key) => {
    const e = entries.find(x => x.key === key)
    return e && e.value && !e.value.startsWith('#') && e.value.length > 3
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-2">
        <div>
          <p className="text-sm text-gray-500">Manage your integrations and API keys. Changes require a service restart.</p>
        </div>
        <Link to="/setup" className="flex items-center gap-1.5 text-xs bg-brand-500 hover:bg-brand-600 text-white px-3 py-1.5 rounded-lg transition-colors">
          <Settings2 size={12} /> Setup Wizard
        </Link>
      </div>

      {/* Telegram — Required */}
      <ConnectionCard
        icon={MessageSquare}
        iconColor="bg-[#26A5E4]"
        title="Telegram"
        description="Bot token + owner ID — required for KOVO to work"
        configured={hasKey('TELEGRAM_BOT_TOKEN')}
      >
        <div className="bg-brand-50 dark:bg-brand-900/10 border border-brand-200 dark:border-brand-800/30 rounded-lg p-3 space-y-1 text-xs text-gray-600 dark:text-gray-400">
          <p><strong>Bot Token:</strong> Message <ExtLink href="https://t.me/BotFather">@BotFather</ExtLink> → <code className="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded">/newbot</code></p>
          <p><strong>User ID:</strong> Message <ExtLink href="https://t.me/userinfobot">@userinfobot</ExtLink> to get your numeric ID</p>
        </div>
        <EnvField label="Bot Token" envKey="TELEGRAM_BOT_TOKEN" entries={entries} onSave={saveEnvKey} />
        <EnvField label="Owner ID" envKey="OWNER_TELEGRAM_ID" entries={entries} onSave={saveEnvKey} />
      </ConnectionCard>

      {/* Voice Calls — Optional */}
      <ConnectionCard
        icon={Phone}
        iconColor="bg-amber-500"
        title="Voice Calls"
        description="Real Telegram voice calls for urgent alerts — needs a second SIM"
        configured={hasKey('TELEGRAM_API_ID') && hasKey('TELEGRAM_API_HASH')}
      >
        <div className="bg-brand-50 dark:bg-brand-900/10 border border-brand-200 dark:border-brand-800/30 rounded-lg p-3 space-y-1 text-xs text-gray-600 dark:text-gray-400">
          <p>Requires a <strong>second phone number</strong> for the caller account.</p>
          <p>Log in at <ExtLink href="https://my.telegram.org">my.telegram.org</ExtLink> with the second number → API development tools</p>
          <p>After saving, use <code className="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded">/reauth_caller +PHONE</code> in Telegram to authenticate.</p>
        </div>
        <EnvField label="API ID" envKey="TELEGRAM_API_ID" entries={entries} onSave={saveEnvKey} />
        <EnvField label="API Hash" envKey="TELEGRAM_API_HASH" entries={entries} onSave={saveEnvKey} />
      </ConnectionCard>

      {/* Google — Optional */}
      <ConnectionCard
        icon={Cloud}
        iconColor="bg-blue-500"
        title="Google Workspace"
        description="Docs, Drive, Gmail, Calendar, Sheets"
        configured={setupStatus?.services?.google_calendar}
      >
        <div className="bg-brand-50 dark:bg-brand-900/10 border border-brand-200 dark:border-brand-800/30 rounded-lg p-3 space-y-1 text-xs text-gray-600 dark:text-gray-400">
          <p><strong>1.</strong> Go to <ExtLink href="https://console.cloud.google.com/">Google Cloud Console</ExtLink> → create/select a project</p>
          <p><strong>2.</strong> Enable APIs: <ExtLink href="https://console.cloud.google.com/apis/library/drive.googleapis.com">Drive</ExtLink>, <ExtLink href="https://console.cloud.google.com/apis/library/docs.googleapis.com">Docs</ExtLink>, <ExtLink href="https://console.cloud.google.com/apis/library/gmail.googleapis.com">Gmail</ExtLink>, <ExtLink href="https://console.cloud.google.com/apis/library/calendar-json.googleapis.com">Calendar</ExtLink>, <ExtLink href="https://console.cloud.google.com/apis/library/sheets.googleapis.com">Sheets</ExtLink></p>
          <p><strong>3.</strong> <ExtLink href="https://console.cloud.google.com/apis/credentials">Credentials</ExtLink> → Create OAuth 2.0 Client ID (Desktop app) → Download JSON</p>
          <p><strong>4.</strong> Upload JSON via the <Link to="/setup" className="text-brand-500 underline">Setup Wizard</Link>, then run <code className="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded">/auth_google</code> in Telegram</p>
        </div>
        <StatusDot ok={setupStatus?.services?.google_calendar} label={setupStatus?.services?.google_calendar ? 'Credentials JSON uploaded' : 'Not configured — use Setup Wizard to upload JSON'} />
      </ConnectionCard>

      {/* Groq — Optional */}
      <ConnectionCard
        icon={Mic}
        iconColor="bg-purple-500"
        title="Groq Transcription"
        description="Fast cloud voice-to-text — free tier (14,400 req/day)"
        configured={hasKey('GROQ_API_KEY')}
      >
        <div className="bg-brand-50 dark:bg-brand-900/10 border border-brand-200 dark:border-brand-800/30 rounded-lg p-3 space-y-1 text-xs text-gray-600 dark:text-gray-400">
          <p>Go to <ExtLink href="https://console.groq.com/keys">console.groq.com/keys</ExtLink> → sign up free → Create API Key</p>
          <p>Uses <code className="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded">whisper-large-v3-turbo</code> model. Falls back to local Whisper if not set.</p>
        </div>
        <EnvField label="Groq API Key" envKey="GROQ_API_KEY" hint="Starts with gsk_" entries={entries} onSave={saveEnvKey} />
      </ConnectionCard>

      {/* GitHub — Optional */}
      <ConnectionCard
        icon={Github}
        iconColor="bg-gray-800 dark:bg-gray-600"
        title="GitHub"
        description="Repo management, issues, PRs — used by update checker"
        configured={hasKey('GITHUB_TOKEN')}
      >
        <div className="bg-brand-50 dark:bg-brand-900/10 border border-brand-200 dark:border-brand-800/30 rounded-lg p-3 space-y-1 text-xs text-gray-600 dark:text-gray-400">
          <p>Go to <ExtLink href="https://github.com/settings/tokens?type=beta">GitHub Settings → Fine-grained tokens</ExtLink></p>
          <p>Create a token with <strong>Contents</strong> (read) permission for your repos.</p>
        </div>
        <EnvField label="GitHub Token" envKey="GITHUB_TOKEN" hint="ghp_ or github_pat_" entries={entries} onSave={saveEnvKey} />
      </ConnectionCard>

      {/* Ollama — Optional */}
      <ConnectionCard
        icon={Database}
        iconColor="bg-gray-500"
        title="Ollama (Local LLM)"
        description="Optional local LLM for heartbeats and cheap tasks"
        configured={ollamaOk}
        testFn={async () => { const r = await fetch('/api/ollama/test', { method: 'POST' }); return r.json() }}
        testLabel="Test"
      >
        <p className="text-xs text-gray-400">Ollama settings are managed in the <span className="text-brand-500">Configuration</span> tab.</p>
      </ConnectionCard>

      {/* Restart reminder */}
      <div className="flex items-center justify-between bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800/30 rounded-xl px-4 py-3">
        <p className="text-xs text-amber-700 dark:text-amber-400">After changing credentials, restart the service to apply.</p>
        <button onClick={async () => { try { await fetch('/api/service/restart', { method: 'POST' }) } catch {} }}
          className="flex items-center gap-1.5 text-xs bg-amber-500 hover:bg-amber-600 text-white px-3 py-1.5 rounded-lg transition-colors">
          <RefreshCw size={12} /> Restart
        </button>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════
// TAB 2: CONFIGURATION (from StructuredConfig)
// ═══════════════════════════════════════════════════════════════
function ConfigTab() {
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
                const val = kvMatch[2].replace(/\s+#.*$/, '').trim().replace(/^["']|["']$/g, '')
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

  const save = async (andRestart = false) => {
    setSaving(true)
    setMsg('')
    try {
      const r = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: raw }),
      })
      if (r.ok) {
        if (andRestart) {
          try { await fetch('/api/service/restart', { method: 'POST' }) } catch {}
          setMsg('Saved & restarting…')
        } else {
          setMsg('Saved — restart to apply')
        }
      } else {
        const d = await r.json()
        setMsg(d.detail || 'Save failed')
      }
    } catch (e) { setMsg(e.message) }
    setSaving(false)
  }

  if (loadError) return <p className="text-sm text-red-500">Failed to load: {loadError}</p>
  if (!config) return <div className="animate-pulse h-40 bg-gray-100 dark:bg-gray-800 rounded-lg" />

  return (
    <div className="space-y-4">
      {/* General */}
      <Section title="General">
        <FieldRow label="Timezone" hint="Logs, schedules, memory timestamps">
          <select className={selectCls} value={config.kovo?.timezone || 'Asia/Dubai'} onChange={e => updateField('kovo', 'timezone', e.target.value)}>
            {['Asia/Dubai', 'Asia/Riyadh', 'Asia/Kuwait', 'Asia/Qatar', 'Asia/Muscat', 'Asia/Kolkata', 'Asia/Karachi', 'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Singapore',
              'Europe/London', 'Europe/Berlin', 'Europe/Paris', 'Europe/Moscow', 'Europe/Istanbul',
              'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles', 'Australia/Sydney', 'UTC'
            ].map(tz => <option key={tz} value={tz}>{tz}</option>)}
          </select>
        </FieldRow>
      </Section>

      {/* Claude */}
      <Section title="Claude">
        <FieldRow label="Default model">
          <select className={selectCls} value={config.claude?.default_model || 'sonnet'} onChange={e => updateField('claude', 'default_model', e.target.value)}>
            <option value="sonnet">Sonnet (fast, balanced)</option>
            <option value="opus">Opus (deep reasoning)</option>
            <option value="haiku">Haiku (quick, cheap)</option>
          </select>
        </FieldRow>
        <FieldRow label="Timeout" hint="Seconds before CLI times out">
          <input type="number" className={inputCls} value={config.claude?.timeout || '300'} onChange={e => updateField('claude', 'timeout', e.target.value)} />
        </FieldRow>
      </Section>

      {/* Ollama */}
      <Section title="Ollama (Local LLM)">
        <FieldRow label="Enabled">
          <select className={selectCls} value={config.ollama?.enabled || 'false'} onChange={e => updateField('ollama', 'enabled', e.target.value)}>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </FieldRow>
        <FieldRow label="URL" hint="Ollama API endpoint">
          <input className={inputCls} value={config.ollama?.url || ''} onChange={e => updateField('ollama', 'url', e.target.value)} />
        </FieldRow>
        <FieldRow label="Model" hint="Default model for cheap tasks">
          <input className={inputCls} value={config.ollama?.default_model || ''} onChange={e => updateField('ollama', 'default_model', e.target.value)} />
        </FieldRow>
      </Section>

      {/* Heartbeat Schedules */}
      <Section title="Heartbeat Schedules" defaultOpen={false}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {[
            { job: 'Archive logs', schedule: 'Daily 3:00 AM', desc: 'Archive daily logs older than 30 days' },
            { job: 'Auto-extract', schedule: 'Daily 11:00 PM', desc: 'Extract learnings → MEMORY.md + SQLite' },
            { job: 'Memory consolidation', schedule: 'Sunday 3:30 AM', desc: 'Archive learnings if > 500 lines' },
            { job: 'Version check', schedule: 'Daily 10:00 AM', desc: 'Check GitHub for new releases' },
            { job: 'Reminders', schedule: 'Every 60 seconds', desc: 'Fire due reminders via message/call' },
          ].map(({ job, schedule, desc }) => (
            <div key={job} className="bg-gray-50 dark:bg-gray-800 rounded-lg p-2.5">
              <p className="text-sm text-gray-700 dark:text-gray-300 font-medium">{job}</p>
              <p className="text-xs text-brand-500">{schedule}</p>
              <p className="text-xs text-gray-400 mt-0.5">{desc}</p>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-400 italic">All schedules use the configured timezone. Manual triggers on the Heartbeat page.</p>
      </Section>

      {/* Transcription */}
      <Section title="Transcription" defaultOpen={false}>
        <FieldRow label="Whisper model" hint="Local fallback model">
          <select className={selectCls} value={config.transcription?.whisper_model || 'base'} onChange={e => updateField('transcription', 'whisper_model', e.target.value)}>
            <option value="base">base (fast, ~150MB)</option>
            <option value="small">small (balanced, ~460MB)</option>
            <option value="medium">medium (accurate, ~1.5GB)</option>
            <option value="large">large (best, ~3GB)</option>
          </select>
        </FieldRow>
        <p className="text-xs text-gray-400">Primary: Groq API (set in Connections tab). Fallback: local Whisper.</p>
      </Section>

      {/* Voice / TTS */}
      <Section title="Voice / TTS" defaultOpen={false}>
        <FieldRow label="TTS backend">
          <select className={selectCls} value={config.telegram_call?.tts?.backend || config.telegram_call?.backend || 'edge-tts'} onChange={e => updateField('telegram_call', 'backend', e.target.value)}>
            <option value="edge-tts">edge-tts (free, Microsoft Azure)</option>
            <option value="piper">piper (local, fast)</option>
            <option value="elevenlabs">ElevenLabs (premium)</option>
          </select>
        </FieldRow>
        <FieldRow label="Voice name">
          <input className={inputCls} value={config.telegram_call?.tts?.voice || config.telegram_call?.voice || 'en-US-AvaMultilingualNeural'} onChange={e => updateField('telegram_call', 'voice', e.target.value)} />
        </FieldRow>
      </Section>

      {/* Security Audit */}
      <Section title="Security Audit" defaultOpen={false}>
        <FieldRow label="Enabled">
          <select className={selectCls} value={config.security_audit?.enabled || 'true'} onChange={e => updateField('security_audit', 'enabled', e.target.value)}>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </FieldRow>
        <FieldRow label="Schedule" hint="Day + time (e.g. sun 07:00)">
          <input className={inputCls} value={config.security_audit?.schedule || 'sun 07:00'} onChange={e => updateField('security_audit', 'schedule', e.target.value)} />
        </FieldRow>
      </Section>

      {/* Gateway */}
      <Section title="Gateway" defaultOpen={false}>
        <FieldRow label="Port">
          <input type="number" className={inputCls} value={config.gateway?.port || '8080'} onChange={e => updateField('gateway', 'port', e.target.value)} />
        </FieldRow>
      </Section>

      {/* Save buttons */}
      <div className="flex items-center gap-3 pt-2 border-t border-gray-100 dark:border-gray-800">
        <button onClick={() => save(false)} disabled={saving}
          className="flex items-center gap-2 text-sm bg-brand-500 hover:bg-brand-600 text-white px-4 py-1.5 rounded-lg disabled:opacity-40 transition-colors">
          <Save size={14} /> {saving ? 'Saving…' : 'Save'}
        </button>
        <button onClick={() => save(true)} disabled={saving}
          className="flex items-center gap-2 text-sm bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600 px-4 py-1.5 rounded-lg disabled:opacity-40 transition-colors">
          <RefreshCw size={14} /> Save & Restart
        </button>
        {msg && <span className="text-xs text-gray-500 flex-1">{msg}</span>}
        <button onClick={() => setShowRaw(!showRaw)}
          className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 ml-auto transition-colors">
          {showRaw ? 'Hide raw YAML' : 'Edit raw YAML'}
        </button>
      </div>

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

// ═══════════════════════════════════════════════════════════════
// TAB 3: BACKUP (kept from BackupManager)
// ═══════════════════════════════════════════════════════════════
function BackupTab() {
  const [backups, setBackups] = useState(null)
  const [running, setRunning] = useState(false)
  const [runningTier, setRunningTier] = useState('')
  const [uploading, setUploading] = useState(false)
  const [msg, setMsg] = useState('')
  const [restoreResult, setRestoreResult] = useState(null)
  const fileInputRef = useRef(null)

  const loadBackups = () =>
    fetch('/api/backup/list').then(r => r.json()).then(setBackups).catch(() => setBackups({ backups: [], total_size: '0B' }))

  useEffect(() => { loadBackups() }, [])

  const runBackup = async (tier) => {
    setRunning(true); setRunningTier(tier); setMsg('')
    try {
      const r = await fetch(`/api/backup?tier=${tier}`, { method: 'POST' })
      const d = await r.json()
      setMsg(d.ok ? `${tier === 'full' ? 'Full' : 'Core'} backup created (${d.size || '?'})` : d.error || 'Failed')
      loadBackups()
    } catch (e) { setMsg('Failed: ' + e.message) }
    setRunning(false); setRunningTier('')
  }

  const deleteBackup = async (filename) => {
    if (!confirm(`Delete ${filename}?`)) return
    try { await fetch(`/api/backup/${filename}`, { method: 'DELETE' }); loadBackups() } catch {}
  }

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.name.endsWith('.tar.gz') && !file.name.endsWith('.tgz')) {
      setRestoreResult({ ok: false, output: 'Only .tar.gz files accepted.' }); return
    }
    if (!confirm(`Restore from "${file.name}"?`)) { fileInputRef.current.value = ''; return }
    setUploading(true); setRestoreResult(null); setMsg('')
    try {
      const formData = new FormData(); formData.append('file', file)
      const r = await fetch('/api/backup/restore', { method: 'POST', body: formData })
      const d = await r.json(); setRestoreResult(d); if (d.ok) loadBackups()
    } catch (e) { setRestoreResult({ ok: false, output: `Upload failed: ${e.message}` }) }
    setUploading(false); fileInputRef.current.value = ''
  }



  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <button onClick={() => runBackup('core')} disabled={running}
          className="flex items-center gap-2 text-sm bg-brand-500 hover:bg-brand-600 text-white px-4 py-1.5 rounded-lg disabled:opacity-50 transition-colors">
          <Archive size={14} /> {running && runningTier === 'core' ? 'Backing up…' : 'Core Backup'}
        </button>
        <button onClick={() => runBackup('full')} disabled={running}
          className="flex items-center gap-2 text-sm bg-purple-500 hover:bg-purple-600 text-white px-4 py-1.5 rounded-lg disabled:opacity-50 transition-colors">
          <Archive size={14} /> {running && runningTier === 'full' ? 'Backing up…' : 'Full Backup'}
        </button>
        <input ref={fileInputRef} type="file" accept=".tar.gz,.tgz" className="hidden" onChange={handleUpload} />
        <button onClick={() => fileInputRef.current?.click()} disabled={uploading}
          className="flex items-center gap-2 text-sm bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600 px-4 py-1.5 rounded-lg disabled:opacity-50 transition-colors">
          {uploading ? <><Loader2 size={14} className="animate-spin" /> Restoring...</> : <><Upload size={14} /> Restore from File</>}
        </button>
        {msg && <span className="text-xs text-gray-500">{msg}</span>}
      </div>
      <p className="text-[11px] text-gray-400">Core = config + brain + packages (~1-5 MB) · Full = core + media (~1-10 GB)</p>

      {restoreResult && (
        <div className={`rounded-lg p-3 text-sm ${restoreResult.ok ? 'bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700/40' : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700/40'}`}>
          <p className={`text-xs font-semibold mb-1 ${restoreResult.ok ? 'text-emerald-700 dark:text-emerald-400' : 'text-red-700 dark:text-red-400'}`}>
            {restoreResult.ok ? 'Restore Complete — service restarting...' : 'Restore Failed'}
          </p>
          {restoreResult.output && <pre className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono max-h-40 overflow-y-auto">{restoreResult.output}</pre>}
        </div>
      )}

      {backups && (
        <div className="space-y-1.5">
          <p className="text-xs text-gray-400">{backups.backups?.length || 0} backups · {backups.total_size || '0B'} total</p>
          {backups.backups?.length > 0 && (
            <div className="max-h-72 overflow-y-auto space-y-1">
              {backups.backups.map(b => (
                <div key={b.name} className="flex items-center justify-between text-sm p-2.5 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700">
                  <div className="flex items-center gap-2 min-w-0">
                    <Archive size={14} className="text-gray-400 flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="text-xs text-gray-700 dark:text-gray-300 font-mono truncate">{b.name}</p>
                      {b.date && <p className="text-[10px] text-gray-400">{new Date(b.date).toLocaleString()}</p>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-xs text-gray-400">{b.size}</span>
                    <a href={`/api/backup/download/${b.name}`} download className="text-xs text-brand-500 hover:text-brand-600 px-2 py-1 rounded hover:bg-brand-50 dark:hover:bg-brand-900/20">
                      <Download size={12} />
                    </a>
                    <button onClick={() => deleteBackup(b.name)} className="text-gray-400 hover:text-red-500 p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20">
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          {(!backups.backups || backups.backups.length === 0) && <p className="text-xs text-gray-400 italic">No backups yet.</p>}
        </div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════
// TAB 4: SYSTEM
// ═══════════════════════════════════════════════════════════════
function SystemTab() {
  const { theme, toggle } = useTheme()
  const [serviceStatus, setServiceStatus] = useState(null)
  const [restarting, setRestarting] = useState(false)
  const [restartMsg, setRestartMsg] = useState('')
  const [info, setInfo] = useState(null)
  const [entries, setEntries] = useState([])
  const [revealed, setRevealed] = useState({})

  useEffect(() => {
    fetch('/api/service/status').then(r => r.json()).then(setServiceStatus).catch(() => {})
    fetch('/api/system/info').then(r => r.json()).then(setInfo).catch(() => {})
    fetch('/api/env').then(r => r.json()).then(d => setEntries(d.entries || [])).catch(() => {})
    const id = setInterval(() => fetch('/api/service/status').then(r => r.json()).then(setServiceStatus).catch(() => {}), 10000)
    return () => clearInterval(id)
  }, [])

  const restart = async () => {
    setRestarting(true); setRestartMsg('')
    try {
      const r = await fetch('/api/service/restart', { method: 'POST' })
      const d = await r.json()
      setRestartMsg(d.restarted ? 'Restarted' : d.error || 'Failed')
    } catch (e) { setRestartMsg(e.message) }
    setRestarting(false)
    setTimeout(() => fetch('/api/service/status').then(r => r.json()).then(setServiceStatus).catch(() => {}), 2000)
  }

  return (
    <div className="space-y-4">
      {/* Updates */}
      <Section title="Updates">
        <UpdateChecker />
      </Section>

      {/* Service */}
      <Section title="Service">
        <div className="flex items-center gap-3">
          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${serviceStatus?.active ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-gray-700 dark:text-gray-300">
            {serviceStatus ? `${serviceStatus.service} — ${serviceStatus.state}` : 'Checking…'}
          </span>
          <button onClick={restart} disabled={restarting}
            className="flex items-center gap-2 text-sm bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-700 px-3 py-1 rounded-lg disabled:opacity-50 transition-colors ml-auto">
            <RefreshCw size={14} className={restarting ? 'animate-spin' : ''} />
            {restarting ? 'Restarting…' : 'Restart'}
          </button>
          {restartMsg && <span className="text-xs text-gray-500">{restartMsg}</span>}
        </div>
      </Section>

      {/* System Info */}
      <Section title="System Info" defaultOpen={false}>
        {info ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: 'Python', value: info.python },
              { label: 'Node', value: info.node },
              { label: 'Disk', value: info.disk_used_gb != null ? `${info.disk_used_gb}/${info.disk_total_gb} GB` : '—' },
              { label: 'RAM', value: info.ram_used_gb != null ? `${info.ram_used_gb}/${info.ram_total_gb} GB` : '—' },
            ].map(({ label, value }) => (
              <div key={label} className="bg-gray-50 dark:bg-gray-800 rounded-lg p-2.5">
                <p className="text-xs text-gray-400 mb-0.5">{label}</p>
                <p className="text-sm text-gray-700 dark:text-gray-200 font-mono">{value ?? '—'}</p>
              </div>
            ))}
          </div>
        ) : <div className="animate-pulse h-14 bg-gray-100 dark:bg-gray-800 rounded-lg" />}
      </Section>

      {/* Environment (.env) */}
      <Section title="Environment (.env)" defaultOpen={false}>
        <div className="space-y-1 font-mono text-sm">
          {entries.length === 0 && <p className="text-gray-400 italic text-sm">No .env file found.</p>}
          {entries.map((e, i) => {
            if (e.type === 'comment') return <div key={i} className="text-gray-400 dark:text-gray-600">{e.raw || ''}</div>
            return (
              <div key={i} className="flex items-center gap-2">
                <span className="text-blue-600 dark:text-blue-400 flex-shrink-0">{e.key}</span>
                <span className="text-gray-400">=</span>
                <span className="text-yellow-600 dark:text-yellow-300 flex-1">{revealed[e.key] || e.masked}</span>
                <button onClick={async () => {
                  if (revealed[e.key]) {
                    setRevealed(prev => ({ ...prev, [e.key]: null }))
                  } else {
                    try {
                      const r = await fetch('/api/env/reveal', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key: e.key }) })
                      const d = await r.json()
                      setRevealed(prev => ({ ...prev, [e.key]: d.value || '(empty)' }))
                    } catch { setRevealed(prev => ({ ...prev, [e.key]: '(error)' })) }
                  }
                }} className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 px-1">
                  {revealed[e.key] ? 'hide' : 'show'}
                </button>
              </div>
            )
          })}
        </div>
      </Section>

      {/* Appearance */}
      <Section title="Appearance" defaultOpen={false}>
        <div className="flex items-center gap-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">Theme: <strong className="text-gray-900 dark:text-white capitalize">{theme}</strong></p>
          <button onClick={toggle}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm transition-colors">
            {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
            Switch to {theme === 'dark' ? 'light' : 'dark'}
          </button>
        </div>
      </Section>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════
// MAIN SETTINGS PAGE
// ═══════════════════════════════════════════════════════════════
export default function Settings() {
  const [tab, setTab] = useState('connections')
  const [version, setVersion] = useState('')

  useEffect(() => { fetch('/api/status').then(r => r.json()).then(d => setVersion(d.version || '')).catch(() => {}) }, [])

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
        {version && <span className="text-sm text-gray-400 font-mono">v{version}</span>}
      </div>

      <TabBar active={tab} onChange={setTab} />

      {tab === 'connections' && <ConnectionsTab />}
      {tab === 'config' && <ConfigTab />}
      {tab === 'backup' && <BackupTab />}
      {tab === 'system' && <SystemTab />}
    </div>
  )
}
