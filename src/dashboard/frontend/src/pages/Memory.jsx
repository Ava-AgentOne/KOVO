import { useState, useEffect } from 'react'
import { Pencil } from 'lucide-react'

const WORKSPACE_FILES = ['MEMORY.md', 'SOUL.md', 'USER.md', 'IDENTITY.md', 'AGENTS.md', 'TOOLS.md', 'HEARTBEAT.md']

export default function Memory() {
  const [files, setFiles] = useState([])
  const [selected, setSelected] = useState(null)
  const [content, setContent] = useState('')
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')
  const [flushing, setFlushing] = useState(false)
  const [flushMsg, setFlushMsg] = useState('')

  useEffect(() => {
    fetch('/api/memory/files')
      .then(r => r.json())
      .then(d => setFiles(d.files || []))
  }, [])

  const loadFile = (name) => {
    setSelected(name)
    setEditing(false)
    setSaveMsg('')
    fetch(`/api/memory/${name}`)
      .then(r => r.json())
      .then(d => setContent(d.content || ''))
      .catch(() => setContent('Error loading file.'))
  }

  const startEdit = () => {
    setEditContent(content)
    setEditing(true)
    setSaveMsg('')
  }

  const saveFile = async () => {
    if (!selected) return
    setSaving(true)
    setSaveMsg('')
    try {
      const isRoot = WORKSPACE_FILES.includes(selected)
      const apiPath = isRoot ? selected : `memory/${selected}`
      const r = await fetch(`/api/workspace/${apiPath}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: editContent }),
      })
      if (r.ok) {
        setContent(editContent)
        setEditing(false)
        setSaveMsg('Saved')
      } else {
        const err = await r.json().catch(() => ({}))
        setSaveMsg(err.detail || 'Save failed')
      }
    } catch (e) {
      setSaveMsg(e.message)
    }
    setSaving(false)
  }

  const handleFlush = async () => {
    setFlushing(true)
    setFlushMsg('')
    try {
      const r = await fetch('/api/memory/flush', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ learnings: '' }),
      })
      const d = await r.json()
      setFlushMsg(d.flushed ? 'Flushed to MEMORY.md' : 'Flush failed')
    } catch (e) {
      setFlushMsg('Error: ' + e.message)
    }
    setFlushing(false)
  }

  const fileBtnCls = (name) => `w-full text-left text-sm px-3 py-1.5 rounded-lg transition-colors ${
    selected === name
      ? 'bg-brand-500 text-white'
      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white'
  }`

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Memory</h1>
        <div className="flex items-center gap-3">
          {flushMsg && <span className="text-xs text-gray-500">{flushMsg}</span>}
          <button
            onClick={handleFlush}
            disabled={flushing}
            className="text-sm bg-brand-500 hover:bg-brand-600 text-white px-3 py-1.5 rounded-lg disabled:opacity-50 transition-colors"
          >
            {flushing ? 'Flushing…' : 'Flush Today → MEMORY.md'}
          </button>
        </div>
      </div>

      <div className="flex gap-4 h-[calc(100vh-220px)]">
        {/* File list */}
        <div className="w-56 flex-shrink-0 space-y-1 overflow-auto">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Workspace</p>
          {WORKSPACE_FILES.map(f => (
            <button key={f} onClick={() => loadFile(f)} className={fileBtnCls(f)}>{f}</button>
          ))}
          <p className="text-xs text-gray-400 uppercase tracking-wide mt-4 mb-2">Daily Logs</p>
          {files.map(f => (
            <button key={f.name} onClick={() => loadFile(f.name)} className={fileBtnCls(f.name)}>
              {f.date}
              <span className="ml-1 text-xs text-gray-400">({(f.size / 1024).toFixed(1)}k)</span>
            </button>
          ))}
        </div>

        {/* Content viewer / editor */}
        <div className="flex-1 flex flex-col min-h-0">
          {selected && (
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm text-gray-500 flex-1 font-mono">{selected}</span>
              {saveMsg && <span className="text-xs text-gray-500">{saveMsg}</span>}
              {!editing ? (
                <button
                  onClick={startEdit}
                  className="flex items-center gap-1 text-xs bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-600 px-3 py-1 rounded-lg transition-colors"
                >
                  <Pencil size={12} /> Edit
                </button>
              ) : (
                <>
                  <button
                    onClick={() => setEditing(false)}
                    className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 px-2 py-1"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={saveFile}
                    disabled={saving}
                    className="text-xs bg-brand-500 hover:bg-brand-600 text-white px-3 py-1 rounded-lg disabled:opacity-50 transition-colors"
                  >
                    {saving ? 'Saving…' : 'Save'}
                  </button>
                </>
              )}
            </div>
          )}

          <div className="flex-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden">
            {editing ? (
              <textarea
                className="w-full h-full p-4 bg-white dark:bg-gray-900 text-sm text-gray-700 dark:text-gray-300 font-mono leading-relaxed resize-none focus:outline-none"
                value={editContent}
                onChange={e => setEditContent(e.target.value)}
                spellCheck={false}
              />
            ) : content ? (
              <pre className="p-4 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono leading-relaxed overflow-auto h-full">
                {content}
              </pre>
            ) : (
              <div className="p-4 text-gray-400 italic text-sm">Select a file to view its contents.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
