import { useState, useEffect } from 'react'
import { Plus, X, Trash2, Repeat, Play, Loader2, History, ChevronDown, ChevronUp, MessageSquare, EyeOff } from 'lucide-react'
import ConfirmModal from '../components/ConfirmModal'
import PageHeader from '../components/PageHeader'
import EmptyState from '../components/EmptyState'
import useApi from '../hooks/useApi'

// Kovo Routines (v3.0 Phase 1) — recurring autonomous tasks. A routine is a
// stored prompt on a cron schedule; results are delivered to the owner.

const inputCls = 'w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-brand-500'

const DAYS = [
  ['mon', 'Monday'], ['tue', 'Tuesday'], ['wed', 'Wednesday'],
  ['thu', 'Thursday'], ['fri', 'Friday'], ['sat', 'Saturday'], ['sun', 'Sunday'],
]

function buildSchedule(preset, time, day, customCron) {
  const [h, m] = (time || '07:00').split(':').map(x => parseInt(x, 10))
  switch (preset) {
    case 'daily':    return { cron: `${m} ${h} * * *`,        text: `Every day at ${time}` }
    case 'weekdays': return { cron: `${m} ${h} * * mon-fri`,  text: `Weekdays at ${time}` }
    case 'weekly':   return { cron: `${m} ${h} * * ${day}`,   text: `Every ${DAYS.find(d => d[0] === day)?.[1]} at ${time}` }
    case 'hourly':   return { cron: '0 * * * *',              text: 'Every hour' }
    default:         return { cron: customCron.trim(),        text: '' }
  }
}

function fmtWhen(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    const today = new Date()
    const time = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
    if (d.toDateString() === today.toDateString()) return `Today ${time}`
    const tomorrow = new Date(today); tomorrow.setDate(today.getDate() + 1)
    if (d.toDateString() === tomorrow.toDateString()) return `Tomorrow ${time}`
    return `${d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })}, ${time}`
  } catch { return iso }
}

function RunHistory({ id }) {
  const { data } = useApi(`/api/routines/${id}/runs`)
  const runs = data?.runs || []
  if (!runs.length) return <p className="text-xs text-gray-400 mt-2">No runs yet.</p>
  return (
    <div className="mt-2 space-y-1.5">
      {runs.map(run => (
        <div key={run.id} className="text-xs bg-gray-50 dark:bg-gray-800/60 rounded-lg px-3 py-2">
          <div className="flex items-center gap-2">
            <span className={`w-1.5 h-1.5 rounded-full ${run.status === 'ok' ? 'bg-emerald-500' : 'bg-red-500'}`} />
            <span className="font-mono text-gray-500">{fmtWhen(run.started_at)}</span>
            <span className="text-gray-400">· {Math.round(run.duration_s)}s</span>
          </div>
          <p className="text-gray-600 dark:text-gray-400 mt-1 line-clamp-3 whitespace-pre-wrap">{run.result}</p>
        </div>
      ))}
    </div>
  )
}

function RoutineCard({ r, onToggle, onDelete, onRun, running }) {
  const [showHistory, setShowHistory] = useState(false)
  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-2 min-w-0">
          <Repeat size={14} className={r.enabled ? 'text-indigo-500' : 'text-gray-400'} />
          <h3 className="font-semibold text-gray-900 dark:text-white text-sm truncate">{r.name}</h3>
          {r.delivery === 'silent' && (
            <span title="Silent — history only" className="text-gray-400"><EyeOff size={12} /></span>
          )}
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <button onClick={() => onRun(r.id)} disabled={running === r.id}
            className="text-gray-300 hover:text-indigo-500 p-1" title="Run now">
            {running === r.id ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          </button>
          <button onClick={() => setShowHistory(s => !s)} className="text-gray-300 hover:text-brand-500 p-1" title="Run history">
            <History size={14} />
          </button>
          <button onClick={() => onDelete(r)} className="text-gray-300 hover:text-red-500 p-1" title="Delete">
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      <p className="text-xs text-gray-500 line-clamp-2 mb-2">{r.prompt}</p>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-gray-400 mb-2">
        <span className="bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 px-1.5 py-0.5 rounded">
          {r.schedule_text || r.cron}
        </span>
        <span className="font-mono">{r.cron}</span>
        {r.enabled && <span>next: <span className="text-gray-600 dark:text-gray-300">{fmtWhen(r.next_run)}</span></span>}
        {r.last_run && (
          <span className={r.last_status === 'ok' ? 'text-emerald-500' : 'text-red-500'}>
            last: {r.last_status} ({fmtWhen(r.last_run)})
          </span>
        )}
      </div>

      <label className="flex items-center gap-2 text-xs text-gray-500 cursor-pointer">
        <input type="checkbox" checked={!!r.enabled} onChange={e => onToggle(r.id, e.target.checked)} className="accent-indigo-500" />
        {r.enabled ? 'Enabled' : 'Disabled'}
      </label>

      {showHistory && <RunHistory id={r.id} />}
    </div>
  )
}

