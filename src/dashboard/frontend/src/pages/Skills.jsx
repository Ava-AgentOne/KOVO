import { useState, useEffect } from 'react'

export default function Skills() {
  const [skills, setSkills] = useState([])
  const [form, setForm] = useState({ name: '', description: '', triggers: '', body: '' })
  const [creating, setCreating] = useState(false)
  const [msg, setMsg] = useState('')

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
        setMsg(`✅ Skill "${form.name}" created`)
        setForm({ name: '', description: '', triggers: '', body: '' })
        loadSkills()
      } else {
        setMsg('❌ ' + JSON.stringify(d))
      }
    } catch (e) {
      setMsg('❌ ' + e.message)
    }
    setCreating(false)
  }

  const handleDelete = async (name) => {
    if (!confirm(`Delete skill "${name}"?`)) return
    await fetch(`/api/skills/${name}`, { method: 'DELETE' })
    loadSkills()
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Skills</h1>

      {/* Skill cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {skills.map(s => (
          <div key={s.name} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <div className="flex justify-between items-start mb-2">
              <h3 className="font-semibold text-brand-400">{s.name}</h3>
              <button onClick={() => handleDelete(s.name)} className="text-xs text-red-500 hover:text-red-400">✕</button>
            </div>
            <p className="text-xs text-gray-400 mb-2">{s.description}</p>
            <div className="flex flex-wrap gap-1">
              {s.triggers.slice(0, 8).map(t => (
                <span key={t} className="text-xs bg-gray-800 text-gray-500 px-1.5 py-0.5 rounded">{t}</span>
              ))}
              {s.triggers.length > 8 && <span className="text-xs text-gray-600">+{s.triggers.length - 8}</span>}
            </div>
          </div>
        ))}
      </div>

      {/* Create form */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
        <h2 className="text-sm font-semibold text-gray-400 uppercase mb-3">Create New Skill</h2>
        <form onSubmit={handleCreate} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input
              placeholder="Skill name (e.g. backup)"
              value={form.name}
              onChange={e => setForm(f => ({...f, name: e.target.value}))}
              className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-brand-500"
              required
            />
            <input
              placeholder="Description"
              value={form.description}
              onChange={e => setForm(f => ({...f, description: e.target.value}))}
              className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-brand-500"
            />
          </div>
          <input
            placeholder="Triggers (comma-separated: backup, archive, save)"
            value={form.triggers}
            onChange={e => setForm(f => ({...f, triggers: e.target.value}))}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-brand-500"
            required
          />
          <textarea
            placeholder="Skill body (Markdown describing capabilities and procedures)"
            value={form.body}
            onChange={e => setForm(f => ({...f, body: e.target.value}))}
            rows={4}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-brand-500 resize-none"
            required
          />
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={creating}
              className="bg-brand-700 hover:bg-brand-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50"
            >
              {creating ? 'Creating…' : '+ Create Skill'}
            </button>
            {msg && <span className="text-sm text-green-400">{msg}</span>}
          </div>
        </form>
      </div>
    </div>
  )
}
