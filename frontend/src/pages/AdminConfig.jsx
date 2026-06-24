import { useEffect, useState } from 'react'
import { api } from '../api/client'
import Icon from '../components/Icon'

function Toggle({ on, onChange, disabled }) {
  return (
    <button type="button" disabled={disabled} onClick={() => onChange(!on)}
      className={`relative w-10 h-6 rounded-full transition disabled:opacity-40 ${on ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-700'}`}>
      <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${on ? 'translate-x-4' : ''}`} />
    </button>
  )
}

export default function AdminConfig() {
  const [roles, setRoles] = useState([])
  const [roleId, setRoleId] = useState(null)
  const [tab, setTab] = useState('permissions') // permissions | widgets
  const [perms, setPerms] = useState(null)
  const [config, setConfig] = useState(null)
  const [saving, setSaving] = useState(null)

  useEffect(() => {
    api.get('/admin/roles').then(({ data }) => {
      setRoles(data)
      const first = data.find((r) => r.slug !== 'admin') || data[0]
      if (first) setRoleId(first.id)
    })
  }, [])

  useEffect(() => {
    if (!roleId) return
    api.get(`/admin/roles/${roleId}/permissions`).then(({ data }) => setPerms(data))
    api.get('/admin/dashboard-config', { params: { role_id: roleId } }).then(({ data }) => setConfig(data))
  }, [roleId])

  const role = roles.find((r) => r.id === roleId)
  const isAdminRole = role?.slug === 'admin'

  const togglePerm = async (code, granted) => {
    setSaving(code)
    try {
      await api.post('/admin/roles/permissions', { role_id: roleId, code, granted })
      setPerms((p) => ({ ...p, permissions: p.permissions.map((x) => x.code === code ? { ...x, granted } : x) }))
    } finally { setSaving(null) }
  }

  const toggleWidget = async (widget) => {
    setSaving(widget.key)
    const next = !widget.is_enabled
    try {
      await api.post('/admin/dashboard-config/toggle', { role_id: roleId, widget_key: widget.key, is_enabled: next })
      setConfig((c) => ({ ...c, modules: c.modules.map((m) => ({ ...m,
        widgets: m.widgets.map((w) => w.key === widget.key ? { ...w, is_enabled: next } : w) })) }))
    } finally { setSaving(null) }
  }

  return (
    <div>
      <h1 className="text-2xl font-extrabold tracking-tight">Roles, Permissions & Dashboards</h1>
      <p className="muted text-sm mt-0.5 mb-5">
        <b>Permissions</b> decide which dashboards a role can open. <b>Widgets</b> decide which cards appear on those dashboards. Changes apply on the user's next refresh.
      </p>

      <div className="flex flex-wrap gap-2 mb-5">
        {roles.map((r) => (
          <button key={r.id} onClick={() => setRoleId(r.id)}
            className={`px-4 py-2 rounded-xl text-sm font-medium border transition ${
              roleId === r.id ? 'bg-blue-600 text-white border-blue-600' : 'surface hover:border-blue-400'}`}>
            {r.name}{r.slug === 'admin' && ' · full access'}
          </button>
        ))}
      </div>

      <div className="seg mb-5">
        <button data-active={tab === 'permissions'} onClick={() => setTab('permissions')}>Module access</button>
        <button data-active={tab === 'widgets'} onClick={() => setTab('widgets')}>Dashboard widgets</button>
      </div>

      {isAdminRole && (
        <div className="surface p-4 mb-4 text-sm muted">The Administrator role always has full access; toggles are disabled.</div>
      )}

      {tab === 'permissions' && perms && (
        <div className="surface p-5 grid sm:grid-cols-2 gap-x-8 gap-y-3">
          {perms.permissions.map((p) => (
            <div key={p.code} className="flex items-center justify-between gap-3 text-sm">
              <div className="min-w-0">
                <div className="font-medium truncate">{p.description || p.code}</div>
                <div className="muted text-xs font-mono">{p.code}</div>
              </div>
              <div className={saving === p.code ? 'opacity-50' : ''}>
                <Toggle on={p.granted} disabled={isAdminRole} onChange={(v) => togglePerm(p.code, v)} />
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'widgets' && config && (
        <div className="grid gap-4 lg:grid-cols-2">
          {config.modules.map((m) => (
            <div key={m.key} className="surface p-5">
              <div className="flex items-center gap-2 mb-3">
                <Icon name={m.icon} className="w-5 h-5 text-blue-500" />
                <h3 className="font-semibold">{m.name}</h3>
              </div>
              <div className="space-y-2">
                {m.widgets.map((w) => (
                  <div key={w.key} className="flex items-center justify-between text-sm">
                    <div className="min-w-0">
                      <div className="font-medium truncate">{w.title}</div>
                      <div className="muted text-xs">{w.viz_type}</div>
                    </div>
                    <div className={saving === w.key ? 'opacity-50' : ''}>
                      <Toggle on={w.is_enabled} disabled={isAdminRole} onChange={() => toggleWidget(w)} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
