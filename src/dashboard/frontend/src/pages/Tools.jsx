import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  CheckCircle, XCircle, AlertTriangle,
  Terminal, Globe, Volume2, Database, Brain, Mic,
  Phone, Cloud, Github, Search, Link2, Bell,
} from 'lucide-react'

// ── Tool metadata — icons, categories, better descriptions ──────
const TOOL_META = {
  shell:          { icon: Terminal, color: 'bg-gray-600',   category: 'core',          desc: 'Execute system commands, manage files, install packages' },
  browser:        { icon: Globe,    color: 'bg-blue-500',   category: 'core',          desc: 'Playwright headless Chromium for scraping, screenshots, automation' },
  claude_cli:     { icon: Brain,    color: 'bg-brand-500',  category: 'ai',            desc: 'Claude Code CLI subprocess — KOVO\'s brain for complex reasoning' },
  ollama:         { icon: Database, color: 'bg-gray-500',   category: 'ai',            desc: 'Local LLM for heartbeats and cheap tasks (optional)' },
  whisper:        { icon: Mic,      color: 'bg-purple-500', category: 'ai',            desc: 'Voice transcription via Groq API (whisper-large-v3-turbo)' },
  tts:            { icon: Volume2,  color: 'bg-emerald-500',category: 'communication', desc: 'Text-to-speech engine (edge-tts) for voice messages and calls' },
  telegram_call:  { icon: Phone,    color: 'bg-amber-500',  category: 'communication', desc: 'Real Telegram voice calls for urgent alerts (needs second SIM)' },
  google_api:     { icon: Cloud,    color: 'bg-blue-600',   category: 'integration',   desc: 'Google Docs, Drive, Gmail, Calendar, Sheets via OAuth2' },
  github:         { icon: Github,   color: 'bg-gray-800 dark:bg-gray-600', category: 'integration', desc: 'Repository management, issues, PRs, update checker' },
}

const CATEGORIES = [
  { id: 'core',          label: 'Core',          desc: 'Essential system capabilities' },
  { id: 'ai',            label: 'AI & Models',   desc: 'Language models and transcription' },
  { id: 'communication', label: 'Communication', desc: 'Voice and messaging' },
  { id: 'integration',   label: 'Integrations',  desc: 'External services' },
]

const statusConfig = {
  configured:     { icon: CheckCircle,   label: 'Configured',     cls: 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-700' },
  installed:      { icon: CheckCircle,   label: 'Installed',      cls: 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-700' },
  not_configured: { icon: AlertTriangle, label: 'Needs Config',   cls: 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-700' },
  not_installed:  { icon: XCircle,       label: 'Not Installed',  cls: 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-700' },
}

function ToolCard({ tool }) {
  const cfg = statusConfig[tool.status] || statusConfig.not_configured
  const StatusIcon = cfg.icon
  const meta = TOOL_META[tool.name] || {}
  const Icon = meta.icon || Terminal

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
      <div className="flex items-start gap-3 mb-2">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${meta.color || 'bg-gray-500'}`}>
          <Icon size={18} className="text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h3 className="font-semibold text-gray-900 dark:text-white text-sm">{tool.name}</h3>
            <span className={`flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full border whitespace-nowrap ${cfg.cls}`}>
              <StatusIcon size={10} />
              {cfg.label}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">{meta.desc || tool.description}</p>
        </div>
      </div>

      {tool.config_needed && (
        <div className="flex items-center justify-between text-xs bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-700/40 rounded-lg px-3 py-2 mt-2 text-amber-700 dark:text-amber-400">
          <span>{tool.config_needed}</span>
          <Link to="/settings" className="text-brand-500 hover:text-brand-600 font-medium ml-2 whitespace-nowrap">
            Settings →
          </Link>
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

export default function Tools() {
  const [tools, setTools] = useState([])
  const [loading, setLoading] = useState(true)
  

  const fetchTools = () => {
    fetch('/api/tools')
      .then(r => r.json())
      .then(d => { setTools(d.tools || []); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => {
    fetchTools()
    const id = setInterval(fetchTools, 60000)
    return () => clearInterval(id)
  }, [])

  const ready = tools.filter(t => t.available).length
  const needsConfig = tools.filter(t => t.status === 'not_configured').length

  // Group tools by category
  const grouped = CATEGORIES.map(cat => ({
    ...cat,
    tools: tools.filter(t => (TOOL_META[t.name]?.category || 'core') === cat.id),
  })).filter(cat => cat.tools.length > 0)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Tools</h1>
          {!loading && (
            <p className="text-sm text-gray-500 mt-0.5">
              {ready}/{tools.length} ready{needsConfig > 0 ? ` \u00b7 ${needsConfig} need configuration` : ''}
            </p>
          )}
        </div>

      </div>

      {loading && (
        <div className="animate-pulse grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1,2,3,4].map(i => <div key={i} className="h-28 bg-gray-200 dark:bg-gray-800 rounded-xl" />)}
        </div>
      )}

      {grouped.map(cat => (
        <div key={cat.id}>
          <div className="flex items-center gap-2 mb-3">
            <h2 className="text-sm font-bold text-gray-700 dark:text-gray-200 uppercase tracking-wide">{cat.label}</h2>
            <span className="text-xs text-gray-400 dark:text-gray-500">{cat.desc}</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {cat.tools.map(tool => <ToolCard key={tool.name} tool={tool} />)}
          </div>
        </div>
      ))}

      {!loading && tools.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-400">No tools found.</p>
          <p className="text-xs text-gray-400 mt-1">Check workspace/TOOLS.md</p>
        </div>
      )}

      
    </div>
  )
}
