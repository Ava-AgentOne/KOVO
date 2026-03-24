import { NavLink, useLocation } from 'react-router-dom'

const nav = [
  { to: '/',          label: '🏠 Overview'   },
  { to: '/chat',      label: '💬 Chat'       },
  { to: '/tools',     label: '🔧 Tools'      },
  { to: '/agents',    label: '🤖 Agents'     },
  { to: '/memory',    label: '🧠 Memory'     },
  { to: '/skills',    label: '⚡ Skills'     },
  { to: '/heartbeat', label: '💓 Heartbeat'  },
  { to: '/logs',      label: '📋 Logs'       },
  { to: '/settings',  label: '⚙️ Settings'  },
]

export default function Layout({ children }) {
  const location = useLocation()
  const isChatPage = location.pathname === '/chat'

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-48 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
        <div className="px-4 py-5 border-b border-gray-800">
          <span className="text-xl font-bold text-brand-500">🦞 MiniClaw</span>
          <p className="text-xs text-gray-500 mt-0.5">AI Agent Dashboard</p>
        </div>
        <nav className="flex-1 py-4 space-y-0.5 px-2">
          {nav.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `block px-3 py-2 rounded text-sm transition-colors ${
                  isActive
                    ? 'bg-brand-700 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-3 border-t border-gray-800 text-xs text-gray-600">
          v0.3.0 · Al Ain, UAE
        </div>
      </aside>

      {/* Main content — Chat page gets full height flex layout */}
      <main className={`flex-1 min-h-0 bg-gray-950 ${isChatPage ? 'flex flex-col p-6' : 'overflow-auto p-6'}`}>
        {children}
      </main>
    </div>
  )
}
