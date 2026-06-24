import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

// Downscale an uploaded image to a small square data-URL (kept in the DB).
function fileToAvatar(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const img = new Image()
      img.onload = () => {
        const size = 256
        const canvas = document.createElement('canvas')
        canvas.width = size; canvas.height = size
        const ctx = canvas.getContext('2d')
        const scale = Math.max(size / img.width, size / img.height)
        const w = img.width * scale, h = img.height * scale
        ctx.drawImage(img, (size - w) / 2, (size - h) / 2, w, h)
        resolve(canvas.toDataURL('image/jpeg', 0.85))
      }
      img.onerror = reject
      img.src = e.target.result
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

export default function Profile() {
  const { user, setUser } = useAuth()
  const fileRef = useRef(null)
  const [form, setForm] = useState(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)

  useEffect(() => {
    if (user) setForm({
      full_name: user.full_name || '', email: user.email || '', phone: user.phone || '',
      job_title: user.job_title || '', address: user.address || '', about: user.about || '',
      avatar_url: user.avatar_url || '',
    })
  }, [user])

  if (!form) return <div className="muted">Loading…</div>
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const pickImage = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const avatar = await fileToAvatar(file)
    setForm((f) => ({ ...f, avatar_url: avatar }))
  }

  const save = async (e) => {
    e.preventDefault()
    setSaving(true); setMsg(null)
    try {
      const { data } = await api.put('/auth/me/profile', form)
      setUser(data)
      setMsg({ type: 'ok', text: 'Profile saved' })
    } catch (err) {
      setMsg({ type: 'err', text: err.response?.data?.detail || 'Failed to save' })
    } finally {
      setSaving(false)
    }
  }

  const initials = (form.full_name || 'U').split(' ').map((w) => w[0]).slice(0, 2).join('')

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-extrabold tracking-tight mb-1">My Profile</h1>
      <p className="muted text-sm mb-5">Manage your contact details and how colleagues see you.</p>

      <form onSubmit={save} className="surface p-6 space-y-6">
        <div className="flex items-center gap-5">
          <div className="w-20 h-20 rounded-2xl overflow-hidden grid place-items-center text-white text-2xl font-bold shrink-0"
            style={{ background: 'linear-gradient(135deg,#3b82f6,#4f46e5)' }}>
            {form.avatar_url ? <img src={form.avatar_url} alt="avatar" className="w-full h-full object-cover" /> : initials}
          </div>
          <div>
            <input ref={fileRef} type="file" accept="image/*" hidden onChange={pickImage} />
            <button type="button" className="btn-ghost border hairline" onClick={() => fileRef.current?.click()}>Upload photo</button>
            {form.avatar_url && (
              <button type="button" className="btn-ghost text-sm" onClick={() => setForm((f) => ({ ...f, avatar_url: '' }))}>Remove</button>
            )}
            <p className="text-xs muted mt-1">Square image, stored at 256×256.</p>
          </div>
          <div className="ml-auto text-right">
            <div className="chip">{user.role?.name}</div>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Full name"><input className="input" value={form.full_name} onChange={set('full_name')} required /></Field>
          <Field label="Email"><input className="input" type="email" value={form.email} onChange={set('email')} required /></Field>
          <Field label="Phone"><input className="input" value={form.phone} onChange={set('phone')} placeholder="07700 900123" /></Field>
          <Field label="Job title"><input className="input" value={form.job_title} onChange={set('job_title')} placeholder="e.g. Room Leader" /></Field>
          <Field label="Address" full><textarea className="input" rows={2} value={form.address} onChange={set('address')} /></Field>
          <Field label="About me" full><textarea className="input" rows={3} value={form.about} onChange={set('about')} placeholder="A short bio your colleagues will see" /></Field>
        </div>

        <div className="flex items-center gap-3">
          <button className="btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>
          {msg && <span className={`text-sm ${msg.type === 'ok' ? 'text-emerald-500' : 'text-red-500'}`}>{msg.text}</span>}
        </div>
      </form>
    </div>
  )
}

function Field({ label, children, full }) {
  return (
    <label className={`block ${full ? 'sm:col-span-2' : ''}`}>
      <span className="text-sm font-medium">{label}</span>
      <div className="mt-1">{children}</div>
    </label>
  )
}
