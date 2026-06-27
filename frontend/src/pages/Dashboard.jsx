import { useEffect, useState, useCallback, useMemo } from 'react'
import { useOutletContext, useParams } from 'react-router-dom'
import { api } from '../api/client'
import WidgetRenderer from '../components/WidgetRenderer'
import FilterBar from '../components/FilterBar'
import ExportShare from '../components/ExportShare'
import DrillModal from '../components/DrillModal'
import { useFilters } from '../context/FilterContext'
import { useBranding } from '../context/BrandingContext'

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
  const { siteId, days, sites, setSiteId, canPickSite, siteName } = useFilters()
  const { brand_name } = useBranding()
  const module = modules.find((m) => m.key === moduleKey)
  const [payloads, setPayloads] = useState({})
  const [meta, setMeta] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [drill, setDrill] = useState(null)

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

  const periodLabel = { 7: 'Last 7 days', 30: 'Last 30 days', 90: 'Last 90 days', 365: 'Last 12 months' }[days] || `Last ${days} days`

  return (
    <div>
      {/* Print-only report header (A4) */}
      <div className="print-only" style={{ marginBottom: 14, borderBottom: '2px solid #0b1220', paddingBottom: 8 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{brand_name}</div>
          <div style={{ fontSize: 12 }}>{new Date().toLocaleString('en-GB')}</div>
        </div>
        <div style={{ fontSize: 15, marginTop: 2 }}>
          {module.name} — {siteName || 'All sites'}{PERIOD_AWARE.has(moduleKey) ? ` · ${periodLabel}` : ' · as of today'}
        </div>
      </div>

      <div className="flex items-start justify-between mb-4 gap-4 flex-wrap">
        <div>
          <div className="eyebrow mb-0.5">Dashboard</div>
          <h1 className="text-[26px] leading-tight font-bold font-display tracking-tight">{module.name}</h1>
          {module.description && <p className="muted text-sm mt-0.5">{module.description}</p>}
        </div>
        <div className="flex items-center gap-2 text-xs muted no-print">
          {meta?.cached && <span className="chip">cached</span>}
          {meta && <span className="hidden sm:inline">Updated {new Date(meta.generated_at).toLocaleTimeString()}</span>}
          <button onClick={load} className="btn-ghost border hairline !px-2.5" title="Refresh">↻</button>
          <ExportShare title={module.name} moduleKey={moduleKey} />
        </div>
      </div>

      <div className="surface px-4 py-3 mb-5 flex items-center gap-3 sticky -top-4 lg:-top-6 z-[5] no-print">
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
        <div className="print-grid grid grid-cols-1 gap-4 md:grid-cols-12 md:auto-rows-fr">
          {module.widgets.map((w) => (
            <div key={w.key} className={SPAN[w.span] || 'md:col-span-4'}>
              <WidgetRenderer widget={w} payload={payloads[w.key]} onEvents={makeEvents(w)} onDrill={setDrill} />
            </div>
          ))}
          {module.widgets.length === 0 && <div className="muted">No widgets enabled for your role.</div>}
        </div>
      )}

      <DrillModal data={drill} onClose={() => setDrill(null)} />
    </div>
  )
}
