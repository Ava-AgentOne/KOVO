import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Cpu, MemoryStick, HardDrive, Clock, Shield, MessageSquare, RefreshCw } from 'lucide-react'
import StatusCard from '../components/StatusCard'

function useApi(url, interval = 10000) {
  const [data, setData] = useState(null)
  useEffect(() => {
    const fetch_ = () => fetch(url).then(r => r.json()).then(setData).catch(() => {})
    fetch_()
    const id = setInterval(fetch_, interval)
    return () => clearInterval(id)
  }, [url, interval])
  return data
}

const ENTRY_LIMIT = 300

function LogEntry({ raw }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = raw.length > ENTRY_LIMIT
  const display = isLong && !expanded ? raw.slice(0, ENTRY_LIMIT) + '…' : raw
  return (
    <div className="border-b border-gray-100 dark:border-gray-800 last:border-0 py-2">
      <pre className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono leading-relaxed break-words">
        {display}
      </pre>
      {isLong && (
        <button
          onClick={() => setExpanded(e => !e)}
          className="mt-1 text-xs text-brand-500 hover:text-brand-600 transition-colors"
        >
          {expanded ? '▲ show less' : '▼ show more'}
        </button>
      )}
    </div>
  )
}

function DailyLog({ content }) {
  if (!content) return <p className="text-gray-400 text-sm italic">No activity logged today yet.</p>
  const parts = content.split(/(?=^- \[\d{2}:\d{2}\])/m).filter(Boolean)
  if (parts.length <= 1) return <LogEntry raw={content} />
  return (
    <div>
      {parts.map((entry, i) => <LogEntry key={i} raw={entry.trimEnd()} />)}
    </div>
  )
}

export default function Overview() {
  const status = useApi('/api/status', 15000)
  const agents = useApi('/api/agents', 30000)
  const memory = useApi('/api/memory/today', 30000)
  const metrics = useApi('/api/metrics', 10000)
  const secLatest = useApi('/api/security/latest', 60000)

  const [auditRunning, setAuditRunning] = useState(false)
  const runAudit = async () => {
    setAuditRunning(true)
    try { await fetch('/api/security/run', { method: 'POST' }) } catch {}
    setAuditRunning(false)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Overview</h1>

      {/* System metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatusCard
          title="CPU"
          value={metrics?.cpu_percent !== undefined ? `${metrics.cpu_percent}%` : '—'}
          percent={metrics?.cpu_percent}
          icon={Cpu}
          sub={metrics?.cpu_cores ? `${metrics.cpu_cores} cores` : undefined}
        />
        <StatusCard
          title="RAM"
          value={metrics?.ram_percent !== undefined ? `${metrics.ram_percent}%` : '—'}
          percent={metrics?.ram_percent}
          icon={MemoryStick}
          sub={metrics?.ram_used_gb ? `${metrics.ram_used_gb} / ${metrics.ram_total_gb} GB` : undefined}
        />
        <StatusCard
          title="Disk"
          value={metrics?.disk_percent !== undefined ? `${metrics.disk_percent}%` : '—'}
          percent={metrics?.disk_percent}
          icon={HardDrive}
          sub={metrics?.disk_used_gb ? `${metrics.disk_used_gb} / ${metrics.disk_total_gb} GB` : undefined}
        />
        <StatusCard
          title="Uptime"
          value={metrics?.uptime ?? '—'}
          icon={Clock}
          sub="System uptime"
        />
      </div>

      {/* Service status row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <StatusCard title="Ollama" value={status?.ollama ? 'Online' : 'Offline'} ok={status?.ollama} sub="NUC 10.0.1.212" />
        <StatusCard title="Telegram" value={status?.telegram ? 'Online' : 'Offline'} ok={status?.telegram} sub="Bot" />
        <StatusCard title="Heartbeat" value={status?.heartbeat_running ? 'Running' : 'Stopped'} ok={status?.heartbeat_running} sub="Scheduler" />
        <StatusCard title="Tools" value={status ? `${status.tools_ready}/${status.tool_count}` : '—'} ok={status && status.tools_ready === status.tool_count} sub="Ready" />
        <StatusCard title="Skills" value={status?.skill_count ?? '—'} sub="Loaded" />
      </div>

      {/* Bottom panels */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Agents */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Agents</h2>
          <div className="space-y-2">
            <div className="flex items-center gap-3 p-3 bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-700/40 rounded-lg">
              <div className="w-2 h-2 rounded-full bg-brand-500 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-semibold text-gray-900 dark:text-white">Kovo</p>
                <p className="text-xs text-gray-500">Main agent · handles all requests · access to all tools</p>
              </div>
              <Link
                to="/chat"
                className="flex items-center gap-1 text-xs bg-brand-500 hover:bg-brand-600 text-white px-3 py-1 rounded-lg transition-colors"
              >
                <MessageSquare size={12} /> Chat
              </Link>
            </div>
            {agents?.sub_agents?.length > 0 ? (
              agents.sub_agents.map(a => (
                <div key={a.name} className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
                  <div className="w-2 h-2 rounded-full bg-green-500 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-semibold text-gray-900 dark:text-white">{a.name}</p>
                    <p className="text-xs text-gray-500">{a.purpose || 'Sub-agent'} · tools: {a.tools.length > 0 ? a.tools.join(', ') : 'none'}</p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-gray-400 text-xs italic pl-2">
                No sub-agents yet — Kovo will recommend creating one when it notices repeated patterns.
              </p>
            )}
          </div>
        </div>

        {/* Security panel */}
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Security</h2>
            <Shield size={16} className="text-gray-400" />
          </div>
          {secLatest ? (
            <div className="space-y-3">
              <div className={`flex items-center gap-2 p-2 rounded-lg text-sm font-medium ${
                secLatest.status === 'clean'
                  ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400'
                  : secLatest.status === 'warning'
                  ? 'bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400'
                  : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400'
              }`}>
                <span>{secLatest.status === 'clean' ? '✓' : secLatest.status === 'warning' ? '⚠' : '!'}</span>
                <span className="capitalize">{secLatest.status}</span>
              </div>
              <p className="text-xs text-gray-500">Last scan: {secLatest.timestamp ? new Date(secLatest.timestamp).toLocaleString() : '—'}</p>
              {secLatest.summary && <p className="text-xs text-gray-600 dark:text-gray-400">{secLatest.summary}</p>}
            </div>
          ) : (
            <p className="text-xs text-gray-400 italic">No scan data yet.</p>
          )}
          <div className="mt-4 flex flex-col gap-2">
            <button
              onClick={runAudit}
              disabled={auditRunning}
              className="flex items-center justify-center gap-2 w-full py-2 text-xs rounded-lg bg-brand-500 hover:bg-brand-600 text-white disabled:opacity-50 transition-colors"
            >
              <RefreshCw size={12} className={auditRunning ? 'animate-spin' : ''} />
              {auditRunning ? 'Running…' : 'Run Audit'}
            </button>
            <Link
              to="/security"
              className="text-center text-xs text-brand-500 hover:text-brand-600 transition-colors"
            >
              View history →
            </Link>
          </div>
        </div>
      </div>

      {/* Today's activity */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Today's Activity — {memory?.date ?? '…'}
        </h2>
        <DailyLog content={memory?.content} />
      </div>
    </div>
  )
}
