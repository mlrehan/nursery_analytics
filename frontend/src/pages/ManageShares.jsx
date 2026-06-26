import { useEffect, useState } from 'react'
import { api } from '../api/client'

const STATUS = {
  active: 'text-emerald-500 bg-emerald-500/10',
  expired: 'text-amber-500 bg-amber-500/10',
  revoked: 'text-red-500 bg-red-500/10',
}

export default function ManageShares() {
  const [links, setLinks] = useState(null)
  const [copied, setCopied] = useState(null)

  const load = () => api.get('/share-links').then(({ data }) => setLinks(data))
  useEffect(() => { load() }, [])

  const revoke = async (token) => {
    if (!window.confirm('Revoke this link? Anyone with it will immediately lose access.')) return
    await api.post(`/share-links/${token}/revoke`); load()
  }
  const remove = async (token) => {
    if (!window.confirm('Delete this link permanently?')) return
    await api.delete(`/share-links/${token}`); load()
  }
  const copy = async (url, token) => {
    try { await navigator.clipboard.writeText(url); setCopied(token); setTimeout(() => setCopied(null), 1500) } catch { /* */ }
  }
  const fmt = (d) => d ? new Date(d).toLocaleDateString('en-GB') : '—'

  return (
    <div>
      <div className="eyebrow mb-0.5">Sharing</div>
      <h1 className="text-[26px] font-bold font-display tracking-tight mb-1">Shared Links</h1>
      <p className="muted text-sm mb-5">Public, no-login links you've created. Revoke any of them at any time.</p>

      {!links && <div className="muted">Loading…</div>}
      {links && links.length === 0 && (
        <div className="surface p-8 text-center muted">
          You haven't shared any dashboards yet. Open a dashboard and use <b>Share</b> to create a public link.
        </div>
      )}

      {links && links.length > 0 && (
        <div className="surface p-2 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left muted border-b hairline">
                <th className="py-2 px-3 font-medium">Dashboard</th>
                <th className="py-2 px-3 font-medium">Created</th>
                <th className="py-2 px-3 font-medium">Expires</th>
                <th className="py-2 px-3 font-medium">Status</th>
                <th className="py-2 px-3 font-medium text-right">Views</th>
                <th className="py-2 px-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {links.map((l) => (
                <tr key={l.token} className="border-b hairline last:border-0">
                  <td className="py-2.5 px-3 font-medium">{l.label}</td>
                  <td className="py-2.5 px-3 muted">{fmt(l.created_at)}</td>
                  <td className="py-2.5 px-3 muted">{l.expires_at ? fmt(l.expires_at) : 'Never'}</td>
                  <td className="py-2.5 px-3">
                    <span className={`text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full ${STATUS[l.status]}`}>{l.status}</span>
                  </td>
                  <td className="py-2.5 px-3 text-right nums">{l.view_count}</td>
                  <td className="py-2.5 px-3 text-right whitespace-nowrap">
                    <button className="btn-ghost text-xs" onClick={() => copy(l.url, l.token)}>{copied === l.token ? 'Copied!' : 'Copy'}</button>
                    <a className="btn-ghost text-xs" href={l.url} target="_blank" rel="noopener noreferrer">Open</a>
                    {l.status !== 'revoked' && <button className="btn-ghost text-xs text-amber-500" onClick={() => revoke(l.token)}>Revoke</button>}
                    <button className="btn-ghost text-xs text-red-500" onClick={() => remove(l.token)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
