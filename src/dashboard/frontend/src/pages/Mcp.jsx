import { useState, useEffect, useRef } from 'react'
import { Plus, Trash2, RefreshCw, Plug, X, CheckCircle2, XCircle, Loader2, Store, Search, ExternalLink, Download, Globe, ShieldAlert } from 'lucide-react'
import ConfirmModal from '../components/ConfirmModal'
import PageHeader from '../components/PageHeader'
import EmptyState from '../components/EmptyState'
import { MCP_CATALOG } from '../data/mcpCatalog'

const inputCls = 'w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-brand-500'

const EMPTY_FORM = {
  name: '', type: 'sse', url: '',
  headerKey: 'Authorization', headerVal: '',
  command: '', args: '', env: '',
}

function ServerCard({ srv, onDelete, onToggle, onTest, testState }) {
  const headerKeys = Object.keys(srv.headers || {})
  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <Plug size={14} className={srv.enabled ? 'text-teal-500' : 'text-gray-400'} />
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

function StoreCard({ entry, installed, onInstall }) {
  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 flex flex-col">
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-2 min-w-0">
          <div className="p-1.5 rounded-lg bg-teal-500/10 text-teal-500 flex-shrink-0">
            <Plug size={14} />
          </div>
          <h3 className="font-semibold text-gray-900 dark:text-white text-sm truncate">{entry.label}</h3>
        </div>
        <span className="text-[10px] uppercase bg-gray-100 dark:bg-gray-800 text-gray-500 px-1.5 py-0.5 rounded flex-shrink-0">{entry.type}</span>
      </div>
      {entry.publisher && (
        <p className="text-[10px] text-gray-400 font-mono truncate mb-1">{entry.publisher}{entry.version ? ` · v${entry.version}` : ''}</p>
      )}
      <p className="text-xs text-gray-500 mb-2">{entry.desc}</p>
      {entry.needs && (
        <p className="text-[11px] text-amber-600 dark:text-amber-400/90 mb-2">Needs: {entry.needs}</p>
      )}
      <div className="flex flex-wrap gap-1 mb-3">
        {(entry.tags || []).map(t => (
          <span key={t} className="text-[10px] bg-gray-100 dark:bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded">{t}</span>
        ))}
      </div>
      <div className="flex items-center gap-2 mt-auto">
        {installed ? (
          <span className="flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400 px-3 py-1.5">
            <CheckCircle2 size={13} /> Installed
          </span>
        ) : (
          <button onClick={() => onInstall(entry)}
            className="flex items-center gap-1.5 text-xs bg-brand-500 hover:bg-brand-600 text-white px-3 py-1.5 rounded-lg transition-colors">
            <Download size={13} /> Install
          </button>
        )}
        <a href={entry.docs} target="_blank" rel="noreferrer"
          className="flex items-center gap-1 text-xs text-gray-400 hover:text-brand-500 transition-colors ml-auto">
          Docs <ExternalLink size={11} />
        </a>
      </div>
    </div>
  )
}

