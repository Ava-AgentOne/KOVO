import { useState, useEffect } from 'react'
import { Pencil, FileText, BookOpen, Brain, Loader2 } from 'lucide-react'

const WORKSPACE_FILES = ['MEMORY.md', 'SOUL.md', 'USER.md', 'IDENTITY.md', 'AGENTS.md', 'TOOLS.md', 'HEARTBEAT.md']

function renderMarkdown(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Code blocks
    .replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) =>
      `<pre class="bg-gray-100 dark:bg-gray-800 rounded-lg px-3 py-2 my-2 text-xs font-mono overflow-x-auto whitespace-pre-wrap border border-gray-200 dark:border-gray-700"><code>${code.trim()}</code></pre>`)
    // Inline code
    .replace(/`([^`]+)`/g, '<code class="bg-gray-200 dark:bg-gray-700 px-1 py-0.5 rounded text-brand-600 dark:text-yellow-300 text-xs font-mono">$1</code>')
    // Bold
    .replace(/\*\*(.*?)\*\*/g, '<strong class="text-gray-900 dark:text-white">$1</strong>')
    // Headers
    .replace(/^### (.+)$/gm, '<h3 class="text-sm font-semibold text-gray-700 dark:text-gray-200 mt-4 mb-1">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-base font-bold text-gray-800 dark:text-gray-100 mt-5 mb-2 pb-1 border-b border-gray-200 dark:border-gray-700">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="text-lg font-bold text-gray-900 dark:text-white mt-4 mb-2">$1</h1>')
    // List items
    .replace(/^- (.+)$/gm, '<div class="flex gap-2 ml-2 my-0.5"><span class="text-gray-400 flex-shrink-0">•</span><span>$1</span></div>')
    // Session markers [HH:MM]
    .replace(/\[(\d{2}:\d{2})\]/g, '<span class="text-brand-500 font-mono text-xs font-medium">[$1]</span>')
    // Newlines
    .replace(/\n/g, '<br/>')
    // Clean up double breaks around block elements
    .replace(/<br\/>(<h[1-3]|<pre|<div)/g, '$1')
    .replace(/(<\/h[1-3]>|<\/pre>|<\/div>)<br\/>/g, '$1')
}

function FileIcon({ name }) {
  if (name === 'MEMORY.md') return <Brain size={14} className="text-brand-500" />
  if (name === 'SOUL.md') return <BookOpen size={14} className="text-pink-500" />
  return <FileText size={14} className="text-gray-400" />
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  return `${(bytes / 1024).toFixed(1)} KB`
}

export default function Memory() {
  const [files, setFiles] = useState([])
  const [selected, setSelected] = useState(null)
  const [content, setContent] = useState('')
  const [loadingContent, setLoadingContent] = useState(false)
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
    setLoadingContent(true)
    fetch(`/api/memory/${name}`)
      .then(r => r.json())
      .then(d => { setContent(d.content || ''); setLoadingContent(false) })
      .catch(() => { setContent('Error loading file.'); setLoadingContent(false) })
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
      setFlushMsg(d.flushed ? 'Extracted to MEMORY.md' : (d.error || 'Flush failed'))
      // Reload MEMORY.md if currently selected
      if (selected === 'MEMORY.md') loadFile('MEMORY.md')
    } catch (e) {
      setFlushMsg('Error: ' + e.message)
    }
    setFlushing(false)
  }

  const fileBtnCls = (name) => `w-full flex items-center gap-2 text-left text-sm px-3 py-1.5 rounded-lg transition-colors ${
    selected === name
      ? 'bg-brand-500 text-white'
      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white'
  }`

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Memory</h1>
        <div className="flex items-center gap-3">
          {flushMsg && <span className="text-xs text-gray-500">{flushMsg}</span>}
          <button
            onClick={handleFlush}
            disabled={flushing}
            className="flex items-center gap-1.5 text-sm bg-brand-500 hover:bg-brand-600 text-white px-3 py-1.5 rounded-lg disabled:opacity-50 transition-colors"
          >
            {flushing ? <Loader2 size={13} className="animate-spin" /> : <Brain size={13} />}
            {flushing ? 'Extracting…' : 'Extract Learnings'}
          </button>
        </div>
      </div>

      <div className="flex gap-4 h-[calc(100vh-200px)]">
        {/* File list */}
        <div className="w-56 flex-shrink-0 space-y-1 overflow-auto">
          <p className="text-xs font-bold text-gray-700 dark:text-gray-200 uppercase tracking-wide mb-2">Workspace</p>
          {WORKSPACE_FILES.map(f => (
            <button key={f} onClick={() => loadFile(f)} className={fileBtnCls(f)}>
              <FileIcon name={f} />
              <span className="truncate">{f}</span>
            </button>
          ))}

          <p className="text-xs font-bold text-gray-700 dark:text-gray-200 uppercase tracking-wide mt-5 mb-2">Daily Logs</p>
          {files.length === 0 && (
            <p className="text-xs text-gray-400 italic px-3">No logs yet</p>
          )}
          {files.map(f => (
            <button key={f.name} onClick={() => loadFile(f.name)} className={fileBtnCls(f.name)}>
              <FileText size={14} className={selected === f.name ? 'text-white' : 'text-gray-400'} />
              <span className="truncate">{f.date}</span>
              <span className={`ml-auto text-[10px] ${selected === f.name ? 'text-white/60' : 'text-gray-400'}`}>
                {formatSize(f.size)}
              </span>
            </button>
          ))}
        </div>

        {/* Content viewer / editor */}
        <div className="flex-1 flex flex-col min-h-0">
          {selected && (
            <div className="flex items-center gap-2 mb-2 flex-shrink-0">
              <span className="text-sm text-gray-500 flex-1 font-mono">{selected}</span>
              {saveMsg && <span className="text-xs text-gray-500">{saveMsg}</span>}
              {!editing ? (
                <button
                  onClick={startEdit}
                  className="flex items-center gap-1.5 text-xs bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-600 px-3 py-1 rounded-lg transition-colors"
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
            {loadingContent ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 size={20} className="text-brand-500 animate-spin" />
              </div>
            ) : editing ? (
              <textarea
                className="w-full h-full p-4 bg-white dark:bg-gray-900 text-sm text-gray-700 dark:text-gray-300 font-mono leading-relaxed resize-none focus:outline-none"
                value={editContent}
                onChange={e => setEditContent(e.target.value)}
                spellCheck={false}
              />
            ) : content ? (
              <div
                className="p-5 text-sm text-gray-700 dark:text-gray-300 leading-relaxed overflow-auto h-full"
                dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-full gap-2">
                <BookOpen size={28} className="text-gray-300 dark:text-gray-600" />
                <p className="text-gray-400 text-sm">Select a file to view</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
