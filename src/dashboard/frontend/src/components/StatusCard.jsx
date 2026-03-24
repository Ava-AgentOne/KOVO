export default function StatusCard({ title, value, percent, sub, ok, icon: Icon }) {
  const barColor =
    percent === undefined ? 'bg-brand-500'
    : percent > 90 ? 'bg-red-500'
    : percent > 75 ? 'bg-yellow-500'
    : 'bg-green-500'

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">{title}</p>
        {Icon && <Icon size={16} className="text-gray-400" />}
        {ok !== undefined && (
          <span className={`text-xs px-1.5 py-0.5 rounded-full ${ok ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400' : 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-400'}`}>
            {ok ? 'online' : 'offline'}
          </span>
        )}
      </div>
      <p className="text-2xl font-bold text-gray-900 dark:text-white">{value ?? '—'}</p>
      {percent !== undefined && (
        <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-1.5">
          <div
            className={`h-1.5 rounded-full transition-all ${barColor}`}
            style={{ width: `${Math.min(percent, 100)}%` }}
          />
        </div>
      )}
      {sub && <p className="text-xs text-gray-500 dark:text-gray-600">{sub}</p>}
    </div>
  )
}
