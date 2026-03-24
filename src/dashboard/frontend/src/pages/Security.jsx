import { useState, useEffect } from 'react'
import { Shield, RefreshCw, RotateCcw, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'
import ConfirmModal from '../components/ConfirmModal'

function useApi(url, interval = 0) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const load = () =>
    fetch(url)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  useEffect(() => {
    load()
    if (!interval) return
    const id = setInterval(load, interval)
    return () => clearInterval(id)
  }, [url])
  return { data, loading, reload: load }
}

function StatusBadge({ status }) {
  if (status === 'clean') return (
    <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
      <CheckCircle size={14} /> Clean
    </span>
  )
  if (status === 'warning') return (
    <span className="flex items-center gap-1 text-yellow-600 dark:text-yellow-400">
      <AlertTriangle size={14} /> Warning
    </span>
  )
  return (
    <span className="flex items-center gap-1 text-red-600 dark:text-red-400">
      <XCircle size={14} /> Alert
    </span>
  )
}

export default function Security() {
  const latest = useApi('/api/security/latest', 30000)
  const history = useApi('/api/security/history')
  const [auditRunning, setAuditRunning] = useState(false)
  const [resetOpen, setResetOpen] = useState(false)

  const runAudit = async () => {
    setAuditRunning(true)
    try {
      await fetch('/api/security/run', { method: 'POST' })
      setTimeout(() => { latest.reload(); history.reload() }, 3000)
    } catch {}
    setAuditRunning(false)
  }

  const resetBaseline = async () => {
    try { await fetch('/api/security/baseline', { method: 'POST' }) } catch {}
    setResetOpen(false)
    latest.reload()
  }

  const l = latest.data

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Security</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setResetOpen(true)}
            className="flex items-center gap-1 px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <RotateCcw size={14} /> Reset Baseline
          </button>
          <button
            onClick={runAudit}
            disabled={auditRunning}
            className="flex items-center gap-1 px-3 py-2 text-sm rounded-lg bg-brand-500 hover:bg-brand-600 text-white disabled:opacity-50 transition-colors"
          >
            <RefreshCw size={14} className={auditRunning ? 'animate-spin' : ''} />
            {auditRunning ? 'Running…' : 'Run Audit'}
          </button>
        </div>
      </div>

      {/* Latest result */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Shield size={18} className="text-brand-500" />
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Latest Audit</h2>
        </div>
        {l ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium"><StatusBadge status={l.status} /></div>
              <p className="text-xs text-gray-400">{l.timestamp ? new Date(l.timestamp).toLocaleString() : '—'}</p>
            </div>
            {l.summary && (
              <p className="text-sm text-gray-600 dark:text-gray-400">{l.summary}</p>
            )}
            {l.findings && l.findings.length > 0 && (
              <div className="space-y-1 mt-2">
                <p className="text-xs font-medium text-gray-500 uppercase">Findings</p>
                {l.findings.map((f, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm p-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <AlertTriangle size={14} className="text-yellow-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700 dark:text-gray-300">{f}</span>
                  </div>
                ))}
              </div>
            )}
            {(!l.findings || l.findings.length === 0) && l.status === 'clean' && (
              <p className="text-sm text-green-600 dark:text-green-400 flex items-center gap-2">
                <CheckCircle size={14} /> No issues found
              </p>
            )}
          </div>
        ) : latest.loading ? (
          <p className="text-sm text-gray-400">Loading…</p>
        ) : (
          <p className="text-sm text-gray-400 italic">No audit data yet. Run your first audit above.</p>
        )}
      </div>

      {/* Audit history */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">Audit History</h2>
        {history.data?.history?.length > 0 ? (
          <div className="space-y-2">
            {history.data.history.map((entry, i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700">
                <div className="flex items-center gap-3">
                  <StatusBadge status={entry.status} />
                  {entry.summary && (
                    <span className="text-xs text-gray-500">{entry.summary}</span>
                  )}
                </div>
                <span className="text-xs text-gray-400">
                  {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : '—'}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400 italic">No audit history yet.</p>
        )}
      </div>

      <ConfirmModal
        open={resetOpen}
        title="Reset Security Baseline"
        message="This will recapture the current system state as the new baseline. Any existing deviations will be forgiven."
        confirmLabel="Reset Baseline"
        confirmColor="brand"
        onConfirm={resetBaseline}
        onCancel={() => setResetOpen(false)}
      />
    </div>
  )
}
