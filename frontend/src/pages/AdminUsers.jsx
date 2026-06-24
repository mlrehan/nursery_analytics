import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

const empty = { email: '', full_name: '', password: '', role_id: '', job_title: '' }

export default function AdminUsers() {
  const { user: me } = useAuth()
  const [users, setUsers] = useState([])
  const [roles, setRoles] = useState([])
  const [form, setForm] = useState(empty)
  const [showAdd, setShowAdd] = useState(false)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const load = async () => {
    const [u, r] = await Promise.all([api.get('/admin/users'), api.get('/admin/roles')])
    setUsers(u.data); setRoles(r.data)
    if (!form.role_id && r.data.length) setForm((f) => ({ ...f, role_id: r.data[0].id }))
  }
  useEffect(() => { load() }, []) // eslint-disable-line

  const create = async (e) => {
    e.preventDefault(); setBusy(true); setError(null)
    try {
      await api.post('/admin/users', { ...form, role_id: Number(form.role_id) })
      setForm(empty); setShowAdd(false); await load()
    } catch (err) { setError(err.response?.data?.detail || 'Failed to create user') }
    finally { setBusy(false) }
  }

  const update = async (id, patch) => {
    await api.put(`/admin/users/${id}`, patch)
    await load()
  }
  const resetPwd = async (id) => {
    const pwd = window.prompt('New password (min 6 chars):')
    if (!pwd) return
    try { await api.post(`/admin/users/${id}/password`, { password: pwd }); alert('Password updated') }
    catch (err) { alert(err.response?.data?.detail || 'Failed') }
  }
  const remove = async (id, name) => {
    if (!window.confirm(`Delete ${name}? This cannot be undone.`)) return
    try { await api.delete(`/admin/users/${id}`); await load() }
    catch (err) { alert(err.response?.data?.detail || 'Failed to delete') }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-5 gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">User Management</h1>
          <p className="muted text-sm mt-0.5">Create users, assign roles, reset passwords and deactivate accounts.</p>
        </div>
        <button className="btn-primary" onClick={() => setShowAdd((s) => !s)}>{showAdd ? 'Close' : '+ Add user'}</button>
      </div>

      {showAdd && (
        <form onSubmit={create} className="surface p-5 mb-5 grid sm:grid-cols-2 lg:grid-cols-5 gap-3 items-end">
          <L label="Full name"><input className="input" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required /></L>
          <L label="Email"><input className="input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required /></L>
          <L label="Temp password"><input className="input" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required /></L>
          <L label="Role">
            <select className="input" value={form.role_id} onChange={(e) => setForm({ ...form, role_id: e.target.value })}>
              {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </L>
          <button className="btn-primary" disabled={busy}>{busy ? 'Creating…' : 'Create'}</button>
          {error && <p className="text-sm text-red-500 sm:col-span-2 lg:col-span-5">{error}</p>}
        </form>
      )}

      <div className="surface p-2 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left muted border-b hairline">
              <th className="py-2 px-3 font-medium">User</th>
              <th className="py-2 px-3 font-medium">Role</th>
              <th className="py-2 px-3 font-medium">Status</th>
              <th className="py-2 px-3 font-medium">Last login</th>
              <th className="py-2 px-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b hairline last:border-0">
                <td className="py-2.5 px-3">
                  <div className="font-medium">{u.full_name}</div>
                  <div className="text-xs muted">{u.email}</div>
                </td>
                <td className="py-2.5 px-3">
                  <select className="input !py-1 !w-auto text-sm" value={u.role.id}
                    disabled={u.id === me?.id}
                    onChange={(e) => update(u.id, { role_id: Number(e.target.value) })}>
                    {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                </td>
                <td className="py-2.5 px-3">
                  <button onClick={() => u.id !== me?.id && update(u.id, { is_active: !u.is_active })}
                    className={`chip ${u.is_active ? 'text-emerald-500' : 'text-slate-400'}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                    {u.is_active ? 'Active' : 'Inactive'}
                  </button>
                </td>
                <td className="py-2.5 px-3 text-xs muted">{u.last_login_at ? new Date(u.last_login_at).toLocaleDateString() : '—'}</td>
                <td className="py-2.5 px-3 text-right whitespace-nowrap">
                  <button className="btn-ghost text-xs" onClick={() => resetPwd(u.id)}>Reset password</button>
                  {u.id !== me?.id && (
                    <button className="btn-ghost text-xs text-red-500" onClick={() => remove(u.id, u.full_name)}>Delete</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function L({ label, children }) {
  return <label className="block"><span className="text-sm font-medium">{label}</span><div className="mt-1">{children}</div></label>
}
