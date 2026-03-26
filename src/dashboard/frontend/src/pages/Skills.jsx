import { useState, useEffect } from 'react'
import { X, Plus, RefreshCw } from 'lucide-react'
import ConfirmModal from '../components/ConfirmModal'

export default function Skills() {
  const [skills, setSkills] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', description: '', triggers: '', body: '' })
  const [creating, setCreating] = useState(false)
  const [msg, setMsg] = useState('')
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [reloading, setReloading] = useState(false)

  const loadSkills = () =>
    fetch('/api/skills').then(r => r.json()).then(d => { setSkills(d.skills || []); setLoading(false) }).catch(() => setLoading(false))

  useEffect(() => { loadSkills() }, [])

  const reloadSkills = async () => {
    setReloading(true)
    try {
      await fetch('/api/skills/reload', { method: 'POST' })
      await loadSkills()
    } catch {}
    setReloading(false)
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    setCreating(true)
    setMsg('')
    try {
      const r = await fetch('/api/skills', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name,
          description: form.description,
          triggers: form.triggers.split(',').map(t => t.trim()).filter(Boolean),
          body: form.body,
        }),
      })
      const d = await r.json()
      if (d.created) {
        setMsg(`"${form.name}" created`)
        setForm({ name: '', description: '', triggers: '', body: '' })
        setShowCreate(false)
        loadSkills()
      } else {
        setMsg('Error: ' + (d.detail || JSON.stringify(d)))
      }
    } catch (err) {
      setMsg('Error: ' + err.message)
    }
    setCreating(false)
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    await fetch(`/api/skills/${deleteTarget}`, { method: 'DELETE' })
    setDeleteTarget(null)
    loadSkills()
  }

  const inputCls = 'bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-brand-500'

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Skills</h1>
          {!loading && <p className="text-sm text-gray-500 mt-0.5">{skills.length} skills loaded</p>}
        </div>
        <div className="flex gap-2">
          <button
            onClick={reloadSkills}
            disabled={reloading}
            className="flex items-center gap-1 text-sm bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600 px-3 py-1.5 rounded-lg transition-colors"
          >
            <RefreshCw size={12} className={reloading ? 'animate-spin' : ''} /> Reload
          </button>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="flex items-center gap-1 text-sm bg-brand-500 hover:bg-brand-600 text-white px-4 py-1.5 rounded-lg transition-colors"
          >
            <Plus size={14} /> New Skill
          </button>
        </div>
      </div>

      {msg && (
        <div className="flex items-center justify-between bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-700/40 rounded-lg px-4 py-2">
          <span className="text-sm text-brand-700 dark:text-brand-300">{msg}</span>
          <button onClick={() => setMsg('')} className="text-brand-500 hover:text-brand-600"><X size={14} /></button>
        </div>
      )}

      {/* Create form */}
      {showCreate && (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Create New Skill</h2>
          <form onSubmit={handleCreate} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <input
                placeholder="Skill name (e.g. backup)"
                value={form.name}
                onChange={e => setForm(f => ({...f, name: e.target.value}))}
                className={inputCls}
                required
              />
              <input
                placeholder="Description"
                value={form.description}
                onChange={e => setForm(f => ({...f, description: e.target.value}))}
                className={inputCls}
              />
            </div>
            <input
              placeholder="Triggers (comma-separated: backup, archive, save)"
              value={form.triggers}
              onChange={e => setForm(f => ({...f, triggers: e.target.value}))}
              className={`w-full ${inputCls}`}
              required
            />
            <textarea
              placeholder={"Skill body \u2014 Markdown describing capabilities and procedures.\n\nExample:\n# Backup Skill\n## When triggered\n1. Run backup script\n2. Report result via Telegram"}
              value={form.body}
              onChange={e => setForm(f => ({...f, body: e.target.value}))}
              rows={6}
              className={`w-full resize-none font-mono ${inputCls}`}
              required
            />
            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={creating}
                className="bg-brand-500 hover:bg-brand-600 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-50 transition-colors"
              >
                {creating ? 'Creating\u2026' : 'Create Skill'}
              </button>
              <button
                type="button"
                onClick={() => setShowCreate(false)}
                className="text-sm text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 px-4 py-2 transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="animate-pulse grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1,2,3,4,5,6].map(i => <div key={i} className="h-32 bg-gray-200 dark:bg-gray-800 rounded-xl" />)}
        </div>
      )}

      {/* Skill cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {skills.map(s => (
          <div key={s.name} className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
            <div className="flex justify-between items-start mb-2">
              <h3 className="font-semibold text-brand-500">{s.name}</h3>
              <button
                onClick={() => setDeleteTarget(s.name)}
                className="text-gray-400 hover:text-red-500 transition-colors p-0.5"
                title="Delete skill"
              >
                <X size={14} />
              </button>
            </div>
            <p className="text-xs text-gray-500 mb-3">{s.description}</p>
            <div className="flex flex-wrap gap-1">
              {s.triggers.slice(0, 8).map(t => (
                <span key={t} className="text-xs bg-gray-100 dark:bg-gray-800 text-gray-500 px-1.5 py-0.5 rounded">{t}</span>
              ))}
              {s.triggers.length > 8 && <span className="text-xs text-gray-400">+{s.triggers.length - 8}</span>}
            </div>
          </div>
        ))}
      </div>

      {!loading && skills.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-400">No skills found.</p>
          <p className="text-xs text-gray-400 mt-1">Create your first skill above.</p>
        </div>
      )}

      {/* Delete confirm modal */}
      <ConfirmModal
        open={!!deleteTarget}
        title="Delete Skill"
        message={`Are you sure you want to delete "${deleteTarget}"? This cannot be undone.`}
        confirmLabel="Delete"
        confirmColor="red"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}
