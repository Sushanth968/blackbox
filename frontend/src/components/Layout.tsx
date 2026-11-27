import { Link, useLocation } from 'react-router-dom'
import { Search, FolderSearch, Library, LayoutGrid, Settings, HelpCircle, Bell, ChevronDown, Github, LogOut, User, X, CheckCircle, AlertTriangle, Info } from 'lucide-react'
import clsx from 'clsx'
import { useState, useRef, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'

const WORKSPACES = [
  { id: 'engineering', name: 'Engineering', subtitle: 'Developer Workspace', color: 'bg-success' },
  { id: 'security', name: 'Security', subtitle: 'Security Team', color: 'bg-danger' },
  { id: 'product', name: 'Product', subtitle: 'Product Workspace', color: 'bg-accent' },
]

const NOTIFICATIONS = [
  { id: 1, type: 'alert', title: 'New evidence linked', body: 'CVE-2024-1234 matched 3 investigations', time: '2m ago', read: false },
  { id: 2, type: 'warning', title: 'Investigation stalled', body: 'INV-089 has had no updates for 7 days', time: '1h ago', read: false },
  { id: 3, type: 'info', title: 'Export complete', body: 'Your evidence export is ready to download', time: '3h ago', read: true },
]

function useDropdown() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  return { open, setOpen, ref }
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation()
  const { user, logout } = useAuth()
  const [activeWorkspace, setActiveWorkspace] = useState(WORKSPACES[0])
  const [notifications, setNotifications] = useState(NOTIFICATIONS)
  const workspaceDropdown = useDropdown()
  const notifDropdown = useDropdown()
  const profileDropdown = useDropdown()
  const sidebarProfileDropdown = useDropdown()

  const unreadCount = notifications.filter(n => !n.read).length

  function markAllRead() {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })))
  }

  function dismissNotif(id: number) {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }

  return (
    <div className="flex h-screen overflow-hidden bg-surface text-foreground">
      {/* Sidebar */}
      <aside className="w-52 flex-shrink-0 bg-panel border-r border-border flex flex-col">
        {/* Logo */}
        <div className="px-4 py-4 border-b border-border">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-accent rounded-md flex items-center justify-center">
              <span className="text-xs font-bold text-white">BB</span>
            </div>
            <span className="text-sm font-bold tracking-wide text-foreground">BLACKBOX</span>
          </div>
        </div>

        {/* Workspace badge */}
        <div className="px-4 py-3 border-b border-border" ref={workspaceDropdown.ref}>
          <button
            onClick={() => workspaceDropdown.setOpen(o => !o)}
            className="w-full flex items-center justify-between gap-2 text-left bg-panel-2 border border-border rounded-lg px-3 py-2 hover:bg-black/5 transition-colors"
          >
            <div className="flex items-center gap-2 min-w-0">
              <div className={`w-2 h-2 rounded-full ${activeWorkspace.color} flex-shrink-0`} />
              <div className="min-w-0">
                <p className="text-xs font-medium text-foreground truncate">{activeWorkspace.name}</p>
                <p className="text-[10px] text-muted truncate">{activeWorkspace.subtitle}</p>
              </div>
            </div>
            <ChevronDown size={12} className={clsx('text-muted flex-shrink-0 transition-transform', workspaceDropdown.open && 'rotate-180')} />
          </button>
          {workspaceDropdown.open && (
            <div className="mt-1 bg-panel border border-border rounded-lg shadow-lg overflow-hidden z-50 absolute w-44">
              {WORKSPACES.map(ws => (
                <button
                  key={ws.id}
                  onClick={() => { setActiveWorkspace(ws); workspaceDropdown.setOpen(false) }}
                  className={clsx(
                    'w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-black/5 transition-colors',
                    activeWorkspace.id === ws.id && 'bg-accent/10'
                  )}
                >
                  <div className={`w-2 h-2 rounded-full ${ws.color} flex-shrink-0`} />
                  <div>
                    <p className="text-xs font-medium text-foreground">{ws.name}</p>
                    <p className="text-[10px] text-muted">{ws.subtitle}</p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 p-2 space-y-0.5">
          <NavItem to="/investigations" icon={<FolderSearch size={15} />} label="Investigations" active={pathname.startsWith('/investigations')} />
          <NavItem to="/evidence" icon={<Library size={15} />} label="Evidence library" active={pathname === '/evidence'} />
          <NavItem to="/workspaces" icon={<LayoutGrid size={15} />} label="Workspaces" active={pathname === '/workspaces'} />
          <NavItem to="/github-issues" icon={<Github size={15} />} label="GitHub Issues" active={pathname === '/github-issues'} />
        </nav>

        {/* Bottom nav */}
        <div className="p-2 border-t border-border space-y-0.5">
          <NavItem to="/settings" icon={<Settings size={15} />} label="Settings" active={pathname === '/settings'} />
          <NavItem to="/help" icon={<HelpCircle size={15} />} label="Help" active={pathname === '/help'} />
        </div>

        {/* User */}
        <div className="p-3 border-t border-border" ref={sidebarProfileDropdown.ref}>
          <button
            onClick={() => sidebarProfileDropdown.setOpen(o => !o)}
            className="w-full flex items-center gap-2.5 hover:bg-black/5 rounded-md p-1 transition-colors"
          >
            <div className="w-7 h-7 rounded-full bg-accent/20 border border-accent/30 flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-bold text-accent">{user?.initials ?? '??'}</span>
            </div>
            <div className="flex-1 min-w-0 text-left">
              <p className="text-xs font-medium text-foreground truncate">{user?.name ?? 'Unknown'}</p>
            </div>
            <ChevronDown size={12} className={clsx('text-muted flex-shrink-0 transition-transform', sidebarProfileDropdown.open && 'rotate-180')} />
          </button>
          {sidebarProfileDropdown.open && (
            <div className="mt-1 bg-panel border border-border rounded-lg shadow-lg overflow-hidden z-50 absolute w-44">
              <Link to="/settings" onClick={() => sidebarProfileDropdown.setOpen(false)} className="flex items-center gap-2 px-3 py-2 text-xs text-muted hover:text-foreground hover:bg-black/5 transition-colors">
                <User size={13} /> Profile
              </Link>
              <Link to="/settings" onClick={() => sidebarProfileDropdown.setOpen(false)} className="flex items-center gap-2 px-3 py-2 text-xs text-muted hover:text-foreground hover:bg-black/5 transition-colors">
                <Settings size={13} /> Settings
              </Link>
              <div className="border-t border-border" />
              <button onClick={logout} className="w-full flex items-center gap-2 px-3 py-2 text-xs text-danger hover:bg-danger/10 transition-colors">
                <LogOut size={13} /> Sign out
              </button>
            </div>
          )}
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
                className="w-full bg-surface border border-border rounded-md pl-8 pr-16 py-1.5 text-xs text-foreground placeholder-muted focus:outline-none focus:border-accent/50 transition-colors"
              />
              <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-muted border border-border rounded px-1 py-0.5 font-mono">⌘K</span>
            </div>
          </div>
          <div className="flex items-center gap-3 ml-auto">
            {/* Notifications */}
            <div ref={notifDropdown.ref} className="relative">
              <button
                onClick={() => notifDropdown.setOpen(o => !o)}
                className="relative p-1.5 text-muted hover:text-foreground transition-colors"
              >
                <Bell size={16} />
                {unreadCount > 0 && (
                  <span className="absolute top-0.5 right-0.5 w-3.5 h-3.5 bg-danger rounded-full text-[9px] font-bold flex items-center justify-center text-white">
                    {unreadCount}
                  </span>
                )}
              </button>
              {notifDropdown.open && (
                <div className="absolute right-0 mt-1 w-80 bg-panel border border-border rounded-lg shadow-xl z-50 overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                    <span className="text-xs font-semibold text-foreground">Notifications</span>
                    {unreadCount > 0 && (
                      <button onClick={markAllRead} className="text-[10px] text-accent hover:underline">Mark all read</button>
                    )}
                  </div>
                  {notifications.length === 0 ? (
                    <p className="text-xs text-muted text-center py-6">No notifications</p>
                  ) : (
                    notifications.map(n => (
                      <div key={n.id} className={clsx('flex items-start gap-3 px-4 py-3 border-b border-border last:border-0 hover:bg-black/5', !n.read && 'bg-accent/5')}>
                        <div className="mt-0.5 flex-shrink-0">
                          {n.type === 'alert' && <CheckCircle size={14} className="text-success" />}
                          {n.type === 'warning' && <AlertTriangle size={14} className="text-warning" />}
                          {n.type === 'info' && <Info size={14} className="text-accent" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-foreground">{n.title}</p>
                          <p className="text-[11px] text-muted mt-0.5">{n.body}</p>
                          <p className="text-[10px] text-muted/60 mt-1">{n.time}</p>
                        </div>
                        <button onClick={() => dismissNotif(n.id)} className="text-muted hover:text-foreground flex-shrink-0 mt-0.5">
                          <X size={12} />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* Profile */}
            <div ref={profileDropdown.ref} className="relative">
              <button
                onClick={() => profileDropdown.setOpen(o => !o)}
                className="w-7 h-7 rounded-full bg-accent/20 border border-accent/30 flex items-center justify-center hover:border-accent/60 transition-colors"
              >
                <span className="text-xs font-bold text-accent">{user?.initials ?? '??'}</span>
              </button>
              {profileDropdown.open && (
                <div className="absolute right-0 mt-1 w-48 bg-panel border border-border rounded-lg shadow-xl z-50 overflow-hidden">
                  <div className="px-3 py-3 border-b border-border">
                    <p className="text-xs font-semibold text-foreground">{user?.name ?? 'Unknown'}</p>
                    <p className="text-[10px] text-muted">{user?.email ?? ''}</p>
                  </div>
                  <Link to="/settings" onClick={() => profileDropdown.setOpen(false)} className="flex items-center gap-2 px-3 py-2 text-xs text-muted hover:text-foreground hover:bg-black/5 transition-colors">
                    <User size={13} /> Profile
                  </Link>
                  <Link to="/settings" onClick={() => profileDropdown.setOpen(false)} className="flex items-center gap-2 px-3 py-2 text-xs text-muted hover:text-foreground hover:bg-black/5 transition-colors">
                    <Settings size={13} /> Settings
                  </Link>
                  <div className="border-t border-border" />
                  <button onClick={logout} className="w-full flex items-center gap-2 px-3 py-2 text-xs text-danger hover:bg-danger/10 transition-colors">
                    <LogOut size={13} /> Sign out
                  </button>
                </div>
              )}
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
          : 'text-muted hover:text-foreground hover:bg-black/5'
      )}
    >
      {icon}
      {label}
    </Link>
  )
}
