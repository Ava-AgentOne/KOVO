import { useState, useEffect, useRef } from 'react'
import { RefreshCw } from 'lucide-react'

function colorize(line) {
  if (line.includes(' ERROR ') || line.includes(' ERROR:') || line.includes('Traceback')) {
    return <span className="text-red-400">{line}</span>
  }
  if (line.includes(' WARNING ') || line.includes(' WARNING:') || line.includes(' WARN ')) {
    return <span className="text-amber-400">{line}</span>
  }
  if (line.includes(' CRITICAL ') || line.includes(' CRITICAL:')) {
    return <span className="text-red-300 font-bold">{line}</span>
  }
  if (line.includes(' INFO ') || line.includes(' INFO:')) {
    return <span className="text-gray-300">{line}</span>
  }
  if (line.includes(' DEBUG ') || line.includes(' DEBUG:')) {
    return <span className="text-gray-600">{line}</span>
  }
  if (line.startsWith('  ') || line.startsWith('\t')) {
    return <span className="text-red-500/60">{line}</span>
  }
  return <span className="text-gray-400">{line}</span>
}

export default function Logs() {
  const [lines, setLines] = useState([])
  const [filter, setFilter] = useState('')
  const [autoScroll, setAutoScroll] = useState(true)
  const bottomRef = useRef(null)

  const loadLogs = () =>
    fetch('/api/logs?lines=300')
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

  const filtered = filter
    ? lines.filter(l => l.toLowerCase().includes(filter.toLowerCase()))
    : lines

  return (
    <div className="space-y-4 h-[calc(100vh-140px)] flex flex-col">
      <div className="flex items-center justify-between flex-shrink-0">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Logs</h1>
        <div className="flex items-center gap-3">
          <input
            placeholder="Filter…"
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-brand-500 w-48"
          />
          <label className="flex items-center gap-2 text-sm text-gray-500 cursor-pointer">
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
            className="flex items-center gap-1 text-sm bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 transition-colors"
          >
            <RefreshCw size={12} /> Refresh
          </button>
        </div>
      </div>

      <div className="flex-1 bg-[#0d1117] border border-gray-700 rounded-xl overflow-auto p-3">
        <div className="font-mono text-xs leading-5 min-w-0">
          {filtered.map((line, i) => (
            <div key={i} className="whitespace-nowrap hover:bg-white/5 px-1 rounded">
              {colorize(line)}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
        {filtered.length === 0 && (
          <p className="text-gray-500 italic text-sm p-2">
            {filter ? 'No lines match filter.' : 'No log entries.'}
          </p>
        )}
      </div>
      <p className="text-xs text-gray-400 flex-shrink-0">
        {filtered.length} lines · refreshes every 5s
      </p>
    </div>
  )
}
