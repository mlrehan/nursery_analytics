import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const DEMO = [
  ['Administrator', 'admin@lait.org.uk', 'Admin123!'],
  ['Management', 'management@lait.org.uk', 'Manager123!'],
  ['Accounts', 'accounts@lait.org.uk', 'Accounts123!'],
  ['Teacher', 'teacher@lait.org.uk', 'Teacher123!'],
  ['Parent', 'parent@lait.org.uk', 'Parent123!'],
]

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('admin@lait.org.uk')
  const [password, setPassword] = useState('Admin123!')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setError(null)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Brand panel */}
      <div className="hidden lg:flex flex-col justify-between p-12 bg-gradient-to-br from-brand-700 via-brand-600 to-brand-900 text-white">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-white/15 grid place-items-center font-extrabold text-xl">N</div>
          <span className="font-bold text-lg">Nursery Analytics</span>
        </div>
        <div>
          <h1 className="text-4xl font-extrabold leading-tight">Stripe-level analytics<br />for UK nursery chains.</h1>
          <p className="mt-4 text-white/80 max-w-md">Occupancy, revenue, attendance, EYFS progress, staffing and compliance — every decision layer in one place.</p>
        </div>
        <p className="text-white/60 text-sm">© LAIT · London</p>
      </div>

      {/* Form */}
      <div className="flex items-center justify-center p-6 bg-slate-50 dark:bg-slate-950">
        <div className="w-full max-w-sm">
          <h2 className="text-2xl font-extrabold">Sign in</h2>
          <p className="muted text-sm mt-1 mb-6">Use a demo account or your credentials.</p>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="text-sm font-medium">Email</label>
              <input className="input mt-1" value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
            </div>
            <div>
              <label className="text-sm font-medium">Password</label>
              <input className="input mt-1" value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
            </div>
            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
            <button className="btn-primary w-full" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
          </form>

          <div className="mt-8">
            <p className="text-xs uppercase tracking-wider muted mb-2">Demo accounts</p>
            <div className="grid grid-cols-1 gap-1.5">
              {DEMO.map(([label, e, p]) => (
                <button key={e} onClick={() => { setEmail(e); setPassword(p) }}
                  className="surface px-3 py-2 text-left text-sm hover:border-brand-400 transition flex justify-between">
                  <span className="font-medium">{label}</span>
                  <span className="muted">{e}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
