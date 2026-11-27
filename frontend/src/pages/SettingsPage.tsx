import { useState } from 'react'
import { User, Bell, Shield, Palette, Key } from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../context/AuthContext'

const SECTIONS = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'api', label: 'API Keys', icon: Key },
]

export default function SettingsPage() {
  const { user } = useAuth()
  const [active, setActive] = useState('profile')
  const [saved, setSaved] = useState(false)

  function handleSave() {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="flex h-full">
      <div className="w-48 flex-shrink-0 border-r border-border p-3 space-y-0.5">
        {SECTIONS.map(s => (
          <button
            key={s.id}
            onClick={() => setActive(s.id)}
            className={clsx(
              'w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-xs transition-colors text-left',
              active === s.id
                ? 'bg-accent/10 text-accent font-medium border border-accent/20'
                : 'text-muted hover:text-foreground hover:bg-black/5'
            )}
          >
            <s.icon size={14} />
            {s.label}
          </button>
        ))}
      </div>

      <div className="flex-1 p-8 max-w-2xl">
        {active === 'profile' && <ProfileSection onSave={handleSave} saved={saved} name={user?.name ?? ''} email={user?.email ?? ''} initials={user?.initials ?? '??'} />}
        {active === 'notifications' && <NotificationsSection onSave={handleSave} saved={saved} />}
        {active === 'security' && <SecuritySection onSave={handleSave} saved={saved} />}
        {active === 'appearance' && <AppearanceSection onSave={handleSave} saved={saved} />}
        {active === 'api' && <ApiKeysSection />}
      </div>
    </div>
  )
}

function SectionHeader({ title, description }: { title: string; description: string }) {
  return (
    <div className="mb-6">
      <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      <p className="text-xs text-muted mt-1">{description}</p>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <label className="block text-xs font-medium text-foreground mb-1.5">{label}</label>
      {children}
    </div>
  )
}

function Input({ defaultValue, placeholder, type = 'text' }: { defaultValue?: string; placeholder?: string; type?: string }) {
  return (
    <input
      type={type}
      defaultValue={defaultValue}
      placeholder={placeholder}
      className="w-full bg-surface border border-border rounded-md px-3 py-2 text-xs text-foreground placeholder-muted focus:outline-none focus:border-accent/50 transition-colors"
    />
  )
}

function SaveButton({ onSave, saved }: { onSave: () => void; saved: boolean }) {
  return (
    <button
      onClick={onSave}
      className={clsx(
        'mt-6 px-4 py-2 rounded-md text-xs font-medium transition-colors',
        saved ? 'bg-success/20 text-success border border-success/30' : 'bg-accent text-white hover:bg-accent/80'
      )}
    >
      {saved ? 'Saved!' : 'Save changes'}
    </button>
  )
}

function Toggle({ label, description, defaultChecked }: { label: string; description: string; defaultChecked?: boolean }) {
  const [checked, setChecked] = useState(defaultChecked ?? false)
  return (
    <div className="flex items-center justify-between py-3 border-b border-border last:border-0">
      <div>
        <p className="text-xs font-medium text-foreground">{label}</p>
        <p className="text-[11px] text-muted mt-0.5">{description}</p>
      </div>
      <button
        onClick={() => setChecked(c => !c)}
        className={clsx('w-9 h-5 rounded-full transition-colors flex-shrink-0', checked ? 'bg-accent' : 'bg-black/10')}
      >
        <span className={clsx('block w-3.5 h-3.5 rounded-full bg-white shadow transition-transform mx-0.5', checked ? 'translate-x-4' : 'translate-x-0')} />
      </button>
    </div>
  )
}

function ProfileSection({ onSave, saved, name, email, initials }: { onSave: () => void; saved: boolean; name: string; email: string; initials: string }) {
  return (
    <div>
      <SectionHeader title="Profile" description="Manage your personal information" />
      <div className="flex items-center gap-4 mb-6">
        <div className="w-14 h-14 rounded-full bg-accent/20 border border-accent/30 flex items-center justify-center">
          <span className="text-lg font-bold text-accent">{initials}</span>
        </div>
        <button className="text-xs text-accent hover:underline">Change avatar</button>
      </div>
      <Field label="Full name"><Input defaultValue={name} /></Field>
      <Field label="Email"><Input defaultValue={email} type="email" /></Field>
      <Field label="Role"><Input defaultValue="Security Engineer" /></Field>
      <SaveButton onSave={onSave} saved={saved} />
    </div>
  )
}

