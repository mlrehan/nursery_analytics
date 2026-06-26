import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'
import WidgetRenderer from '../components/WidgetRenderer'

const SPAN = { 3: 'md:col-span-3', 4: 'md:col-span-4', 6: 'md:col-span-6', 8: 'md:col-span-8', 12: 'md:col-span-12' }

export default function PublicDashboard() {
  const { token } = useParams()
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/public/report', { params: { token } })
      .then(({ data }) => setReport(data))
      .catch((e) => setError(e.response?.data?.detail || 'This share link is invalid or has expired.'))
      .finally(() => setLoading(false))
  }, [token])

  if (loading) return <div className="min-h-screen grid place-items-center muted">Loading shared report…</div>
  if (error) {
    return (
      <div className="min-h-screen grid place-items-center p-6 text-center">
        <div className="surface p-8 max-w-md">
          <div className="text-2xl font-bold font-display mb-2">Link unavailable</div>
          <p className="muted text-sm">{error}</p>
          <a href="/" className="btn-primary mt-5 inline-flex">Go to sign in</a>
        </div>
      </div>
    )
  }

  const r = report
  const initials = (r.brand_name || 'N').trim().charAt(0).toUpperCase()
  return (
    <div className="min-h-screen bg-[var(--page)]">
      {/* Public header */}
      <header className="sticky top-0 z-10 bg-[var(--surface)] border-b hairline">
        <div className="max-w-6xl mx-auto px-4 lg:px-6 h-16 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl grid place-items-center text-white font-extrabold font-display overflow-hidden brandmark shrink-0">
            {r.logo_url ? <img src={r.logo_url} alt="" className="w-full h-full object-contain" /> : initials}
          </div>
          <div className="min-w-0">
            <div className="font-bold font-display leading-tight truncate">{r.brand_name}</div>
            <div className="text-[11px] muted">Shared report · read-only</div>
          </div>
          <div className="ml-auto text-xs muted hidden sm:block">
            Updated {new Date(r.generated_at).toLocaleString('en-GB')}
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 lg:px-6 py-6">
        <div className="mb-5">
          <div className="eyebrow mb-0.5">Dashboard Report</div>
          <h1 className="text-[26px] leading-tight font-bold font-display tracking-tight">{r.module_name}</h1>
          <p className="muted text-sm mt-0.5">{r.scope_label}</p>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-12 items-stretch">
          {r.widgets.map((w) => (
            <div key={w.key} className={SPAN[w.span] || 'md:col-span-4'}>
              <WidgetRenderer widget={w} payload={r.data[w.key]} />
            </div>
          ))}
        </div>

        <div className="mt-8 py-6 border-t hairline text-center">
          <p className="text-sm muted">Powered by <span className="font-semibold">{r.brand_name}</span> — enterprise early-years analytics.</p>
          <a href="/" className="btn-ghost border hairline text-sm mt-3 inline-flex">Sign in to the full platform</a>
        </div>
      </main>
    </div>
  )
}
