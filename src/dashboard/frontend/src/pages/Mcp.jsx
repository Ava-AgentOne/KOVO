import { useState, useEffect } from 'react'
import { Plus, Trash2, RefreshCw, Plug, X, CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import ConfirmModal from '../components/ConfirmModal'
import PageHeader from '../components/PageHeader'
import EmptyState from '../components/EmptyState'

const inputCls = 'w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-brand-500'

function ServerCard({ srv, onDelete, onToggle, onTest, testState }) {
  const headerKeys = Object.keys(srv.headers || {})
  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <Plug size={14} className={srv.enabled ? 'text-brand-500' : 'text-gray-400'} />
          <h3 className="font-semibold text-gray-900 dark:text-white text-sm truncate">{srv.name}</h3>
          <span className="text-[10px] uppercase bg-gray-100 dark:bg-gray-800 text-gray-500 px-1.5 py-0.5 rounded">{srv.type}</span>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <button onClick={() => onTest(srv.name)} className="text-gray-300 hover:text-brand-500 p-1" title="Test connection">
            {testState === 'testing' ? <Loader2 size={13} className="animate-spin" />
              : testState === 'ok' ? <CheckCircle2 size={13} className="text-emerald-500" />
              : testState === 'fail' ? <XCircle size={13} className="text-red-500" />
              : <RefreshCw size={13} />}
          </button>
          <button onClick={() => onDelete(srv.name)} className="text-gray-300 hover:text-red-500 p-1" title="Remove">
            <Trash2 size={13} />
          </button>
        </div>
      </div>
      <p className="text-xs text-gray-500 font-mono truncate mb-2">{srv.url || srv.command}</p>
      {headerKeys.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {headerKeys.map(k => (
            <span key={k} className="text-[10px] bg-gray-100 dark:bg-gray-800 text-gray-500 px-1.5 py-0.5 rounded border border-gray-200 dark:border-gray-700">
              {k}: {srv.headers[k]}
            </span>
          ))}
        </div>
      )}
      <label className="flex items-center gap-2 text-xs text-gray-500 cursor-pointer">
        <input type="checkbox" checked={srv.enabled} onChange={e => onToggle(srv.name, e.target.checked)} className="accent-brand-500" />
        {srv.enabled ? 'Enabled' : 'Disabled'}
      </label>
    </div>
  )
}

