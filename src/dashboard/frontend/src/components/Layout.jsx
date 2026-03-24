import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, MessageSquare, Wrench, Bot, Brain,
  Zap, HeartPulse, Shield, ScrollText, Settings,
  Sun, Moon, Menu, X,
} from 'lucide-react'
import KovoLogo from './KovoLogo'
import { useTheme } from '../context/ThemeContext'

const NAV = [
  { to: '/',          label: 'Overview',  Icon: LayoutDashboard },
  { to: '/chat',      label: 'Chat',      Icon: MessageSquare },
  { to: '/tools',     label: 'Tools',     Icon: Wrench },
  { to: '/agents',    label: 'Agents',    Icon: Bot },
  { to: '/memory',    label: 'Memory',    Icon: Brain },
  { to: '/skills',    label: 'Skills',    Icon: Zap },
  { to: '/heartbeat', label: 'Heartbeat', Icon: HeartPulse },
  { to: '/security',  label: 'Security',  Icon: Shield },
  { to: '/logs',      label: 'Logs',      Icon: ScrollText },
  { to: '/settings',  label: 'Settings',  Icon: Settings },
]

function NavItem({ to, label, Icon, onClick }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      onClick={onClick}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
          isActive
            ? 'bg-brand-500 text-white'
            : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white'
        }`
      }
    >
      <Icon size={18} />
      {label}
    </NavLink>
  )
}

export default function Layout({ children }) {
  const { theme, toggle } = useTheme()
  const [mobileOpen, setMobileOpen] = useState(false)
  const closeMobile = () => setMobileOpen(false)

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950">
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/50 md:hidden"
          onClick={closeMobile}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-30 flex flex-col w-56 bg-white dark:bg-gray-900
          border-r border-gray-200 dark:border-gray-800 transform transition-transform duration-200
          md:static md:translate-x-0
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-5 border-b border-gray-200 dark:border-gray-800">
          <KovoLogo size={36} />
          <div>
            <div className="text-base font-bold text-brand-500">Kovo</div>
            <div className="text-xs text-gray-400 dark:text-gray-500">AI Assistant</div>
          </div>
          <button
            onClick={closeMobile}
            className="ml-auto md:hidden text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            <X size={18} />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {NAV.map(item => (
            <NavItem key={item.to} {...item} onClick={closeMobile} />
          ))}
        </nav>

        {/* Theme toggle */}
        <div className="px-4 py-4 border-t border-gray-200 dark:border-gray-800">
          <button
            onClick={toggle}
            className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            {theme === 'dark' ? 'Light mode' : 'Dark mode'}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile topbar */}
        <header className="flex items-center gap-3 px-4 py-3 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 md:hidden">
          <button
            onClick={() => setMobileOpen(true)}
            className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
          >
            <Menu size={22} />
          </button>
          <KovoLogo size={28} />
          <span className="text-sm font-bold text-brand-500">Kovo</span>
          <button
            onClick={toggle}
            className="ml-auto text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
          >
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
