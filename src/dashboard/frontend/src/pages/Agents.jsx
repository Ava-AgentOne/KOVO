import { useState, useEffect } from 'react'
import { Plus, Bot, X, Trash2, ChevronDown } from 'lucide-react'
import ConfirmModal from '../components/ConfirmModal'

const AVAILABLE_TOOLS = ['shell', 'browser', 'google_api', 'telegram_call', 'tts', 'ollama', 'claude_cli', 'whisper', 'github']

const TEMPLATES = [
  {
    name: 'devops',
    label: 'DevOps',
    purpose: 'Server management, deployments, and infrastructure monitoring',
    tools: ['shell', 'browser'],
    soul: '# DevOps Agent\n\nYou are a DevOps specialist focused on server health, deployments, and infrastructure.\n\n## Responsibilities\n- Monitor system resources (CPU, RAM, disk)\n- Run deployments and rollbacks\n- Manage Docker containers and services\n- Investigate and fix server issues\n\n## Approach\n- Always check current state before making changes\n- Create backups before destructive operations\n- Report findings concisely via Telegram',
  },
  {
    name: 'researcher',
    label: 'Research',
    purpose: 'Web research, summarization, and report generation',
    tools: ['browser', 'shell'],
    soul: '# Research Agent\n\nYou are a research specialist who browses the web, collects information, and produces concise summaries.\n\n## Responsibilities\n- Search the web for requested topics\n- Summarize articles and reports\n- Compare options and present findings\n- Generate HTML reports with sources\n\n## Approach\n- Cite sources for all claims\n- Present balanced perspectives\n- Flag when information may be outdated',
  },
  {
    name: 'writer',
    label: 'Writer',
    purpose: 'Content creation, editing, and document management',
    tools: ['shell', 'google_api'],
    soul: '# Writing Agent\n\nYou are a writing specialist who creates and edits documents, emails, and content.\n\n## Responsibilities\n- Draft documents, emails, and messages\n- Edit and proofread existing content\n- Create Google Docs with proper formatting\n- Maintain consistent tone and style\n\n## Approach\n- Ask for clarification on tone and audience\n- Provide multiple drafts when requested\n- Use clear, concise language',
  },
]

const inputCls = 'w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-brand-500'