function NotificationsSection({ onSave, saved }: { onSave: () => void; saved: boolean }) {
  return (
    <div>
      <SectionHeader title="Notifications" description="Choose what you get notified about" />
      <div className="bg-panel border border-border rounded-lg px-4">
        <Toggle label="New evidence matched" description="When evidence is linked to an investigation" defaultChecked />
        <Toggle label="Investigation updates" description="When an investigation status changes" defaultChecked />
        <Toggle label="Stalled investigations" description="When an investigation has no updates for 7 days" defaultChecked />
        <Toggle label="Export complete" description="When a data export is ready to download" />
        <Toggle label="Weekly digest" description="A summary of activity every Monday morning" />
      </div>
      <SaveButton onSave={onSave} saved={saved} />
    </div>
  )
}

function SecuritySection({ onSave, saved }: { onSave: () => void; saved: boolean }) {
  return (
    <div>
      <SectionHeader title="Security" description="Manage your password and authentication" />
      <Field label="Current password"><Input type="password" placeholder="••••••••" /></Field>
      <Field label="New password"><Input type="password" placeholder="••••••••" /></Field>
      <Field label="Confirm new password"><Input type="password" placeholder="••••••••" /></Field>
      <div className="mt-6 p-4 bg-panel border border-border rounded-lg">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-foreground">Two-factor authentication</p>
            <p className="text-[11px] text-muted mt-0.5">Add an extra layer of security to your account</p>
          </div>
          <button className="text-xs bg-accent/10 text-accent border border-accent/20 rounded-md px-3 py-1.5 hover:bg-accent/20 transition-colors">Enable 2FA</button>
        </div>
      </div>
      <SaveButton onSave={onSave} saved={saved} />
    </div>
  )
}

function AppearanceSection({ onSave, saved }: { onSave: () => void; saved: boolean }) {
  const [theme, setTheme] = useState('light')
  return (
    <div>
      <SectionHeader title="Appearance" description="Customize how Blackbox looks" />
      <p className="text-xs font-medium text-foreground mb-3">Theme</p>
      <div className="flex gap-3 mb-6">
        {(['light', 'dark', 'system'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTheme(t)}
            className={clsx(
              'flex-1 py-3 rounded-lg border text-xs capitalize transition-colors',
              theme === t ? 'border-accent text-accent bg-accent/10' : 'border-border text-muted hover:border-black/20'
            )}
          >
            {t}
          </button>
        ))}
      </div>
      <div className="bg-panel border border-border rounded-lg px-4">
        <Toggle label="Compact density" description="Reduce spacing for more information density" />
        <Toggle label="Animate transitions" description="Enable smooth page and panel transitions" defaultChecked />
      </div>
      <SaveButton onSave={onSave} saved={saved} />
    </div>
  )
}

function ApiKeysSection() {
  const [keys] = useState([
    { id: 1, name: 'CI Integration', prefix: 'bbx_ci_••••••••', created: 'Nov 12, 2026', lastUsed: '2 hours ago' },
    { id: 2, name: 'Export Script', prefix: 'bbx_ex_••••••••', created: 'Oct 3, 2026', lastUsed: '5 days ago' },
  ])

  return (
    <div>
      <SectionHeader title="API Keys" description="Manage keys for programmatic access" />
      <div className="space-y-3 mb-4">
        {keys.map(k => (
          <div key={k.id} className="bg-panel border border-border rounded-lg px-4 py-3 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-foreground">{k.name}</p>
              <p className="text-[11px] text-muted mt-0.5 font-mono">{k.prefix}</p>
              <p className="text-[10px] text-muted/60 mt-1">Created {k.created} · Last used {k.lastUsed}</p>
            </div>
            <button className="text-xs text-danger hover:bg-danger/10 px-3 py-1.5 rounded-md transition-colors">Revoke</button>
          </div>
        ))}
      </div>
      <button className="text-xs bg-accent text-white px-4 py-2 rounded-md hover:bg-accent/80 transition-colors">
        Generate new key
      </button>
    </div>
  )
}
