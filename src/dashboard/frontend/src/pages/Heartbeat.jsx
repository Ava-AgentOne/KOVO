import { useState, useEffect } from 'react'
import { Zap, BarChart2, HeartPulse, HeartCrack, Clock, Brain, Archive, GitBranch, Bell, Loader2, Plus, X, Phone, MessageSquare, Cloud } from 'lucide-react'
import PageHeader from '../components/PageHeader'

const inputCls = 'w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-brand-500'

const DELIVERY_BADGES = {
  message: { Icon: MessageSquare, cls: 'bg-sky-500/10 text-sky-600 dark:text-sky-400' },
  call:    { Icon: Phone,         cls: 'bg-amber-500/10 text-amber-600 dark:text-amber-400' },
  both:    { Icon: Bell,          cls: 'bg-rose-500/10 text-rose-600 dark:text-rose-400' },
}

function fmtDue(iso) {
  try {
    const d = new Date(iso)
    const sameDay = d.toDateString() === new Date().toDateString()
    const time = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
    return sameDay ? `Today ${time}`
      : `${d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })}, ${time}`
  } catch { return iso }
}

// v2.1 Step 5 (D): full reminders management — list, create, cancel
function RemindersManager() {
  const [reminders, setReminders] = useState([])
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ message: '', due_at: '', delivery: 'message' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const load = () =>
    fetch('/api/reminders').then(r => r.json())
      .then(d => setReminders(d.reminders || [])).catch(() => {})

  useEffect(() => {
    load()
    const id = setInterval(load, 30000)
    return () => clearInterval(id)
  }, [])

  const create = async () => {
    if (!form.message.trim() || !form.due_at) return
    setSaving(true); setError('')
    try {
      const r = await fetch('/api/reminders', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const d = await r.json()
      if (d.created) {
        setForm({ message: '', due_at: '', delivery: 'message' })
        setShowAdd(false); load()
      } else { setError(d.detail || 'Create failed') }
    } catch (e) { setError(e.message) }
    setSaving(false)
  }

  const cancel = async (id) => {
    try { await fetch(`/api/reminders/${id}`, { method: 'DELETE' }) } catch {}
    load()
  }

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Bell size={16} className="text-brand-500" />
          <h2 className="text-xs font-bold text-gray-700 dark:text-gray-200 uppercase tracking-wide">Reminders</h2>
          <span className="text-xs text-gray-400">{reminders.length} upcoming</span>
        </div>
        <button onClick={() => setShowAdd(!showAdd)}
          className="flex items-center gap-1.5 text-xs bg-brand-500 hover:bg-brand-600 text-white px-3 py-1.5 rounded-lg transition-colors">
          <Plus size={13} /> New Reminder
        </button>
      </div>

      {showAdd && (
        <div className="mb-3 p-4 bg-gray-50 dark:bg-gray-800/60 rounded-lg space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="md:col-span-1">
              <label className="text-xs text-gray-500 block mb-1">Remind me to…</label>
              <input placeholder="water the plants" value={form.message}
                onChange={e => setForm(f => ({...f, message: e.target.value}))} className={inputCls} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">When</label>
              <input type="datetime-local" value={form.due_at}
                onChange={e => setForm(f => ({...f, due_at: e.target.value}))} className={inputCls} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Delivery</label>
              <select value={form.delivery} onChange={e => setForm(f => ({...f, delivery: e.target.value}))} className={inputCls}>
                <option value="message">Message</option>
                <option value="call">Voice call</option>
                <option value="both">Message + call</option>
              </select>
            </div>
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
          <div className="flex gap-2">
            <button onClick={create} disabled={saving || !form.message.trim() || !form.due_at}
              className="bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-white px-4 py-2 rounded-lg text-sm transition-colors">
              {saving ? 'Saving…' : 'Create Reminder'}
            </button>
            <button onClick={() => setShowAdd(false)} className="text-sm text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 px-4 py-2">Cancel</button>
          </div>
        </div>
      )}

      {reminders.length === 0 ? (
        <p className="text-sm text-gray-400">
          Nothing scheduled. Create one here, or just tell Kovo — “remind me to call mom at 6pm”.
        </p>
      ) : (
        <div className="space-y-2">
          {reminders.map(r => {
            const badge = DELIVERY_BADGES[r.delivery] || DELIVERY_BADGES.message
            const BadgeIcon = badge.Icon
            return (
              <div key={r.id} className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg group">
                <span className={`flex items-center gap-1 text-[11px] px-2 py-1 rounded-full flex-shrink-0 ${badge.cls}`}>
                  <BadgeIcon size={11} /> {r.delivery}
                </span>
                <p className="text-sm text-gray-800 dark:text-gray-200 flex-1 min-w-0 truncate">{r.message}</p>
                <span className="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0 font-mono">{fmtDue(r.due_at)}</span>
                <button onClick={() => cancel(r.id)} title="Cancel reminder"
                  className="text-gray-300 hover:text-red-500 transition-colors p-1 flex-shrink-0">
                  <X size={14} />
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

const JOB_META = {
  auto_extract:                { icon: Brain,     desc: 'Extract learnings from daily logs → MEMORY.md',     color: 'text-brand-500' },
  archive_logs:                { icon: Archive,   desc: 'Archive daily logs older than 30 days',              color: 'text-gray-500' },
  version_check:               { icon: GitBranch, desc: 'Check GitHub for new KOVO releases',                 color: 'text-emerald-500' },
  weekly_memory_consolidation: { icon: Archive,   desc: 'Archive Learnings if >500 lines (never touches Pinned)', color: 'text-amber-500' },
  check_reminders:             { icon: Bell,      desc: 'Fire due reminders via Telegram message or call',    color: 'text-blue-500' },
  offsite_backup:              { icon: Cloud,     desc: 'Upload a fresh backup to Google Drive (retention-pruned)', color: 'text-teal-500' },
  check_routines:              { icon: Clock,     desc: 'Run due routines — recurring autonomous tasks', color: 'text-indigo-500' },
}

function renderReport(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) =>
      `<pre class="bg-gray-100 dark:bg-gray-800 rounded-lg px-3 py-2 my-2 text-xs font-mono overflow-x-auto whitespace-pre border border-gray-200 dark:border-gray-700"><code>${code.trim()}</code></pre>`)
    .replace(/`([^`]+)`/g, '<code class="bg-gray-200 dark:bg-gray-700 px-1 py-0.5 rounded text-xs font-mono">$1</code>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.+)$/gm, '<div class="flex gap-2 ml-2 my-0.5"><span class="text-gray-400">•</span><span>$1</span></div>')
    .replace(/✅/g, '<span class="text-emerald-500">✅</span>')
    .replace(/❌/g, '<span class="text-red-500">❌</span>')
    .replace(/⚠️/g, '<span class="text-amber-500">⚠️</span>')
    .replace(/\n/g, '<br/>')
    .replace(/<br\/>(<pre|<\/pre>|<div)/g, '$1')
    .replace(/(<\/pre>|<\/div>)<br\/>/g, '$1')
}

function formatNextRun(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = d - now
  if (diffMs < 0) return 'overdue'
  const diffH = Math.floor(diffMs / 3600000)
  const diffM = Math.floor((diffMs % 3600000) / 60000)
  if (diffH > 24) {
    const days = Math.floor(diffH / 24)
    return `in ${days}d — ${d.toLocaleDateString([], { weekday: 'short' })} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
  }
  if (diffH > 0) return `in ${diffH}h ${diffM}m — ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
  return `in ${diffM}m`
}

export default function Heartbeat() {
  const [status, setStatus] = useState(null)
  const [report, setReport] = useState('')
  const [loading, setLoading] = useState(false)
  const [checkType, setCheckType] = useState('')

  const loadStatus = () =>
    fetch('/api/heartbeat/status').then(r => r.json()).then(setStatus).catch(console.error)

  useEffect(() => {
    loadStatus()
    const id = setInterval(loadStatus, 30000)
    return () => clearInterval(id)
  }, [])

  const runCheck = async (endpoint, type) => {
    setLoading(true)
    setCheckType(type)
    setReport('')
    try {
      const r = await fetch(endpoint, { method: 'POST' })
      const d = await r.json()
      setReport(d.report || JSON.stringify(d, null, 2))
    } catch (e) {
      setReport('Error: ' + e.message)
    }
    setLoading(false)
  }

  const running = status?.running
  const jobs = status?.jobs || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <PageHeader title="Heartbeat" subtitle="Scheduled checks, reports, and alerts" icon={HeartPulse} accent="rose" />
        <div className="flex items-center gap-2">
          <button
            onClick={() => runCheck('/api/heartbeat/check', 'quick')}
            disabled={loading}
            className="flex items-center gap-1.5 text-sm bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-lg disabled:opacity-50 transition-colors"
          >
            {loading && checkType === 'quick' ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />}
            Quick Check
          </button>
          <button
            onClick={() => runCheck('/api/heartbeat/full', 'full')}
            disabled={loading}
            className="flex items-center gap-1.5 text-sm bg-brand-500 hover:bg-brand-600 text-white px-3 py-1.5 rounded-lg disabled:opacity-50 transition-colors"
          >
            {loading && checkType === 'full' ? <Loader2 size={13} className="animate-spin" /> : <BarChart2 size={13} />}
            Full Report
          </button>
        </div>
      </div>

      {/* Scheduler status + jobs */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
        <div className="flex items-center gap-3 mb-4">
          {running ? (
            <HeartPulse size={24} className="text-red-500 animate-pulse" />
          ) : (
            <HeartCrack size={24} className="text-gray-400" />
          )}
          <div>
            <p className="font-semibold text-gray-900 dark:text-white">
              Scheduler {running ? 'running' : 'stopped'}
            </p>
            <p className="text-xs text-gray-500">{jobs.length} cron jobs + reminder checker (every 60s)</p>
          </div>
        </div>

        <div className="space-y-2">
          {jobs.map(job => {
            const meta = JOB_META[job.id] || { icon: Clock, desc: job.id, color: 'text-gray-400' }
            const Icon = meta.icon
            return (
              <div key={job.id} className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <Icon size={16} className={`flex-shrink-0 ${meta.color}`} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{job.id.replace(/_/g, ' ')}</p>
                  <p className="text-xs text-gray-400">{meta.desc}</p>
                </div>
                <span className="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0 font-mono">
                  {formatNextRun(job.next_run)}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Reminders management (v2.1) */}
      <RemindersManager />

      {/* Report output */}
      {(loading || report) && (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
          <h2 className="text-xs font-bold text-gray-700 dark:text-gray-200 uppercase tracking-wide mb-3">
            {checkType === 'quick' ? 'Quick Check' : 'Full Report'}
          </h2>
          {loading ? (
            <div className="flex items-center gap-2 text-gray-400 text-sm">
              <Loader2 size={14} className="animate-spin" /> Running system checks…
            </div>
          ) : (
            <div
              className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed"
              dangerouslySetInnerHTML={{ __html: renderReport(report) }}
            />
          )}
        </div>
      )}
    </div>
  )
}
