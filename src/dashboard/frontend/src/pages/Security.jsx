import { useState, useEffect } from 'react'
import { Shield, RefreshCw, RotateCcw, AlertTriangle, CheckCircle, XCircle, Info, Wrench, Loader2 } from 'lucide-react'
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

const FIX_HINTS = {
  'Executable files found in /tmp': {
    hint: 'Remove executable files from /tmp and /dev/shm that shouldn\'t be there.',
    command: 'find /tmp /dev/shm -type f -executable -not -path "*/systemd*" 2>/dev/null',
    prompt: 'Security issue: Executable files found in /tmp or /dev/shm. Please investigate what executable files exist in /tmp and /dev/shm, determine which are safe to remove (not systemd related), remove the suspicious ones, and report what you found and what you did.',
  },
  'open port': {
    hint: 'Review unexpected open ports and close them with firewall rules.',
    command: 'ss -tlnp',
    prompt: 'Security issue: Unexpected open ports detected. Please run ss -tlnp to check all listening ports, identify any that should not be open, and suggest or apply firewall rules to close them. Report your findings.',
  },
  'Failed systemd': {
    hint: 'Restart or disable failed services.',
    command: 'systemctl --failed',
    prompt: 'Security issue: Failed systemd services detected. Please check which services have failed using systemctl --failed, attempt to restart them, and if they keep failing, investigate the logs and report what happened.',
  },
  'SUID': {
    hint: 'Review SUID binaries for anything unusual.',
    command: 'find / -perm -4000 -type f 2>/dev/null',
    prompt: 'Security issue: SUID binary check needed. Please find all SUID binaries on the system, compare against the expected list for Ubuntu, and flag any unusual ones. Report your findings.',
  },
  'failed login': {
    hint: 'Review failed login attempts and harden SSH.',
    command: 'journalctl -u ssh --since "1 hour ago" | grep "Failed"',
    prompt: 'Security issue: Failed login attempts detected. Please check recent failed SSH login attempts, identify if any IPs are brute-forcing, and recommend security hardening steps like fail2ban. Report your findings.',
  },
}

function getFix(finding) {
  for (const [key, fix] of Object.entries(FIX_HINTS)) {
    if (finding.toLowerCase().includes(key.toLowerCase())) return fix
  }
  return null
}

function FindingRow({ finding, onFixComplete }) {
  const [expanded, setExpanded] = useState(false)
  const [fixing, setFixing] = useState(false)
  const [fixResult, setFixResult] = useState(null)
  const fix = getFix(finding)

  const runFix = async () => {
    setFixing(true)
    setFixResult(null)
    try {
      const r = await fetch('/api/security/fix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ finding, prompt: fix.prompt }),
      })
      const d = await r.json()
      setFixResult(d)
      if (d.ok && onFixComplete) onFixComplete()
    } catch (e) {
      setFixResult({ ok: false, text: `Request failed: ${e.message}` })
    }
    setFixing(false)
  }

  return (
    <div className="bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700 overflow-hidden">
      <div className="flex items-center gap-3 p-3">
        <AlertTriangle size={16} className="text-amber-500 flex-shrink-0" />
        <span className="text-sm text-gray-700 dark:text-gray-300 flex-1">{finding}</span>
        {fix && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1.5 text-xs font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-700/50 px-3 py-1.5 rounded-lg hover:bg-amber-200 dark:hover:bg-amber-900/50 transition-colors flex-shrink-0"
          >
            <Wrench size={12} />
            {expanded ? 'Hide' : 'Fix'}
          </button>
        )}
      </div>

      {expanded && fix && (
        <div className="px-3 pb-3 border-t border-gray-200 dark:border-gray-700">
          <div className="mt-3 space-y-3">
            <p className="text-sm text-gray-600 dark:text-gray-400">{fix.hint}</p>

            {fix.command && (
              <div className="text-xs font-mono bg-white dark:bg-gray-900 rounded-lg px-3 py-2 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700">
                <span className="text-gray-400">$</span> {fix.command}
              </div>
            )}

            {/* Fix result */}
            {fixResult && (
              <div className={`rounded-lg p-3 text-sm ${
                fixResult.ok
                  ? 'bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700/40'
                  : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700/40'
              }`}>
                <p className={`text-xs font-semibold mb-1 ${fixResult.ok ? 'text-emerald-700 dark:text-emerald-400' : 'text-red-700 dark:text-red-400'}`}>
                  {fixResult.ok ? 'Fix Applied' : 'Fix Failed'}
                </p>
                <pre className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono leading-relaxed max-h-48 overflow-y-auto">
                  {fixResult.text}
                </pre>
              </div>
            )}

            {/* Action button */}
            <button
              onClick={runFix}
              disabled={fixing}
              className="flex items-center gap-2 text-sm font-medium bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 rounded-lg disabled:opacity-50 transition-colors"
            >
              {fixing ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Kovo is fixing...
                </>
              ) : (
                <>
                  <Wrench size={14} />
                  {fixResult ? 'Run Again' : 'Fix with Kovo'}
                </>
              )}
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
            {l.summary && <p className="text-sm text-gray-600 dark:text-gray-400">{l.summary}</p>}
            {l.findings && l.findings.length > 0 && (
              <div className="space-y-2 mt-2">
                <p className="text-xs font-medium text-gray-500 uppercase">
                  Findings {'\u2014'} {l.findings.length} issue{l.findings.length > 1 ? 's' : ''}
                </p>
                {l.findings.map((f, i) => (
                  <FindingRow key={i} finding={f} onFixComplete={() => { setTimeout(() => { latest.reload(); history.reload() }, 3000) }} />
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

      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">Audit History</h2>
        {history.data?.history?.length > 0 ? (
          <div className="space-y-2">
            {history.data.history.map((entry, i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700">
                <div className="flex items-center gap-3">
                  <StatusBadge status={entry.status} />
                  {entry.summary && <span className="text-xs text-gray-500">{entry.summary}</span>}
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
