import { useFilters } from '../context/FilterContext'

/** Global dashboard toolbar: site picker + period segmented control + active chips.
 *  `showPeriod` is false on snapshot dashboards (Executive etc.) where a lookback
 *  period has no effect — we show an "as of today" note instead of a dead control. */
export default function FilterBar({ showPeriod = true }) {
  const { sites, canPickSite, periods, siteId, days, setSiteId, setDays, siteName } = useFilters()

  return (
    <div className="flex flex-wrap items-center gap-3">
      {canPickSite && sites.length > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-xs muted hidden sm:inline">Site</span>
          <select
            value={siteId ?? ''}
            onChange={(e) => setSiteId(e.target.value ? Number(e.target.value) : null)}
            className="input !py-1.5 !w-auto pr-8 text-sm font-medium cursor-pointer"
          >
            <option value="">All sites</option>
            {sites.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
      )}

      {showPeriod ? (
        <div className="seg" role="tablist" title="Applies to activity-over-time reports">
          {periods.map((p) => (
            <button key={p.value} data-active={days === p.value} onClick={() => setDays(p.value)}>
              {p.label}
            </button>
          ))}
        </div>
      ) : (
        <span className="chip" title="This dashboard is a live snapshot; a lookback period doesn't apply">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> Live snapshot · as of today
        </span>
      )}

      {siteId && (
        <button onClick={() => setSiteId(null)} className="chip hover:opacity-80" title="Clear site filter">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
          {siteName}
          <span className="ml-0.5 text-base leading-none">×</span>
        </button>
      )}
    </div>
  )
}
