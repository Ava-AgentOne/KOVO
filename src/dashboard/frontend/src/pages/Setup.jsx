import { useState, useEffect } from 'react'

const STEP_LABELS = {
  welcome: 'Welcome',
  services: 'Services',
  core: 'Credentials',
  google: 'Google',
  calls: 'Voice Calls',
  groq: 'Transcription',
  review: 'Review',
}

function Field({ label, name, value, onChange, placeholder = '', hint = '' }) {
  return (
    <div className="space-y-1">
      <label className="text-sm text-gray-300">{label}</label>
      <input
        type="text"
        value={value}
        onChange={e => onChange(name, e.target.value)}
        placeholder={placeholder}
        autoComplete="off"
        className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 font-mono placeholder-gray-600 focus:outline-none focus:border-brand-500"
      />
      {hint && <p className="text-xs text-gray-500">{hint}</p>}
    </div>
  )
}

function ProgressDots({ steps, current }) {
  return (
    <div className="flex items-center justify-center gap-1 flex-wrap">
      {steps.map((step, i) => (
        <div key={step} className="flex items-center gap-1">
          <div
            title={STEP_LABELS[step]}
            className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-medium transition-colors ${
              i === current
                ? 'bg-brand-600 text-white'
                : i < current
                ? 'bg-green-700 text-white'
                : 'bg-gray-800 text-gray-500'
            }`}
          >
            {i < current ? '✓' : i + 1}
          </div>
          {i < steps.length - 1 && (
            <div className={`w-5 h-px ${i < current ? 'bg-green-700' : 'bg-gray-700'}`} />
          )}
        </div>
      ))}
    </div>
  )
}

function WelcomePage() {
  return (
    <div className="space-y-5 text-center py-2">
      <div className="text-5xl">🐾</div>
      <h1 className="text-2xl font-bold text-white">Welcome to MiniClaw</h1>
      <p className="text-gray-400 text-sm leading-relaxed max-w-sm mx-auto">
        This wizard will help you set up your credentials. You'll need your Telegram bot token
        and user ID. Optional services like Google Calendar, voice calls, and transcription can
        be configured now or skipped.
      </p>
      <p className="text-gray-600 text-xs">
        Credentials are saved to <code className="text-gray-500">config/.env</code> on this machine.
      </p>
    </div>
  )
}

function ServicesPage({ services, setServices }) {
  const toggle = key => setServices(s => ({ ...s, [key]: !s[key] }))

  const items = [
    {
      key: 'google',
      label: 'Google Calendar / Drive',
      desc: 'Access Google Docs, Calendar, Gmail, and Sheets',
    },
    {
      key: 'calls',
      label: 'Telegram Voice Calls',
      desc: 'Answer and make voice calls through Telegram',
    },
    {
      key: 'groq',
      label: 'Groq Transcription',
      desc: 'Fast cloud voice-to-text via whisper-large-v3-turbo',
    },
  ]

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-white">Optional Services</h2>
        <p className="text-sm text-gray-400 mt-1">
          Select the integrations you want to enable. You can configure them later via Settings.
        </p>
      </div>
      <div className="space-y-2">
        {items.map(({ key, label, desc }) => (
          <label
            key={key}
            className="flex items-start gap-3 p-3 bg-gray-800 hover:bg-gray-800/80 rounded-lg cursor-pointer transition-colors"
          >
            <input
              type="checkbox"
              checked={services[key]}
              onChange={() => toggle(key)}
              className="mt-0.5 accent-brand-600"
            />
            <div>
              <p className="text-sm font-medium text-gray-200">{label}</p>
              <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
            </div>
          </label>
        ))}
      </div>
    </div>
  )
}

function CorePage({ form, set }) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-white">Core Credentials</h2>
        <p className="text-sm text-gray-400 mt-1">Required for MiniClaw to start.</p>
      </div>
      <Field
        label="Telegram Bot Token"
        name="telegram_bot_token"
        value={form.telegram_bot_token}
        onChange={set}
        placeholder="1234567890:AABBCCDDeeffgghh..."
        hint="Get this from @BotFather on Telegram"
      />
      <Field
        label="Your Telegram User ID"
        name="esam_telegram_id"
        value={form.esam_telegram_id}
        onChange={set}
        placeholder="123456789"
        hint="Get this by messaging @userinfobot on Telegram"
      />
      <Field
        label="Webhook URL (optional)"
        name="webhook_url"
        value={form.webhook_url}
        onChange={set}
        placeholder="https://your-domain.com"
        hint="Leave empty to use long-polling (recommended for most setups)"
      />
    </div>
  )
}

function GooglePage({ form, set }) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-white">Google Credentials</h2>
        <p className="text-sm text-gray-400 mt-1">
          Paste your Google service account JSON. MiniClaw uses this to access Calendar, Drive, Docs, and Gmail.
        </p>
      </div>
      <div className="space-y-1">
        <label className="text-sm text-gray-300">Service Account JSON</label>
        <textarea
          value={form.google_credentials_json}
          onChange={e => set('google_credentials_json', e.target.value)}
          placeholder={'{\n  "type": "service_account",\n  "project_id": "...",\n  ...\n}'}
          spellCheck={false}
          className="w-full h-44 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 font-mono placeholder-gray-600 resize-none focus:outline-none focus:border-brand-500"
        />
        <p className="text-xs text-gray-500">
          Create a service account at{' '}
          <span className="text-gray-400">console.cloud.google.com</span> → IAM → Service Accounts,
          then download the JSON key file.
        </p>
      </div>
    </div>
  )
}

function CallsPage({ form, set }) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-white">Telegram Voice Calls</h2>
        <p className="text-sm text-gray-400 mt-1">
          Required to answer and make voice calls. Get these from{' '}
          <span className="text-gray-300">my.telegram.org</span> → API development tools.
        </p>
      </div>
      <Field
        label="API ID"
        name="telegram_api_id"
        value={form.telegram_api_id}
        onChange={set}
        placeholder="12345678"
      />
      <Field
        label="API Hash"
        name="telegram_api_hash"
        value={form.telegram_api_hash}
        onChange={set}
        placeholder="abc123def456..."
      />
    </div>
  )
}

function GroqPage({ form, set }) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-white">Groq Transcription</h2>
        <p className="text-sm text-gray-400 mt-1">
          Fast cloud transcription using whisper-large-v3-turbo. Falls back to local Whisper if
          not configured.
        </p>
      </div>
      <Field
        label="Groq API Key"
        name="groq_api_key"
        value={form.groq_api_key}
        onChange={set}
        placeholder="gsk_..."
        hint="Get this from console.groq.com"
      />
    </div>
  )
}

function ReviewPage({ form, services, error }) {
  const mask = val => {
    if (!val) return '—'
    if (val.length <= 8) return '•'.repeat(val.length)
    return val.slice(0, 4) + '•'.repeat(val.length - 8) + val.slice(-4)
  }

  const rows = [
    { label: 'Bot Token', value: mask(form.telegram_bot_token), ok: !!form.telegram_bot_token },
    { label: 'User ID', value: form.esam_telegram_id || '—', ok: !!form.esam_telegram_id },
    form.webhook_url && { label: 'Webhook URL', value: form.webhook_url, ok: true },
    services.google && {
      label: 'Google Creds',
      value: form.google_credentials_json ? '✓ JSON provided' : '✗ Empty',
      ok: !!form.google_credentials_json,
    },
    services.calls && {
      label: 'Telegram API ID',
      value: form.telegram_api_id || '—',
      ok: !!form.telegram_api_id,
    },
    services.calls && {
      label: 'Telegram API Hash',
      value: mask(form.telegram_api_hash),
      ok: !!form.telegram_api_hash,
    },
    services.groq && {
      label: 'Groq API Key',
      value: mask(form.groq_api_key),
      ok: !!form.groq_api_key,
    },
  ].filter(Boolean)

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-white">Review & Save</h2>
        <p className="text-sm text-gray-400 mt-1">
          Check your settings. The service will restart automatically after saving.
        </p>
      </div>
      <div className="space-y-0 font-mono text-sm">
        {rows.map(({ label, value, ok }) => (
          <div key={label} className="flex items-center gap-3 py-1.5 border-b border-gray-800">
            <span className="text-gray-500 w-36 flex-shrink-0 text-xs">{label}</span>
            <span className={ok ? 'text-yellow-300' : 'text-red-400'}>{value}</span>
          </div>
        ))}
      </div>
      {error && <p className="text-sm text-red-400 mt-2">❌ {error}</p>}
    </div>
  )
}

function SavedScreen({ countdown }) {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-center space-y-4">
        <div className="text-5xl">✅</div>
        <h1 className="text-2xl font-bold text-white">Configuration saved!</h1>
        <p className="text-gray-400 text-sm">MiniClaw is restarting with your new credentials…</p>
        <p className="text-gray-500 text-sm">
          Redirecting to dashboard in {countdown}s
        </p>
        <a href="/dashboard/" className="text-brand-400 hover:text-brand-300 text-sm underline block">
          Go now →
        </a>
      </div>
    </div>
  )
}

export default function Setup() {
  const [services, setServices] = useState({ google: false, calls: false, groq: false })
  const [form, setForm] = useState({
    telegram_bot_token: '',
    esam_telegram_id: '',
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

  // Build active step list based on service selections
  const steps = ['welcome', 'services', 'core']
  if (services.google) steps.push('google')
  if (services.calls) steps.push('calls')
  if (services.groq) steps.push('groq')
  steps.push('review')

  // Clamp stepIndex if services were deselected and steps list shrinks
  useEffect(() => {
    if (stepIndex >= steps.length) setStepIndex(steps.length - 1)
  }, [services]) // eslint-disable-line react-hooks/exhaustive-deps

  const currentStep = steps[stepIndex]
  const isLast = stepIndex === steps.length - 1
  const isFirst = stepIndex === 0

  const next = () => setStepIndex(i => Math.min(i + 1, steps.length - 1))
  const back = () => setStepIndex(i => Math.max(i - 1, 0))
  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))

  // Countdown redirect after save
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

  if (saved) return <SavedScreen countdown={countdown} />

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        <ProgressDots steps={steps} current={stepIndex} />

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 mt-6">
          {currentStep === 'welcome'   && <WelcomePage />}
          {currentStep === 'services'  && <ServicesPage services={services} setServices={setServices} />}
          {currentStep === 'core'      && <CorePage form={form} set={set} />}
          {currentStep === 'google'    && <GooglePage form={form} set={set} />}
          {currentStep === 'calls'     && <CallsPage form={form} set={set} />}
          {currentStep === 'groq'      && <GroqPage form={form} set={set} />}
          {currentStep === 'review'    && <ReviewPage form={form} services={services} error={error} />}

          <div className="flex justify-between mt-8 pt-4 border-t border-gray-800">
            {!isFirst ? (
              <button
                onClick={back}
                className="text-sm text-gray-400 hover:text-gray-200 px-4 py-2 transition-colors"
              >
                ← Back
              </button>
            ) : <div />}

            {isLast ? (
              <button
                onClick={save}
                disabled={saving}
                className="bg-brand-700 hover:bg-brand-600 text-white text-sm px-6 py-2 rounded disabled:opacity-50 transition-colors"
              >
                {saving ? 'Saving…' : 'Save & Launch'}
              </button>
            ) : (
              <button
                onClick={next}
                className="bg-brand-700 hover:bg-brand-600 text-white text-sm px-6 py-2 rounded transition-colors"
              >
                {currentStep === 'welcome' ? 'Get Started →' : 'Next →'}
              </button>
            )}
          </div>
        </div>

        <p className="text-center text-xs text-gray-600 mt-4">
          MiniClaw Setup Wizard — credentials stored locally, never transmitted
        </p>
      </div>
    </div>
  )
}
