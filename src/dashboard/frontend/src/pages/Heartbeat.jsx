import { useState, useEffect } from 'react'
import { Zap, BarChart2, HeartPulse, HeartCrack, Clock, Brain, Archive, GitBranch, Bell, Loader2 } from 'lucide-react'

const JOB_META = {
  auto_extract:                { icon: Brain,     desc: 'Extract learnings from daily logs → MEMORY.md',     color: 'text-brand-500' },
  archive_logs:                { icon: Archive,   desc: 'Archive daily logs older than 30 days',              color: 'text-gray-500' },
  version_check:               { icon: GitBranch, desc: 'Check GitHub for new KOVO releases',                 color: 'text-emerald-500' },
  weekly_memory_consolidation: { icon: Archive,   desc: 'Archive Learnings if >500 lines (never touches Pinned)', color: 'text-amber-500' },
  check_reminders:             { icon: Bell,      desc: 'Fire due reminders via Telegram message or call',    color: 'text-blue-500' },
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
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Heartbeat</h1>
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
          {/* Reminder checker — always-on interval job */}
          <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <Bell size={16} className="text-blue-500 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-800 dark:text-gray-200">check reminders</p>
              <p className="text-xs text-gray-400">Fire due reminders via Telegram message or call</p>
            </div>
            <span className="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0 font-mono">every 60s</span>
          </div>
        </div>
      </div>

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
