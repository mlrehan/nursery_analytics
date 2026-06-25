import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import AdminConfig from './pages/AdminConfig'
import AdminUsers from './pages/AdminUsers'
import AdminSettings from './pages/AdminSettings'
import Profile from './pages/Profile'

function Protected({ children, adminOnly }) {
  const { user, loading, isAdmin } = useAuth()
  if (loading) {
    return <div className="min-h-screen grid place-items-center muted">Loading…</div>
  }
  if (!user) return <Navigate to="/login" replace />
  if (adminOnly && !isAdmin) return <Navigate to="/" replace />
  return children
}

export default function App() {
  const { user } = useAuth()
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route element={<Protected><Layout /></Protected>}>
        <Route path="/" element={<div className="muted">Loading your dashboards…</div>} />
        <Route path="/m/:moduleKey" element={<Dashboard />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/admin" element={<Protected adminOnly><AdminConfig /></Protected>} />
        <Route path="/admin/users" element={<Protected adminOnly><AdminUsers /></Protected>} />
        <Route path="/admin/settings" element={<Protected adminOnly><AdminSettings /></Protected>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
