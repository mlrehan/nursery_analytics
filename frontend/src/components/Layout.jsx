import { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import Icon from './Icon'

function SunMoon({ dark }) {
  return dark
    ? <Icon name="sparkles" className="w-5 h-5" />
    : <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z" /></svg>
}

export default function Layout() {
  const { user, logout, isAdmin } = useAuth()
  const { dark, toggle } = useTheme()
  const navigate = useNavigate()
  const [modules, setModules] = useState([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    api.get('/dashboards/me').then(({ data }) => {
      setModules(data.modules)
      setLoading(false)
      if (data.modules.length) navigate(`/m/${data.modules[0].key}`, { replace: true })
    }).catch(() => setLoading(false))
  }, []) // eslint-disable-line

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className={`fixed lg:static z-30 h-screen w-72 shrink-0 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col transition-transform ${open ? '' : '-translate-x-full lg:translate-x-0'}`}>
        <div className="h-16 flex items-center gap-2 px-5 border-b border-slate-200 dark:border-slate-800">
          <div className="w-8 h-8 rounded-lg bg-brand-600 grid place-items-center text-white font-extrabold">N</div>
          <div>
            <div className="font-bold leading-tight">Nursery Analytics</div>
            <div className="text-[11px] muted">LAIT · London</div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto p-3 space-y-1">
          {loading && <div className="px-3 py-2 text-sm muted">Loading…</div>}
          {modules.map((m) => (
            <NavLink key={m.key} to={`/m/${m.key}`} onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition ${
                  isActive ? 'bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-300'
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'}`}>
              <Icon name={m.icon} className="w-5 h-5 shrink-0" />
              <span className="truncate">{m.name}</span>
            </NavLink>
          ))}
          {isAdmin && (
            <NavLink to="/admin" onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 mt-2 rounded-xl text-sm font-medium border-t border-slate-200 dark:border-slate-800 pt-3 ${
                  isActive ? 'text-brand-700 dark:text-brand-300' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'}`}>
              <Icon name="cog" className="w-5 h-5" />
              <span>Dashboard Settings</span>
            </NavLink>
          )}
        </nav>
        <div className="p-4 border-t border-slate-200 dark:border-slate-800 text-xs muted">
          v1.0 · {modules.length} dashboards
        </div>
      </aside>

      {open && <div className="fixed inset-0 bg-black/40 z-20 lg:hidden" onClick={() => setOpen(false)} />}

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 sticky top-0 z-10 flex items-center justify-between px-4 lg:px-6 bg-white/80 dark:bg-slate-900/80 backdrop-blur border-b border-slate-200 dark:border-slate-800">
          <button className="lg:hidden btn-ghost p-2" onClick={() => setOpen(true)}>
            <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 6h16M4 12h16M4 18h16"/></svg>
          </button>
          <div className="hidden sm:block">
            <span className="text-xs uppercase tracking-wider muted">Signed in as</span>
            <span className="ml-2 font-semibold capitalize">{user?.role?.name}</span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={toggle} className="btn-ghost p-2" title="Toggle theme"><SunMoon dark={dark} /></button>
            <div className="hidden sm:flex flex-col items-end mr-1">
              <span className="text-sm font-semibold">{user?.full_name}</span>
              <span className="text-[11px] muted">{user?.email}</span>
            </div>
            <button onClick={logout} className="btn-ghost text-sm">Sign out</button>
          </div>
        </header>
        <main className="flex-1 p-4 lg:p-6 overflow-x-hidden">
          <Outlet context={{ modules }} />
        </main>
      </div>
    </div>
  )
}
