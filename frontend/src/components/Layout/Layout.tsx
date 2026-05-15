import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import {
  Building2, TrendingUp, LogOut, Settings, CheckSquare, ChevronLeft, ChevronRight,
} from 'lucide-react'
import { useState } from 'react'
import clsx from 'clsx'

export default function Layout() {
  const { name, logout } = useAuthStore()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const handleLogout = () => {
    if (window.confirm('Are you sure you want to log out?')) {
      logout()
      navigate('/login')
    }
  }

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <aside className={clsx(
        'bg-brand-700 text-white flex flex-col transition-all duration-200 relative flex-shrink-0',
        sidebarOpen ? 'w-56' : 'w-14',
      )}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-brand-600">
          <div className="w-7 h-7 bg-brand-500 rounded-md flex items-center justify-center flex-shrink-0">
            <TrendingUp size={15} className="text-white" />
          </div>
          {sidebarOpen && (
            <span className="font-semibold text-sm tracking-wide truncate">TallyToInsights</span>
          )}
        </div>

        {/* Toggle button */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="absolute -right-3 top-14 w-6 h-6 bg-brand-700 border border-brand-500 rounded-full flex items-center justify-center text-brand-100 hover:bg-brand-600 z-10"
        >
          {sidebarOpen ? <ChevronLeft size={12} /> : <ChevronRight size={12} />}
        </button>

        {/* Nav */}
        <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
          <NavItem to="/companies" icon={<Building2 size={16} />} label="Companies" open={sidebarOpen} />
          <NavItem to="/checks" icon={<CheckSquare size={16} />} label="Checks" open={sidebarOpen} />
        </nav>

        {/* Divider */}
        <div className="mx-3 border-t border-brand-600" />

        {/* Bottom: Settings + User */}
        <div className="px-2 py-2 space-y-0.5">
          <NavItem to="/settings" icon={<Settings size={16} />} label="Settings" open={sidebarOpen} />
        </div>

        {/* User section */}
        <div className="px-3 py-3 border-t border-brand-600">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-brand-500 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0">
              {(name || 'U').charAt(0).toUpperCase()}
            </div>
            {sidebarOpen && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate leading-none">{name}</p>
              </div>
            )}
            <button
              onClick={handleLogout}
              title="Logout"
              className="p-1.5 hover:bg-brand-600 rounded-md flex-shrink-0 opacity-70 hover:opacity-100 transition-opacity"
            >
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto bg-gray-50">
        <Outlet />
      </main>
    </div>
  )
}

function NavItem({
  to, icon, label, open,
}: {
  to: string
  icon: React.ReactNode
  label: string
  open: boolean
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        clsx(
          'flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm transition-colors',
          isActive
            ? 'bg-brand-500 text-white'
            : 'text-brand-100 opacity-80 hover:bg-brand-600 hover:opacity-100',
        )
      }
    >
      <span className="flex-shrink-0">{icon}</span>
      {open && <span className="truncate">{label}</span>}
    </NavLink>
  )
}
