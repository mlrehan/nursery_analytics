import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useBranding } from '../context/BrandingContext'

const DEMO = [
  ['Administrator', 'admin@lait.org.uk', 'Admin123!'],
  ['Management', 'management@lait.org.uk', 'Manager123!'],
  ['Accounts', 'accounts@lait.org.uk', 'Accounts123!'],
  ['Teacher', 'teacher@lait.org.uk', 'Teacher123!'],
  ['Parent', 'parent@lait.org.uk', 'Parent123!'],
]

export default function Login() {
  const { login } = useAuth()
  const { brand_name, brand_tagline, logo_url, letter } = useBranding()
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
    <div className="min-h-screen grid lg:grid-cols-2 bg-[var(--page)]">
      {/* Brand panel */}
      <div className="relative hidden lg:flex flex-col justify-between p-12 text-white overflow-hidden"
        style={{ backgroundImage: 'linear-gradient(135deg,#1e1b4b 0%,#3730a3 45%,#6d28d9 100%)' }}>
        {/* signature aurora mesh + faint grid */}
        <div className="absolute inset-0 opacity-70" style={{
          backgroundImage:
            'radial-gradient(600px 360px at 80% 10%, rgba(124,92,246,.55), transparent 60%),' +
            'radial-gradient(560px 360px at 10% 90%, rgba(37,99,235,.45), transparent 55%)' }} />
        <div className="absolute inset-0 opacity-[0.06]" style={{
          backgroundImage: 'linear-gradient(#fff 1px,transparent 1px),linear-gradient(90deg,#fff 1px,transparent 1px)',
          backgroundSize: '40px 40px' }} />
        <div className="relative flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl grid place-items-center font-extrabold text-xl font-display overflow-hidden bg-white/15 backdrop-blur">
            {logo_url ? <img src={logo_url} alt="" className="w-full h-full object-contain" /> : letter}
          </div>
          <span className="font-bold text-lg font-display">{brand_name}</span>
        </div>
        <div className="relative">
          <div className="eyebrow text-white/70 mb-3">{brand_tagline || 'Early Years Intelligence'}</div>
          <h1 className="text-[40px] leading-[1.05] font-bold font-display">Every decision layer<br />of your nursery,<br />in one command centre.</h1>
          <p className="mt-5 text-white/75 max-w-md">Occupancy, revenue, attendance, EYFS progress, staffing and compliance — live, filterable, and inspection-ready.</p>
          <div className="mt-8 flex gap-6 text-sm text-white/80">
            <div><div className="text-2xl font-bold font-display nums">15</div>dashboards</div>
            <div><div className="text-2xl font-bold font-display nums">5</div>roles</div>
            <div><div className="text-2xl font-bold font-display nums">EYFS</div>aligned</div>
          </div>
        </div>
        <p className="relative text-white/55 text-sm">© {new Date().getFullYear()} {brand_name}</p>
      </div>

      {/* Form */}
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-2.5 mb-8">
            <div className="w-10 h-10 rounded-xl grid place-items-center text-white font-extrabold font-display overflow-hidden brandmark">
              {logo_url ? <img src={logo_url} alt="" className="w-full h-full object-contain" /> : letter}
            </div>
            <span className="font-bold text-lg font-display">{brand_name}</span>
          </div>
          <h2 className="text-2xl font-bold font-display">Welcome back</h2>
          <p className="muted text-sm mt-1 mb-6">Sign in to your {brand_name} workspace.</p>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="text-sm font-medium">Email</label>
              <input className="input mt-1" value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
            </div>
            <div>
              <label className="text-sm font-medium">Password</label>
              <input className="input mt-1" value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
            </div>
            {error && <p className="text-sm text-red-500">{error}</p>}
            <button className="btn-primary w-full" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
          </form>

          <div className="mt-8">
            <p className="eyebrow mb-2">Demo accounts</p>
            <div className="grid grid-cols-1 gap-1.5">
              {DEMO.map(([label, e, p]) => (
                <button key={e} onClick={() => { setEmail(e); setPassword(p) }}
                  className="surface px-3 py-2 text-left text-sm hover:-translate-y-0.5 hover:shadow-md transition flex justify-between items-center">
                  <span className="font-medium">{label}</span>
                  <span className="muted text-xs">{e}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
