import { useState, useEffect } from 'react'
import { CheckCircle, XCircle, AlertTriangle, ExternalLink } from 'lucide-react'

const statusConfig = {
  configured:     { icon: CheckCircle,   label: 'Configured',     cls: 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-700' },
  installed:      { icon: CheckCircle,   label: 'Installed',      cls: 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-700' },
  not_configured: { icon: AlertTriangle, label: 'Needs Config',   cls: 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-700' },
  not_installed:  { icon: XCircle,       label: 'Not Installed',  cls: 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-700' },
}

function ToolCard({ tool }) {
  const cfg = statusConfig[tool.status] || statusConfig.not_configured
  const StatusIcon = cfg.icon

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
      <div className="flex items-start justify-between gap-2 mb-2">
        <h3 className="font-semibold text-gray-900 dark:text-white text-base">{tool.name}</h3>
        <span className={`flex items-center gap-1 text-xs px-2 py-1 rounded-lg border whitespace-nowrap ${cfg.cls}`}>
          <StatusIcon size={12} />
          {cfg.label}
        </span>
      </div>
      <p className="text-sm text-gray-500 mb-3">{tool.description}</p>

      {tool.config_needed && (
        <div className="text-xs bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-700/40 rounded-lg px-3 py-2 text-amber-700 dark:text-amber-400">
          {tool.config_needed}
        </div>
      )}
      {tool.install_command && tool.status === 'not_installed' && (
        <div className="text-xs bg-gray-50 dark:bg-gray-800 rounded-lg px-3 py-2 mt-2 font-mono text-gray-600 dark:text-gray-400">
          $ {tool.install_command}
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
              {saving ? 'Saving\u2026' : 'Save'}
            </button>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-lg leading-none">&times;</button>
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

  const ready = tools.filter(t => t.available).length
  const needsConfig = tools.filter(t => t.status === 'not_configured').length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Tool Registry</h1>
          {!loading && (
            <p className="text-sm text-gray-500 mt-0.5">
              {ready}/{tools.length} ready{needsConfig > 0 ? ` \u00b7 ${needsConfig} need configuration` : ''}
            </p>
          )}
        </div>
        <button
          onClick={() => setShowRaw(true)}
          className="flex items-center gap-1 text-sm bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600 px-3 py-1.5 rounded-lg transition-colors"
        >
          <ExternalLink size={12} /> Edit TOOLS.md
        </button>
      </div>

      {loading && (
        <div className="animate-pulse grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1,2,3,4].map(i => <div key={i} className="h-28 bg-gray-200 dark:bg-gray-800 rounded-xl" />)}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {tools.map(tool => <ToolCard key={tool.name} tool={tool} />)}
      </div>

      {!loading && tools.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-400">No tools found.</p>
          <p className="text-xs text-gray-400 mt-1">Check workspace/TOOLS.md</p>
        </div>
      )}

      {showRaw && <RawEditor onClose={() => { setShowRaw(false); fetchTools() }} />}
    </div>
  )
}
