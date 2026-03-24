import { useState, useEffect, useRef } from 'react'

const LEVEL_COLOR = {
  ERROR: 'text-red-400',
  WARNING: 'text-yellow-400',
  WARN: 'text-yellow-400',
  INFO: 'text-blue-300',
  DEBUG: 'text-gray-500',
}

function colorize(line) {
  for (const [key, cls] of Object.entries(LEVEL_COLOR)) {
    if (line.includes(` ${key} `) || line.includes(` ${key}:`)) {
      return <span className={cls}>{line}</span>
    }
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
        <h1 className="text-2xl font-bold text-white">Logs</h1>
        <div className="flex items-center gap-3">
          <input
            placeholder="Filter…"
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-brand-500 w-48"
          />
          <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
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
            className="text-sm bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1.5 rounded"
          >
            ↺ Refresh
          </button>
        </div>
      </div>

      <div className="flex-1 bg-gray-900 border border-gray-800 rounded-lg overflow-auto p-3">
        <div className="font-mono text-xs leading-5 space-y-0.5">
          {filtered.map((line, i) => (
            <div key={i} className="hover:bg-gray-800 px-1 rounded">
              {colorize(line)}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
        {filtered.length === 0 && (
          <p className="text-gray-600 italic text-sm p-2">
            {filter ? 'No lines match filter.' : 'No log entries.'}
          </p>
        )}
      </div>
      <p className="text-xs text-gray-600 flex-shrink-0">
        {filtered.length} lines · refreshes every 5s
      </p>
    </div>
  )
}
