// v2.1 design system: consistent empty state — icon + one line + optional action.
export default function EmptyState({ icon: Icon, title, hint, actionLabel, onAction }) {
  return (
    <div className="text-center py-12 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl">
      {Icon && <Icon size={28} className="text-gray-300 dark:text-gray-600 mx-auto mb-2" />}
      <p className="text-sm text-gray-500">{title}</p>
      {hint && <p className="text-xs text-gray-400 mt-1">{hint}</p>}
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-4 text-xs bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 rounded-lg transition-colors"
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}
