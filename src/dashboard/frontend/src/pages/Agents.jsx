import { useState, useEffect } from 'react'
import { Plus, Bot, X, Trash2, Brain, Zap, ChevronDown, ChevronUp } from 'lucide-react'
import { Link } from 'react-router-dom'
import ConfirmModal from '../components/ConfirmModal'

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
  const [skills, setSkills] = useState([])
  const [availableTools, setAvailableTools] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [form, setForm] = useState({ name: '', soul: '', tools: [], purpose: '' })
  const [creating, setCreating] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [error, setError] = useState('')

  const fetchAll = () => {
    Promise.all([
      fetch('/api/agents').then(r => r.json()),
      fetch('/api/skills').then(r => r.json()),
      fetch('/api/tools').then(r => r.json()),
    ]).then(([agents, skillsData, toolsData]) => {
      setData(agents)
      setSkills(skillsData.skills || [])
      setAvailableTools((toolsData.tools || []).map(t => t.name))
      setLoading(false)
      if (agents.sub_agents?.length > 0) setShowAdvanced(true)
    }).catch(() => setLoading(false))
  }

  useEffect(() => { fetchAll() }, [])

  const applyTemplate = (tmpl) => {
    setForm({ name: tmpl.name, purpose: tmpl.purpose, tools: [...tmpl.tools], soul: tmpl.soul })
  }

  const toggleTool = (tool) => {
    setForm(f => ({ ...f, tools: f.tools.includes(tool) ? f.tools.filter(t => t !== tool) : [...f.tools, tool] }))
  }

  const createAgent = async () => {
    if (!form.name || !form.soul) return
    setCreating(true)
    setError('')
    try {
      const r = await fetch('/api/agents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: form.name, soul: form.soul, tools: form.tools, purpose: form.purpose }),
      })
      const d = await r.json()
      if (d.created) {
        setForm({ name: '', soul: '', tools: [], purpose: '' })
        setShowCreate(false)
        fetchAll()
      } else { setError(d.detail || 'Creation failed') }
    } catch (e) { setError(e.message) }
    setCreating(false)
  }

  const deleteAgent = async () => {
    if (!deleteTarget) return
    try { await fetch(`/api/agents/${deleteTarget}`, { method: 'DELETE' }) } catch {}
    setDeleteTarget(null)
    fetchAll()
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Agent</h1>
        <div className="animate-pulse space-y-4">
          <div className="h-40 bg-gray-200 dark:bg-gray-800 rounded-xl" />
          <div className="h-32 bg-gray-200 dark:bg-gray-800 rounded-xl" />
        </div>
      </div>
    )
  }

  const subAgentCount = data?.sub_agents?.length || 0

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Agent</h1>

      {/* Main Agent Card */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
        <div className="flex items-start gap-4 mb-4">
          <div className="w-14 h-14 bg-brand-500 rounded-xl flex items-center justify-center flex-shrink-0">
            <Bot size={28} className="text-white" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">Kovo</h2>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-700 font-medium">Active</span>
            </div>
            <p className="text-sm text-gray-500">
              Your primary AI assistant. Handles all requests with access to every tool.
              Uses smart context loading — only loads what each message needs.
            </p>
          </div>
          <Link to="/chat" className="flex items-center gap-1.5 text-xs bg-brand-500 hover:bg-brand-600 text-white px-3 py-1.5 rounded-lg transition-colors flex-shrink-0 self-start">
            Chat →
          </Link>
        </div>

        <div className="mb-4">
          <p className="text-xs text-gray-400 mb-2">Tools ({availableTools.length})</p>
          <div className="flex flex-wrap gap-1.5">
            {availableTools.map(t => (
              <span key={t} className="text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded-full border border-gray-200 dark:border-gray-700">{t}</span>
            ))}
          </div>
        </div>

        <div>
          <p className="text-xs text-gray-400 mb-2">Always loaded</p>
          <div className="flex flex-wrap gap-1.5">
            {['SOUL.md', 'USER.md', 'IDENTITY.md', 'Pinned Memory'].map(f => (
              <span key={f} className="text-xs bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400 px-2 py-0.5 rounded-full border border-brand-200 dark:border-brand-700">{f}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Skills — primary extension mechanism */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Zap size={16} className="text-brand-500" />
            <h2 className="text-sm font-bold text-gray-700 dark:text-gray-200 uppercase tracking-wide">Skills</h2>
            <span className="text-xs text-gray-400">{skills.length} loaded</span>
          </div>
          <Link to="/skills" className="text-xs text-brand-500 hover:text-brand-600 transition-colors">Manage Skills →</Link>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
          {skills.map(s => (
            <div key={s.name} className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg px-3 py-2.5">
              <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{s.name}</p>
              <p className="text-[11px] text-gray-400 mt-0.5 line-clamp-2">{s.description}</p>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-400 mt-2 italic">
          Skills are the primary way to extend Kovo — they define procedures and knowledge for specific topics.
          Kovo loads the best-matching skill automatically based on your message.
        </p>
      </div>

      {/* Sub-Agents — advanced, collapsible */}
      <div className="border-t border-gray-200 dark:border-gray-800 pt-4">
        <button onClick={() => setShowAdvanced(!showAdvanced)} className="flex items-center gap-2 w-full text-left">
          <Brain size={16} className="text-gray-400" />
          <h2 className="text-sm font-bold text-gray-700 dark:text-gray-200 uppercase tracking-wide">Sub-Agents</h2>
          <span className="text-xs text-gray-400">({subAgentCount})</span>
          <span className="text-[10px] text-gray-300 dark:text-gray-600 ml-1">Advanced</span>
          {showAdvanced ? <ChevronUp size={14} className="text-gray-400 ml-auto" /> : <ChevronDown size={14} className="text-gray-400 ml-auto" />}
        </button>

        {showAdvanced && (
          <div className="mt-4 space-y-4">
            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg px-4 py-3">
              <p className="text-xs text-gray-500">
                Sub-agents are specialist workers that Kovo can delegate to. They have their own SOUL.md and a subset of tools.
                For most use cases, <strong className="text-gray-700 dark:text-gray-300">skills are a better choice</strong> — they're simpler and don't add the overhead of a separate agent context.
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Consider a sub-agent when you need: isolated context, different personality for a specific domain, or when Kovo recommends one after repeated patterns.
              </p>
            </div>

            {subAgentCount > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {data.sub_agents.map(agent => (
                  <div key={agent.name} className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-emerald-500" />
                        <h3 className="font-semibold text-gray-900 dark:text-white">{agent.name}</h3>
                      </div>
                      <button onClick={() => setDeleteTarget(agent.name)} className="text-gray-400 hover:text-red-500 transition-colors p-0.5" title="Delete">
                        <Trash2 size={14} />
                      </button>
                    </div>
                    {agent.purpose && <p className="text-xs text-gray-500 mb-2">{agent.purpose}</p>}
                    {agent.tools?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-2">
                        {agent.tools.map(t => (
                          <span key={t} className="text-xs bg-gray-100 dark:bg-gray-800 text-gray-500 px-1.5 py-0.5 rounded-full border border-gray-200 dark:border-gray-700">{t}</span>
                        ))}
                      </div>
                    )}
                    {agent.soul_preview && (
                      <pre className="text-xs text-gray-500 font-mono bg-gray-50 dark:bg-gray-800 rounded-lg p-2 overflow-auto max-h-20 whitespace-pre-wrap">{agent.soul_preview}</pre>
                    )}
                  </div>
                ))}
              </div>
            )}

            {subAgentCount === 0 && !showCreate && (
              <div className="text-center py-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl">
                <Bot size={28} className="text-gray-300 dark:text-gray-600 mx-auto mb-2" />
                <p className="text-sm text-gray-500">No sub-agents</p>
                <p className="text-xs text-gray-400 mt-1">Kovo handles everything with skills. Create a sub-agent only if you need one.</p>
              </div>
            )}

            {!showCreate && (
              <button onClick={() => setShowCreate(true)}
                className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-brand-500 px-3 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                <Plus size={13} /> Create Sub-Agent
              </button>
            )}

            {showCreate && (
              <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Create Sub-Agent</h3>
                  <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"><X size={16} /></button>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-2">Start from a template:</p>
                  <div className="flex gap-2">
                    {TEMPLATES.map(tmpl => (
                      <button key={tmpl.name} onClick={() => applyTemplate(tmpl)}
                        className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${form.name === tmpl.name ? 'bg-brand-500 text-white border-brand-500' : 'bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700 hover:border-brand-400'}`}>
                        {tmpl.label}
                      </button>
                    ))}
                    <button onClick={() => setForm({ name: '', soul: '', tools: [], purpose: '' })}
                      className="text-xs px-3 py-1.5 rounded-lg border bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700 hover:border-brand-400 transition-colors">
                      Blank
                    </button>
                  </div>
                </div>
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
                <div>
                  <label className="text-xs text-gray-500 block mb-2">Tools this agent can use:</label>
                  <div className="flex flex-wrap gap-2">
                    {availableTools.map(tool => (
                      <label key={tool} className="flex items-center gap-1.5 cursor-pointer">
                        <input type="checkbox" checked={form.tools.includes(tool)} onChange={() => toggleTool(tool)} className="accent-brand-500 w-3.5 h-3.5" />
                        <span className="text-xs text-gray-700 dark:text-gray-300">{tool}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs text-gray-500 block mb-1">SOUL.md &mdash; agent persona and instructions</label>
                  <textarea placeholder={"# Agent Name\n\nDescribe the agent's personality and how it should handle requests."}
                    value={form.soul} onChange={e => setForm(f => ({...f, soul: e.target.value}))} rows={8} className={`resize-none font-mono ${inputCls}`} />
                </div>
                {error && <p className="text-sm text-red-500">{error}</p>}
                <div className="flex gap-2">
                  <button onClick={createAgent} disabled={creating || !form.name || !form.soul}
                    className="bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-white px-4 py-2 rounded-lg text-sm transition-colors">
                    {creating ? 'Creating\u2026' : 'Create Sub-Agent'}
                  </button>
                  <button onClick={() => setShowCreate(false)} className="text-sm text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 px-4 py-2 transition-colors">Cancel</button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <ConfirmModal open={!!deleteTarget} title="Delete Sub-Agent"
        message={`Are you sure you want to delete "${deleteTarget}"? The agent's SOUL.md will be removed.`}
        confirmLabel="Delete" confirmColor="red" onConfirm={deleteAgent} onCancel={() => setDeleteTarget(null)} />
    </div>
  )
}
