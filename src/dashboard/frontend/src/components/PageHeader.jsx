// v2.1 design system: consistent page header — accent icon chip + title +
// subtitle. Accent colors are per-domain (see Layout nav for the mapping).
const ACCENTS = {
  brand:   'bg-brand-500/10 text-brand-500',
  violet:  'bg-violet-500/10 text-violet-500',
  indigo:  'bg-indigo-500/10 text-indigo-500',
  fuchsia: 'bg-fuchsia-500/10 text-fuchsia-500',
  emerald: 'bg-emerald-500/10 text-emerald-500',
  teal:    'bg-teal-500/10 text-teal-500',
  rose:    'bg-rose-500/10 text-rose-500',
  amber:   'bg-amber-500/10 text-amber-500',
  orange:  'bg-orange-500/10 text-orange-500',
  sky:     'bg-sky-500/10 text-sky-500',
  gray:    'bg-gray-500/10 text-gray-500 dark:text-gray-400',
}

export default function PageHeader({ title, subtitle, icon: Icon, accent = 'brand' }) {
  return (
    <div className="flex items-center gap-3">
      {Icon && (
        <div className={`p-2 rounded-xl flex-shrink-0 ${ACCENTS[accent] || ACCENTS.brand}`}>
          <Icon size={20} />
        </div>
      )}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white">{title}</h1>
        {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
    </div>
  )
}
