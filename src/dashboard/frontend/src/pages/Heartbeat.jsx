import { useState, useEffect } from 'react'
import { Zap, BarChart2, HeartPulse, HeartCrack } from 'lucide-react'

export default function Heartbeat() {
  const [status, setStatus] = useState(null)
  const [report, setReport] = useState('')
  const [loading, setLoading] = useState(false)

  const loadStatus = () =>
    fetch('/api/heartbeat/status').then(r => r.json()).then(setStatus).catch(console.error)

  useEffect(() => {
    loadStatus()
    const id = setInterval(loadStatus, 30000)
    return () => clearInterval(id)
  }, [])

  const runCheck = async (endpoint) => {
    setLoading(true)
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

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Heartbeat</h1>

      {/* Scheduler status */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
        <div className="flex items-center gap-3 mb-4">
          {running ? (
            <HeartPulse size={28} className="text-red-500 animate-pulse" />
          ) : (
            <HeartCrack size={28} className="text-gray-400" />
          )}
          <div>
            <p className="font-semibold text-gray-900 dark:text-white">
              Scheduler {running ? 'running' : 'stopped'}
            </p>
            <p className="text-xs text-gray-500">{status?.jobs?.length ?? 0} jobs scheduled</p>
          </div>
        </div>

        {status?.jobs?.length > 0 && (
          <div className="space-y-2">
            {status.jobs.map(job => (
              <div key={job.id} className="flex justify-between items-center text-sm p-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <span className="text-gray-600 dark:text-gray-400 font-mono">{job.id}</span>
                <span className="text-gray-400 text-xs">
                  next: {job.next_run ? new Date(job.next_run).toLocaleString() : '—'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Manual triggers */}
      <div className="flex gap-3">
        <button
          onClick={() => runCheck('/api/heartbeat/check')}
          disabled={loading}
          className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-50 transition-colors"
        >
          <Zap size={14} /> Quick Check
        </button>
        <button
          onClick={() => runCheck('/api/heartbeat/full')}
          disabled={loading}
          className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-50 transition-colors"
        >
          <BarChart2 size={14} /> Full Report
        </button>
      </div>

      {/* Report output */}
      {(loading || report) && (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
          <h2 className="text-xs text-gray-400 uppercase tracking-wide mb-3">Report Output</h2>
          {loading ? (
            <p className="text-gray-400 italic text-sm animate-pulse">Running…</p>
          ) : (
            <pre className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono">{report}</pre>
          )}
        </div>
      )}
    </div>
  )
}
