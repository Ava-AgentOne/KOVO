import { useState, useEffect, useCallback } from 'react'
import KovoLogo from '../components/KovoLogo'

// ── Floating particles ───────────────────────────────────────────
function FloatingParticles() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {Array.from({ length: 20 }).map((_, i) => (
        <div
          key={i}
          className="kovo-particle"
          style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
            width: `${3 + Math.random() * 5}px`,
            height: `${3 + Math.random() * 5}px`,
            animationDelay: `${Math.random() * 8}s`,
            animationDuration: `${6 + Math.random() * 8}s`,
            opacity: 0.15 + Math.random() * 0.25,
          }}
        />
      ))}
    </div>
  )
}

// ── Typing effect ────────────────────────────────────────────────
function TypeWriter({ text, speed = 40, delay = 0, onDone }) {
  const [displayed, setDisplayed] = useState('')
  const [started, setStarted] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setStarted(true), delay)
    return () => clearTimeout(t)
  }, [delay])

  useEffect(() => {
    if (!started) return
    if (displayed.length >= text.length) { onDone?.(); return }
    const t = setTimeout(() => setDisplayed(text.slice(0, displayed.length + 1)), speed)
    return () => clearTimeout(t)
  }, [displayed, started, text, speed])

  return (
    <span>
      {displayed}
      {started && displayed.length < text.length && (
        <span className="inline-block w-0.5 h-5 bg-brand-400 ml-0.5 animate-pulse align-middle" />
      )}
    </span>
  )
}

// ── Step labels ──────────────────────────────────────────────────
const STEP_LABELS = {
  services: 'Services',
  core: 'Credentials',
  google: 'Google',
  calls: 'Voice Calls',
  groq: 'Transcription',
  review: 'Review',
}

