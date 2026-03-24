import { useState, useEffect } from 'react'
import { Search, Download, X } from 'lucide-react'
import ConfirmModal from '../components/ConfirmModal'

function ClawHubBrowser() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [installing, setInstalling] = useState(null)
  const [msg, setMsg] = useState('')

  const search = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setResults([])
    setMsg('')
    try {
      const r = await fetch(`/api/skills/clawhub/search?q=${encodeURIComponent(query)}`)
      const d = await r.json()
      if (d.error) { setMsg(d.error); return }
      setResults(d.results || [])
      if (!d.results?.length) setMsg('No results found.')
    } catch (e) {
      setMsg('ClawHub unavailable — is the clawhub CLI installed?')
    } finally {
      setLoading(false)
    }
  }

  const install = async (name) => {
    setInstalling(name)
    setMsg('')
    try {
      const r = await fetch('/api/skills/clawhub/install', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      })
      const d = await r.json()
      setMsg(d.ok ? `Installed "${name}"` : d.error || 'Install failed')
    } catch {
      setMsg('Install failed.')
    } finally {
      setInstalling(null)
    }
  }

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">ClawHub — Skill Marketplace</h2>
      <form onSubmit={search} className="flex gap-2 mb-3">
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search skills…"
          className="flex-1 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-brand-500"
        />
        <button
          type="submit"
          disabled={loading}
          className="flex items-center gap-1 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm disabled:opacity-50 transition-colors"
        >
          <Search size={14} />
          {loading ? 'Searching…' : 'Search'}
        </button>
      </form>
      {msg && <p className="text-xs text-gray-500 mb-2">{msg}</p>}
      {results.length > 0 && (
        <div className="space-y-2">
          {results.map(r => (
            <div key={r.name} className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900 dark:text-white">{r.name}</p>
                <p className="text-xs text-gray-500">{r.description}</p>
              </div>
              <button
                onClick={() => install(r.name)}
                disabled={installing === r.name}
                className="flex items-center gap-1 text-xs px-3 py-1 bg-brand-500 hover:bg-brand-600 text-white rounded-lg disabled:opacity-50 transition-colors"
              >
                <Download size={12} />
                {installing === r.name ? 'Installing…' : 'Install'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Skills() {
  const [skills, setSkills] = useState([])
  const [form, setForm] = useState({ name: '', description: '', triggers: '', body: '' })
  const [creating, setCreating] = useState(false)
  const [msg, setMsg] = useState('')
  const [deleteTarget, setDeleteTarget] = useState(null)

  const loadSkills = () =>
    fetch('/api/skills').then(r => r.json()).then(d => setSkills(d.skills || []))

  useEffect(() => { loadSkills() }, [])

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
        setMsg(`Skill "${form.name}" created`)
        setForm({ name: '', description: '', triggers: '', body: '' })
        loadSkills()
      } else {
        setMsg('Error: ' + JSON.stringify(d))
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
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Skills</h1>

      {/* Skill cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {skills.map(s => (
          <div key={s.name} className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
            <div className="flex justify-between items-start mb-2">
              <h3 className="font-semibold text-brand-500">{s.name}</h3>
              <button
                onClick={() => setDeleteTarget(s.name)}
                className="text-gray-400 hover:text-red-500 transition-colors"
              >
                <X size={16} />
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

      {/* Create form */}
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
            placeholder="Skill body (Markdown describing capabilities and procedures)"
            value={form.body}
            onChange={e => setForm(f => ({...f, body: e.target.value}))}
            rows={4}
            className={`w-full resize-none ${inputCls}`}
            required
          />
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={creating}
              className="bg-brand-500 hover:bg-brand-600 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-50 transition-colors"
            >
              {creating ? 'Creating…' : '+ Create Skill'}
            </button>
            {msg && <span className="text-sm text-gray-500">{msg}</span>}
          </div>
        </form>
      </div>

      {/* ClawHub browser */}
      <ClawHubBrowser />

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
