import { useEffect, useState, useCallback } from 'react'
import { useOutletContext, useParams } from 'react-router-dom'
import { api } from '../api/client'
import WidgetRenderer from '../components/WidgetRenderer'

// Literal classes so Tailwind keeps them in the build.
const SPAN = { 3: 'md:col-span-3', 4: 'md:col-span-4', 6: 'md:col-span-6', 8: 'md:col-span-8', 12: 'md:col-span-12' }

export default function Dashboard() {
  const { moduleKey } = useParams()
  const { modules } = useOutletContext()
  const module = modules.find((m) => m.key === moduleKey)
  const [payloads, setPayloads] = useState({})
  const [meta, setMeta] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    if (!moduleKey) return
    setLoading(true); setError(null)
    try {
      const { data } = await api.get(`/dashboards/${moduleKey}/data`)
      setPayloads(data.data || {})
      setMeta(data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load dashboard')
    } finally {
      setLoading(false)
    }
  }, [moduleKey])

  useEffect(() => { load() }, [load])

  if (!module) return <div className="muted">Select a dashboard.</div>

  return (
    <div>
      <div className="flex items-end justify-between mb-5 gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">{module.name}</h1>
          {module.description && <p className="muted text-sm mt-0.5">{module.description}</p>}
        </div>
        <div className="flex items-center gap-3">
          {meta && <span className="text-xs muted">Updated {new Date(meta.generated_at).toLocaleTimeString()}</span>}
          <button onClick={load} className="btn-ghost text-sm border border-slate-200 dark:border-slate-800">Refresh</button>
        </div>
      </div>

      {error && <div className="surface p-4 text-red-600 dark:text-red-400 text-sm">{error}</div>}

      {loading ? (
        <div className="grid gap-4 md:grid-cols-12">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className={`${SPAN[i % 2 ? 8 : 4]} h-40 surface animate-pulse`} />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-12 md:auto-rows-fr">
          {module.widgets.map((w) => (
            <div key={w.key} className={SPAN[w.span] || 'md:col-span-4'}>
              <WidgetRenderer widget={w} payload={payloads[w.key]} />
            </div>
          ))}
          {module.widgets.length === 0 && <div className="muted">No widgets enabled for your role.</div>}
        </div>
      )}
    </div>
  )
}
