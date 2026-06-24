import { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { FilterProvider } from '../context/FilterContext'
import Icon from './Icon'

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

export default function Layout() {
  const { user, logout, isAdmin } = useAuth()
  const navigate = useNavigate()
  const [modules, setModules] = useState([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    api.get('/dashboards/me').then(({ data }) => {
      setModules(data.modules); setLoading(false)
      if (data.modules.length) navigate(`/m/${data.modules[0].key}`, { replace: true })
    }).catch(() => setLoading(false))
  }, []) // eslint-disable-line

  const initials = (user?.full_name || 'U').split(' ').map((w) => w[0]).slice(0, 2).join('')

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className={`fixed lg:static z-30 h-screen w-64 shrink-0 flex flex-col transition-transform
        bg-[var(--surface)] border-r hairline ${open ? '' : '-translate-x-full lg:translate-x-0'}`}>
        <div className="h-16 flex items-center gap-2.5 px-5 border-b hairline">
          <div className="w-9 h-9 rounded-xl grid place-items-center text-white font-extrabold"
            style={{ background: 'linear-gradient(135deg,#3b82f6,#4f46e5)' }}>N</div>
          <div>
            <div className="font-bold leading-tight text-[15px]">Nursery Analytics</div>
            <div className="text-[11px] muted tracking-wide">ENTERPRISE · LONDON</div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto p-3 space-y-0.5">
          {loading && <div className="px-3 py-2 text-sm muted">Loading…</div>}
          {modules.map((m) => (
            <NavLink key={m.key} to={`/m/${m.key}`} onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition ${
                  isActive ? 'text-white' : 'muted hover:text-[var(--text)]'}`}
              style={({ isActive }) => isActive
                ? { background: 'linear-gradient(135deg,rgba(59,130,246,.9),rgba(79,70,229,.9))' }
                : undefined}>
              <Icon name={m.icon} className="w-[18px] h-[18px] shrink-0" />
              <span className="truncate">{m.name}</span>
            </NavLink>
          ))}
          {isAdmin && (
            <NavLink to="/admin" onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 mt-2 rounded-xl text-sm font-medium border-t hairline pt-3 ${
                  isActive ? 'text-blue-500' : 'muted hover:text-[var(--text)]'}`}>
              <Icon name="cog" className="w-[18px] h-[18px]" />
              <span>Dashboard Settings</span>
            </NavLink>
          )}
        </nav>
        <div className="p-4 border-t hairline text-xs muted">v1.0 · {modules.length} dashboards</div>
      </aside>

      {open && <div className="fixed inset-0 bg-black/50 z-20 lg:hidden" onClick={() => setOpen(false)} />}

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 sticky top-0 z-10 flex items-center gap-3 px-4 lg:px-6
          bg-[var(--surface)]/80 backdrop-blur border-b hairline">
          <button className="lg:hidden btn-ghost p-2" onClick={() => setOpen(true)}>
            <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 6h16M4 12h16M4 18h16" /></svg>
          </button>
          <div className="hidden md:flex items-center gap-2 flex-1 max-w-md">
            <div className="surface-2 flex items-center gap-2 px-3 py-2 w-full">
              <svg className="w-4 h-4 muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="7" /><path d="M21 21l-4-4" /></svg>
              <input placeholder="Search metrics, reports, insights…" className="bg-transparent outline-none text-sm w-full muted" />
            </div>
          </div>
          <div className="flex items-center gap-2 ml-auto">
            <ThemeBtn />
            <div className="hidden sm:flex flex-col items-end mr-1">
              <span className="text-sm font-semibold leading-tight">{user?.full_name}</span>
              <span className="text-[11px] muted capitalize">{user?.role?.name}</span>
            </div>
            <div className="w-9 h-9 rounded-full grid place-items-center text-white text-xs font-bold"
              style={{ background: 'linear-gradient(135deg,#3b82f6,#4f46e5)' }}>{initials}</div>
            <button onClick={logout} className="btn-ghost text-sm">Sign out</button>
          </div>
        </header>

        <main className="flex-1 p-4 lg:p-6 overflow-x-hidden">
          <FilterProvider>
            <Outlet context={{ modules }} />
          </FilterProvider>
        </main>
      </div>
    </div>
  )
}
