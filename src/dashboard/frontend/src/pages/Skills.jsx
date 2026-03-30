import { useState, useEffect } from 'react'
import { Plus, Trash2, RefreshCw, Zap, ChevronDown, ChevronUp, X, Eye } from 'lucide-react'
import ConfirmModal from '../components/ConfirmModal'

const inputCls = 'w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-brand-500'

function SkillCard({ skill, onDelete, onView }) {
  const [expanded, setExpanded] = useState(false)
  const triggers = skill.triggers || []
  const showAll = expanded || triggers.length <= 8
  const visible = showAll ? triggers : triggers.slice(0, 8)

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <Zap size={14} className="text-brand-500 flex-shrink-0" />
          <h3 className="font-semibold text-gray-900 dark:text-white text-sm">{skill.name}</h3>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <button onClick={() => onView(skill)} className="text-gray-300 hover:text-brand-500 transition-colors p-1" title="View SKILL.md">
            <Eye size={13} />
          </button>
          <button onClick={() => onDelete(skill.name)} className="text-gray-300 hover:text-red-500 transition-colors p-1" title="Delete">
            <Trash2 size={13} />
          </button>
        </div>
      </div>
      <p className="text-xs text-gray-500 mb-3 line-clamp-2">{skill.description}</p>
      <div className="flex flex-wrap gap-1">
        {visible.map((t, i) => (
          <span key={i} className="text-[10px] bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 px-1.5 py-0.5 rounded border border-gray-200 dark:border-gray-700">{t}</span>
        ))}
        {!showAll && (
          <button
            onClick={() => setExpanded(true)}
            className="text-[10px] bg-brand-50 dark:bg-brand-900/20 text-brand-500 px-1.5 py-0.5 rounded border border-brand-200 dark:border-brand-700 hover:bg-brand-100 dark:hover:bg-brand-900/40 transition-colors"
          >
            +{triggers.length - 8} more
          </button>
        )}
        {expanded && triggers.length > 8 && (
          <button
            onClick={() => setExpanded(false)}
            className="text-[10px] text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 px-1.5 py-0.5"
          >
            show less
          </button>
        )}
      </div>
    </div>
  )
}

function ViewModal({ skill, onClose }) {
  const [content, setContent] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!skill) return
    fetch(`/api/skills/${skill.name}`)
      .then(r => r.json())
      .then(d => { setContent(d.content || d.soul || 'No content found.'); setLoading(false) })
      .catch(() => { setContent('Error loading skill.'); setLoading(false) })
  }, [skill])

  if (!skill) return null

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-6">
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl w-full max-w-2xl flex flex-col" style={{ maxHeight: '70vh' }}>
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-2">
            <Zap size={14} className="text-brand-500" />
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{skill.name}/SKILL.md</h3>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-lg leading-none">&times;</button>
        </div>
        <div className="flex-1 overflow-auto p-5">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw size={16} className="text-brand-500 animate-spin" />
            </div>
          ) : (
            <pre className="text-sm text-gray-700 dark:text-gray-300 font-mono leading-relaxed whitespace-pre-wrap">{content}</pre>
          )}
        </div>
      </div>
    </div>
  )
}

export default function Skills() {
  const [skills, setSkills] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [viewTarget, setViewTarget] = useState(null)
  const [form, setForm] = useState({ name: '', description: '', triggers: '', body: '' })
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')

  const fetchSkills = () => {
    fetch('/api/skills')
      .then(r => r.json())
      .then(d => { setSkills(d.skills || []); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => { fetchSkills() }, [])

  const createSkill = async (e) => {
    e.preventDefault()
    if (!form.name) return
    setCreating(true)
    setError('')
    try {
      const r = await fetch('/api/skills', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const d = await r.json()
      if (d.created) {
        setForm({ name: '', description: '', triggers: '', body: '' })
        setShowCreate(false)
        fetchSkills()
      } else { setError(d.detail || 'Creation failed') }
    } catch (e) { setError(e.message) }
    setCreating(false)
  }

  const deleteSkill = async () => {
    if (!deleteTarget) return
    try { await fetch(`/api/skills/${deleteTarget}`, { method: 'DELETE' }) } catch {}
    setDeleteTarget(null)
    fetchSkills()
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Skills</h1>
          {!loading && (
            <p className="text-sm text-gray-500 mt-0.5">{skills.length} loaded · Kovo picks the best match per message</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchSkills}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            title="Reload"
          >
            <RefreshCw size={14} />
          </button>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="flex items-center gap-1.5 text-sm bg-brand-500 hover:bg-brand-600 text-white px-4 py-1.5 rounded-lg transition-colors"
          >
            <Plus size={14} /> New Skill
          </button>
        </div>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Create New Skill</h3>
            <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
              <X size={16} />
            </button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Name</label>
              <input placeholder="e.g. backup" value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} className={inputCls} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Description</label>
              <input placeholder="What this skill does" value={form.description} onChange={e => setForm(f => ({...f, description: e.target.value}))} className={inputCls} />
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Triggers (comma-separated keywords)</label>
            <input placeholder="backup, archive, save, snapshot" value={form.triggers} onChange={e => setForm(f => ({...f, triggers: e.target.value}))} className={inputCls} />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">SKILL.md content</label>
            <textarea
              placeholder={"# Backup Skill\n\n## When triggered\n1. Run backup script\n2. Report result via Telegram"}
              value={form.body}
              onChange={e => setForm(f => ({...f, body: e.target.value}))}
              rows={6}
              className={`resize-none font-mono ${inputCls}`}
            />
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
          <div className="flex gap-2">
            <button onClick={createSkill} disabled={creating || !form.name}
              className="bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-white px-4 py-2 rounded-lg text-sm transition-colors">
              {creating ? 'Creating…' : 'Create Skill'}
            </button>
            <button onClick={() => setShowCreate(false)}
              className="text-sm text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 px-4 py-2 transition-colors">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 animate-pulse">
          {[1,2,3,4,5,6].map(i => <div key={i} className="h-28 bg-gray-200 dark:bg-gray-800 rounded-xl" />)}
        </div>
      )}

      {/* Skills grid */}
      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {skills.map(s => (
            <SkillCard
              key={s.name}
              skill={s}
              onDelete={(name) => setDeleteTarget(name)}
              onView={(skill) => setViewTarget(skill)}
            />
          ))}
        </div>
      )}

      {!loading && skills.length === 0 && (
        <div className="text-center py-12 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl">
          <Zap size={28} className="text-gray-300 dark:text-gray-600 mx-auto mb-2" />
          <p className="text-gray-500 text-sm">No skills loaded</p>
          <p className="text-xs text-gray-400 mt-1">Create a skill to teach Kovo new procedures</p>
        </div>
      )}

      {/* View modal */}
      <ViewModal skill={viewTarget} onClose={() => setViewTarget(null)} />

      {/* Delete confirmation */}
      <ConfirmModal
        open={!!deleteTarget}
        title="Delete Skill"
        message={`Are you sure you want to delete the "${deleteTarget}" skill? This will remove the skill directory and its SKILL.md file.`}
        confirmLabel="Delete"
        confirmColor="red"
        onConfirm={deleteSkill}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}
