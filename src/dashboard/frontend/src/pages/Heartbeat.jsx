import { useState, useEffect } from 'react'

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

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Heartbeat</h1>

      {/* Scheduler status */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
        <div className="flex items-center gap-3 mb-4">
          <span className={`text-2xl ${status?.running ? 'animate-pulse' : ''}`}>
            {status?.running ? '💓' : '💔'}
          </span>
          <div>
            <p className="font-semibold text-white">
              Scheduler {status?.running ? 'running' : 'stopped'}
            </p>
            <p className="text-xs text-gray-500">{status?.jobs?.length ?? 0} jobs scheduled</p>
          </div>
        </div>

        {status?.jobs?.length > 0 && (
          <div className="space-y-2">
            {status.jobs.map(job => (
              <div key={job.id} className="flex justify-between items-center text-sm">
                <span className="text-gray-400 font-mono">{job.id}</span>
                <span className="text-gray-600">
                  next: {job.next_run ? new Date(job.next_run).toLocaleString('en-AE', { timeZone: 'Asia/Dubai' }) : '—'}
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
          className="bg-green-800 hover:bg-green-700 text-white text-sm px-4 py-2 rounded disabled:opacity-50"
        >
          ⚡ Quick Check
        </button>
        <button
          onClick={() => runCheck('/api/heartbeat/full')}
          disabled={loading}
          className="bg-blue-800 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded disabled:opacity-50"
        >
          📊 Full Report
        </button>
      </div>

      {/* Report output */}
      {(loading || report) && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h2 className="text-xs text-gray-500 uppercase tracking-wide mb-3">Report Output</h2>
          {loading ? (
            <p className="text-gray-500 italic text-sm animate-pulse">Running…</p>
          ) : (
            <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono">{report}</pre>
          )}
        </div>
      )}
    </div>
  )
}
