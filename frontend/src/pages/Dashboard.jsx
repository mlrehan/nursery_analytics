import { useEffect, useState, useCallback, useMemo } from 'react'
import { useOutletContext, useParams } from 'react-router-dom'
import { api } from '../api/client'
import WidgetRenderer from '../components/WidgetRenderer'
import FilterBar from '../components/FilterBar'
import { useFilters } from '../context/FilterContext'

// Literal classes so Tailwind keeps them in the build.
const SPAN = { 3: 'md:col-span-3', 4: 'md:col-span-4', 6: 'md:col-span-6', 8: 'md:col-span-8', 12: 'md:col-span-12' }
// widgets whose x-axis categories are site names → clicking cross-filters by site
const SITE_CLICK_WIDGETS = new Set(['exec.site_breakdown', 'ms.occupancy', 'ms.revenue'])
// dashboards where the lookback period actually changes numbers (have activity-over-time
// reports). Others are live snapshots, so the period control is hidden there.
const PERIOD_AWARE = new Set(['attendance', 'eyfs', 'occupancy', 'staff', 'finance', 'parent_comms', 'nutrition', 'analytics'])

export default function Dashboard() {
  const { moduleKey } = useParams()
  const { modules } = useOutletContext()
  const { siteId, days, sites, setSiteId, canPickSite } = useFilters()
  const module = modules.find((m) => m.key === moduleKey)
  const [payloads, setPayloads] = useState({})
  const [meta, setMeta] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    if (!moduleKey) return
    setLoading(true); setError(null)
    try {
      const { data } = await api.get(`/dashboards/${moduleKey}/data`, { params: { site_id: siteId || undefined, days } })
      setPayloads(data.data || {})
      setMeta(data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load dashboard')
    } finally {
      setLoading(false)
    }
  }, [moduleKey, siteId, days])

  useEffect(() => { load() }, [load])

  const makeEvents = useMemo(() => (widget) => {
    if (!canPickSite || !SITE_CLICK_WIDGETS.has(widget.key)) return undefined
    return {
      click: (params) => {
        const match = sites.find((s) => s.name === params.name)
        if (match) setSiteId(match.id === siteId ? null : match.id)
      },
    }
  }, [canPickSite, sites, siteId, setSiteId])

  if (!module) return <div className="muted">Select a dashboard.</div>

  return (
    <div>
      <div className="flex items-start justify-between mb-4 gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">{module.name}</h1>
          {module.description && <p className="muted text-sm mt-0.5">{module.description}</p>}
        </div>
        <div className="flex items-center gap-2 text-xs muted">
          {meta?.cached && <span className="chip">cached</span>}
          {meta && <span>Updated {new Date(meta.generated_at).toLocaleTimeString()}</span>}
          <button onClick={load} className="btn-ghost border hairline !px-2.5" title="Refresh">↻</button>
        </div>
      </div>

      <div className="surface px-4 py-3 mb-5 flex items-center gap-3 sticky -top-4 lg:-top-6 z-[5]">
        <FilterBar showPeriod={PERIOD_AWARE.has(moduleKey)} />
      </div>

      {error && <div className="surface p-4 text-red-500 text-sm mb-4">{error}</div>}

      {loading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-12">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className={`${SPAN[i < 4 ? 3 : 6]} h-36 surface animate-pulse`} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-12 md:auto-rows-fr">
          {module.widgets.map((w) => (
            <div key={w.key} className={SPAN[w.span] || 'md:col-span-4'}>
              <WidgetRenderer widget={w} payload={payloads[w.key]} onEvents={makeEvents(w)} />
            </div>
          ))}
          {module.widgets.length === 0 && <div className="muted">No widgets enabled for your role.</div>}
        </div>
      )}
    </div>
  )
}
