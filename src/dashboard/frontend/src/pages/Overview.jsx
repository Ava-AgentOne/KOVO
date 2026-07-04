import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Cpu, MemoryStick, HardDrive, Clock, Shield, MessageSquare,
  RefreshCw, Trash2, Save, RotateCcw, Settings as SettingsIcon,
  ScrollText, Bell, AlertTriangle, Phone, Image as ImageIcon,
  FileText, Plug, Send, X,
} from 'lucide-react'
import StatusCard from '../components/StatusCard'
import useApi from '../hooks/useApi'
import ConfirmModal from '../components/ConfirmModal'

// ── Mission Control (v2.1) — the Overview answers "what has Kovo been doing?"
// Live busy indicator, activity feed, sparkline metrics, reminders and
// integration-health widgets. Data endpoints: src/dashboard/routers/overview.py

function fmt12(hhmm) {
  if (!hhmm) return ''
  const [h, m] = hhmm.split(':')
  const hr = parseInt(h, 10)
  const ampm = hr >= 12 ? 'PM' : 'AM'
  const h12 = hr === 0 ? 12 : hr > 12 ? hr - 12 : hr
  return `${h12}:${m} ${ampm}`
}

function fmtDue(iso) {
  try {
    const d = new Date(iso)
    const today = new Date()
    const sameDay = d.toDateString() === today.toDateString()
    const time = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
    if (sameDay) return `Today ${time}`
    return `${d.toLocaleDateString([], { month: 'short', day: 'numeric' })}, ${time}`
  } catch { return iso }
}

const FEED_ICONS = {
  chat: MessageSquare,
  reminder: Bell,
  alert: AlertTriangle,
  call: Phone,
  image: ImageIcon,
  note: FileText,
}

function BusyPill({ busy }) {
  if (!busy) return null
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-700/40 rounded-full max-w-full">
      <span className="relative flex h-2.5 w-2.5 flex-shrink-0">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-brand-500" />
      </span>
      <span className="text-xs text-brand-600 dark:text-brand-400 font-medium truncate">
        Kovo is working on: “{busy.preview}”
      </span>
      <span className="text-[10px] text-gray-400 flex-shrink-0">via {busy.channel}</span>
    </div>
  )
}