// ── Progress bar ─────────────────────────────────────────────────
function ProgressBar({ steps, current }) {
  const pct = ((current) / (steps.length - 1)) * 100
  return (
    <div className="w-full max-w-md mx-auto">
      <div className="flex justify-between mb-2">
        {steps.map((step, i) => (
          <div key={step} className="flex flex-col items-center" style={{ width: `${100 / steps.length}%` }}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-500 ${
              i < current ? 'bg-emerald-500 text-white scale-90' :
              i === current ? 'bg-brand-500 text-white ring-4 ring-brand-500/20 scale-110' :
              'bg-gray-200 dark:bg-gray-800 text-gray-400'
            }`}>
              {i < current ? '✓' : i + 1}
            </div>
            <span className={`text-[10px] mt-1.5 transition-colors ${
              i === current ? 'text-brand-400 font-semibold' : 'text-gray-400'
            }`}>{STEP_LABELS[step]}</span>
          </div>
        ))}
      </div>
      <div className="h-1.5 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-brand-500 to-emerald-500 rounded-full transition-all duration-700 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

// ── Help box ─────────────────────────────────────────────────────
function HelpBox({ children }) {
  return (
    <div className="bg-brand-50 dark:bg-brand-900/10 border border-brand-200 dark:border-brand-800/30 rounded-xl p-4 space-y-2">
      <p className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wide">How to get this</p>
      <div className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed space-y-2">
        {children}
      </div>
    </div>
  )
}

// ── External link ────────────────────────────────────────────────
function ExtLink({ href, children }) {
  return (
    <a href={href} target="_blank" rel="noreferrer" className="text-brand-500 hover:text-brand-600 underline underline-offset-2 font-medium">
      {children} ↗
    </a>
  )
}

// ── Form field ───────────────────────────────────────────────────
function Field({ label, name, value, onChange, placeholder = '', hint = '' }) {
  return (
    <div className="space-y-1.5 kovo-fade-up">
      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</label>
      <input
        type="text"
        value={value}
        onChange={e => onChange(name, e.target.value)}
        placeholder={placeholder}
        autoComplete="off"
        className="w-full bg-gray-50 dark:bg-gray-800/80 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-sm text-gray-900 dark:text-gray-200 font-mono placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500 transition-all"
      />
      {hint && <p className="text-xs text-gray-400 pl-1">{hint}</p>}
    </div>
  )
}

// ── SPLASH PAGE ──────────────────────────────────────────────────
function SplashPage({ onStart }) {
  const [showFeatures, setShowFeatures] = useState(false)
  const [showButton, setShowButton] = useState(false)

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950 flex flex-col items-center justify-center relative overflow-hidden">
      <FloatingParticles />

      {/* Glow behind mascot */}
      <div className="absolute w-96 h-96 bg-brand-500/10 rounded-full blur-[120px] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />

      <div className="relative z-10 flex flex-col items-center text-center px-6 max-w-lg">
        {/* Animated mascot — big, centered */}
        <div className="kovo-splash-entrance mb-8">
          <KovoLogo size={220} animate={true} />
        </div>

        {/* Title */}
        <h1 className="text-5xl font-black text-white tracking-tight kovo-fade-up" style={{ animationDelay: '0.6s' }}>
          <span className="text-brand-400">KOVO</span>
        </h1>

        {/* Typing subtitle */}
        <p className="text-lg text-gray-300 mt-4 kovo-fade-up" style={{ animationDelay: '1s' }}>
          <TypeWriter
            text="Your self-hosted AI agent, ready to set up."
            speed={30}
            delay={1200}
            onDone={() => { setTimeout(() => setShowFeatures(true), 300); setTimeout(() => setShowButton(true), 800) }}
          />
        </p>

        {/* Feature pills */}
        {showFeatures && (
          <div className="flex flex-wrap justify-center gap-2 mt-6">
            {['Claude Code Brain', 'Telegram Chat', 'Web Dashboard', 'Voice Calls', 'Security Audits'].map((f, i) => (
              <span
                key={f}
                className="px-3 py-1.5 text-xs font-medium rounded-full border border-brand-500/30 text-brand-300 bg-brand-500/5 kovo-fade-up"
                style={{ animationDelay: `${i * 0.1}s` }}
              >
                {f}
              </span>
            ))}
          </div>
        )}

        {/* CTA */}
        {showButton && (
          <div className="kovo-fade-up mt-10">
            <button
              onClick={onStart}
              className="group relative px-10 py-4 bg-brand-500 hover:bg-brand-600 text-white font-bold rounded-2xl text-base transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-brand-500/25"
            >
              Get Started
              <span className="inline-block ml-2 transition-transform group-hover:translate-x-1">→</span>
            </button>
            <p className="text-gray-500 text-xs mt-4">Takes about 2 minutes</p>
          </div>
        )}
      </div>

      <div className="absolute bottom-6 text-center">
        <p className="text-gray-600 text-xs">Powered by Claude Code · GNU AGPLv3</p>
      </div>
    </div>
  )
}

// ── SERVICE SELECTION ────────────────────────────────────────────
function ServicesPage({ services, onToggle }) {
  const items = [
    { key: 'google', icon: '🔗', label: 'Google Workspace', desc: 'Access Docs, Calendar, Gmail, Drive, and Sheets' },
    { key: 'calls', icon: '📞', label: 'Telegram Voice Calls', desc: 'Real calls for urgent alerts — needs a second SIM' },
    { key: 'groq', icon: '🎙️', label: 'Groq Transcription', desc: 'Fast cloud voice-to-text — free tier available' },
  ]

  return (
    <div className="space-y-5">
      <div className="kovo-fade-up">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Optional Integrations</h2>
        <p className="text-sm text-gray-500 mt-1">Pick what you need now. You can always add more later from Settings.</p>
      </div>
      <div className="space-y-3">
        {items.map(({ key, icon, label, desc }, i) => (
          <button
            key={key}
            type="button"
            onClick={() => onToggle(key)}
            className={`w-full flex items-center gap-4 p-4 rounded-xl border text-left transition-all duration-200 kovo-fade-up ${
              services[key]
                ? 'border-brand-500/50 bg-brand-500/5 dark:bg-brand-500/10 shadow-sm'
                : 'border-gray-200 dark:border-gray-700/50 bg-white dark:bg-gray-800/40 hover:border-gray-300 dark:hover:border-gray-600'
            }`}
            style={{ animationDelay: `${i * 0.1}s` }}
          >
            <span className="text-2xl">{icon}</span>
            <div className="flex-1">
              <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">{label}</p>
              <p className="text-xs text-gray-400 mt-0.5">{desc}</p>
            </div>
            <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${
              services[key] ? 'border-brand-500 bg-brand-500' : 'border-gray-300 dark:border-gray-600'
            }`}>
              {services[key] && <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

// ── CORE CREDENTIALS ─────────────────────────────────────────────
function CorePage({ form, set }) {
  return (
    <div className="space-y-5">
      <div className="kovo-fade-up">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Core Credentials</h2>
        <p className="text-sm text-gray-500 mt-1">Required for Kovo to connect to Telegram.</p>
      </div>

      <HelpBox>
        <p><strong>Step 1:</strong> Open Telegram and search for <ExtLink href="https://t.me/BotFather">@BotFather</ExtLink></p>
        <p><strong>Step 2:</strong> Send <code className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-xs font-mono">/newbot</code>, follow the prompts, and copy the token it gives you.</p>
        <p><strong>Step 3:</strong> To find your User ID, message <ExtLink href="https://t.me/userinfobot">@userinfobot</ExtLink> on Telegram — it replies with your numeric ID.</p>
      </HelpBox>

      <Field label="Telegram Bot Token" name="telegram_bot_token" value={form.telegram_bot_token} onChange={set} placeholder="1234567890:AABBCCDDeeffgghh..." />
      <Field label="Your Telegram User ID" name="owner_telegram_id" value={form.owner_telegram_id} onChange={set} placeholder="123456789" />
      <Field label="Webhook URL" name="webhook_url" value={form.webhook_url} onChange={set} placeholder="https://your-domain.com (optional)" hint="Leave empty for polling mode — recommended for home labs" />
    </div>
  )
}

// ── GOOGLE ────────────────────────────────────────────────────────
function GooglePage({ form, set }) {
  return (
    <div className="space-y-5">
      <div className="kovo-fade-up">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Google Credentials</h2>
        <p className="text-sm text-gray-500 mt-1">Enables Google Docs, Drive, Gmail, Calendar, and Sheets access.</p>
      </div>

      <HelpBox>
        <p><strong>Step 1:</strong> Go to <ExtLink href="https://console.cloud.google.com/">Google Cloud Console</ExtLink> and create a project (or select an existing one)</p>
        <p><strong>Step 2:</strong> Enable the APIs Kovo needs — go to <ExtLink href="https://console.cloud.google.com/apis/library">APIs &amp; Services → Library</ExtLink> and enable each one:</p>
        <div className="pl-4 space-y-0.5 text-xs">
          <p>• <ExtLink href="https://console.cloud.google.com/apis/library/drive.googleapis.com">Google Drive API</ExtLink></p>
          <p>• <ExtLink href="https://console.cloud.google.com/apis/library/docs.googleapis.com">Google Docs API</ExtLink></p>
          <p>• <ExtLink href="https://console.cloud.google.com/apis/library/gmail.googleapis.com">Gmail API</ExtLink></p>
          <p>• <ExtLink href="https://console.cloud.google.com/apis/library/calendar-json.googleapis.com">Google Calendar API</ExtLink></p>
          <p>• <ExtLink href="https://console.cloud.google.com/apis/library/sheets.googleapis.com">Google Sheets API</ExtLink></p>
        </div>
        <p><strong>Step 3:</strong> Go to <ExtLink href="https://console.cloud.google.com/apis/credentials">Credentials</ExtLink> → click <strong>"Create Credentials" → "OAuth 2.0 Client ID"</strong> → select <strong>"Desktop app"</strong></p>
        <p><strong>Step 4:</strong> Download the JSON file and paste its contents below</p>
        <p className="text-xs text-gray-400">Full guide: <ExtLink href="https://developers.google.com/workspace/guides/create-credentials">Google Workspace API setup</ExtLink></p>
      </HelpBox>

      <div className="space-y-1.5 kovo-fade-up">
        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Service Account JSON</label>
        <textarea
          value={form.google_credentials_json}
          onChange={e => set('google_credentials_json', e.target.value)}
          placeholder={'{\n  "type": "service_account",\n  "project_id": "...",\n  ...\n}'}
          spellCheck={false}
          className="w-full h-40 bg-gray-50 dark:bg-gray-800/80 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-900 dark:text-gray-200 font-mono placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500 transition-all"
        />
      </div>
    </div>
  )
}

// ── VOICE CALLS ──────────────────────────────────────────────────
function CallsPage({ form, set }) {
  return (
    <div className="space-y-5">
      <div className="kovo-fade-up">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Telegram Voice Calls</h2>
        <p className="text-sm text-gray-500 mt-1">Enables Kovo to make real Telegram voice calls for urgent alerts.</p>
      </div>

      <HelpBox>
        <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-3 space-y-1.5 mb-3">
          <p className="text-xs font-bold text-gray-600 dark:text-gray-300">Three Telegram accounts involved:</p>
          <p className="text-xs"><span className="inline-block w-4 h-4 rounded-full bg-emerald-500 text-white text-[10px] font-bold text-center leading-4 mr-1.5">1</span><strong>Your main account</strong> — your personal Telegram (where you chat with friends, family, etc.)</p>
          <p className="text-xs"><span className="inline-block w-4 h-4 rounded-full bg-brand-500 text-white text-[10px] font-bold text-center leading-4 mr-1.5">2</span><strong>Kovo Bot</strong> — the bot you created with @BotFather in the previous step. You chat with Kovo through this bot. Bots <strong>cannot</strong> make voice calls.</p>
          <p className="text-xs"><span className="inline-block w-4 h-4 rounded-full bg-amber-500 text-white text-[10px] font-bold text-center leading-4 mr-1.5">3</span><strong>Caller account</strong> — a second <em>real</em> Telegram user account (needs a second SIM/eSIM). This is the account that physically dials your main account for urgent alerts.</p>
        </div>
        <p className="text-xs text-gray-400 italic mb-2">Why? Telegram bots can send messages but can't make voice calls. Only real user accounts can call. So Kovo uses this second account as a "caller" that rings your main phone when something is urgent.</p>
        <p><strong>Step 1:</strong> Get a <strong>second phone number</strong> — a spare SIM, eSIM, or prepaid card</p>
        <p><strong>Step 2:</strong> Install Telegram on any phone and create an account with that second number. This becomes the <strong>Caller account</strong> <span className="inline-block w-3 h-3 rounded-full bg-amber-500 text-[8px] text-white font-bold text-center leading-3">3</span></p>
        <p><strong>Step 3:</strong> On a browser, go to <ExtLink href="https://my.telegram.org">my.telegram.org</ExtLink> and log in with the <strong>second number</strong> (Caller account <span className="inline-block w-3 h-3 rounded-full bg-amber-500 text-[8px] text-white font-bold text-center leading-3">3</span>, not your main)</p>
        <p><strong>Step 4:</strong> Click <strong>"API development tools"</strong> → fill in any app name → copy the <strong>API ID</strong> and <strong>API Hash</strong></p>
        <p><strong>Step 5:</strong> After finishing this wizard, open your <strong>Kovo Bot</strong> chat <span className="inline-block w-3 h-3 rounded-full bg-brand-500 text-[8px] text-white font-bold text-center leading-3">2</span> on your <strong>main account</strong> <span className="inline-block w-3 h-3 rounded-full bg-emerald-500 text-[8px] text-white font-bold text-center leading-3">1</span> and send:</p>
        <p className="pl-4"><code className="bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded text-xs font-mono">/reauth_caller +971XXXXXXXX</code></p>
        <p className="pl-4 text-xs text-gray-400">Use the <strong>Caller's phone number</strong> <span className="inline-block w-3 h-3 rounded-full bg-amber-500 text-[8px] text-white font-bold text-center leading-3">3</span>. Telegram sends an OTP to that number — enter it when prompted.</p>
        <div className="bg-emerald-50 dark:bg-emerald-900/15 rounded-lg p-2.5 mt-2">
          <p className="text-xs text-emerald-700 dark:text-emerald-400"><strong>Result:</strong> When Kovo detects something urgent (disk full, security alert, etc.), the Caller account <span className="inline-block w-3 h-3 rounded-full bg-amber-500 text-[8px] text-white font-bold text-center leading-3">3</span> dials your main account <span className="inline-block w-3 h-3 rounded-full bg-emerald-500 text-[8px] text-white font-bold text-center leading-3">1</span> — your phone rings and you hear a TTS voice message.</p>
        </div>
      </HelpBox>

      <Field label="API ID" name="telegram_api_id" value={form.telegram_api_id} onChange={set} placeholder="12345678" />
      <Field label="API Hash" name="telegram_api_hash" value={form.telegram_api_hash} onChange={set} placeholder="abc123def456ghi789..." />
    </div>
  )
}

// ── GROQ ─────────────────────────────────────────────────────────
function GroqPage({ form, set }) {
  return (
    <div className="space-y-5">
      <div className="kovo-fade-up">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Groq Transcription</h2>
        <p className="text-sm text-gray-500 mt-1">Fast cloud transcription for voice messages. Falls back to local Whisper if skipped.</p>
      </div>

      <HelpBox>
        <p><strong>Step 1:</strong> Go to <ExtLink href="https://console.groq.com/keys">console.groq.com/keys</ExtLink></p>
        <p><strong>Step 2:</strong> Sign up for free (Google or GitHub login)</p>
        <p><strong>Step 3:</strong> Click <strong>"Create API Key"</strong> and copy it</p>
        <p className="text-xs text-gray-400">Free tier includes 14,400 requests/day — more than enough for personal use. Kovo uses the <code className="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded text-xs">whisper-large-v3-turbo</code> model for fast, accurate transcription.</p>
      </HelpBox>

      <Field label="Groq API Key" name="groq_api_key" value={form.groq_api_key} onChange={set} placeholder="gsk_..." />
    </div>
  )
}

// ── REVIEW ────────────────────────────────────────────────────────
function ReviewPage({ form, services, error }) {
  const mask = val => {
    if (!val) return '—'
    if (val.length <= 8) return '•'.repeat(val.length)
    return val.slice(0, 4) + '•'.repeat(Math.max(0, val.length - 8)) + val.slice(-4)
  }

  const rows = [
    { label: 'Bot Token', value: mask(form.telegram_bot_token), ok: !!form.telegram_bot_token },
    { label: 'User ID', value: form.owner_telegram_id || '—', ok: !!form.owner_telegram_id },
    form.webhook_url && { label: 'Webhook', value: form.webhook_url, ok: true },
    services.google && { label: 'Google', value: form.google_credentials_json ? '✓ JSON provided' : '✗ Not set', ok: !!form.google_credentials_json },
    services.calls && { label: 'API ID', value: form.telegram_api_id || '—', ok: !!form.telegram_api_id },
    services.calls && { label: 'API Hash', value: mask(form.telegram_api_hash), ok: !!form.telegram_api_hash },
    services.groq && { label: 'Groq Key', value: mask(form.groq_api_key), ok: !!form.groq_api_key },
  ].filter(Boolean)

  return (
    <div className="space-y-5">
      <div className="kovo-fade-up">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Review & Launch</h2>
        <p className="text-sm text-gray-500 mt-1">Everything looks good? Kovo will restart with your credentials.</p>
      </div>
      <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4 space-y-0 kovo-fade-up">
        {rows.map(({ label, value, ok }, i) => (
          <div key={label} className={`flex items-center gap-3 py-2.5 ${i < rows.length - 1 ? 'border-b border-gray-200 dark:border-gray-700/50' : ''}`}>
            <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${ok ? 'bg-emerald-500' : 'bg-red-400'}`} />
            <span className="text-xs text-gray-400 w-20 flex-shrink-0">{label}</span>
            <span className={`text-sm font-mono ${ok ? 'text-gray-700 dark:text-gray-300' : 'text-red-400'}`}>{value}</span>
          </div>
        ))}
      </div>
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700/40 rounded-xl p-3 kovo-fade-up">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}
    </div>
  )
}

// ── SAVED SCREEN ─────────────────────────────────────────────────
function SavedScreen({ countdown }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950 flex items-center justify-center relative overflow-hidden">
      <FloatingParticles />
      <div className="absolute w-96 h-96 bg-emerald-500/10 rounded-full blur-[120px] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
      <div className="relative z-10 flex flex-col items-center text-center space-y-6 px-6">
        <div className="kovo-splash-entrance">
          <KovoLogo size={160} animate={true} />
        </div>
        <h1 className="text-3xl font-black text-white kovo-fade-up" style={{ animationDelay: '0.3s' }}>
          <span className="text-emerald-400">All set!</span>
        </h1>
        <p className="text-gray-400 text-sm kovo-fade-up" style={{ animationDelay: '0.6s' }}>
          Kovo is restarting with your credentials...
        </p>
        <div className="kovo-fade-up" style={{ animationDelay: '0.9s' }}>
          <div className="inline-flex items-center gap-2 bg-gray-800/60 rounded-full px-5 py-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-gray-300 text-sm">Dashboard in {countdown}s</span>
          </div>
        </div>
        <a href="/dashboard/" className="text-brand-400 hover:text-brand-300 text-sm underline block kovo-fade-up" style={{ animationDelay: '1.2s' }}>
          Skip to dashboard →
        </a>
      </div>
    </div>
  )
}

// ── MAIN SETUP COMPONENT ─────────────────────────────────────────
export default function Setup() {
  const [showSplash, setShowSplash] = useState(true)
  const [services, setServices] = useState({ google: false, calls: false, groq: false })
  const [form, setForm] = useState({
    telegram_bot_token: '',
    owner_telegram_id: '',
    webhook_url: '',
    google_credentials_json: '',
    telegram_api_id: '',
    telegram_api_hash: '',
    groq_api_key: '',
  })
  const [stepIndex, setStepIndex] = useState(0)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [countdown, setCountdown] = useState(5)

  const toggleService = useCallback((key) => {
    setServices(prev => ({ ...prev, [key]: !prev[key] }))
  }, [])

  const steps = ['services', 'core']
  if (services.google) steps.push('google')
  if (services.calls) steps.push('calls')
  if (services.groq) steps.push('groq')
  steps.push('review')

  useEffect(() => {
    if (stepIndex >= steps.length) setStepIndex(steps.length - 1)
  }, [services])

  const currentStep = steps[stepIndex]
  const isLast = stepIndex === steps.length - 1
  const isFirst = stepIndex === 0

  const next = () => setStepIndex(i => Math.min(i + 1, steps.length - 1))
  const back = () => setStepIndex(i => Math.max(i - 1, 0))
  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))

  useEffect(() => {
    if (!saved) return
    if (countdown <= 0) { window.location.href = '/dashboard/'; return }
    const t = setTimeout(() => setCountdown(c => c - 1), 1000)
    return () => clearTimeout(t)
  }, [saved, countdown])

  const save = async () => {
    setSaving(true)
    setError('')
    try {
      const r = await fetch('/api/setup/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, restart: true }),
      })
      const d = await r.json()
      if (!r.ok) setError(d.detail || 'Save failed')
      else setSaved(true)
    } catch (e) {
      setError(e.message)
    }
    setSaving(false)
  }

  if (showSplash) return <SplashPage onStart={() => setShowSplash(false)} />
  if (saved) return <SavedScreen countdown={countdown} />

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center p-4 relative">
      <div className="absolute w-[500px] h-[500px] bg-brand-500/5 rounded-full blur-[150px] top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none" />

      <div className="w-full max-w-lg relative z-10">
        {/* Header — big logo + KOVO + Setup Wizard below */}
        <div className="flex flex-col items-center gap-2 mb-8">
          <KovoLogo size={140} animate={true} />
          <span className="text-3xl font-black text-brand-500 tracking-wide">KOVO</span>
          <span className="text-base text-gray-400 font-semibold tracking-widest uppercase">Setup Wizard</span>
        </div>

        <ProgressBar steps={steps} current={stepIndex} />

        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-8 mt-6 shadow-sm">
          <div key={currentStep} className="kovo-step-enter">
            {currentStep === 'services' && <ServicesPage services={services} onToggle={toggleService} />}
            {currentStep === 'core'     && <CorePage form={form} set={set} />}
            {currentStep === 'google'   && <GooglePage form={form} set={set} />}
            {currentStep === 'calls'    && <CallsPage form={form} set={set} />}
            {currentStep === 'groq'     && <GroqPage form={form} set={set} />}
            {currentStep === 'review'   && <ReviewPage form={form} services={services} error={error} />}
          </div>

          <div className="flex justify-between mt-8 pt-4 border-t border-gray-100 dark:border-gray-800">
            {!isFirst ? (
              <button onClick={back} className="text-sm text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 px-4 py-2.5 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-all">
                ← Back
              </button>
            ) : <div />}

            {isLast ? (
              <button
                onClick={save}
                disabled={saving || !form.telegram_bot_token || !form.owner_telegram_id}
                className="bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-bold px-8 py-2.5 rounded-xl disabled:opacity-40 transition-all hover:shadow-lg hover:shadow-emerald-500/20 hover:scale-[1.02]"
              >
                {saving ? (
                  <span className="flex items-center gap-2">
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                    Saving...
                  </span>
                ) : 'Save & Launch Kovo'}
              </button>
            ) : (
              <button
                onClick={next}
                className="bg-brand-500 hover:bg-brand-600 text-white text-sm font-bold px-6 py-2.5 rounded-xl transition-all hover:shadow-lg hover:shadow-brand-500/20 hover:scale-[1.02]"
              >
                Next →
              </button>
            )}
          </div>
        </div>

        <p className="text-center text-xs text-gray-400 mt-4">
          Credentials stored locally at <code className="text-gray-500">config/.env</code> — never transmitted
        </p>
      </div>
    </div>
  )
}