export default function Agents() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', soul: '', tools: [], purpose: '' })
  const [creating, setCreating] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [error, setError] = useState('')

  const fetchAgents = () => {
    fetch('/api/agents')
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => {
    fetchAgents()
    const id = setInterval(fetchAgents, 15000)
    return () => clearInterval(id)
  }, [])

  const applyTemplate = (tmpl) => {
    setForm({
      name: tmpl.name,
      purpose: tmpl.purpose,
      tools: [...tmpl.tools],
      soul: tmpl.soul,
    })
  }

  const toggleTool = (tool) => {
    setForm(f => ({
      ...f,
      tools: f.tools.includes(tool)
        ? f.tools.filter(t => t !== tool)
        : [...f.tools, tool],
    }))
  }

  const createAgent = async () => {
    if (!form.name || !form.soul) return
    setCreating(true)
    setError('')
    try {
      const r = await fetch('/api/agents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name,
          soul: form.soul,
          tools: form.tools,
          purpose: form.purpose,
        }),
      })
      const d = await r.json()
      if (d.created) {
        setForm({ name: '', soul: '', tools: [], purpose: '' })
        setShowCreate(false)
        fetchAgents()
      } else {
        setError(d.detail || 'Creation failed')
      }
    } catch (e) { setError(e.message) }
    setCreating(false)
  }

  const deleteAgent = async () => {
    if (!deleteTarget) return
    try {
      await fetch(`/api/agents/${deleteTarget}`, { method: 'DELETE' })
    } catch {}
    setDeleteTarget(null)
    fetchAgents()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Agents</h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-1 text-sm bg-brand-500 hover:bg-brand-600 text-white px-4 py-1.5 rounded-lg transition-colors"
        >
          <Plus size={14} /> New Sub-Agent
        </button>
      </div>

      {/* Main agent */}
      <div className="bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-700/40 rounded-xl p-4">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-3 h-3 rounded-full bg-brand-500" />
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">Kovo &mdash; Main Agent</h2>
          <span className="ml-auto text-xs bg-brand-100 dark:bg-brand-900/40 text-brand-700 dark:text-brand-300 px-2 py-0.5 rounded-full">active</span>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
          Primary AI assistant. Handles all requests, has access to <strong className="text-gray-800 dark:text-gray-200">all tools</strong>,
          reads SOUL.md, USER.md, MEMORY.md. Routes complex tasks to Claude Opus when needed.
        </p>
        <div className="flex flex-wrap gap-1.5">
          {AVAILABLE_TOOLS.map(t => (
            <span key={t} className="text-xs bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded-full border border-gray-200 dark:border-gray-700">
              {t}
            </span>
          ))}
        </div>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Create Sub-Agent</h3>
            <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
              <X size={16} />
            </button>
          </div>

          {/* Templates */}
          <div>
            <p className="text-xs text-gray-500 mb-2">Start from a template:</p>
            <div className="flex gap-2">
              {TEMPLATES.map(tmpl => (
                <button
                  key={tmpl.name}
                  onClick={() => applyTemplate(tmpl)}
                  className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                    form.name === tmpl.name
                      ? 'bg-brand-500 text-white border-brand-500'
                      : 'bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700 hover:border-brand-400'
                  }`}
                >
                  {tmpl.label}
                </button>
              ))}
              <button
                onClick={() => setForm({ name: '', soul: '', tools: [], purpose: '' })}
                className="text-xs px-3 py-1.5 rounded-lg border bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700 hover:border-brand-400 transition-colors"
              >
                Blank
              </button>
            </div>
          </div>

          {/* Name + Purpose */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Name</label>
              <input placeholder="e.g. devops" value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} className={inputCls} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Purpose</label>
              <input placeholder="What does this agent specialise in?" value={form.purpose} onChange={e => setForm(f => ({...f, purpose: e.target.value}))} className={inputCls} />
            </div>
          </div>

          {/* Tool selection */}
          <div>
            <label className="text-xs text-gray-500 block mb-2">Tools this agent can use:</label>
            <div className="flex flex-wrap gap-2">
              {AVAILABLE_TOOLS.map(tool => (
                <label key={tool} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.tools.includes(tool)}
                    onChange={() => toggleTool(tool)}
                    className="accent-brand-500 w-3.5 h-3.5"
                  />
                  <span className="text-xs text-gray-700 dark:text-gray-300">{tool}</span>
                </label>
              ))}
            </div>
          </div>

          {/* SOUL content */}
          <div>
            <label className="text-xs text-gray-500 block mb-1">SOUL.md &mdash; agent persona and instructions</label>
            <textarea
              placeholder={"# Agent Name\n\nDescribe the agent's personality, specialisation, and how it should handle requests."}
              value={form.soul}
              onChange={e => setForm(f => ({...f, soul: e.target.value}))}
              rows={8}
              className={`resize-none font-mono ${inputCls}`}
            />
          </div>

          {error && <p className="text-sm text-red-500">{error}</p>}

          <div className="flex gap-2">
            <button
              onClick={createAgent}
              disabled={creating || !form.name || !form.soul}
              className="bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-white px-4 py-2 rounded-lg text-sm transition-colors"
            >
              {creating ? 'Creating\u2026' : 'Create Sub-Agent'}
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="text-sm text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 px-4 py-2 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Sub-agents */}
      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
        Sub-Agents ({data?.sub_agents?.length ?? 0})
      </h2>

      {(!data?.sub_agents || data.sub_agents.length === 0) && !loading && (
        <div className="text-center py-8 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl">
          <Bot size={32} className="text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <p className="text-sm text-gray-500">No sub-agents yet</p>
          <p className="text-xs text-gray-400 mt-1">Kovo will recommend creating one when it notices repeated patterns, or create one manually.</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {(data?.sub_agents || []).map(agent => (
          <div key={agent.name} className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                <h3 className="font-semibold text-gray-900 dark:text-white">{agent.name}</h3>
              </div>
              <button
                onClick={() => setDeleteTarget(agent.name)}
                className="text-gray-400 hover:text-red-500 transition-colors p-0.5"
                title="Delete agent"
              >
                <Trash2 size={14} />
              </button>
            </div>
            {agent.purpose && <p className="text-xs text-gray-500 mb-3">{agent.purpose}</p>}
            {agent.tools && agent.tools.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-3">
                {agent.tools.map(t => (
                  <span key={t} className="text-xs bg-gray-100 dark:bg-gray-800 text-gray-500 px-2 py-0.5 rounded-full border border-gray-200 dark:border-gray-700">{t}</span>
                ))}
              </div>
            )}
            {agent.soul_preview && (
              <pre className="text-xs text-gray-500 font-mono bg-gray-50 dark:bg-gray-800 rounded-lg p-2 overflow-auto max-h-24 whitespace-pre-wrap">
                {agent.soul_preview}
              </pre>
            )}
          </div>
        ))}
      </div>

      <ConfirmModal
        open={!!deleteTarget}
        title="Delete Sub-Agent"
        message={`Are you sure you want to delete "${deleteTarget}"? The agent's SOUL.md will be removed.`}
        confirmLabel="Delete"
        confirmColor="red"
        onConfirm={deleteAgent}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}
