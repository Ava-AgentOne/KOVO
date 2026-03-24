import { useState, useEffect } from 'react'

const inputCls = 'w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-brand-500'

export default function Agents() {
  const [data, setData] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', soul: '', tools: '', purpose: '' })
  const [creating, setCreating] = useState(false)

  const fetchAgents = () => {
    fetch('/api/agents')
      .then(r => r.json())
      .then(setData)
      .catch(console.error)
  }

  useEffect(() => {
    fetchAgents()
    const id = setInterval(fetchAgents, 15000)
    return () => clearInterval(id)
  }, [])

  const createAgent = async () => {
    if (!form.name || !form.soul) return
    setCreating(true)
    try {
      await fetch('/api/agents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name,
          soul: form.soul,
          tools: form.tools.split(',').map(s => s.trim()).filter(Boolean),
          purpose: form.purpose,
        }),
      })
      setForm({ name: '', soul: '', tools: '', purpose: '' })
      setShowCreate(false)
      fetchAgents()
    } catch (e) { console.error(e) }
    setCreating(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Agents</h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="text-sm bg-brand-500 hover:bg-brand-600 text-white px-4 py-1.5 rounded-lg transition-colors"
        >
          + New Sub-Agent
        </button>
      </div>

      {/* Main agent card */}
      <div className="bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-700/40 rounded-xl p-4">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-3 h-3 rounded-full bg-brand-500" />
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">Kovo — Main Agent</h2>
          <span className="ml-auto text-xs bg-brand-100 dark:bg-brand-900/40 text-brand-700 dark:text-brand-300 px-2 py-0.5 rounded-full">active</span>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
          Your primary AI assistant. Handles all requests, has access to <strong className="text-gray-800 dark:text-gray-200">all tools</strong>,
          reads SOUL.md, USER.md, MEMORY.md. Recommends sub-agents when it notices repeated patterns.
        </p>
        <div className="flex flex-wrap gap-1.5">
          {['shell', 'browser', 'google_api', 'telegram_call', 'tts', 'ollama', 'claude_cli', 'whisper'].map(t => (
            <span key={t} className="text-xs bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded-full border border-gray-200 dark:border-gray-700">
              {t}
            </span>
          ))}
        </div>
      </div>

      {/* Create sub-agent form */}
      {showCreate && (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-4 space-y-3">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Create Sub-Agent</h3>
          <input placeholder="Name (e.g. devops)" value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} className={inputCls} />
          <input placeholder="Purpose (e.g. DevOps and server management)" value={form.purpose} onChange={e => setForm(f => ({...f, purpose: e.target.value}))} className={inputCls} />
          <input placeholder="Tools (comma-separated, e.g. shell,browser)" value={form.tools} onChange={e => setForm(f => ({...f, tools: e.target.value}))} className={inputCls} />
          <textarea
            placeholder="SOUL.md content — sub-agent's persona and specialisation"
            value={form.soul}
            onChange={e => setForm(f => ({...f, soul: e.target.value}))}
            rows={6}
            className={`resize-none font-mono ${inputCls}`}
          />
          <div className="flex gap-2">
            <button
              onClick={createAgent}
              disabled={creating || !form.name || !form.soul}
              className="bg-brand-500 hover:bg-brand-600 disabled:bg-gray-200 dark:disabled:bg-gray-700 disabled:text-gray-400 text-white px-4 py-1.5 rounded-lg text-sm transition-colors"
            >
              {creating ? 'Creating…' : 'Create'}
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 px-4 py-1.5 rounded-lg text-sm transition-colors"
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

      {data?.sub_agents?.length === 0 && (
        <p className="text-gray-400 italic text-sm">
          No sub-agents yet. Kovo will recommend creating one when it notices a pattern,
          or you can create one manually above.
        </p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {(data?.sub_agents || []).map(agent => (
          <div key={agent.name} className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-green-500" />
              <h3 className="font-semibold text-gray-900 dark:text-white">{agent.name}</h3>
            </div>
            {agent.purpose && <p className="text-xs text-gray-500 mb-3">{agent.purpose}</p>}
            {agent.tools.length > 0 && (
              <div className="mb-3">
                <p className="text-xs text-gray-400 mb-1">Tools:</p>
                <div className="flex flex-wrap gap-1">
                  {agent.tools.map(t => (
                    <span key={t} className="text-xs bg-gray-100 dark:bg-gray-800 text-gray-500 px-2 py-0.5 rounded-full border border-gray-200 dark:border-gray-700">{t}</span>
                  ))}
                </div>
              </div>
            )}
            {agent.soul_preview && (
              <div>
                <p className="text-xs text-gray-400 mb-1">SOUL preview:</p>
                <pre className="text-xs text-gray-500 font-mono bg-gray-50 dark:bg-gray-800 rounded-lg p-2 overflow-auto max-h-24 whitespace-pre-wrap">
                  {agent.soul_preview}
                </pre>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
