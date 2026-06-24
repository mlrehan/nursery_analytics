import { useMemo } from 'react'
import EChart from './EChart'
import { buildOption, buildSparkline } from '../charts/echartsOptions'
import { useTheme } from '../context/ThemeContext'

function formatValue(value, unit) {
  if (typeof value === 'string') return value
  if (value === null || value === undefined) return '—'
  if (unit === '£') {
    const abs = Math.abs(value)
    if (abs >= 1_000_000) return `${value < 0 ? '-' : ''}£${(abs / 1_000_000).toFixed(1)}M`
    if (abs >= 1_000) return `${value < 0 ? '-' : ''}£${(abs / 1_000).toFixed(1)}K`
    return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 }).format(value)
  }
  if (unit === '%') return `${value}%`
  return new Intl.NumberFormat('en-GB').format(value)
}

function AccentIcon({ accent = 'blue', unit }) {
  const glyph = unit === '£'
    ? <path d="M18 7c0-2.2-2-4-4.5-4S9 4.8 9 7c0 4-2 5-2 5h11M7 12h7M6 19h12" />
    : unit === '%'
    ? <><circle cx="7" cy="7" r="2.2" /><circle cx="17" cy="17" r="2.2" /><path d="M6 18L18 6" /></>
    : <path d="M4 19V10m5 9V5m5 14v-7m5 7V8" />
  return (
    <span className={`accent-${accent} grid place-items-center w-9 h-9 rounded-xl shrink-0`}>
      <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">{glyph}</svg>
    </span>
  )
}

function Delta({ delta }) {
  if (delta === null || delta === undefined) return null
  const up = delta >= 0
  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-bold ${up ? 'text-emerald-500' : 'text-red-500'}`}>
      <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
        <path d={up ? 'M6 15l6-6 6 6' : 'M6 9l6 6 6-6'} />
      </svg>
      {Math.abs(delta)}%
    </span>
  )
}

function KpiCard({ widget, payload }) {
  const { dark } = useTheme()
  const spark = payload?.spark
  const sparkOpt = useMemo(
    () => (spark?.length ? buildSparkline(spark, payload.accent) : null),
    [spark, payload?.accent, dark],
  )
  return (
    <div className="surface p-5 flex flex-col justify-between h-full overflow-hidden">
      <div className="flex items-start gap-3">
        <AccentIcon accent={payload?.accent} unit={payload?.unit} />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium muted truncate">{payload?.label || widget.title}</p>
          <div className="mt-1 flex items-baseline gap-2 flex-wrap">
            <span className="text-2xl font-extrabold tracking-tight">{formatValue(payload?.value, payload?.unit)}</span>
            <Delta delta={payload?.delta} />
          </div>
          {payload?.sub && <p className="mt-0.5 text-xs muted truncate">{payload.sub}</p>}
        </div>
        {payload?.status && (
          <span className={`text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full
            ${payload.status === 'ok' ? 'text-emerald-500 bg-emerald-500/10' : 'text-amber-500 bg-amber-500/10'}`}>
            {payload.status === 'ok' ? 'OK' : 'Alert'}
          </span>
        )}
      </div>
      {sparkOpt && <div className="mt-3 -mb-1"><EChart option={sparkOpt} height={44} /></div>}
    </div>
  )
}

function ChartCard({ widget, children, action }) {
  return (
    <div className="surface p-5 h-full flex flex-col">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold">{widget.title}</h3>
          {widget.description && <p className="text-xs muted">{widget.description}</p>}
        </div>
        {action}
      </div>
      <div className="flex-1 min-h-0">{children}</div>
    </div>
  )
}

function TableCard({ widget, payload }) {
  const cols = payload?.columns || []
  const rows = payload?.rows || []
  return (
    <div className="surface p-5 h-full flex flex-col">
      <h3 className="text-sm font-semibold mb-3">{widget.title}</h3>
      <div className="overflow-auto -mx-1">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left muted border-b hairline">
              {cols.map((c) => <th key={c} className="font-medium py-2 px-2 whitespace-nowrap">{c}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={cols.length} className="py-6 text-center muted">No records</td></tr>}
            {rows.map((r, i) => (
              <tr key={i} className="border-b hairline last:border-0">
                {r.map((cell, j) => {
                  const sev = String(cell).toLowerCase()
                  const cls = ['high', 'investigating'].includes(sev) ? 'text-red-500 font-semibold'
                    : ['medium', 'monitoring', 'elevated'].includes(sev) ? 'text-amber-500 font-medium'
                    : ['active', 'resolved', 'low'].includes(sev) ? 'text-emerald-500' : ''
                  return <td key={j} className={`py-2 px-2 whitespace-nowrap ${cls}`}>{cell}</td>
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function WidgetRenderer({ widget, payload, onEvents }) {
  const { dark } = useTheme()
  const option = useMemo(() => buildOption(widget.viz_type, payload, dark), [widget.viz_type, payload, dark])

  if (!payload) return <div className="surface p-5 h-full grid place-items-center muted text-sm">No data</div>

  switch (widget.viz_type) {
    case 'kpi':
      return <KpiCard widget={widget} payload={payload} />
    case 'table':
      return <TableCard widget={widget} payload={payload} />
    case 'gauge':
      return <ChartCard widget={widget}><EChart option={option} height={210} /></ChartCard>
    default:
      return (
        <ChartCard widget={widget} action={onEvents ? <span className="chip text-[10px]">click to filter</span> : null}>
          <EChart option={option} height={300} onEvents={onEvents} />
        </ChartCard>
      )
  }
}
