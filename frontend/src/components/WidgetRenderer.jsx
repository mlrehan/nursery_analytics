import { useMemo } from 'react'
import EChart from './EChart'
import { buildOption } from '../charts/echartsOptions'
import { useTheme } from '../context/ThemeContext'

function formatValue(value, unit) {
  if (typeof value === 'string') return value
  if (value === null || value === undefined) return '—'
  if (unit === '£') {
    return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 }).format(value)
  }
  if (unit === '%') return `${value}%`
  return new Intl.NumberFormat('en-GB').format(value)
}

const statusRing = {
  ok: 'ring-emerald-500/20 text-emerald-600 dark:text-emerald-400',
  warn: 'ring-amber-500/20 text-amber-600 dark:text-amber-400',
}

function KpiCard({ widget, payload }) {
  const status = payload?.status
  return (
    <div className="surface p-5 flex flex-col justify-between h-full">
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium muted">{payload?.label || widget.title}</p>
        {status && (
          <span className={`text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full ring-1 ${statusRing[status] || ''}`}>
            {status === 'ok' ? 'OK' : 'Alert'}
          </span>
        )}
      </div>
      <div className="mt-3">
        <div className="text-3xl font-extrabold tracking-tight">{formatValue(payload?.value, payload?.unit)}</div>
        {payload?.sub && <p className="mt-1 text-xs muted">{payload.sub}</p>}
      </div>
    </div>
  )
}

function ChartCard({ widget, payload, children, height = 300 }) {
  return (
    <div className="surface p-5 h-full flex flex-col">
      <div className="mb-2">
        <h3 className="text-sm font-semibold">{widget.title}</h3>
        {widget.description && <p className="text-xs muted">{widget.description}</p>}
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
            <tr className="text-left muted border-b border-slate-200 dark:border-slate-800">
              {cols.map((c) => <th key={c} className="font-medium py-2 px-2 whitespace-nowrap">{c}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td colSpan={cols.length} className="py-6 text-center muted">No records</td></tr>
            )}
            {rows.map((r, i) => (
              <tr key={i} className="border-b border-slate-100 dark:border-slate-800/60 last:border-0">
                {r.map((cell, j) => {
                  const sev = String(cell).toLowerCase()
                  const cls = sev === 'high' ? 'text-red-600 dark:text-red-400 font-semibold'
                    : sev === 'medium' ? 'text-amber-600 dark:text-amber-400 font-medium'
                    : ''
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

export default function WidgetRenderer({ widget, payload }) {
  const { dark } = useTheme()
  const option = useMemo(
    () => buildOption(widget.viz_type, payload, dark),
    [widget.viz_type, payload, dark],
  )

  if (!payload) {
    return <div className="surface p-5 h-full grid place-items-center muted text-sm">No data</div>
  }

  switch (widget.viz_type) {
    case 'kpi':
      return <KpiCard widget={widget} payload={payload} />
    case 'table':
      return <TableCard widget={widget} payload={payload} />
    case 'gauge':
      return (
        <ChartCard widget={widget} payload={payload}>
          <EChart option={option} height={220} />
        </ChartCard>
      )
    default:
      return (
        <ChartCard widget={widget} payload={payload}>
          <EChart option={option} height={300} />
        </ChartCard>
      )
  }
}
