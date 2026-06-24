import { useFilters } from '../context/FilterContext'

/** Global dashboard toolbar: site picker + period segmented control + active chips. */
export default function FilterBar() {
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

      <div className="seg" role="tablist">
        {periods.map((p) => (
          <button key={p.value} data-active={days === p.value} onClick={() => setDays(p.value)}>
            {p.label}
          </button>
        ))}
      </div>

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
