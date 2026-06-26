import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { useFilters } from '../context/FilterContext'
import { useBranding } from '../context/BrandingContext'

/** Enterprise export: branded PDF download + public, no-login share link. */
export default function ExportShare({ title, moduleKey }) {
  const { siteId, days } = useFilters()
  const { brand_name } = useBranding()
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)
  const [shareUrl, setShareUrl] = useState(null)
  const [minting, setMinting] = useState(false)
  const ref = useRef(null)

  // a fresh public link is needed whenever the dashboard/filters change
  useEffect(() => { setShareUrl(null) }, [moduleKey, siteId, days])

  useEffect(() => {
    const onClick = (e) => { if (!ref.current?.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  const mintLink = async () => {
    if (shareUrl || minting) return shareUrl
    setMinting(true)
    try {
      const { data } = await api.post(`/dashboards/${moduleKey}/share-link`, null,
        { params: { site_id: siteId || undefined, days } })
      setShareUrl(data.url)
      return data.url
    } catch { return null } finally { setMinting(false) }
  }

  const openMenu = () => { setOpen((o) => !o); if (!open) mintLink() }

  const downloadPdf = async () => {
    setBusy(true)
    try {
      const res = await api.get(`/dashboards/${moduleKey}/report.pdf`, {
        params: { site_id: siteId || undefined, days }, responseType: 'blob',
      })
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `${brand_name}-${title}-${new Date().toISOString().slice(0, 10)}.pdf`.replace(/\s+/g, '_')
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url)
    } catch { alert('Could not generate the PDF. Please try again.') } finally { setBusy(false) }
  }

  const copyLink = async () => {
    const url = shareUrl || (await mintLink())
    if (!url) return
    try { await navigator.clipboard.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 1500) } catch { /* */ }
  }

  const msg = `${brand_name} — ${title}`
  const e = encodeURIComponent
  const linkFor = (kind) => {
    const u = shareUrl || ''
    switch (kind) {
      case 'Email': return `mailto:?subject=${e(msg)}&body=${e(msg + '\n\nView the report (no login needed):\n' + u)}`
      case 'WhatsApp': return `https://wa.me/?text=${e(msg + ' — ' + u)}`
      case 'LinkedIn': return `https://www.linkedin.com/sharing/share-offsite/?url=${e(u)}`
      case 'X': return `https://twitter.com/intent/tweet?text=${e(msg)}&url=${e(u)}`
      case 'Facebook': return `https://www.facebook.com/sharer/sharer.php?u=${e(u)}`
      default: return u
    }
  }

  return (
    <div ref={ref} className="relative no-print flex items-center gap-2">
      <button onClick={downloadPdf} disabled={busy} className="btn-primary text-sm !py-1.5" title="Download a branded PDF report">
        {busy ? (
          <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12a9 9 0 11-6.2-8.5" /></svg>
        ) : (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 3v12m0 0l-4-4m4 4l4-4M5 21h14" /></svg>
        )}
        {busy ? 'Generating…' : 'Export PDF'}
      </button>
      <button onClick={openMenu} className="btn-ghost border hairline text-sm !py-1.5" title="Share a public link">
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M4 12v7a1 1 0 001 1h14a1 1 0 001-1v-7M16 6l-4-4-4 4M12 2v14" /></svg>
        Share
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-60 surface p-1.5 z-50 shadow-xl">
          <div className="px-2.5 pt-1.5 pb-1 eyebrow">Public link · no login needed</div>
          {minting && <div className="px-2.5 py-2 text-sm muted">Preparing link…</div>}
          {!minting && (
            <>
              <button onClick={copyLink} className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm hover:bg-[var(--surface-2)] transition">
                <svg className="w-4 h-4 muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M10 14a5 5 0 007 0l3-3a5 5 0 00-7-7l-1 1M14 10a5 5 0 00-7 0l-3 3a5 5 0 007 7l1-1" /></svg>
                {copied ? 'Link copied!' : 'Copy link'}
              </button>
              <button onClick={() => { downloadPdf(); setOpen(false) }} className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm hover:bg-[var(--surface-2)] transition">
                <svg className="w-4 h-4 muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M12 3v12m0 0l-4-4m4 4l4-4M5 21h14" /></svg>
                Download PDF
              </button>
              <div className="my-1 border-t hairline" />
              {['Email', 'WhatsApp', 'LinkedIn', 'X', 'Facebook'].map((label) => (
                <a key={label} href={shareUrl ? linkFor(label) : undefined} target="_blank" rel="noopener noreferrer"
                  onClick={(ev) => { if (!shareUrl) ev.preventDefault(); else setOpen(false) }}
                  className={`flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition ${shareUrl ? 'hover:bg-[var(--surface-2)]' : 'opacity-40 cursor-default'}`}>
                  <span className="w-1.5 h-1.5 rounded-full bg-[color:var(--brand-1)]" />{label}
                </a>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  )
}
