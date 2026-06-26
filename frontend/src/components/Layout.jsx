import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { useBranding } from '../context/BrandingContext'
import { FilterProvider } from '../context/FilterContext'
import Icon from './Icon'
import SearchBox from './SearchBox'

function ThemeBtn() {
  const { dark, toggle } = useTheme()
  return (
    <button onClick={toggle} className="btn-ghost p-2" title="Toggle theme">
      {dark ? (
        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M4 12H2m20 0h-2M5.6 5.6l1.4 1.4m10 10l1.4 1.4m0-12.8l-1.4 1.4m-10 10l-1.4 1.4" />
        </svg>
      ) : (
        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z" /></svg>
      )}
    </button>
  )
}

/** Sidebar nav item: active accent bar + a strong gradient tooltip when collapsed.
 *  The tooltip is portalled to <body> with fixed coords so the scrolling sidebar
 *  never clips it. Shows on hover AND focus (keyboard or click), hides on blur. */
function NavItem({ to, icon, label, collapsed, onClick, end }) {
  const [tip, setTip] = useState(null)
  const show = (e) => {
    if (!collapsed) return
    const r = e.currentTarget.getBoundingClientRect()
    setTip({ top: r.top + r.height / 2, left: r.right + 12 })
  }
  const hide = () => setTip(null)
  useEffect(() => { if (!collapsed) setTip(null) }, [collapsed])

  return (
    <>
      <NavLink to={to} end={end}
        onClick={(e) => { hide(); onClick?.(e) }}
        onMouseEnter={show} onMouseLeave={hide} onFocus={show} onBlur={hide}
        className={({ isActive }) =>
          `relative flex items-center gap-3 rounded-xl text-sm font-medium outline-none transition
           ${collapsed ? 'justify-center px-0 py-2.5' : 'px-3 py-2'}
           ${isActive ? 'text-[var(--text)] bg-[var(--surface-2)]' : 'muted hover:text-[var(--text)] hover:bg-[var(--surface-2)]'}
           focus-visible:ring-2 focus-visible:ring-[color:var(--brand-1)]`}>
        {({ isActive }) => (
          <>
            {isActive && <span className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-full brandmark" />}
            <Icon name={icon} className={`w-[18px] h-[18px] shrink-0 ${isActive ? 'text-indigo-500' : ''}`} />
            {!collapsed && <span className="truncate">{label}</span>}
          </>
        )}
      </NavLink>
      {tip && createPortal(
        <div style={{ position: 'fixed', top: tip.top, left: tip.left, transform: 'translateY(-50%)', zIndex: 80 }}
          className="pointer-events-none rounded-lg px-3 py-1.5 text-xs font-bold text-white whitespace-nowrap shadow-2xl brandmark">
          {label}
          <span className="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-y-[6px] border-y-transparent border-r-[6px]"
            style={{ borderRightColor: 'var(--brand-1)' }} />
        </div>, document.body)}
    </>
  )
}

export default function Layout() {
  const { user, logout, isAdmin } = useAuth()
  const { brand_name, brand_tagline, logo_url, letter } = useBranding()
  const navigate = useNavigate()
  const [modules, setModules] = useState([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('na_sidebar') === '1')

  useEffect(() => { localStorage.setItem('na_sidebar', collapsed ? '1' : '0') }, [collapsed])

  useEffect(() => {
    api.get('/dashboards/me').then(({ data }) => {
      setModules(data.modules); setLoading(false)
      if (data.modules.length) navigate(`/m/${data.modules[0].key}`, { replace: true })
    }).catch(() => setLoading(false))
  }, []) // eslint-disable-line

  const initials = (user?.full_name || 'U').split(' ').map((w) => w[0]).slice(0, 2).join('')
  const railW = collapsed ? 'lg:w-20' : 'lg:w-64'

  const LogoMark = ({ size = 'w-9 h-9 text-base' }) => (
    <div className={`${size} rounded-xl grid place-items-center text-white font-extrabold font-display shrink-0 overflow-hidden brandmark`}>
      {logo_url ? <img src={logo_url} alt="" className="w-full h-full object-contain" /> : letter}
    </div>
  )

  return (
    <FilterProvider>
    <div className="h-screen flex overflow-hidden">
      {/* Sidebar — fixed, never scrolls away */}
      <aside className={`fixed lg:static z-30 h-screen w-64 ${railW} shrink-0 flex flex-col transition-all duration-200
        bg-[var(--surface)] border-r hairline ${open ? '' : '-translate-x-full lg:translate-x-0'}`}>
        <div className={`h-16 flex items-center gap-2.5 border-b hairline ${collapsed ? 'lg:justify-center px-3' : 'px-5'}`}>
          <LogoMark />
          {!collapsed && (
            <div className="min-w-0">
              <div className="font-bold leading-tight text-[15px] font-display truncate">{brand_name}</div>
              {brand_tagline && <div className="text-[10.5px] muted tracking-[0.12em] uppercase truncate">{brand_tagline}</div>}
            </div>
          )}
        </div>

        <nav className="flex-1 overflow-y-auto p-3 space-y-0.5">
          {!collapsed && <div className="eyebrow px-3 pt-1 pb-2">Dashboards</div>}
          {loading && <div className="px-3 py-2 text-sm muted">Loading…</div>}
          {modules.map((m) => (
            <NavItem key={m.key} to={`/m/${m.key}`} icon={m.icon} label={m.name}
              collapsed={collapsed} onClick={() => setOpen(false)} />
          ))}
          <div className="mt-2 border-t hairline pt-3 space-y-0.5">
            {!collapsed && <div className="eyebrow px-3 pb-2">Sharing</div>}
            <NavItem to="/shares" icon="chat" label="Shared Links" collapsed={collapsed} onClick={() => setOpen(false)} />
          </div>
          {isAdmin && (
            <div className="mt-2 border-t hairline pt-3 space-y-0.5">
              {!collapsed && <div className="eyebrow px-3 pb-2">Administration</div>}
              <NavItem to="/admin/users" icon="users" label="User Management" collapsed={collapsed} onClick={() => setOpen(false)} />
              <NavItem to="/admin/settings" icon="sparkles" label="Branding & Settings" collapsed={collapsed} onClick={() => setOpen(false)} />
              <NavItem to="/admin" end icon="cog" label="Roles & Dashboards" collapsed={collapsed} onClick={() => setOpen(false)} />
            </div>
          )}
        </nav>

        <button onClick={() => setCollapsed((c) => !c)}
          className="hidden lg:flex items-center gap-2 m-3 px-3 py-2 rounded-xl text-xs font-semibold muted hover:bg-[var(--surface-2)] transition"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
          <svg className={`w-4 h-4 transition-transform ${collapsed ? 'rotate-180' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 18l-6-6 6-6" /></svg>
          {!collapsed && <span>Collapse</span>}
        </button>
      </aside>

      {open && <div className="fixed inset-0 bg-black/50 z-20 lg:hidden" onClick={() => setOpen(false)} />}

      {/* Right column — header fixed, only main scrolls */}
      <div className="flex-1 flex flex-col min-w-0 h-screen">
        <header className="app-header h-16 shrink-0 flex items-center gap-3 px-4 lg:px-6 bg-[var(--surface)] border-b hairline">
          <button className="lg:hidden btn-ghost p-2" onClick={() => setOpen(true)}>
            <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 6h16M4 12h16M4 18h16" /></svg>
          </button>
          <div className="hidden md:flex flex-1 max-w-md"><SearchBox /></div>
          <div className="flex items-center gap-2 ml-auto">
            <ThemeBtn />
            <NavLink to="/profile" className="flex items-center gap-2 rounded-xl px-1.5 py-1 hover:bg-[var(--surface-2)] transition" title="My profile">
              <div className="hidden sm:flex flex-col items-end mr-1">
                <span className="text-sm font-semibold leading-tight">{user?.full_name}</span>
                <span className="text-[11px] muted capitalize">{user?.role?.name}</span>
              </div>
              <div className="w-9 h-9 rounded-full overflow-hidden grid place-items-center text-white text-xs font-bold brandmark">
                {user?.avatar_url ? <img src={user.avatar_url} alt="" className="w-full h-full object-cover" /> : initials}
              </div>
            </NavLink>
            <button onClick={logout} className="btn-ghost text-sm">Sign out</button>
          </div>
        </header>

        <main className="app-main flex-1 overflow-y-auto p-4 lg:p-6">
          <Outlet context={{ modules }} />
        </main>
      </div>
    </div>
    </FilterProvider>
  )
}
