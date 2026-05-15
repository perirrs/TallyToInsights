import { useState, useEffect } from 'react'
import { BrowserRouter, HashRouter, Routes, Route, Navigate } from 'react-router-dom'
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
import ChecksPage from './pages/Checks'
import ActivationPage from './pages/Activation'
import DumpLayout from './pages/DumpLayout'

// In Electron: if no token after all retries, show a "backend unavailable" screen.
// In browser: redirect to login as usual.
function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  if (!token) {
    if (window.electron) {
      return (
        <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center gap-4">
          <div className="text-slate-300 text-lg font-semibold">Backend service unavailable</div>
          <div className="text-slate-500 text-sm">Close and reopen the application to try again.</div>
        </div>
      )
    }
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

export default function App() {
  // null = still checking, true/false = result
  const [activated, setActivated] = useState<boolean | null>(null)
  const [ready, setReady] = useState(false)
  const [statusMsg, setStatusMsg] = useState('Starting…')
  const login = useAuthStore((s) => s.login)

  // Step 1: check activation
  useEffect(() => {
    if (window.electron) {
      window.electron.isActivated().then(setActivated)
    } else {
      // Plain browser dev session — skip activation
      setActivated(true)
      setReady(true)
    }
  }, [])

  // Step 2: once activation is confirmed, auto-login (desktop only)
  useEffect(() => {
    if (activated === null) return
    if (!activated) { setReady(true); return }   // show activation screen
    if (!window.electron) { setReady(true); return } // browser — normal login

    let cancelled = false

    async function tryAutoLogin() {
      // Fast path: main process may have already fetched the token (production)
      try {
        const mainToken = await window.electron!.getDesktopToken()
        if (mainToken?.access_token && !cancelled) {
          login(mainToken.access_token, mainToken.user_id, mainToken.name, mainToken.is_admin)
          if (!cancelled) setReady(true)
          return
        }
      } catch (_) {}

      // Retry loop: backend may still be starting (up to ~30 s)
      for (let i = 0; i < 15 && !cancelled; i++) {
        setStatusMsg(i === 0 ? 'Connecting to backend…' : `Connecting to backend… (${i + 1}/15)`)
        try {
          const { data } = await api.post('/auth/desktop-auto-login')
          if (data?.access_token && !cancelled) {
            login(data.access_token, data.user_id, data.name, data.is_admin)
            if (!cancelled) setReady(true)
            return
          }
        } catch (_) {}
        // Wait 2 s before next attempt (skip delay on last attempt)
        if (!cancelled && i < 14) await new Promise((r) => setTimeout(r, 2000))
      }

      // All retries exhausted — mark ready so RequireAuth shows the error screen
      if (!cancelled) setReady(true)
    }

    tryAutoLogin()
    return () => { cancelled = true }
  }, [activated])

  // Loading screen (shown during activation check + auto-login retries)
  if (!ready) {
    return (
      <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center gap-3">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-slate-400 text-sm">{statusMsg}</p>
      </div>
    )
  }

  // Show activation screen if not activated
  if (!activated) return <ActivationPage />

  const Router = window.electron ? HashRouter : BrowserRouter

  return (
    <Router>
      <Routes>
        {/* Login page only exists in browser mode — desktop never shows it */}
        {!window.electron && <Route path="/login" element={<LoginPage />} />}

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

          <Route path="dumps/:dumpId" element={<DumpLayout />}>
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="financial" element={<FinancialPage />} />
            <Route path="cashflow" element={<CashFlowPage />} />
            <Route path="receivables" element={<ReceivablesPage />} />
            <Route path="gst" element={<GSTPage />} />
            <Route path="inventory" element={<InventoryPage />} />
            <Route path="payroll" element={<PayrollPage />} />
            <Route path="vouchers" element={<VouchersPage />} />
            <Route path="audit" element={<AuditPage />} />
            <Route path="audit/:checkId" element={<CheckDetailPage />} />
          </Route>

          <Route path="companies/:companyId/compare" element={<ComparePage />} />
          <Route path="checks" element={<ChecksPage />} />
        </Route>
      </Routes>
    </Router>
  )
}
