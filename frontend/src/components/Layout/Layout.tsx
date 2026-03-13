import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import {
  Building2, Upload, BarChart3, Shield, LogOut,
  TrendingUp, Users, ChevronDown,
} from 'lucide-react'
import { useState } from 'react'
import clsx from 'clsx'

export default function Layout() {
  const { name, isAdmin, logout } = useAuthStore()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className={clsx(
        'bg-brand-700 text-white flex flex-col transition-all duration-200',
        sidebarOpen ? 'w-64' : 'w-16',
      )}>
        {/* Logo */}
        <div className="flex items-center gap-3 p-4 border-b border-brand-600">
          <div className="w-8 h-8 bg-brand-500 rounded-lg flex items-center justify-center flex-shrink-0">
            <TrendingUp size={18} className="text-white" />
          </div>
          {sidebarOpen && (
            <span className="font-bold text-sm tracking-wide">TallyToInsights</span>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          <NavItem to="/companies" icon={<Building2 size={18} />} label="Companies" open={sidebarOpen} />
          {isAdmin && (
            <NavItem to="/users" icon={<Users size={18} />} label="Users" open={sidebarOpen} />
          )}
        </nav>

        {/* User */}
        <div className="p-3 border-t border-brand-600">
          <div className="flex items-center gap-2 p-2">
            <div className="w-8 h-8 bg-brand-500 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0">
              {(name || 'U').charAt(0).toUpperCase()}
            </div>
            {sidebarOpen && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{name}</p>
                {isAdmin && <p className="text-xs text-brand-50 opacity-70">Admin</p>}
              </div>
            )}
            <button onClick={handleLogout} className="p-1 hover:bg-brand-600 rounded">
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
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
          'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
          isActive
            ? 'bg-brand-500 text-white'
            : 'text-brand-50 opacity-80 hover:bg-brand-600 hover:opacity-100',
        )
      }
    >
      <span className="flex-shrink-0">{icon}</span>
      {open && <span>{label}</span>}
    </NavLink>
  )
}
