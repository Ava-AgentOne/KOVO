import { useState, useEffect } from 'react'
import { Download, RefreshCw, CheckCircle, AlertCircle, Loader2, ChevronDown, ChevronUp, FileText } from 'lucide-react'

export default function UpdateChecker() {
  const [info, setInfo] = useState(null)
  const [checking, setChecking] = useState(false)
  const [updating, setUpdating] = useState(false)
  const [updateMsg, setUpdateMsg] = useState('')
  const [showLog, setShowLog] = useState(false)
  const [logLines, setLogLines] = useState([])
  const [error, setError] = useState(null)

  const checkUpdate = async () => {
    setChecking(true)
    setError(null)
    try {
      const r = await fetch('/api/update/check')
      const d = await r.json()
      if (d.error) setError(d.error)
      else setInfo(d)
    } catch (e) { setError(e.message) }
    setChecking(false)
  }

  const applyUpdate = async () => {
    if (!confirm('Apply update? KOVO will restart automatically.')) return
    setUpdating(true)
    setUpdateMsg('')
    try {
      const r = await fetch('/api/update/apply', { method: 'POST' })
      const d = await r.json()
      if (d.ok) {
        setUpdateMsg('Update started — service will restart in ~30 seconds...')
        // Poll the log
        const poll = setInterval(async () => {
          try {
            const lr = await fetch('/api/update/log?lines=30')
            const ld = await lr.json()
            setLogLines(ld.lines || [])
            // Check if update is done
            const lastLine = (ld.lines || []).slice(-1)[0] || ''
            if (lastLine.includes('Update complete') || lastLine.includes('Service restarted')) {
              clearInterval(poll)
              setUpdating(false)
              setUpdateMsg('Update complete! Refresh the page.')
              setTimeout(() => checkUpdate(), 3000)
            }
          } catch {}
        }, 2000)
        setShowLog(true)
        // Safety timeout
        setTimeout(() => { clearInterval(poll); setUpdating(false) }, 120000)
      } else {
        setUpdateMsg(d.error || 'Update failed')
        setUpdating(false)
      }
    } catch (e) {
      setUpdateMsg('Failed: ' + e.message)
      setUpdating(false)
    }
  }

  const loadLog = async () => {
    setShowLog(s => !s)
    if (!showLog) {
      try {
        const r = await fetch('/api/update/log?lines=50')
        const d = await r.json()
        setLogLines(d.lines || [])
      } catch {}
    }
  }

  useEffect(() => { checkUpdate() }, [])

  return (
    <div className="space-y-3">
      {/* Version info */}
      <div className="flex items-center gap-3 flex-wrap">
        {info ? (
          <>
            <div className="flex items-center gap-2">
              {info.update_available ? (
                <AlertCircle size={16} className="text-amber-500" />
              ) : (
                <CheckCircle size={16} className="text-green-500" />
              )}
              <span className="text-sm text-gray-700 dark:text-gray-300">
                v{info.local_version}
                <span className="text-gray-400 ml-1">({info.local_sha})</span>
              </span>
            </div>
            {info.update_available && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-700">
                v{info.remote_version} available
              </span>
            )}
            {!info.update_available && (
              <span className="text-xs text-gray-400">Up to date</span>
            )}
          </>
        ) : error ? (
          <span className="text-sm text-red-500">{error}</span>
        ) : (
          <span className="text-sm text-gray-400">Checking...</span>
        )}

        <div className="flex items-center gap-2 ml-auto">
          <button onClick={checkUpdate} disabled={checking}
            className="flex items-center gap-1.5 text-sm bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 px-3 py-1 rounded-lg disabled:opacity-50 transition-colors">
            <RefreshCw size={13} className={checking ? 'animate-spin' : ''} />
            Check
          </button>
          {info?.update_available && (
            <button onClick={applyUpdate} disabled={updating}
              className="flex items-center gap-1.5 text-sm bg-brand-500 hover:bg-brand-600 text-white px-3 py-1 rounded-lg disabled:opacity-50 transition-colors">
              {updating ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
              {updating ? 'Updating...' : 'Update Now'}
            </button>
          )}
        </div>
      </div>

      {/* Latest commit info */}
      {info?.latest_commit?.message && (
        <div className="text-xs text-gray-400">
          Latest: <span className="text-gray-600 dark:text-gray-300">{info.latest_commit.message}</span>
          <span className="ml-2">{info.latest_commit.date?.split('T')[0]}</span>
        </div>
      )}

      {/* Update message */}
      {updateMsg && (
        <div className={`text-sm px-3 py-2 rounded-lg ${
          updateMsg.includes('complete') || updateMsg.includes('Refresh')
            ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-700'
            : updateMsg.includes('Failed') || updateMsg.includes('failed')
            ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-700'
            : 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-700'
        }`}>
          {updateMsg}
        </div>
      )}

      {/* Update log toggle */}
      <button onClick={loadLog}
        className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors">
        <FileText size={12} />
        {showLog ? 'Hide update log' : 'Show update log'}
        {showLog ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>

      {showLog && logLines.length > 0 && (
        <pre className="text-xs text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 rounded-lg p-3 max-h-48 overflow-y-auto font-mono leading-relaxed border border-gray-100 dark:border-gray-700">
          {logLines.join('\n')}
        </pre>
      )}
      {showLog && logLines.length === 0 && (
        <p className="text-xs text-gray-400 italic">No update log yet.</p>
      )}
    </div>
  )
}
