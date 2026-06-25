import { useEffect, useRef, useState } from 'react'
import { useTheme } from '../context/ThemeContext'
import { useBranding } from '../context/BrandingContext'

/** Print / PDF export + social sharing for the current dashboard.
 *  PDF = the browser's "Save as PDF" via the print dialog (clean A4 print CSS). */
export default function ExportShare({ title }) {
  const { dark, setDark } = useTheme()
  const { brand_name } = useBranding()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const onClick = (e) => { if (!ref.current?.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  // Charts render to <canvas> with theme-based colours, so force light mode for a
  // clean printout, then restore afterwards.
  const print = () => {
    const wasDark = dark
    const go = () => window.print()
    if (wasDark) {
      setDark(false)
      const restore = () => { setDark(true); window.removeEventListener('afterprint', restore) }
      window.addEventListener('afterprint', restore)
      setTimeout(go, 450)   // let ECharts re-render in light theme
    } else {
      setTimeout(go, 100)
    }
  }

  const url = window.location.href
  const text = `${brand_name} — ${title} report`
  const enc = encodeURIComponent
  const shares = [
    ['Email', `mailto:?subject=${enc(text)}&body=${enc(text + '\n' + url)}`,
      'M4 6h16v12H4z M4 6l8 6 8-6'],
    ['WhatsApp', `https://wa.me/?text=${enc(text + ' ' + url)}`,
      'M20 12a8 8 0 01-11.9 7L4 20l1.1-4A8 8 0 1120 12z'],
    ['LinkedIn', `https://www.linkedin.com/sharing/share-offsite/?url=${enc(url)}`,
      'M4 9h3v11H4z M5.5 4a1.5 1.5 0 100 3 1.5 1.5 0 000-3z M10 9h3v1.5c.5-1 1.7-1.8 3.2-1.8 2.3 0 3.8 1.5 3.8 4.3V20h-3v-5.5c0-1.3-.5-2.2-1.7-2.2-1 0-1.5.7-1.8 1.4V20h-3z'],
    ['X', `https://twitter.com/intent/tweet?text=${enc(text)}&url=${enc(url)}`,
      'M4 4l16 16 M20 4L4 20'],
    ['Facebook', `https://www.facebook.com/sharer/sharer.php?u=${enc(url)}`,
      'M14 8h3V4h-3c-2.2 0-4 1.8-4 4v2H7v4h3v6h4v-6h3l1-4h-4V8a1 1 0 011-1z'],
  ]

  return (
    <div ref={ref} className="relative no-print flex items-center gap-2">
      <button onClick={print} className="btn-ghost border hairline text-sm" title="Print or save as PDF (A4)">
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M6 9V3h12v6M6 18H4v-6h16v6h-2M8 14h8v7H8z" /></svg>
        Print / PDF
      </button>
      <button onClick={() => setOpen((o) => !o)} className="btn-ghost border hairline text-sm" title="Share">
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M4 12v7a1 1 0 001 1h14a1 1 0 001-1v-7M16 6l-4-4-4 4M12 2v14" /></svg>
        Share
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-2 w-44 surface p-1.5 z-50 shadow-xl">
          {shares.map(([label, href, d]) => (
            <a key={label} href={href} target="_blank" rel="noopener noreferrer"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm hover:bg-[var(--surface-2)] transition">
              <svg className="w-4 h-4 muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"><path d={d} /></svg>
              {label}
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
