import { useState, useEffect } from 'react'
import { Shield, RefreshCw, RotateCcw, AlertTriangle, CheckCircle, XCircle, Info, Wrench, Loader2, Play } from 'lucide-react'
import ConfirmModal from '../components/ConfirmModal'
import useApi from '../hooks/useApi'



function StatusBadge({ status }) {
  if (status === 'clean') return (
    <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-medium">
      <CheckCircle size={16} /> Clean
    </span>
  )
  if (status === 'warning') return (
    <span className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400 font-medium">
      <AlertTriangle size={16} /> Warning
    </span>
  )
  if (status === 'critical') return (
    <span className="flex items-center gap-1.5 text-red-600 dark:text-red-400 font-medium">
      <XCircle size={16} /> Critical
    </span>
  )
  return (
    <span className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400">
      <Info size={16} /> No data
    </span>
  )
}

// Direct fix commands for known findings
const FIX_CONFIG = {
  'Executable files found in /tmp': {
    hint: 'Remove non-system executable files from /tmp and /dev/shm.',
    preview_cmd: 'find /tmp /dev/shm -type f -executable -not -path "*/systemd*"',
    fix_cmd: 'find /tmp /dev/shm -type f -executable -not -path "*/systemd*" -delete',
  },
  'failed login': {
    hint: 'High number of failed SSH logins. Consider installing fail2ban.',
    preview_cmd: 'grep "Failed password" /var/log/auth.log',
    fix_cmd: 'sudo apt-get install -y fail2ban',
  },
  'security updates': {
    hint: 'Security updates are available. Apply them to stay patched.',
    preview_cmd: 'apt list --upgradable',
    fix_cmd: 'sudo apt-get upgrade -y --with-new-pkgs',
  },
  'Failed systemd': {
    hint: 'Some systemd services have failed.',
    preview_cmd: 'systemctl --failed --no-legend',
    fix_cmd: null,  // Requires manual intervention — service names vary
  },
  'Malware detected': {
    hint: 'ClamAV detected malware. Review and quarantine.',
    preview_cmd: 'clamscan -r /tmp /dev/shm --no-summary',
    fix_cmd: 'clamscan -r /tmp /dev/shm --remove',
  },
  'Rootkit detected': {
    hint: 'chkrootkit found a potential rootkit. Investigate immediately.',
    preview_cmd: 'sudo chkrootkit -q',
    fix_cmd: null,  // No auto-fix for rootkits — needs manual investigation
  },
}

function getFixConfig(finding) {
  for (const [key, config] of Object.entries(FIX_CONFIG)) {
    if (finding.toLowerCase().includes(key.toLowerCase())) return config
  }
  return null
}

