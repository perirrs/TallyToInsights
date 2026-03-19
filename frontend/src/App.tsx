import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import api from './api/client'
import Layout from './components/Layout/Layout'
import LoginPage from './pages/Login'
import CompaniesPage from './pages/Companies'
import UploadsPage from './pages/Uploads'
import DashboardPage from './pages/Dashboard'
import FinancialPage from './pages/Reports/Financial'
import CashFlowPage from './pages/Reports/CashFlow'
import ReceivablesPage from './pages/Reports/Receivables'
import GSTPage from './pages/Reports/GST'
import InventoryPage from './pages/Reports/Inventory'
import PayrollPage from './pages/Reports/Payroll'
import ComparePage from './pages/Reports/Compare'
import VouchersPage from './pages/Reports/Vouchers'
import AuditPage from './pages/Audit/AuditDashboard'
import CheckDetailPage from './pages/Audit/CheckDetail'
import UsersPage from './pages/Users'
import ActivationPage from './pages/Activation'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  // null = checking, true = activated (or not in Electron), false = needs activation
  const [activated, setActivated] = useState<boolean | null>(null)
  // false until we've attempted desktop auto-login (prevents flash of login screen)
  const [ready, setReady] = useState(false)
  const login = useAuthStore((s) => s.login)

  useEffect(() => {
    if (window.electron) {
      window.electron.isActivated().then(setActivated)
    } else {
      // Running in a browser (dev without Electron) — skip activation
      setActivated(true)
      setReady(true)
    }
  }, [])

  // After activation is confirmed, attempt desktop auto-login
  useEffect(() => {
    if (activated === null) return
    if (!activated) { setReady(true); return }  // show activation screen

    if (!window.electron) { setReady(true); return }  // plain browser — use normal login

    // Desktop app: call localhost-only endpoint to get a token automatically
    api.post('/auth/desktop-auto-login')
      .then(({ data }) => {
        if (data?.access_token) {
          login(data.access_token, data.user_id, data.name, data.is_admin)
        }
      })
      .catch(() => {})
      .finally(() => setReady(true))
  }, [activated])

  // Blank slate while checking activation / fetching desktop token
  if (!ready) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  // Show activation screen (app.relaunch() is called on success — no routing needed)
  if (!activated) {
    return <ActivationPage />
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="/companies" replace />} />
          <Route path="companies" element={<CompaniesPage />} />
          <Route path="companies/:companyId/uploads" element={<UploadsPage />} />
          <Route path="dumps/:dumpId/dashboard" element={<DashboardPage />} />
          <Route path="dumps/:dumpId/financial" element={<FinancialPage />} />
          <Route path="dumps/:dumpId/cashflow" element={<CashFlowPage />} />
          <Route path="dumps/:dumpId/receivables" element={<ReceivablesPage />} />
          <Route path="dumps/:dumpId/gst" element={<GSTPage />} />
          <Route path="dumps/:dumpId/inventory" element={<InventoryPage />} />
          <Route path="dumps/:dumpId/payroll" element={<PayrollPage />} />
          <Route path="dumps/:dumpId/vouchers" element={<VouchersPage />} />
          <Route path="dumps/:dumpId/audit" element={<AuditPage />} />
          <Route path="dumps/:dumpId/audit/:checkId" element={<CheckDetailPage />} />
          <Route path="companies/:companyId/compare" element={<ComparePage />} />
          <Route path="users" element={<UsersPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