export default function Routines() {
  const { data, loading, reload } = useApi('/api/routines', 30000)
  const routines = data?.routines || []
  const [showAdd, setShowAdd] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [running, setRunning] = useState(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    name: '', prompt: '', preset: 'daily', time: '07:00', day: 'mon',
    customCron: '', delivery: 'message',
  })

  const create = async () => {
    const { cron, text } = buildSchedule(form.preset, form.time, form.day, form.customCron)
    if (!form.name.trim() || !form.prompt.trim() || !cron) {
      setError('Name, prompt, and schedule are required.'); return
    }
    setSaving(true); setError('')
    try {
      const r = await fetch('/api/routines', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name.trim(), prompt: form.prompt.trim(),
          cron, schedule_text: text, delivery: form.delivery,
        }),
      })
      const d = await r.json()
      if (d.created) {
        setForm({ name: '', prompt: '', preset: 'daily', time: '07:00', day: 'mon', customCron: '', delivery: 'message' })
        setShowAdd(false); reload()
      } else { setError(d.detail || 'Create failed') }
    } catch (e) { setError(e.message) }
    setSaving(false)
  }

  const toggle = async (id, enabled) => {
    try {
      await fetch(`/api/routines/${id}/toggle`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      })
    } catch {}
    reload()
  }

  const remove = async () => {
    if (!deleteTarget) return
    try { await fetch(`/api/routines/${deleteTarget.id}`, { method: 'DELETE' }) } catch {}
    setDeleteTarget(null); reload()
  }

  const runNow = async (id) => {
    setRunning(id)
    try { await fetch(`/api/routines/${id}/run`, { method: 'POST' }) } catch {}
    // The run happens in the background — give it a beat, then refresh
    setTimeout(() => { setRunning(null); reload() }, 4000)
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <PageHeader title="Routines" icon={Repeat} accent="indigo"
          subtitle={!loading ? `${routines.length} routine${routines.length === 1 ? '' : 's'} · recurring tasks Kovo runs for you` : undefined} />
        <button onClick={() => setShowAdd(!showAdd)}
          className="flex items-center gap-1.5 text-sm bg-brand-500 hover:bg-brand-600 text-white px-4 py-1.5 rounded-lg transition-colors">
          <Plus size={14} /> New Routine
        </button>
      </div>

      {showAdd && (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">New Routine</h3>
            <button onClick={() => setShowAdd(false)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"><X size={16} /></button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Name</label>
              <input placeholder="morning briefing" value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className={inputCls} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Result delivery</label>
              <select value={form.delivery} onChange={e => setForm(f => ({ ...f, delivery: e.target.value }))} className={inputCls}>
                <option value="message">Message me the result</option>
                <option value="silent">Silent (history only; failures still alert)</option>
              </select>
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">What should Kovo do? (the prompt it runs)</label>
            <textarea rows={3} placeholder="Check my email and summarize anything important. Alert me about anything urgent."
              value={form.prompt} onChange={e => setForm(f => ({ ...f, prompt: e.target.value }))}
              className={`resize-none ${inputCls}`} />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Schedule</label>
              <select value={form.preset} onChange={e => setForm(f => ({ ...f, preset: e.target.value }))} className={inputCls}>
                <option value="daily">Every day</option>
                <option value="weekdays">Weekdays</option>
                <option value="weekly">Weekly</option>
                <option value="hourly">Every hour</option>
                <option value="custom">Custom cron</option>
              </select>
            </div>
            {form.preset === 'weekly' && (
              <div>
                <label className="text-xs text-gray-500 block mb-1">Day</label>
                <select value={form.day} onChange={e => setForm(f => ({ ...f, day: e.target.value }))} className={inputCls}>
                  {DAYS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
            )}
            {['daily', 'weekdays', 'weekly'].includes(form.preset) && (
              <div>
                <label className="text-xs text-gray-500 block mb-1">Time</label>
                <input type="time" value={form.time} onChange={e => setForm(f => ({ ...f, time: e.target.value }))} className={inputCls} />
              </div>
            )}
            {form.preset === 'custom' && (
              <div className="col-span-2">
                <label className="text-xs text-gray-500 block mb-1">Cron (min hour day month weekday)</label>
                <input placeholder="0 7 * * mon-fri" value={form.customCron}
                  onChange={e => setForm(f => ({ ...f, customCron: e.target.value }))} className={`font-mono ${inputCls}`} />
              </div>
            )}
          </div>
          <p className="text-[11px] text-gray-400">
            Tip: you can also just tell Kovo in chat — “check my email every Monday at 9 and alert me if anything needs me”.
          </p>
          {error && <p className="text-sm text-red-500">{error}</p>}
          <div className="flex gap-2">
            <button onClick={create} disabled={saving}
              className="bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-white px-4 py-2 rounded-lg text-sm transition-colors">
              {saving ? 'Saving…' : 'Create Routine'}
            </button>
            <button onClick={() => setShowAdd(false)} className="text-sm text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 px-4 py-2">Cancel</button>
          </div>
        </div>
      )}

      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 animate-pulse">
          {[1, 2].map(i => <div key={i} className="h-36 bg-gray-200 dark:bg-gray-800 rounded-xl" />)}
        </div>
      )}

      {!loading && routines.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {routines.map(r => (
            <RoutineCard key={r.id} r={r} onToggle={toggle}
              onDelete={setDeleteTarget} onRun={runNow} running={running} />
          ))}
        </div>
      )}

      {!loading && routines.length === 0 && (
        <EmptyState icon={Repeat} title="No routines yet"
          hint="Routines are recurring tasks Kovo runs on a schedule — morning briefings, weekly email checks, nightly reports"
          actionLabel="New Routine" onAction={() => setShowAdd(true)} />
      )}

      <ConfirmModal open={!!deleteTarget} title="Delete Routine"
        message={`Delete "${deleteTarget?.name}"? Its schedule and run history will be removed.`}
        confirmLabel="Delete" confirmColor="red" onConfirm={remove} onCancel={() => setDeleteTarget(null)} />
    </div>
  )
}
