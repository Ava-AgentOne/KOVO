import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Cpu, MemoryStick, HardDrive, Clock, Shield, MessageSquare,
  RefreshCw, Trash2, Save, RotateCcw, Settings as SettingsIcon,
  ScrollText,
} from 'lucide-react'
import StatusCard from '../components/StatusCard'
import ConfirmModal from '../components/ConfirmModal'

function useApi(url, interval = 10000) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  useEffect(() => {
    const fetch_ = () =>
      fetch(url)
        .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json() })
        .then(d => { setData(d); setLoading(false); setError(null) })
        .catch(e => { setLoading(false); setError(e.message) })
    fetch_()
    const id = setInterval(fetch_, interval)
    return () => clearInterval(id)
  }, [url, interval])
  return { data, loading, error }
}

function SimpleMarkdown({ text }) {
  if (!text) return null
  const html = text
    .replace(/\*\*`([^`]+)`\*\*/g, '<strong><code class="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs">$1</code></strong>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code class="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs">$1</code>')
    .replace(/^## (.+)$/gm, '<p class="text-sm font-semibold text-gray-700 dark:text-gray-300 mt-3 mb-1">$1</p>')
    .replace(/^# (.+)$/gm, '<p class="text-base font-bold text-gray-800 dark:text-gray-200 mt-3 mb-1">$1</p>')
  return <div className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed" dangerouslySetInnerHTML={{ __html: html }} />
}

const ENTRY_LIMIT = 300

function LogEntry({ raw }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = raw.length > ENTRY_LIMIT
  const display = isLong && !expanded ? raw.slice(0, ENTRY_LIMIT) + '\u2026' : raw
  return (
    <div className="border-b border-gray-100 dark:border-gray-800 last:border-0 py-2.5">
      <SimpleMarkdown text={display} />
      {isLong && (
        <button onClick={() => setExpanded(e => !e)} className="mt-1 text-xs text-brand-500 hover:text-brand-600 transition-colors">
          {expanded ? '\u25b2 show less' : '\u25bc show more'}
        </button>
      )}
    </div>
  )
}

function DailyLog({ content }) {
  if (!content) return <p className="text-gray-400 text-sm italic">No activity logged today yet.</p>
  const parts = content.split(/(?=^- \[\d{2}:\d{2}\])/m).filter(Boolean)
  if (parts.length <= 1) return <LogEntry raw={content} />
  return <div>{parts.map((entry, i) => <LogEntry key={i} raw={entry.trimEnd()} />)}</div>
}

function ServiceDot({ name, status, sub }) {
  const isOnline = status === true || status === 'Online' || status === 'Running'
  return (
    <div className="flex items-center gap-3 py-1.5">
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
  const { data: agents } = useApi('/api/agents', 30000)
  const { data: memory } = useApi('/api/memory/today', 30000)
  const { data: metrics, loading: metricsLoading } = useApi('/api/metrics', 10000)
  const { data: secLatest } = useApi('/api/security/latest', 60000)
  const [auditRunning, setAuditRunning] = useState(false)
  const [confirmRestart, setConfirmRestart] = useState(false)
  const [actionFeedback, setActionFeedback] = useState('')
  const navigate = useNavigate()

  const runAudit = async () => {
    setAuditRunning(true)
    try { await fetch('/api/security/run', { method: 'POST' }) } catch {}
    setAuditRunning(false)
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
    <div className="space-y-6">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{getGreeting()}</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          {status ? `${status.tools_ready ?? 0} tools ready \u00b7 ${status.skill_count ?? 0} skills loaded` : 'Connecting\u2026'}
        </p>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatusCard title="CPU" value={metrics?.cpu_percent !== undefined ? `${metrics.cpu_percent}%` : '\u2014'} percent={metrics?.cpu_percent} icon={Cpu} sub={metrics?.cpu_cores ? `${metrics.cpu_cores} cores` : undefined} />
        <StatusCard title="RAM" value={metrics?.ram_used_gb ? `${metrics.ram_used_gb} GB` : '\u2014'} percent={metrics?.ram_percent} icon={MemoryStick} sub={metrics?.ram_total_gb ? `${metrics.ram_used_gb} / ${metrics.ram_total_gb} GB` : undefined} />
        <StatusCard title="Disk" value={metrics?.disk_percent !== undefined ? `${metrics.disk_percent}%` : '\u2014'} percent={metrics?.disk_percent} icon={HardDrive} sub={metrics?.disk_used_gb ? `${metrics.disk_used_gb} / ${metrics.disk_total_gb} GB` : undefined} />
        <StatusCard title="Uptime" value={metrics?.uptime ?? '\u2014'} icon={Clock} sub="System uptime" />
      </div>

      {/* Services + Security | Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: Services + Security stacked */}
        <div className="space-y-4">
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Services</h2>
            <ServiceDot name="Ollama" status={status?.ollama} sub="NUC <OLLAMA-HOST>" />
            <ServiceDot name="Telegram" status={status?.telegram} sub="Bot" />
            <ServiceDot name="Heartbeat" status={status?.heartbeat_running} sub="Scheduler" />
            <ServiceDot name="Tools" status={status && status.tools_ready === status.tool_count} sub={status ? `${status.tools_ready}/${status.tool_count} ready` : ''} />
            <ServiceDot name="Skills" status={true} sub={status?.skill_count ? `${status.skill_count} loaded` : ''} />
          </div>

          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Security</h2>
              <Link to="/security" className="text-xs text-brand-500 hover:text-brand-600">Details &rarr;</Link>
            </div>
            {secLatest && secLatest.status ? (
              <div className="space-y-3">
                <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium ${
                  secLatest.status === 'clean' ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400' :
                  secLatest.status === 'warning' ? 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400' :
                  'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400'
                }`}>
                  <span className={`w-2 h-2 rounded-full ${
                    secLatest.status === 'clean' ? 'bg-emerald-500' : secLatest.status === 'warning' ? 'bg-amber-500' : 'bg-red-500'
                  }`} />
                  {secLatest.status === 'clean' ? 'No threats detected' : secLatest.status === 'warning' ? 'Warnings found' : 'Critical issues'}
                </div>
                <p className="text-xs text-gray-500">Last scan: {secLatest.timestamp ? new Date(secLatest.timestamp).toLocaleDateString() : '\u2014'}</p>
              </div>
            ) : (
              <p className="text-sm text-gray-400">No scans yet. Run your first audit below.</p>
            )}
            <button onClick={runAudit} disabled={auditRunning}
              className="mt-3 flex items-center justify-center gap-2 w-full py-2 text-xs rounded-lg bg-brand-500 hover:bg-brand-600 text-white disabled:opacity-50 transition-colors">
              <RefreshCw size={12} className={auditRunning ? 'animate-spin' : ''} />
              {auditRunning ? 'Running\u2026' : 'Run Audit'}
            </button>
          </div>
        </div>

        {/* Right: Agent card + Quick Actions */}
        <div className="space-y-4">
          {/* Agent */}
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Agent</h2>
              <Link to="/agents" className="text-xs text-brand-500 hover:text-brand-600">Manage &rarr;</Link>
            </div>
            <div className="flex items-center gap-3 p-3 bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-700/40 rounded-lg">
              <span className="w-2.5 h-2.5 rounded-full bg-brand-500 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-900 dark:text-white">Kovo</p>
                <p className="text-xs text-gray-500 truncate">Main agent &middot; {status?.tools_ready ?? '?'} tools &middot; {status?.skill_count ?? '?'} skills</p>
              </div>
              <Link to="/chat" className="flex items-center gap-1 text-xs bg-brand-500 hover:bg-brand-600 text-white px-3 py-1.5 rounded-lg transition-colors flex-shrink-0">
                <MessageSquare size={12} /> Chat
              </Link>
            </div>
            {agents?.sub_agents?.length > 0 && agents.sub_agents.map(a => (
              <div key={a.name} className="flex items-center gap-3 p-3 mt-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 flex-shrink-0" />
                <div className="min-w-0"><p className="text-sm font-semibold text-gray-900 dark:text-white">{a.name}</p>
                <p className="text-xs text-gray-500 truncate">{a.purpose || 'Sub-agent'}</p></div>
              </div>
            ))}
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

      {/* Today's Activity */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Today &mdash; {memory?.date ?? '\u2026'}</h2>
          <Link to="/memory" className="text-xs text-brand-500 hover:text-brand-600">All logs &rarr;</Link>
        </div>
        <DailyLog content={memory?.content} />
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
