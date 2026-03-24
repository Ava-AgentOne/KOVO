import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
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
    <div className="border-b border-gray-800 last:border-0 py-2">
      <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono leading-relaxed break-words">
        {display}
      </pre>
      {isLong && (
        <button
          onClick={() => setExpanded(e => !e)}
          className="mt-1 text-xs text-brand-400 hover:text-brand-300 transition-colors"
        >
          {expanded ? '▲ show less' : '▼ show more'}
        </button>
      )}
    </div>
  )
}

function DailyLog({ content }) {
  if (!content) return <p className="text-gray-600 text-sm italic">No activity logged today yet.</p>

  // Split on entry lines: "- [HH:MM]" starts each entry
  const parts = content.split(/(?=^- \[\d{2}:\d{2}\])/m).filter(Boolean)
  if (parts.length <= 1) {
    return <LogEntry raw={content} />
  }
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

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Overview</h1>

      {/* Status cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <StatusCard
          title="Ollama"
          value={status?.ollama ? '✓' : '✗'}
          ok={status?.ollama}
          sub="NUC 10.0.1.212"
        />
        <StatusCard
          title="Telegram"
          value={status?.telegram ? '✓' : '✗'}
          ok={status?.telegram}
          sub="Bot"
        />
        <StatusCard
          title="Heartbeat"
          value={status?.heartbeat_running ? '✓' : '✗'}
          ok={status?.heartbeat_running}
          sub="Scheduler"
        />
        <StatusCard
          title="Tools"
          value={status ? `${status.tools_ready}/${status.tool_count}` : '—'}
          ok={status && status.tools_ready === status.tool_count}
          sub="Ready"
        />
        <StatusCard
          title="Skills"
          value={status?.skill_count ?? '—'}
          sub="Loaded"
        />
      </div>

      {/* Agents panel */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
          Agents
        </h2>
        <div className="space-y-2">
          <div className="flex items-center gap-3 p-3 bg-brand-900/30 border border-brand-700/50 rounded-lg">
            <div className="w-2 h-2 rounded-full bg-brand-400 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-semibold text-white">🦞 MiniClaw</p>
              <p className="text-xs text-gray-400">Main agent · handles all requests · access to all tools</p>
            </div>
            <Link
              to="/chat"
              className="text-xs bg-brand-700 hover:bg-brand-600 text-white px-3 py-1 rounded transition-colors"
            >
              Chat →
            </Link>
          </div>

          {agents?.sub_agents?.length > 0 ? (
            agents.sub_agents.map(a => (
              <div key={a.name} className="flex items-center gap-3 p-3 bg-gray-800 border border-gray-700 rounded-lg">
                <div className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0" />
                <div>
                  <p className="text-sm font-semibold text-white">{a.name}</p>
                  <p className="text-xs text-gray-400">
                    {a.purpose || 'Sub-agent'} · tools: {a.tools.length > 0 ? a.tools.join(', ') : 'none'}
                  </p>
                </div>
              </div>
            ))
          ) : (
            <p className="text-gray-600 text-xs italic pl-2">
              No sub-agents yet — MiniClaw will recommend creating one when it notices repeated patterns.
            </p>
          )}
        </div>
      </div>

      {/* Today's activity */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
          Today's Activity — {memory?.date ?? '…'}
        </h2>
        <DailyLog content={memory?.content} />
      </div>
    </div>
  )
}