function FindingRow({ finding, onFixComplete }) {
  const [expanded, setExpanded] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  const [previewResult, setPreviewResult] = useState(null)
  const [fixing, setFixing] = useState(false)
  const [fixResult, setFixResult] = useState(null)
  const config = getFixConfig(finding)

  const runPreview = async () => {
    if (!config?.preview_cmd) return
    setPreviewing(true)
    setPreviewResult(null)
    try {
      const r = await fetch('/api/security/fix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: config.preview_cmd, dry_run: true }),
      })
      const d = await r.json()
      setPreviewResult(d)
    } catch (e) {
      setPreviewResult({ ok: false, output: `Request failed: ${e.message}` })
    }
    setPreviewing(false)
  }

  const runFix = async () => {
    if (!config?.fix_cmd) return
    setFixing(true)
    setFixResult(null)
    try {
      const r = await fetch('/api/security/fix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: config.fix_cmd, dry_run: false }),
      })
      const d = await r.json()
      setFixResult(d)
      // Auto re-run audit after a successful fix
      if (d.ok && onFixComplete) {
        setTimeout(onFixComplete, 1000)
      }
    } catch (e) {
      setFixResult({ ok: false, output: `Request failed: ${e.message}` })
    }
    setFixing(false)
  }

  // Auto-preview when expanded
  useEffect(() => {
    if (expanded && !previewResult && !previewing && config?.preview_cmd) {
      runPreview()
    }
  }, [expanded])

  return (
    <div className="bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700 overflow-hidden">
      <div className="flex items-center gap-3 p-3">
        <AlertTriangle size={16} className="text-amber-500 flex-shrink-0" />
        <span className="text-sm text-gray-700 dark:text-gray-300 flex-1">{finding}</span>
        {config && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1.5 text-sm font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-700/50 px-3 py-1.5 rounded-lg hover:bg-amber-200 dark:hover:bg-amber-900/50 transition-colors flex-shrink-0"
          >
            <Wrench size={14} />
            {expanded ? 'Hide' : 'Fix'}
          </button>
        )}
      </div>

      {expanded && config && (
        <div className="px-3 pb-3 border-t border-gray-200 dark:border-gray-700">
          <div className="mt-3 space-y-3">
            <p className="text-sm text-gray-600 dark:text-gray-400">{config.hint}</p>

            {/* Preview: what will be fixed */}
            {previewResult && (
              <div className="rounded-lg bg-gray-900 dark:bg-black p-3 overflow-x-auto">
                <p className="text-xs text-gray-400 mb-1.5 font-medium">
                  {previewing ? 'Scanning...' : 'Found:'}
                </p>
                <pre className="text-xs text-green-400 whitespace-pre-wrap font-mono leading-relaxed max-h-32 overflow-y-auto">
                  {previewResult.output || '(nothing found)'}
                </pre>
              </div>
            )}

            {previewing && !previewResult && (
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Loader2 size={14} className="animate-spin" /> Scanning...
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
                  {fixResult.ok ? 'Fix Applied — re-running audit...' : 'Fix Failed'}
                </p>
                <pre className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono leading-relaxed max-h-32 overflow-y-auto">
                  {fixResult.output}
                </pre>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex items-center gap-2">
              {config.fix_cmd ? (
                <button
                  onClick={runFix}
                  disabled={fixing}
                  className="flex items-center gap-2 text-sm font-medium bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 rounded-lg disabled:opacity-50 transition-colors"
                >
                  {fixing ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      Fixing...
                    </>
                  ) : (
                    <>
                      <Wrench size={14} />
                      {fixResult ? 'Fix Again' : 'Apply Fix'}
                    </>
                  )}
                </button>
              ) : (
                <p className="text-sm text-amber-600 dark:text-amber-400 italic">
                  This issue requires manual investigation — no auto-fix available.
                </p>
              )}

              {config.preview_cmd && (
                <button
                  onClick={runPreview}
                  disabled={previewing}
                  className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
                >
                  <Play size={12} /> Re-scan
                </button>
              )}
            </div>
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
  const [showAllHistory, setShowAllHistory] = useState(false)

  const runAudit = async () => {
    setAuditRunning(true)
    try {
      await fetch('/api/security/run', { method: 'POST' })
      // Poll until results update
      const startTime = Date.now()
      const poll = setInterval(() => {
        latest.reload()
        history.reload()
        if (Date.now() - startTime > 10000) clearInterval(poll)
      }, 2000)
      setTimeout(() => clearInterval(poll), 12000)
    } catch {}
    setTimeout(() => setAuditRunning(false), 3000)
  }

  const clearHistory = async () => {
    try { await fetch('/api/security/history', { method: 'DELETE' }) } catch {}
    setResetOpen(false)
    history.reload()
  }

  const handleFixComplete = () => {
    // Re-run audit after fix
    runAudit()
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
            <RotateCcw size={14} /> Clear History
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
              <StatusBadge status={l.status} />
              <p className="text-xs text-gray-400">{l.timestamp ? new Date(l.timestamp).toLocaleString() : '\u2014'}</p>
            </div>
            {l.summary && <p className="text-sm text-gray-600 dark:text-gray-400">{l.summary}</p>}
            {l.findings && l.findings.length > 0 && (
              <div className="space-y-2 mt-2">
                <p className="text-xs font-medium text-gray-500 uppercase">
                  Findings {'\u2014'} {l.findings.length} issue{l.findings.length > 1 ? 's' : ''}
                </p>
                {l.findings.map((f, i) => (
                  <FindingRow key={i} finding={f} onFixComplete={handleFixComplete} />
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
          <>
          <div className="space-y-2">
            {(showAllHistory ? history.data.history : history.data.history.slice(0, 10)).map((entry, i) => (
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
          {!showAllHistory && history.data.history.length > 10 && (
            <button onClick={() => setShowAllHistory(true)} className="w-full text-center text-xs text-brand-500 hover:text-brand-600 py-2 mt-2 border-t border-gray-100 dark:border-gray-800">
              Show all {history.data.history.length} entries
            </button>
          )}
          </>
        ) : (
          <p className="text-sm text-gray-400 italic">No audit history yet.</p>
        )}
      </div>

      <ConfirmModal
        open={resetOpen}
        title="Clear Audit History?"
        message="This will remove all past audit entries. The latest scan result will be kept."
        confirmLabel="Clear History"
        confirmColor="red"
        onConfirm={clearHistory}
        onCancel={() => setResetOpen(false)}
      />
    </div>
  )
}
