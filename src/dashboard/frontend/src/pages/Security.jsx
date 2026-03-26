import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, RefreshCw, RotateCcw, AlertTriangle, CheckCircle, XCircle, Info, MessageSquare, Wrench } from 'lucide-react'
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
    <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
      <CheckCircle size={14} /> Clean
    </span>
  )
  if (status === 'warning') return (
    <span className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400">
      <AlertTriangle size={14} /> Warning
    </span>
  )
  if (status === 'critical') return (
    <span className="flex items-center gap-1.5 text-red-600 dark:text-red-400">
      <XCircle size={14} /> Critical
    </span>
  )
  return (
    <span className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400">
      <Info size={14} /> No data
    </span>
  )
}

// Map common security findings to fix suggestions
const FIX_HINTS = {
  'Executable files found in /tmp': {
    hint: 'Remove executable files from /tmp and /dev/shm that shouldn\'t be there.',
    command: 'find /tmp /dev/shm -type f -executable -not -path "*/systemd*" 2>/dev/null',
    autofix: 'Find and review executable files in /tmp. Remove anything suspicious.',
  },
  'open port': {
    hint: 'Review unexpected open ports and close them with firewall rules.',
    command: 'ss -tlnp',
    autofix: 'Check for unexpected open ports and suggest firewall rules.',
  },
  'Failed systemd': {
    hint: 'Restart or disable failed services.',
    command: 'systemctl --failed',
    autofix: 'Check failed systemd services and attempt to restart them.',
  },
  'SUID': {
    hint: 'Review SUID binaries. Non-standard SUID files may be a security risk.',
    command: 'find / -perm -4000 -type f 2>/dev/null',
    autofix: 'Review SUID binaries and flag any unusual ones.',
  },
  'failed login': {
    hint: 'Review failed login attempts and consider adding fail2ban.',
    command: 'journalctl -u ssh --since "1 hour ago" | grep "Failed"',
    autofix: 'Check failed login attempts and recommend security hardening.',
  },
}

function getFix(finding) {
  for (const [key, fix] of Object.entries(FIX_HINTS)) {
    if (finding.toLowerCase().includes(key.toLowerCase())) return fix
  }
  return null
}

function FindingRow({ finding }) {
  const [expanded, setExpanded] = useState(false)
  const navigate = useNavigate()
  const fix = getFix(finding)

  const askKovo = () => {
    // Navigate to chat — the agent will see this as a message
    navigate('/chat')
    // Store the fix request so chat can pick it up
    sessionStorage.setItem('kovo-chat-prefill', `Fix this security issue: ${finding}`)
  }

  return (
    <div className="bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700">
      <div className="flex items-start gap-2 p-3">
        <AlertTriangle size={14} className="text-amber-500 flex-shrink-0 mt-0.5" />
        <span className="text-sm text-gray-700 dark:text-gray-300 flex-1">{finding}</span>
        {fix && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-brand-500 hover:text-brand-600 flex-shrink-0"
          >
            {expanded ? 'Hide' : 'Fix'}
          </button>
        )}
      </div>
      {expanded && fix && (
        <div className="px-3 pb-3 pt-0 border-t border-gray-100 dark:border-gray-700 mt-0">
          <div className="mt-2 space-y-2">
            <p className="text-xs text-gray-500">{fix.hint}</p>
            {fix.command && (
              <div className="text-xs font-mono bg-white dark:bg-gray-900 rounded px-2 py-1.5 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700">
                $ {fix.command}
              </div>
            )}
            <button
              onClick={askKovo}
              className="flex items-center gap-1.5 text-xs bg-brand-500 hover:bg-brand-600 text-white px-3 py-1.5 rounded-lg transition-colors"
            >
              <MessageSquare size={12} /> Ask Kovo to fix
            </button>
          </div>
        </div>
      )}
    </div>
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
  const hasData = l && l.status && l.status !== 'unknown'

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
            {auditRunning ? 'Running\u2026' : 'Run Audit'}
          </button>
        </div>
      </div>

      {/* Latest result */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Shield size={18} className="text-brand-500" />
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Latest Audit</h2>
        </div>
        {hasData ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium"><StatusBadge status={l.status} /></div>
              <p className="text-xs text-gray-400">{l.timestamp ? new Date(l.timestamp).toLocaleString() : '\u2014'}</p>
            </div>
            {l.summary && (
              <p className="text-sm text-gray-600 dark:text-gray-400">{l.summary}</p>
            )}
            {l.findings && l.findings.length > 0 && (
              <div className="space-y-2 mt-2">
                <p className="text-xs font-medium text-gray-500 uppercase">Findings &mdash; {l.findings.length} issue{l.findings.length > 1 ? 's' : ''}</p>
                {l.findings.map((f, i) => (
                  <FindingRow key={i} finding={f} />
                ))}
              </div>
            )}
            {(!l.findings || l.findings.length === 0) && l.status === 'clean' && (
              <p className="text-sm text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
                <CheckCircle size={14} /> No issues found
              </p>
            )}
          </div>
        ) : (
          <div className="text-center py-8">
            <Shield size={32} className="text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="text-sm text-gray-500 dark:text-gray-400">No scans yet</p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Run your first audit to establish a security baseline.</p>
          </div>
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
                  {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : '\u2014'}
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
        title="Reset Security Baseline?"
        message="This will recapture the current system state as the new baseline. Any existing deviations will be forgiven."
        confirmLabel="Reset Baseline"
        confirmColor="brand"
        onConfirm={resetBaseline}
        onCancel={() => setResetOpen(false)}
      />
    </div>
  )
}
