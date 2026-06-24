import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useFilters } from '../context/FilterContext'

export default function SearchBox() {
  const navigate = useNavigate()
  const { setSiteId } = useFilters()
  const [q, setQ] = useState('')
  const [res, setRes] = useState(null)
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(false)
  const boxRef = useRef(null)

  // debounced fetch
  useEffect(() => {
    if (!q.trim()) { setRes(null); return }
    const t = setTimeout(() => {
      api.get('/search', { params: { q } }).then(({ data }) => { setRes(data); setOpen(true) }).catch(() => {})
    }, 220)
    return () => clearTimeout(t)
  }, [q])

  useEffect(() => {
    const onClick = (e) => { if (!boxRef.current?.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  const go = (fn) => { fn(); setOpen(false); setQ(''); setRes(null) }
  const groups = res ? [
    ['Dashboards', res.modules.map((m) => ({ label: m.name, sub: 'Dashboard', act: () => navigate(`/m/${m.key}`) }))],
    ['Sites', res.sites.map((s) => ({ label: s.name, sub: s.borough, act: () => { setSiteId(s.id); navigate('/m/executive') } }))],
    ['Children', res.children.map((c) => ({ label: c.name, sub: `${c.room || '—'} · ${c.status}`, act: () => navigate('/m/occupancy') }))],
    ['Staff', res.staff.map((s) => ({ label: s.name, sub: s.role, act: () => navigate('/m/staff') }))],
  ].filter(([, items]) => items.length) : []

  return (
    <div ref={boxRef} className="relative w-full max-w-md">
      <div className={`surface-2 flex items-center gap-2 px-3 py-2 transition ${active ? 'ring-2 ring-blue-500' : ''}`}>
        <svg className="w-4 h-4 muted shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="7" /><path d="M21 21l-4-4" /></svg>
        <input
          value={q} onChange={(e) => setQ(e.target.value)}
          onFocus={() => { setActive(true); if (res) setOpen(true) }} onBlur={() => setActive(false)}
          placeholder="Search dashboards, sites, children, staff…"
          className="bg-transparent outline-none text-sm w-full"
        />
        {q && <button onClick={() => { setQ(''); setRes(null) }} className="muted text-lg leading-none">×</button>}
      </div>

      {open && res && (
        <div className="absolute mt-2 w-full surface p-2 z-50 max-h-[70vh] overflow-auto shadow-xl">
          {res.total === 0 && <div className="p-3 text-sm muted">No results for “{res.query}”.</div>}
          {groups.map(([title, items]) => (
            <div key={title} className="mb-1">
              <div className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wide muted">{title}</div>
              {items.map((it, i) => (
                <button key={i} onClick={() => go(it.act)}
                  className="w-full text-left px-2 py-2 rounded-lg hover:bg-[var(--surface-2)] flex items-center justify-between gap-2">
                  <span className="text-sm font-medium truncate">{it.label}</span>
                  <span className="text-xs muted shrink-0">{it.sub}</span>
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
