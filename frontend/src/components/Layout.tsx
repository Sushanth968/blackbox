import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Search, FolderSearch, Library, LayoutGrid, Settings, HelpCircle, Bell, ChevronDown } from 'lucide-react'
import clsx from 'clsx'

export default function Layout({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation()

  return (
    <div className="flex h-screen overflow-hidden bg-surface text-white">
      {/* Sidebar */}
      <aside className="w-52 flex-shrink-0 bg-panel border-r border-border flex flex-col">
        {/* Logo */}
        <div className="px-4 py-4 border-b border-border">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-white/10 border border-border rounded-md flex items-center justify-center">
              <span className="text-xs font-bold text-white">BB</span>
            </div>
            <span className="text-sm font-bold tracking-wide text-white">BLACKBOX</span>
          </div>
        </div>

        {/* Workspace badge */}
        <div className="px-4 py-3 border-b border-border">
          <button className="w-full flex items-center justify-between gap-2 text-left bg-panel-2 border border-border rounded-lg px-3 py-2 hover:bg-white/5 transition-colors">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-2 h-2 rounded-full bg-success flex-shrink-0" />
              <div className="min-w-0">
                <p className="text-xs font-medium text-white truncate">Engineering</p>
                <p className="text-[10px] text-muted truncate">Developer Workspace</p>
              </div>
            </div>
            <ChevronDown size={12} className="text-muted flex-shrink-0" />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-2 space-y-0.5">
          <NavItem to="/" icon={<LayoutDashboard size={15} />} label="Overview" active={pathname === '/'} />
          <NavItem to="/investigations" icon={<FolderSearch size={15} />} label="Investigations" active={pathname.startsWith('/investigations')} />
          <NavItem to="/evidence" icon={<Library size={15} />} label="Evidence library" active={pathname === '/evidence'} />
          <NavItem to="/workspaces" icon={<LayoutGrid size={15} />} label="Workspaces" active={pathname === '/workspaces'} />
        </nav>

        {/* Bottom nav */}
        <div className="p-2 border-t border-border space-y-0.5">
          <NavItem to="/settings" icon={<Settings size={15} />} label="Settings" active={pathname === '/settings'} />
          <NavItem to="/help" icon={<HelpCircle size={15} />} label="Help" active={pathname === '/help'} />
        </div>

        {/* User */}
        <div className="p-3 border-t border-border">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-full bg-accent/20 border border-accent/30 flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-bold text-accent">KR</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-white truncate">Karthik</p>
            </div>
            <ChevronDown size={12} className="text-muted flex-shrink-0" />
          </div>
        </div>
      </aside>

      {/* Right side: top bar + content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-12 flex-shrink-0 border-b border-border bg-panel flex items-center px-5 gap-4">
          <div className="flex-1 flex items-center gap-2 max-w-xl">
            <div className="flex-1 relative">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
              <input
                type="text"
                placeholder="Search events, evidence, entities..."
                className="w-full bg-surface border border-border rounded-md pl-8 pr-16 py-1.5 text-xs text-white placeholder-muted focus:outline-none focus:border-accent/50 transition-colors"
              />
              <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-muted border border-border rounded px-1 py-0.5 font-mono">⌘K</span>
            </div>
          </div>
          <div className="flex items-center gap-3 ml-auto">
            <button className="relative p-1.5 text-muted hover:text-white transition-colors">
              <Bell size={16} />
              <span className="absolute top-0.5 right-0.5 w-3.5 h-3.5 bg-danger rounded-full text-[9px] font-bold flex items-center justify-center text-white">3</span>
            </button>
            <div className="w-7 h-7 rounded-full bg-accent/20 border border-accent/30 flex items-center justify-center">
              <span className="text-xs font-bold text-accent">KR</span>
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  )
}

function NavItem({ to, icon, label, active }: { to: string; icon: React.ReactNode; label: string; active: boolean }) {
  return (
    <Link
      to={to}
      className={clsx(
        'flex items-center gap-2.5 px-3 py-2 rounded-md text-xs transition-colors',
        active
          ? 'bg-accent/10 text-accent font-medium border border-accent/20'
          : 'text-muted hover:text-white hover:bg-white/5'
      )}
    >
      {icon}
      {label}
    </Link>
  )
}
