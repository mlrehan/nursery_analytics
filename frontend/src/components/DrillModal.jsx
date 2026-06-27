import { useEffect } from 'react'

const SEV = {
  high: 'text-red-500 font-semibold', medium: 'text-amber-500 font-medium',
  low: 'text-emerald-500', overdue: 'text-red-500 font-medium',
}

/** Click-through detail dialog for a KPI: shows {title, columns, rows}. */
export default function DrillModal({ data, onClose }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  if (!data) return null
  const { title, columns = [], rows = [] } = data

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center p-4 sm:p-8 bg-black/50 backdrop-blur-sm overflow-auto"
      onMouseDown={onClose}>
      <div className="surface w-full max-w-3xl my-6" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4 border-b hairline">
          <div>
            <div className="eyebrow">Details</div>
            <h3 className="text-lg font-bold font-display">{title}</h3>
          </div>
          <button onClick={onClose} className="btn-ghost p-2" aria-label="Close">
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M6 6l12 12M18 6L6 18" /></svg>
          </button>
        </div>
        <div className="p-3 max-h-[70vh] overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-[var(--surface)]">
              <tr className="text-left muted border-b hairline">
                {columns.map((c) => <th key={c} className="font-medium py-2 px-3 whitespace-nowrap">{c}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && <tr><td colSpan={columns.length} className="py-8 text-center muted">Nothing to show — all clear.</td></tr>}
              {rows.map((r, i) => (
                <tr key={i} className="border-b hairline last:border-0">
                  {r.map((cell, j) => {
                    const cls = SEV[String(cell).toLowerCase()] || ''
                    return <td key={j} className={`py-2 px-3 whitespace-nowrap ${cls}`}>{cell}</td>
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="px-5 py-3 border-t hairline text-right">
          <span className="text-xs muted mr-auto">{rows.length} record{rows.length === 1 ? '' : 's'}</span>
        </div>
      </div>
    </div>
  )
}