function QuickChat() {
  const [text, setText] = useState('')
  const navigate = useNavigate()
  const go = () => {
    const msg = text.trim()
    if (!msg) return
    navigate(`/chat?q=${encodeURIComponent(msg)}`)
  }
  return (
    <div className="flex items-center gap-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-2.5 focus-within:border-brand-400 transition-colors">
      <MessageSquare size={16} className="text-brand-500 flex-shrink-0" />
      <input
        value={text}
        onChange={e => setText(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter') go() }}
        placeholder="Ask Kovo anything…"
        className="flex-1 bg-transparent text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none"
      />
      <button onClick={go} disabled={!text.trim()}
        className="flex items-center gap-1.5 text-xs bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-white px-3 py-1.5 rounded-lg transition-colors">
        <Send size={12} /> Send
      </button>
    </div>
  )
}

function ActivityFeed({ entries }) {
  if (!entries?.length) {
    return (
      <div className="text-center py-10">
        <FileText size={26} className="text-gray-300 dark:text-gray-600 mx-auto mb-2" />
        <p className="text-sm text-gray-500">All quiet — nothing logged today yet.</p>
        <p className="text-xs text-gray-400 mt-1">Chats, reminders, calls, and alerts show up here as they happen.</p>
      </div>
    )
  }
  return (
    <div className="space-y-0.5">
      {entries.map((e, i) => {
        const Icon = FEED_ICONS[e.type] || FileText
        return (
          <div key={i} className="flex items-start gap-3 py-2 border-b border-gray-100 dark:border-gray-800 last:border-0">
            <span className="text-[11px] text-brand-500 font-mono font-medium w-16 flex-shrink-0 pt-0.5">{fmt12(e.time)}</span>
            <Icon size={14} className="text-gray-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-gray-700 dark:text-gray-300 min-w-0 flex-1">{e.text}</p>
            {e.model && <span className="text-[10px] text-gray-400 flex-shrink-0">{e.model}</span>}
          </div>
        )
      })}
    </div>
  )
}

function RemindersWidget() {
  const { data, reload } = useApi('/api/reminders', 30000)
  const reminders = data?.reminders || []
  const cancel = async (id) => {
    try { await fetch(`/api/reminders/${id}`, { method: 'DELETE' }) } catch {}
    reload()
  }
  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Reminders</h2>
        <span className="text-xs text-gray-400">{reminders.length} upcoming</span>
      </div>
      {reminders.length === 0 ? (
        <p className="text-sm text-gray-400">Nothing scheduled. Ask Kovo to remind you about something.</p>
      ) : (
        <div className="space-y-2">
          {reminders.map(r => (
            <div key={r.id} className="flex items-start gap-2 p-2 bg-gray-50 dark:bg-gray-800/60 rounded-lg group">
              <Bell size={13} className="text-brand-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-800 dark:text-gray-200 truncate">{r.message}</p>
                <p className="text-[11px] text-gray-400">
                  {fmtDue(r.due_at)}
                  {r.delivery && r.delivery !== 'message' && (
                    <span className="ml-1.5 text-amber-500">· {r.delivery}</span>
                  )}
                </p>
              </div>
              <button onClick={() => cancel(r.id)} title="Cancel reminder"
                className="text-gray-300 hover:text-red-500 transition-colors p-0.5 flex-shrink-0">
                <X size={13} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function IntegrationsWidget() {
  const { data } = useApi('/api/mcp/servers', 60000)
  const servers = data?.servers || []
  const [results, setResults] = useState({})

  const test = async (name) => {
    setResults(r => ({ ...r, [name]: 'testing' }))
    try {
      const res = await fetch(`/api/mcp/servers/${name}/test`, { method: 'POST' })
      const d = await res.json()
      setResults(r => ({ ...r, [name]: d.reachable ? 'ok' : 'fail' }))
    } catch {
      setResults(r => ({ ...r, [name]: 'fail' }))
    }
  }

  useEffect(() => {
    servers.filter(s => s.enabled && results[s.name] === undefined).forEach(s => test(s.name))
  }, [servers])  // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Integrations</h2>
        <Link to="/integrations" className="text-xs text-brand-500 hover:text-brand-600">Manage &rarr;</Link>
      </div>
      {servers.length === 0 ? (
        <p className="text-sm text-gray-400">No MCP servers connected yet.</p>
      ) : (
        <div className="space-y-1.5">
          {servers.map(s => {
            const state = !s.enabled ? 'disabled' : (results[s.name] || 'testing')
            return (
              <div key={s.name} className="flex items-center gap-2.5 py-1">
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  state === 'ok' ? 'bg-emerald-500' :
                  state === 'fail' ? 'bg-red-500' :
                  state === 'disabled' ? 'bg-gray-300 dark:bg-gray-600' :
                  'bg-amber-400 animate-pulse'
                }`} />
                <Plug size={13} className="text-gray-400 flex-shrink-0" />
                <span className="text-sm text-gray-800 dark:text-gray-200 truncate flex-1">{s.name}</span>
                <span className="text-[11px] text-gray-400">
                  {state === 'ok' ? 'connected' : state === 'fail' ? 'unreachable' : state === 'disabled' ? 'off' : 'checking…'}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function ServiceDot({ name, status, sub }) {
  const isOnline = status === true || status === 'Online' || status === 'Running'
  return (
    <div className="flex items-center gap-3 py-1">
      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${isOnline ? 'bg-emerald-500' : 'bg-red-500'}`} />
      <span className="text-sm text-gray-800 dark:text-gray-200">{name}</span>
      {sub && <span className="text-xs text-gray-400 ml-auto">{sub}</span>}
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-8 w-48 bg-gray-200 dark:bg-gray-800 rounded" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[1,2,3,4].map(i => <div key={i} className="h-28 bg-gray-200 dark:bg-gray-800 rounded-xl" />)}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {[1,2].map(i => <div key={i} className="h-48 bg-gray-200 dark:bg-gray-800 rounded-xl" />)}
      </div>
    </div>
  )
}

function getGreeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

export default function Overview() {
  const { data: status } = useApi('/api/status', 15000)
  const { data: metrics, loading: metricsLoading } = useApi('/api/metrics', 10000)
  const { data: history } = useApi('/api/metrics/history', 60000)
  const { data: busyData } = useApi('/api/activity/busy', 3000)
  const { data: activityData } = useApi('/api/activity/recent', 10000)
  const { data: secLatest } = useApi('/api/security/latest', 60000)
  const [auditRunning, setAuditRunning] = useState(false)
  const [confirmRestart, setConfirmRestart] = useState(false)
  const [actionFeedback, setActionFeedback] = useState('')
  const navigate = useNavigate()

  const [auditResult, setAuditResult] = useState(null)

  const samples = history?.samples || []
  const spark = (key) => samples.map(s => s[key])

  const runAudit = async () => {
    setAuditRunning(true)
    setAuditResult(null)
    const before = secLatest?.timestamp || ''
    try { await fetch('/api/security/run', { method: 'POST' }) } catch {}
    let attempts = 0
    const poll = setInterval(async () => {
      attempts++
      try {
        const r = await fetch('/api/security/latest')
        const d = await r.json()
        if (d.timestamp && d.timestamp !== before) {
          clearInterval(poll)
          setAuditRunning(false)
          setAuditResult(d.status === 'clean' ? 'clean' : d.status === 'warning' ? 'warning' : 'critical')
          setTimeout(() => setAuditResult(null), 5000)
        }
      } catch {}
      if (attempts > 30) { clearInterval(poll); setAuditRunning(false) }
    }, 1000)
  }
  const doRestart = async () => {
    setConfirmRestart(false)
    try { await fetch('/api/service/restart', { method: 'POST' }) } catch {}
  }
  const quickAction = async (url, label) => {
    setActionFeedback(`${label}...`)
    try {
      await fetch(url, { method: 'POST' })
      setActionFeedback(`${label} done`)
    } catch { setActionFeedback(`${label} failed`) }
    setTimeout(() => setActionFeedback(''), 3000)
  }

  if (metricsLoading && !metrics) return <LoadingSkeleton />

  return (
    <div className="space-y-5">
      {/* Greeting + busy indicator */}
      <div className="flex flex-wrap items-center gap-3 justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{getGreeting()}</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {status ? `${status.tools_ready ?? 0} tools ready · ${status.skill_count ?? 0} skills loaded` : 'Connecting…'}
          </p>
        </div>
        <BusyPill busy={busyData?.busy} />
      </div>

      {/* Quick chat */}
      <QuickChat />

      {/* Metric cards with 24h sparklines */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatusCard title="CPU" value={metrics?.cpu_percent !== undefined ? `${metrics.cpu_percent}%` : '—'} percent={metrics?.cpu_percent} icon={Cpu} sub={metrics?.cpu_cores ? `${metrics.cpu_cores} cores · 24h` : undefined} spark={spark('cpu')} />
        <StatusCard title="RAM" value={metrics?.ram_used_gb ? `${metrics.ram_used_gb} GB` : '—'} percent={metrics?.ram_percent} icon={MemoryStick} sub={metrics?.ram_total_gb ? `${metrics.ram_used_gb} / ${metrics.ram_total_gb} GB · 24h` : undefined} spark={spark('ram')} />
        <StatusCard title="Disk" value={metrics?.disk_percent !== undefined ? `${metrics.disk_percent}%` : '—'} percent={metrics?.disk_percent} icon={HardDrive} sub={metrics?.disk_used_gb ? `${metrics.disk_used_gb} / ${metrics.disk_total_gb} GB · 24h` : undefined} spark={spark('disk')} />
        <StatusCard title="Uptime" value={metrics?.uptime ?? '—'} icon={Clock} sub="System uptime" />
      </div>

      {/* Main grid: activity feed | widgets */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Live activity */}
        <div className="xl:col-span-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Live Activity</h2>
            <Link to="/memory" className="text-xs text-brand-500 hover:text-brand-600">All logs &rarr;</Link>
          </div>
          <ActivityFeed entries={activityData?.entries} />
        </div>

        {/* Right column widgets */}
        <div className="space-y-4">
          <RemindersWidget />
          <IntegrationsWidget />

          {/* Security */}
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Security</h2>
              <Link to="/security" className="text-xs text-brand-500 hover:text-brand-600">Details &rarr;</Link>
            </div>
            {secLatest && secLatest.status ? (
              <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium ${
                secLatest.status === 'clean' ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400' :
                secLatest.status === 'warning' ? 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400' :
                'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400'
              }`}>
                <span className={`w-2 h-2 rounded-full ${
                  secLatest.status === 'clean' ? 'bg-emerald-500' : secLatest.status === 'warning' ? 'bg-amber-500' : 'bg-red-500'
                }`} />
                {secLatest.status === 'clean' ? 'No threats detected' : secLatest.status === 'warning' ? 'Warnings found' : 'Critical issues'}
                <span className="ml-auto text-[11px] font-normal text-gray-400">
                  {secLatest.timestamp ? new Date(secLatest.timestamp).toLocaleDateString() : ''}
                </span>
              </div>
            ) : (
              <p className="text-sm text-gray-400">No scans yet.</p>
            )}
            <button onClick={runAudit} disabled={auditRunning}
              className={`mt-3 flex items-center justify-center gap-2 w-full py-2 text-xs rounded-lg transition-all duration-300 ${
                auditResult === 'clean' ? 'bg-emerald-500 text-white' :
                auditResult === 'warning' ? 'bg-amber-500 text-white' :
                auditResult === 'critical' ? 'bg-red-500 text-white' :
                'bg-brand-500 hover:bg-brand-600 text-white disabled:opacity-50'
              }`}>
              {auditRunning ? (
                <><RefreshCw size={12} className="animate-spin" /> Scanning{'…'}</>
              ) : auditResult === 'clean' ? (
                <><Shield size={12} /> All Clear</>
              ) : auditResult === 'warning' ? (
                <><Shield size={12} /> Warnings Found</>
              ) : auditResult === 'critical' ? (
                <><Shield size={12} /> Issues Found</>
              ) : (
                <><RefreshCw size={12} /> Run Audit</>
              )}
            </button>
          </div>

          {/* Services */}
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Services</h2>
            <ServiceDot name="Ollama" status={status?.ollama} sub="Local LLM" />
            <ServiceDot name="Telegram" status={status?.telegram} sub="Bot" />
            <ServiceDot name="Heartbeat" status={status?.heartbeat_running} sub="Scheduler" />
            <ServiceDot name="Tools" status={status && status.tools_ready === status.tool_count} sub={status ? `${status.tools_ready}/${status.tool_count} ready` : ''} />
            <ServiceDot name="Skills" status={true} sub={status?.skill_count ? `${status.skill_count} loaded` : ''} />
          </div>

          {/* Quick Actions */}
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Quick Actions</h2>
              {actionFeedback && <span className="text-xs text-gray-400">{actionFeedback}</span>}
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button onClick={() => quickAction('/api/backup', 'Backup')}
                className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-xs font-medium bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:border-brand-400 hover:text-brand-500 transition-colors">
                <Save size={14} /> Backup Now
              </button>
              <button onClick={() => quickAction('/api/storage/purge', 'Purge')}
                className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-xs font-medium bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:border-brand-400 hover:text-brand-500 transition-colors">
                <Trash2 size={14} /> Purge Files
              </button>
              <button onClick={() => setConfirmRestart(true)}
                className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-xs font-medium bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:border-brand-400 hover:text-brand-500 transition-colors">
                <RotateCcw size={14} /> Restart
              </button>
              <button onClick={() => navigate('/settings')}
                className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-xs font-medium bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:border-brand-400 hover:text-brand-500 transition-colors">
                <SettingsIcon size={14} /> Settings
              </button>
            </div>
            <button onClick={() => navigate('/logs')}
              className="mt-2 flex items-center justify-center gap-2 w-full py-2 text-xs rounded-lg text-gray-500 hover:text-brand-500 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
              <ScrollText size={12} /> View Logs
            </button>
          </div>
        </div>
      </div>

      <ConfirmModal
        open={confirmRestart}
        title="Restart Kovo?"
        message="This will restart the Kovo service. The agent will be briefly unavailable."
        confirmLabel="Restart"
        confirmColor="brand"
        onConfirm={doRestart}
        onCancel={() => setConfirmRestart(false)}
      />
    </div>
  )
}
