import { useState, useEffect } from 'react'
import { CheckCircle, XCircle, AlertTriangle, Pencil } from 'lucide-react'

const statusColors = {
  installed: 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-700',
  configured: 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-700',
  not_installed: 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-700',
  not_configured: 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-700',
}

const statusIcon = {
  installed: CheckCircle,
  configured: CheckCircle,
  not_installed: XCircle,
  not_configured: AlertTriangle,
}

const statusLabel = {
  installed: 'Installed',
  configured: 'Configured',
  not_installed: 'Not installed',
  not_configured: 'Not configured',
}

const ALL_STATUSES = ['configured', 'installed', 'not_configured', 'not_installed']

const inputCls = 'w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-1.5 text-sm text-gray-900 dark:text-gray-200 focus:outline-none focus:border-brand-500'

function ToolCard({ tool, onRefresh }) {
  const [editing, setEditing] = useState(false)
  const [editStatus, setEditStatus] = useState(tool.status)
  const [editConfig, setEditConfig] = useState(tool.config_needed || '')
  const [editDesc, setEditDesc] = useState(tool.description || '')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  const startEdit = () => {
    setEditStatus(tool.status)
    setEditConfig(tool.config_needed || '')
    setEditDesc(tool.description || '')
    setEditing(true)
    setMsg('')
  }

  const saveTool = async () => {
    setSaving(true)
    setMsg('')
    try {
      const body = { status: editStatus }
      if (editConfig !== (tool.config_needed || '')) body.config_needed = editConfig || null
      if (editDesc !== (tool.description || '')) body.description = editDesc
      const r = await fetch(`/api/tools/${tool.name}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (r.ok) {
        setMsg('Saved')
        setEditing(false)
        onRefresh()
      } else {
        const err = await r.json().catch(() => ({}))
        setMsg(err.detail || 'Failed')
      }
    } catch (e) {
      setMsg(e.message)
    }
    setSaving(false)
  }

  const markInstalled = async () => {
    await fetch(`/api/tools/${tool.name}/install`, { method: 'POST' })
    onRefresh()
  }

  const StatusIcon = statusIcon[tool.status] || AlertTriangle

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 dark:text-white text-base">{tool.name}</h3>
          {!editing && <p className="text-sm text-gray-500 mt-0.5">{tool.description}</p>}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {msg && <span className="text-xs text-gray-500">{msg}</span>}
          {!editing ? (
            <>
              <span className={`flex items-center gap-1 text-xs px-2 py-1 rounded-lg border whitespace-nowrap ${statusColors[tool.status] || 'text-gray-400 border-gray-300'}`}>
                <StatusIcon size={12} />
                {statusLabel[tool.status] || tool.status}
              </span>
              <button
                onClick={startEdit}
                className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
              >
                <Pencil size={14} />
              </button>
            </>
          ) : (
            <>
              <button onClick={() => setEditing(false)} className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 px-2 py-1">Cancel</button>
              <button
                onClick={saveTool}
                disabled={saving}
                className="text-xs bg-brand-500 hover:bg-brand-600 text-white px-3 py-1 rounded-lg disabled:opacity-50 transition-colors"
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
            </>
          )}
        </div>
      </div>

      {editing && (
        <div className="mt-3 space-y-2">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Description</label>
            <input className={inputCls} value={editDesc} onChange={e => setEditDesc(e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Status</label>
            <select
              className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1.5 text-sm text-gray-900 dark:text-gray-200 focus:outline-none focus:border-brand-500"
              value={editStatus}
              onChange={e => setEditStatus(e.target.value)}
            >
              {ALL_STATUSES.map(s => <option key={s} value={s}>{statusLabel[s] || s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Config notes (optional)</label>
            <input className={inputCls} value={editConfig} onChange={e => setEditConfig(e.target.value)} placeholder="What configuration is needed?" />
          </div>
        </div>
      )}

      {!editing && !tool.available && (
        <div className="mt-3 space-y-1.5">
          {tool.install_command && (
            <p className="text-xs text-gray-500">
              <span className="text-gray-400">Install: </span>
              <code className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-brand-600 dark:text-yellow-300">{tool.install_command}</code>
            </p>
          )}
          {tool.config_needed && (
            <p className="text-xs text-gray-500">
              <span className="text-gray-400">Config needed: </span>
              <span className="text-orange-500 dark:text-orange-300">{tool.config_needed}</span>
            </p>
          )}
          {tool.status === 'not_installed' && tool.install_command && (
            <button
              onClick={markInstalled}
              className="mt-2 text-xs bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 px-3 py-1 rounded-lg border border-gray-200 dark:border-gray-600 transition-colors"
            >
              Mark as installed
            </button>
          )}
        </div>
      )}
    </div>
  )
}

function RawEditor({ onClose }) {
  const [content, setContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    fetch('/api/workspace/TOOLS.md')
      .then(r => r.json())
      .then(d => setContent(d.content || ''))
      .catch(() => setContent('Error loading file.'))
  }, [])

  const save = async () => {
    setSaving(true)
    setMsg('')
    try {
      const r = await fetch('/api/workspace/TOOLS.md', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      })
      if (r.ok) setMsg('Saved')
      else { const err = await r.json().catch(() => ({})); setMsg(err.detail || 'Save failed') }
    } catch (e) { setMsg(e.message) }
    setSaving(false)
  }

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-6">
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl w-full max-w-3xl flex flex-col" style={{ height: '80vh' }}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Edit TOOLS.md</h3>
          <div className="flex items-center gap-3">
            {msg && <span className="text-xs text-gray-500">{msg}</span>}
            <button onClick={save} disabled={saving} className="text-xs bg-brand-500 hover:bg-brand-600 text-white px-3 py-1 rounded-lg disabled:opacity-50 transition-colors">
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-lg leading-none">×</button>
          </div>
        </div>
        <textarea
          className="flex-1 p-4 bg-gray-50 dark:bg-gray-900 text-sm text-gray-700 dark:text-gray-300 font-mono leading-relaxed resize-none focus:outline-none rounded-b-xl"
          value={content}
          onChange={e => setContent(e.target.value)}
          spellCheck={false}
        />
      </div>
    </div>
  )
}

export default function Tools() {
  const [tools, setTools] = useState([])
  const [loading, setLoading] = useState(true)
  const [showRaw, setShowRaw] = useState(false)

  const fetchTools = () => {
    fetch('/api/tools')
      .then(r => r.json())
      .then(d => { setTools(d.tools || []); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => {
    fetchTools()
    const id = setInterval(fetchTools, 15000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Tool Registry</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">
            {tools.filter(t => t.available).length}/{tools.length} ready
          </span>
          <button
            onClick={() => setShowRaw(true)}
            className="text-sm bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600 px-3 py-1.5 rounded-lg transition-colors"
          >
            Edit TOOLS.md
          </button>
        </div>
      </div>

      {loading && <p className="text-gray-400 italic">Loading tools…</p>}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {tools.map(tool => <ToolCard key={tool.name} tool={tool} onRefresh={fetchTools} />)}
      </div>

      {!loading && tools.length === 0 && (
        <p className="text-gray-400 italic">No tools found. Check workspace/TOOLS.md.</p>
      )}

      {showRaw && <RawEditor onClose={() => { setShowRaw(false); fetchTools() }} />}
    </div>
  )
}
