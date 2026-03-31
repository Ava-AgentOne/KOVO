import { useState, useEffect, useRef } from 'react'
import { RefreshCw, AlertTriangle, AlertCircle, Search } from 'lucide-react'

const TS_REGEX = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/

// Convert 24h timestamps to 12h format in log lines
function to12h(line) {
  return line.replace(/^(\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2}):(\d{2})/, (_, date, h, m, s) => {
    const hr = parseInt(h)
    const ampm = hr >= 12 ? 'PM' : 'AM'
    const h12 = hr === 0 ? 12 : hr > 12 ? hr - 12 : hr
    return date + ' ' + h12 + ':' + m + ':' + s + ' ' + ampm
  })
}

function getLevel(line) {
  if (line.includes(' CRITICAL ') || line.includes(' CRITICAL:')) return 'critical'
  if (line.includes(' ERROR ') || line.includes(' ERROR:') || line.includes('Traceback')) return 'error'
  if (line.includes(' WARNING ') || line.includes(' WARNING:') || line.includes(' WARN ')) return 'warning'
  if (line.includes(' DEBUG ') || line.includes(' DEBUG:')) return 'debug'
  if (line.includes(' INFO ') || line.includes(' INFO:')) return 'info'
  if (!TS_REGEX.test(line)) return 'continuation'
  return 'info'
}

const LEVEL_CLASSES = {
  critical:     'text-red-700 dark:text-red-300 font-bold',
  error:        'text-red-600 dark:text-red-400',
  warning:      'text-amber-600 dark:text-amber-400',
  info:         'text-gray-700 dark:text-gray-300',
  debug:        'text-gray-400 dark:text-gray-600',
  continuation: 'text-red-400 dark:text-red-500/60 pl-4',
}

function colorize(line) {
  const cls = LEVEL_CLASSES[getLevel(line)] || 'text-gray-600 dark:text-gray-400'
  return <span className={cls}>{to12h(line)}</span>
}

const PRESETS = [
  { id: 'all',       label: 'All',           fn: () => true },
  { id: 'errors',    label: 'Errors',        fn: l => { const lv = getLevel(l); return lv === 'error' || lv === 'critical' || lv === 'continuation' }, icon: AlertCircle, color: 'text-red-500' },
  { id: 'warnings',  label: 'Warnings+',     fn: l => { const lv = getLevel(l); return lv !== 'info' && lv !== 'debug' }, icon: AlertTriangle, color: 'text-amber-500' },
  { id: 'no-noise',  label: 'Hide Noise',    fn: l => !l.includes('/api/logs') && !l.includes('/api/metrics') && !l.includes('/api/status') && !l.includes('getUpdates') && !l.includes('/api/service/status') },
  { id: 'agent',     label: 'Agent',         fn: l => l.includes('kovo') || l.includes('agent') || l.includes('claude') || l.includes('sonnet') || l.includes('opus') || l.includes('telegram') },
]

export default function Logs() {
  const [lines, setLines] = useState([])
  const [textFilter, setTextFilter] = useState('')
  const [preset, setPreset] = useState('all')
  const [autoScroll, setAutoScroll] = useState(true)
  const bottomRef = useRef(null)

  const loadLogs = () =>
    fetch('/api/logs?lines=500')
      .then(r => r.json())
      .then(d => setLines(d.lines || []))
      .catch(console.error)

  useEffect(() => {
    loadLogs()
    const id = setInterval(loadLogs, 5000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [lines, autoScroll])

  const presetFilter = PRESETS.find(p => p.id === preset)?.fn || (() => true)
  const filtered = lines
    .filter(presetFilter)
    .filter(l => !textFilter || l.toLowerCase().includes(textFilter.toLowerCase()))

  const errorCount = lines.filter(l => { const lv = getLevel(l); return lv === 'error' || lv === 'critical' }).length
  const warnCount = lines.filter(l => getLevel(l) === 'warning').length

  return (
    <div className="space-y-3 h-[calc(100vh-140px)] flex flex-col">
      <div className="flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Logs</h1>
          {errorCount > 0 && (
            <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-500/10 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-500/20">
              <AlertCircle size={11} /> {errorCount}
            </span>
          )}
          {warnCount > 0 && (
            <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-500/20">
              <AlertTriangle size={11} /> {warnCount}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={e => setAutoScroll(e.target.checked)}
              className="accent-brand-500"
            />
            Auto-scroll
          </label>
          <button
            onClick={loadLogs}
            className="flex items-center gap-1 text-xs bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 transition-colors"
          >
            <RefreshCw size={11} /> Refresh
          </button>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-2 flex-shrink-0 flex-wrap">
        {PRESETS.map(p => (
          <button
            key={p.id}
            onClick={() => setPreset(p.id)}
            className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg border transition-colors ${
              preset === p.id
                ? 'bg-brand-100 dark:bg-brand-500/10 text-brand-600 dark:text-brand-400 border-brand-300 dark:border-brand-500/30'
                : 'bg-gray-100 dark:bg-gray-800/50 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:text-gray-800 dark:hover:text-gray-300'
            }`}
          >
            {p.icon && <p.icon size={11} className={preset === p.id ? 'text-brand-600 dark:text-brand-400' : (p.color || '')} />}
            {p.label}
          </button>
        ))}
        <div className="flex-1" />
        <div className="relative">
          <Search size={11} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
          <input
            placeholder="Search logs…"
            value={textFilter}
            onChange={e => setTextFilter(e.target.value)}
            className="bg-gray-100 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg pl-7 pr-3 py-1 text-xs text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:border-brand-500 w-52"
          />
        </div>
      </div>

      {/* Log output */}
      <div className="flex-1 bg-gray-50 dark:bg-[#0d1117] border border-gray-200 dark:border-gray-700 rounded-xl overflow-auto p-3">
        <div className="font-mono text-xs leading-5 min-w-0">
          {filtered.map((line, i) => (
            <div key={i} className="whitespace-nowrap hover:bg-gray-100 dark:hover:bg-white/5 px-1 rounded">
              {colorize(line)}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
        {filtered.length === 0 && (
          <p className="text-gray-400 dark:text-gray-500 italic text-sm p-2">
            {textFilter || preset !== 'all' ? 'No lines match current filters.' : 'No log entries.'}
          </p>
        )}
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0">
        {filtered.length} / {lines.length} lines · refreshes every 5s
      </p>
    </div>
  )
}