export default function Mcp() {
  const [servers, setServers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [tests, setTests] = useState({})
  const [error, setError] = useState('')
  const [form, setForm] = useState({ name: '', type: 'sse', url: '', headerKey: 'Authorization', headerVal: '' })
  const [saving, setSaving] = useState(false)

  const fetchServers = () => {
    fetch('/api/mcp/servers')
      .then(r => r.json())
      .then(d => { setServers(d.servers || []); setLoading(false) })
      .catch(() => setLoading(false))
  }
  useEffect(() => { fetchServers() }, [])

  const addServer = async () => {
    if (!form.name || !form.url) { setError('Name and URL are required.'); return }
    setSaving(true); setError('')
    const body = { name: form.name, type: form.type, url: form.url, enabled: true }
    if (form.headerVal) body.headers = { [form.headerKey]: form.headerVal }
    try {
      const r = await fetch('/api/mcp/servers', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      })
      const d = await r.json()
      if (d.added) {
        setForm({ name: '', type: 'sse', url: '', headerKey: 'Authorization', headerVal: '' })
        setShowAdd(false); fetchServers()
      } else { setError(d.detail || 'Add failed') }
    } catch (e) { setError(e.message) }
    setSaving(false)
  }

  const removeServer = async () => {
    if (!deleteTarget) return
    try { await fetch(`/api/mcp/servers/${deleteTarget}`, { method: 'DELETE' }) } catch {}
    setDeleteTarget(null); fetchServers()
  }

  const toggleServer = async (name, enabled) => {
    setServers(prev => prev.map(s => s.name === name ? { ...s, enabled } : s))
    try {
      await fetch(`/api/mcp/servers/${name}/toggle`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ enabled }),
      })
    } catch {}
  }

  const testServer = async (name) => {
    setTests(t => ({ ...t, [name]: 'testing' }))
    try {
      const r = await fetch(`/api/mcp/servers/${name}/test`, { method: 'POST' })
      const d = await r.json()
      setTests(t => ({ ...t, [name]: d.reachable ? 'ok' : 'fail' }))
    } catch { setTests(t => ({ ...t, [name]: 'fail' })) }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <PageHeader title="Integrations" icon={Plug} accent="teal"
          subtitle={!loading ? `${servers.length} MCP server${servers.length === 1 ? '' : 's'} · connect Kovo to external tools` : undefined} />
        <div className="flex items-center gap-2">
          <button onClick={fetchServers} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800" title="Reload">
            <RefreshCw size={14} />
          </button>
          <button onClick={() => setShowAdd(!showAdd)} className="flex items-center gap-1.5 text-sm bg-brand-500 hover:bg-brand-600 text-white px-4 py-1.5 rounded-lg transition-colors">
            <Plus size={14} /> Add Server
          </button>
        </div>
      </div>

      {showAdd && (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Add MCP Server</h3>
            <button onClick={() => setShowAdd(false)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"><X size={16} /></button>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Name</label>
              <input placeholder="home_assistant" value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} className={inputCls} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Transport</label>
              <select value={form.type} onChange={e => setForm(f => ({...f, type: e.target.value}))} className={inputCls}>
                <option value="sse">sse</option>
                <option value="http">http</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">URL</label>
              <input placeholder="http://10.0.1.20:8123/mcp_server/sse" value={form.url} onChange={e => setForm(f => ({...f, url: e.target.value}))} className={inputCls} />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Auth header (optional)</label>
              <input value={form.headerKey} onChange={e => setForm(f => ({...f, headerKey: e.target.value}))} className={inputCls} />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-500 block mb-1">Header value — use ${'{'}ENV_VAR{'}'} for secrets</label>
              <input placeholder="Bearer ${HA_TOKEN}" value={form.headerVal} onChange={e => setForm(f => ({...f, headerVal: e.target.value}))} className={inputCls} />
            </div>
          </div>
          <p className="text-[11px] text-gray-400">Tip: put the real token in <code>config/.env</code> (e.g. <code>HA_TOKEN=…</code>) and reference it here as <code>${'{'}HA_TOKEN{'}'}</code> so secrets never sit in settings.yaml.</p>
          {error && <p className="text-sm text-red-500">{error}</p>}
          <div className="flex gap-2">
            <button onClick={addServer} disabled={saving || !form.name || !form.url} className="bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-white px-4 py-2 rounded-lg text-sm transition-colors">
              {saving ? 'Saving…' : 'Add Server'}
            </button>
            <button onClick={() => setShowAdd(false)} className="text-sm text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 px-4 py-2">Cancel</button>
          </div>
        </div>
      )}

      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 animate-pulse">
          {[1,2,3].map(i => <div key={i} className="h-32 bg-gray-200 dark:bg-gray-800 rounded-xl" />)}
        </div>
      )}

      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {servers.map(s => (
            <ServerCard key={s.name} srv={s} testState={tests[s.name]}
              onDelete={setDeleteTarget} onToggle={toggleServer} onTest={testServer} />
          ))}
        </div>
      )}

      {!loading && servers.length === 0 && (
        <EmptyState icon={Plug} title="No integrations connected"
          hint="Add an MCP server to give Kovo new tools (Home Assistant, GitHub, …)"
          actionLabel="Add Server" onAction={() => setShowAdd(true)} />
      )}

      <ConfirmModal
        open={!!deleteTarget}
        title="Remove MCP Server"
        message={`Remove the "${deleteTarget}" integration? Kovo will lose access to its tools.`}
        confirmLabel="Remove"
        confirmColor="red"
        onConfirm={removeServer}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}