export default function Mcp() {
  const [tab, setTab] = useState('servers')
  const [servers, setServers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [tests, setTests] = useState({})
  const [error, setError] = useState('')
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [search, setSearch] = useState('')
  const [registry, setRegistry] = useState({ state: 'idle', servers: [] })
  const topRef = useRef(null)

  // Live search against the official MCP registry (debounced)
  useEffect(() => {
    const q = search.trim()
    if (tab !== 'store' || q.length < 2) {
      setRegistry({ state: 'idle', servers: [] })
      return
    }
    setRegistry(r => ({ ...r, state: 'loading' }))
    const t = setTimeout(() => {
      fetch(`/api/mcp/registry?q=${encodeURIComponent(q)}`)
        .then(r => r.json())
        .then(d => setRegistry(d.ok
          ? { state: 'ok', servers: d.servers || [] }
          : { state: 'error', servers: [], error: d.error }))
        .catch(e => setRegistry({ state: 'error', servers: [], error: e.message }))
    }, 450)
    return () => clearTimeout(t)
  }, [search, tab])

  const fetchServers = () => {
    fetch('/api/mcp/servers')
      .then(r => r.json())
      .then(d => { setServers(d.servers || []); setLoading(false) })
      .catch(() => setLoading(false))
  }
  useEffect(() => { fetchServers() }, [])

  const parseEnv = (text) => {
    const env = {}
    text.split('\n').map(l => l.trim()).filter(Boolean).forEach(line => {
      const i = line.indexOf('=')
      if (i > 0) env[line.slice(0, i).trim()] = line.slice(i + 1).trim()
    })
    return Object.keys(env).length ? env : undefined
  }

  const addServer = async () => {
    const isStdio = form.type === 'stdio'
    if (!form.name || (isStdio ? !form.command : !form.url)) {
      setError(isStdio ? 'Name and command are required.' : 'Name and URL are required.')
      return
    }
    setSaving(true); setError('')
    const body = { name: form.name, type: form.type, enabled: true }
    if (isStdio) {
      body.command = form.command
      if (form.args.trim()) body.args = form.args.trim().split(/\s+/)
      const env = parseEnv(form.env)
      if (env) body.env = env
    } else {
      body.url = form.url
      if (form.headerVal) body.headers = { [form.headerKey]: form.headerVal }
    }
    try {
      const r = await fetch('/api/mcp/servers', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      })
      const d = await r.json()
      if (d.added) {
        setForm(EMPTY_FORM)
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

  // Store → Install: prefill the Add form and jump to the Servers tab
  const installFromStore = (entry) => {
    setForm({
      name: entry.id,
      type: entry.type,
      url: entry.url || '',
      headerKey: entry.headers ? Object.keys(entry.headers)[0] : 'Authorization',
      headerVal: entry.headers ? Object.values(entry.headers)[0] : '',
      command: entry.command || '',
      args: (entry.args || []).join(' '),
      env: Object.entries(entry.env || {}).map(([k, v]) => `${k}=${v}`).join('\n'),
    })
    setTab('servers')
    setShowAdd(true)
    setError('')
    topRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const installedIds = new Set(servers.map(s => s.name))
  const q = search.trim().toLowerCase()
  const catalog = MCP_CATALOG.filter(e =>
    !q || e.label.toLowerCase().includes(q) || e.desc.toLowerCase().includes(q) ||
    (e.tags || []).some(t => t.includes(q))
  )

  const isStdio = form.type === 'stdio'

  return (
    <div className="space-y-5" ref={topRef}>
      <div className="flex items-center justify-between">
        <PageHeader title="Integrations" icon={Plug} accent="teal"
          subtitle={!loading ? `${servers.length} MCP server${servers.length === 1 ? '' : 's'} · connect Kovo to external tools` : undefined} />
        <div className="flex items-center gap-2">
          <button onClick={fetchServers} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800" title="Reload">
            <RefreshCw size={14} />
          </button>
          <button onClick={() => { setTab('servers'); setShowAdd(!showAdd) }} className="flex items-center gap-1.5 text-sm bg-brand-500 hover:bg-brand-600 text-white px-4 py-1.5 rounded-lg transition-colors">
            <Plus size={14} /> Add Server
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 dark:border-gray-800">
        {[
          { id: 'servers', label: `Servers (${servers.length})`, Icon: Plug },
          { id: 'store', label: 'Store', Icon: Store },
        ].map(({ id, label, Icon }) => (
          <button key={id} onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === id
                ? 'border-brand-500 text-brand-500'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}>
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {tab === 'servers' && (
        <>
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
                    <option value="stdio">stdio (local command)</option>
                  </select>
                </div>
                {!isStdio && (
                  <div>
                    <label className="text-xs text-gray-500 block mb-1">URL</label>
                    <input placeholder="http://10.0.1.20:8123/mcp_server/sse" value={form.url} onChange={e => setForm(f => ({...f, url: e.target.value}))} className={inputCls} />
                  </div>
                )}
                {isStdio && (
                  <div>
                    <label className="text-xs text-gray-500 block mb-1">Command</label>
                    <input placeholder="npx" value={form.command} onChange={e => setForm(f => ({...f, command: e.target.value}))} className={inputCls} />
                  </div>
                )}
              </div>
              {!isStdio && (
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
              )}
              {isStdio && (
                <>
                  <div>
                    <label className="text-xs text-gray-500 block mb-1">Arguments (space-separated)</label>
                    <input placeholder="-y @modelcontextprotocol/server-filesystem /home/esam" value={form.args} onChange={e => setForm(f => ({...f, args: e.target.value}))} className={`font-mono ${inputCls}`} />
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 block mb-1">Environment (KEY=value per line — use ${'{'}ENV_VAR{'}'} for secrets)</label>
                    <textarea rows={2} placeholder={'BRAVE_API_KEY=${BRAVE_API_KEY}'} value={form.env} onChange={e => setForm(f => ({...f, env: e.target.value}))} className={`resize-none font-mono ${inputCls}`} />
                  </div>
                </>
              )}
              <p className="text-[11px] text-gray-400">Tip: put the real token in <code>config/.env</code> (e.g. <code>HA_TOKEN=…</code>) and reference it here as <code>${'{'}HA_TOKEN{'}'}</code> so secrets never sit in settings.yaml.</p>
              {error && <p className="text-sm text-red-500">{error}</p>}
              <div className="flex gap-2">
                <button onClick={addServer} disabled={saving || !form.name || (isStdio ? !form.command : !form.url)} className="bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-white px-4 py-2 rounded-lg text-sm transition-colors">
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
              hint="Browse the Store for popular servers, or add one manually"
              actionLabel="Browse Store" onAction={() => setTab('store')} />
          )}
        </>
      )}

      {tab === 'store' && (
        <>
          <div className="flex items-center gap-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-2.5 focus-within:border-brand-400 transition-colors max-w-md">
            <Search size={15} className="text-gray-400 flex-shrink-0" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search the catalog… (smart home, database, web)"
              className="flex-1 bg-transparent text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none"
            />
            {search && (
              <button onClick={() => setSearch('')} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                <X size={14} />
              </button>
            )}
          </div>

          {/* Curated catalog */}
          <div className="flex items-center gap-2">
            <CheckCircle2 size={14} className="text-teal-500" />
            <h2 className="text-xs font-bold text-gray-700 dark:text-gray-200 uppercase tracking-wide">Curated</h2>
            <span className="text-xs text-gray-400">hand-checked, ships with KOVO</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {catalog.map(entry => (
              <StoreCard key={entry.id} entry={entry}
                installed={installedIds.has(entry.id)} onInstall={installFromStore} />
            ))}
          </div>
          {catalog.length === 0 && (
            <p className="text-sm text-gray-400">No curated matches for “{search}”.</p>
          )}

          {/* Live registry */}
          <div className="flex items-center gap-2 pt-3">
            <Globe size={14} className="text-teal-500" />
            <h2 className="text-xs font-bold text-gray-700 dark:text-gray-200 uppercase tracking-wide">MCP Registry</h2>
            <span className="text-xs text-gray-400">live · registry.modelcontextprotocol.io</span>
          </div>

          {registry.state === 'idle' && (
            <p className="text-sm text-gray-400">
              Type at least 2 characters to search thousands of community-published servers.
            </p>
          )}
          {registry.state === 'loading' && (
            <div className="flex items-center gap-2 text-gray-400 text-sm py-2">
              <Loader2 size={14} className="animate-spin" /> Searching the registry…
            </div>
          )}
          {registry.state === 'error' && (
            <p className="text-sm text-amber-600 dark:text-amber-400">
              Registry unreachable right now — the curated catalog above still works. ({registry.error})
            </p>
          )}
          {registry.state === 'ok' && (
            <>
              {registry.servers.length > 0 ? (
                <>
                  <div className="flex items-start gap-2 text-[11px] text-amber-600 dark:text-amber-400/90 bg-amber-500/5 border border-amber-500/20 rounded-lg px-3 py-2">
                    <ShieldAlert size={13} className="flex-shrink-0 mt-0.5" />
                    <span>Registry entries are community-published and <strong>not vetted</strong> — install only servers whose publisher you trust, and check the docs link before adding credentials.</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {registry.servers.map(entry => (
                      <StoreCard key={`reg-${entry.id}`} entry={entry}
                        installed={installedIds.has(entry.id)} onInstall={installFromStore} />
                    ))}
                  </div>
                </>
              ) : (
                <p className="text-sm text-gray-400">No registry matches for “{search}”.</p>
              )}
            </>
          )}

          <p className="text-[11px] text-gray-400">
            Install prefills the Add form; you supply paths and tokens.
            Secrets go in <code>config/.env</code> and are referenced as <code>${'{'}VAR{'}'}</code>.
          </p>
        </>
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
