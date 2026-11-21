import { Link, useLocation } from 'react-router-dom'
import { FolderOpen } from 'lucide-react'
import clsx from 'clsx'

export default function Layout({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation()

  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 bg-panel border-r border-border flex flex-col">
        <div className="px-5 py-4 border-b border-border">
          <span className="text-lg font-bold tracking-tight text-white">BlackBox</span>
          <p className="text-xs text-gray-500 mt-0.5">Investigation Platform</p>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          <NavItem to="/investigations" icon={<FolderOpen size={16} />} label="Investigations" active={pathname.startsWith('/investigations')} />
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-6">
        {children}
      </main>
    </div>
  )
}

function NavItem({ to, icon, label, active }: { to: string; icon: React.ReactNode; label: string; active: boolean }) {
  return (
    <Link
      to={to}
      className={clsx(
        'flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors',
        active ? 'bg-accent/20 text-accent font-medium' : 'text-gray-400 hover:text-white hover:bg-white/5'
      )}
    >
      {icon}
      {label}
    </Link>
  )
}
