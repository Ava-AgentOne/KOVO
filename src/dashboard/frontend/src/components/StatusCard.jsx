export default function StatusCard({ title, value, ok, sub }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">{title}</p>
      <div className="flex items-center gap-2">
        <span className={`text-lg font-semibold ${ok === true ? 'text-green-400' : ok === false ? 'text-red-400' : 'text-gray-200'}`}>
          {value}
        </span>
        {ok !== undefined && (
          <span className={`text-xs px-1.5 py-0.5 rounded ${ok ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}>
            {ok ? 'online' : 'offline'}
          </span>
        )}
      </div>
      {sub && <p className="text-xs text-gray-600 mt-1">{sub}</p>}
    </div>
  )
}
