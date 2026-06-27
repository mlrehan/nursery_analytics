import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { useBranding } from '../context/BrandingContext'

const toDataURL = (file) => new Promise((res, rej) => {
  const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(file)
})

export default function AdminSettings() {
  const branding = useBranding()
  const logoRef = useRef(null)
  const iconRef = useRef(null)
  const [form, setForm] = useState(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)

  useEffect(() => {
    api.get('/settings/branding').then(({ data }) => setForm({
      brand_name: data.brand_name || '', brand_tagline: data.brand_tagline || '',
      logo_url: data.logo_url || '', icon_url: data.icon_url || '',
      demo_mode: data.demo_mode !== false,
    }))
  }, [])

  if (!form) return <div className="muted">Loading…</div>
  const letter = (form.brand_name || 'N').trim().charAt(0).toUpperCase()

  async function pick(e, key, maxKB = 400) {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > maxKB * 1024) { setMsg({ type: 'err', text: `Image too large (max ${maxKB}KB).` }); return }
    const dataUrl = await toDataURL(file)
    setForm((f) => ({ ...f, [key]: dataUrl }))
    setMsg(null)
  }

  const save = async (e) => {
    e.preventDefault(); setSaving(true); setMsg(null)
    try {
      const { data } = await api.put('/settings/branding', form)
      branding.setBranding({ brand_name: data.brand_name, brand_tagline: data.brand_tagline, logo_url: data.logo_url, icon_url: data.icon_url, demo_mode: data.demo_mode })
      setMsg({ type: 'ok', text: 'Branding saved — it applies everywhere instantly.' })
    } catch (err) {
      setMsg({ type: 'err', text: err.response?.data?.detail || 'Failed to save' })
    } finally { setSaving(false) }
  }

  return (
    <div className="max-w-3xl">
      <div className="eyebrow mb-0.5">Administration</div>
      <h1 className="text-[26px] font-bold font-display tracking-tight mb-1">Branding &amp; Settings</h1>
      <p className="muted text-sm mb-5">White-label the platform — your product name, logo and browser icon.</p>

      <form onSubmit={save} className="surface p-6 space-y-7">
        {/* Live preview */}
        <div className="surface-2 p-4 flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl grid place-items-center text-white font-extrabold font-display overflow-hidden brandmark">
            {form.logo_url ? <img src={form.logo_url} alt="" className="w-full h-full object-contain" /> : letter}
          </div>
          <div>
            <div className="font-bold font-display leading-tight">{form.brand_name || 'Your product name'}</div>
            {form.brand_tagline && <div className="text-[11px] muted uppercase tracking-[0.12em]">{form.brand_tagline}</div>}
          </div>
          <span className="chip ml-auto">Live preview</span>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <label className="block sm:col-span-2">
            <span className="text-sm font-medium">Product name</span>
            <input className="input mt-1" value={form.brand_name} onChange={(e) => setForm({ ...form, brand_name: e.target.value })} required />
            <span className="text-xs muted">Shown in the sidebar, sign-in screen and browser tab.</span>
          </label>
          <label className="block sm:col-span-2">
            <span className="text-sm font-medium">Tagline <span className="muted">(optional)</span></span>
            <input className="input mt-1" value={form.brand_tagline} onChange={(e) => setForm({ ...form, brand_tagline: e.target.value })} placeholder="e.g. Early Years Intelligence" />
          </label>
        </div>

        {/* Logo */}
        <div className="flex items-start gap-4">
          <div className="w-16 h-16 rounded-xl grid place-items-center text-white text-2xl font-extrabold font-display overflow-hidden brandmark shrink-0">
            {form.logo_url ? <img src={form.logo_url} alt="" className="w-full h-full object-contain" /> : letter}
          </div>
          <div>
            <div className="text-sm font-medium">Logo</div>
            <p className="text-xs muted mb-2">PNG, SVG or JPG. Leave empty to use the first letter (“{letter}”) of the name.</p>
            <input ref={logoRef} type="file" accept="image/png,image/svg+xml,image/jpeg,image/webp" hidden onChange={(e) => pick(e, 'logo_url')} />
            <button type="button" className="btn-ghost border hairline text-sm" onClick={() => logoRef.current?.click()}>Upload logo</button>
            {form.logo_url && <button type="button" className="btn-ghost text-sm" onClick={() => setForm({ ...form, logo_url: '' })}>Reset to letter</button>}
          </div>
        </div>

        {/* Favicon / site icon */}
        <div className="flex items-start gap-4">
          <div className="w-16 h-16 surface-2 grid place-items-center overflow-hidden shrink-0">
            {form.icon_url ? <img src={form.icon_url} alt="" className="w-8 h-8 object-contain" /> : <span className="muted text-xs">none</span>}
          </div>
          <div>
            <div className="text-sm font-medium">Site icon (browser tab)</div>
            <p className="text-xs muted mb-2">Small square image — ideally a .png or .svg, 32–64px.</p>
            <input ref={iconRef} type="file" accept="image/png,image/svg+xml,image/x-icon,image/jpeg" hidden onChange={(e) => pick(e, 'icon_url', 200)} />
            <button type="button" className="btn-ghost border hairline text-sm" onClick={() => iconRef.current?.click()}>Upload icon</button>
            {form.icon_url && <button type="button" className="btn-ghost text-sm" onClick={() => setForm({ ...form, icon_url: '' })}>Remove</button>}
          </div>
        </div>

        {/* Demo-data banner toggle */}
        <div className="surface-2 p-4 flex items-center justify-between gap-4">
          <div className="min-w-0">
            <div className="text-sm font-medium">Show “fictional data” banner</div>
            <p className="text-xs muted">Displays a demo notice across the app and shared links. Turn off once real nursery data is loaded.</p>
          </div>
          <button type="button" onClick={() => setForm({ ...form, demo_mode: !form.demo_mode })}
            className={`relative w-11 h-6 rounded-full transition shrink-0 ${form.demo_mode ? 'bg-amber-500' : 'bg-slate-300 dark:bg-slate-700'}`}>
            <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${form.demo_mode ? 'translate-x-5' : ''}`} />
          </button>
        </div>

        <div className="flex items-center gap-3 border-t hairline pt-5">
          <button className="btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Save branding'}</button>
          {msg && <span className={`text-sm ${msg.type === 'ok' ? 'text-emerald-500' : 'text-red-500'}`}>{msg.text}</span>}
        </div>
      </form>
    </div>
  )
}
