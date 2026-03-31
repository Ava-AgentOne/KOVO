export default function StatusCard({ title, value, percent, sub, ok, icon: Icon }) {
  const barColor =
    percent === undefined ? 'bg-brand-500'
    : percent > 85 ? 'bg-red-500'
    : percent > 60 ? 'bg-amber-400'
    : 'bg-emerald-500'

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">{title}</p>
        {Icon && <Icon size={16} className="text-gray-400" />}
        {ok !== undefined && (
          <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${ok ? 'bg-emerald-500' : 'bg-red-500'}`} />
        )}
      </div>
      <p className={`text-2xl font-bold ${ok === false ? 'text-red-500' : 'text-gray-900 dark:text-white'}`}>{value ?? '—'}</p>
      {percent !== undefined && (
        <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-500 ${barColor}`}
            style={{ width: `${Math.min(percent, 100)}%` }}
          />
        </div>
      )}
      {sub && <p className="text-xs text-gray-500 dark:text-gray-400">{sub}</p>}
    </div>
  )
}
