import { useEffect, useState } from 'react'
import { api } from '../api/client'
import Icon from '../components/Icon'

function Toggle({ on, onChange }) {
  return (
    <button onClick={() => onChange(!on)}
      className={`relative w-10 h-6 rounded-full transition ${on ? 'bg-brand-600' : 'bg-slate-300 dark:bg-slate-700'}`}>
      <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${on ? 'translate-x-4' : ''}`} />
    </button>
  )
}

export default function AdminConfig() {
  const [roles, setRoles] = useState([])
  const [roleId, setRoleId] = useState(null)
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
    if (roleId) api.get('/admin/dashboard-config', { params: { role_id: roleId } }).then(({ data }) => setConfig(data))
  }, [roleId])

  const toggle = async (widget) => {
    setSaving(widget.key)
    const next = !widget.is_enabled
    try {
      await api.post('/admin/dashboard-config/toggle', { role_id: roleId, widget_key: widget.key, is_enabled: next })
      setConfig((c) => ({
        ...c,
        modules: c.modules.map((m) => ({
          ...m,
          widgets: m.widgets.map((w) => (w.key === widget.key ? { ...w, is_enabled: next } : w)),
        })),
      }))
    } finally {
      setSaving(null)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-extrabold tracking-tight">Dashboard Settings</h1>
      <p className="muted text-sm mt-0.5 mb-5">Control which widgets each role sees. Changes apply on their next refresh.</p>

      <div className="flex flex-wrap gap-2 mb-6">
        {roles.map((r) => (
          <button key={r.id} onClick={() => setRoleId(r.id)}
            className={`px-4 py-2 rounded-xl text-sm font-medium border transition ${
              roleId === r.id ? 'bg-brand-600 text-white border-brand-600'
                : 'surface hover:border-brand-400'}`}>
            {r.name}{r.slug === 'admin' && ' (full access)'}
          </button>
        ))}
      </div>

      {config && (
        <div className="grid gap-4 lg:grid-cols-2">
          {config.modules.map((m) => (
            <div key={m.key} className="surface p-5">
              <div className="flex items-center gap-2 mb-3">
                <Icon name={m.icon} className="w-5 h-5 text-brand-600" />
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
                      <Toggle on={w.is_enabled} onChange={() => toggle(w)} />
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
