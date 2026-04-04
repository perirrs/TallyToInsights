import { useMemo, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import KPICard from '../components/UI/KPICard'
import { RiskBadge } from '../components/UI/RiskBadge'
import DrillVouchers, { DrillFilters } from '../components/DrillVouchers'
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import {
  TrendingUp, TrendingDown, DollarSign, Shield, AlertTriangle,
  FileText, BarChart3, Download, ArrowRight,
} from 'lucide-react'

/** Convert "YYYY-MM" string to { date_from, date_to } for drill filters */
function monthRange(ym: string) {
  const [y, m] = ym.split('-').map(Number)
  const last = new Date(y, m, 0).getDate()
  return { date_from: `${ym}-01`, date_to: `${ym}-${String(last).padStart(2, '0')}` }
}

const INR = (v: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)

const COLORS = ['#1A56DB', '#16A34A', '#EA580C', '#7C3AED', '#DB2777', '#0891B2', '#D97706', '#059669']
const RISK_COLORS: Record<string, string> = { High: '#DC2626', Medium: '#D97706', Low: '#2563EB' }
const STATUS_COLORS: Record<string, string> = { Pass: '#16A34A', Fail: '#DC2626', Warning: '#D97706', Skipped: '#9CA3AF' }

interface Drill { title: string; subtitle?: string; filters: DrillFilters }

export default function DashboardPage() {
  const { dumpId } = useParams<{ dumpId: string }>()
  const navigate = useNavigate()
  const [drill, setDrill] = useState<Drill | null>(null)

  const { data: kpis, isLoading } = useQuery({
    queryKey: ['dashboard', dumpId],
    queryFn: () => api.get(`/reports/${dumpId}/dashboard`).then((r) => r.data),
  })

  // Audit summary for extra charts — same cache key used by ChecksSidebar & AuditDashboard
  const { data: auditSummary } = useQuery({
    queryKey: ['audit-summary', dumpId],
    queryFn: () => api.get(`/audit/${dumpId}/summary`).then((r) => r.data),
    staleTime: 60_000,
  })

  const auditResults = auditSummary?.results || []

  // Audit status distribution
  const statusDist = useMemo(() => {
    if (!auditResults.length) return []
    const counts: Record<string, number> = {}
    for (const r of auditResults) {
      const k = r.status === 'pass' ? 'Pass' : r.status === 'fail' ? 'Fail' : r.status === 'warning' ? 'Warning' : 'Skipped'
      counts[k] = (counts[k] || 0) + 1
    }
    return Object.entries(counts).map(([name, value]) => ({ name, value }))
  }, [auditResults])

  // Risk level breakdown of failures
  const riskDist = useMemo(() => {
    if (!auditResults.length) return []
    const counts: Record<string, number> = { High: 0, Medium: 0, Low: 0 }
    for (const r of auditResults) {
      if (r.status !== 'pass' && r.status !== 'skipped') {
        counts[r.risk_level] = (counts[r.risk_level] || 0) + 1
      }
    }
    return Object.entries(counts)
      .filter(([, v]) => v > 0)
      .map(([name, value]) => ({ name, value }))
  }, [auditResults])

  // Top failing categories
  const topFailCats = useMemo(
    () => (auditSummary?.category_summary || [])
      .filter((c: any) => c.fail > 0)
      .sort((a: any, b: any) => b.fail - a.fail)
      .slice(0, 8)
      .map((c: any) => ({ name: c.category, fail: c.fail, pass: c.pass })),
    [auditSummary],
  )

  const navLinks = [
    { label: 'P&L / Balance Sheet', path: 'financial', icon: <TrendingUp size={14} /> },
    { label: 'Cash Flow', path: 'cashflow', icon: <DollarSign size={14} /> },
    { label: 'Receivables', path: 'receivables', icon: <FileText size={14} /> },
    { label: 'Payables', path: 'payables', icon: <FileText size={14} /> },
    { label: 'GST Report', path: 'gst', icon: <BarChart3 size={14} /> },
    { label: 'Inventory', path: 'inventory', icon: <BarChart3 size={14} /> },
    { label: 'Payroll', path: 'payroll', icon: <FileText size={14} /> },
    { label: 'Vouchers', path: 'vouchers', icon: <FileText size={14} /> },
    { label: 'Audit Report', path: 'audit', icon: <Shield size={14} /> },
  ]

  if (isLoading) return (
    <div className="flex items-center justify-center h-full text-gray-500 p-12">Loading dashboard...</div>
  )
  if (!kpis) return null

  return (
    <div className="p-6">
      <button onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ChevronLeft size={16} /> Back
      </button>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">
            {kpis.financial_year && `FY ${kpis.financial_year} · `}
            {kpis.period_from && `${kpis.period_from} → ${kpis.period_to}`}
          </p>
        </div>
        <div className="flex gap-2">
          <a href={`/api/exports/${dumpId}/excel`} className="btn-secondary text-xs flex items-center gap-1">
            <Download size={12} /> Excel
          </a>
          <a href={`/api/exports/${dumpId}/pdf`} className="btn-secondary text-xs flex items-center gap-1">
            <Download size={12} /> PDF
          </a>
        </div>
      </div>

      {/* Quick Nav */}
      <div className="flex flex-wrap gap-2 mb-6">
        {navLinks.map((l) => (
          <Link key={l.path} to={`/dumps/${dumpId}/${l.path}`}
            className="flex items-center gap-1 text-xs bg-white border border-gray-200 px-3 py-1.5 rounded-lg hover:bg-brand-50 hover:border-brand-300 transition-colors text-gray-600">
            {l.icon} {l.label}
          </Link>
        ))}
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4 mb-6">
        <KPICard title="Revenue" value={INR(kpis.revenue)} color="blue" icon={<TrendingUp size={18} />}
          onClick={() => setDrill({ title: 'Revenue Vouchers', filters: { voucher_type: 'Sales' } })} />
        <KPICard title="Expenses" value={INR(kpis.expenses)} color="orange" icon={<TrendingDown size={18} />}
          onClick={() => setDrill({ title: 'Expense Vouchers', filters: { voucher_type: 'Purchase' } })} />
        <KPICard title="Net Profit" value={INR(kpis.net_profit)}
          subtitle={`${kpis.net_margin_pct?.toFixed(1)}% margin`}
          color={kpis.net_profit >= 0 ? 'green' : 'red'} />
        <KPICard title="Cash Position" value={INR(kpis.cash_position)} color="green" icon={<DollarSign size={18} />}
          onClick={() => setDrill({ title: 'Cash & Bank Vouchers', filters: { voucher_type: 'Receipt' } })} />
        <KPICard title="Audit Health" value={`${kpis.audit_health_score}%`}
          subtitle={`${kpis.audit_failures} failures`}
          color={kpis.audit_health_score >= 80 ? 'green' : kpis.audit_health_score >= 60 ? 'orange' : 'red'}
          icon={<Shield size={18} />} />
        <KPICard title="Receivables" value={INR(kpis.receivables)} color="purple"
          onClick={() => setDrill({ title: 'Receivable Vouchers', filters: { voucher_type: 'Sales' } })} />
        <KPICard title="Payables" value={INR(kpis.payables)} color="orange"
          onClick={() => setDrill({ title: 'Payable Vouchers', filters: { voucher_type: 'Purchase' } })} />
        <KPICard title="Amount at Risk" value={INR(kpis.amount_at_risk)} color="red" icon={<AlertTriangle size={18} />} />
        <KPICard title="Total Vouchers" value={kpis.total_vouchers?.toLocaleString()} color="blue"
          onClick={() => setDrill({ title: 'All Vouchers', filters: {} })} />
        <KPICard title="High Risk Issues" value={kpis.audit_high_risk} color="red" />
      </div>

      {/* Row 1: Monthly Revenue + Voucher Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="card">
          <h3 className="font-semibold text-gray-800 mb-1 text-sm">Monthly Revenue</h3>
          <p className="text-xs text-gray-400 mb-3">Click a bar to see vouchers for that month</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={kpis.monthly_revenue || []} style={{ cursor: 'pointer' }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}K`} />
              <Tooltip formatter={(v: number) => INR(v)} />
              <Bar dataKey="revenue" fill="#1A56DB" radius={[4, 4, 0, 0]}
                onClick={(data) => {
                  if (!data?.month) return
                  setDrill({ title: `Revenue — ${data.month}`, filters: { voucher_type: 'Sales', ...monthRange(data.month) } })
                }}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h3 className="font-semibold text-gray-800 mb-1 text-sm">Voucher Type Distribution</h3>
          <p className="text-xs text-gray-400 mb-3">Click a slice to see those vouchers</p>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={kpis.voucher_breakdown || []} dataKey="count" nameKey="type"
                cx="50%" cy="50%" outerRadius={75}
                label={({ type, count }) => `${type}: ${count}`} labelLine={false}
                style={{ cursor: 'pointer' }}
                onClick={(data) => {
                  if (!data?.type) return
                  setDrill({ title: `${data.type} Vouchers`, subtitle: `${data.count} entries`, filters: { voucher_type: data.type } })
                }}>
                {(kpis.voucher_breakdown || []).map((_: any, i: number) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Row 2: Audit Charts (only when audit data available) */}
      {auditResults.length > 0 && (
        <>
          <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <Shield size={14} className="text-brand-600" /> Audit Overview
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            {/* Audit Status Donut */}
            <div className="card">
              <h3 className="font-semibold text-gray-800 mb-3 text-sm">Check Status</h3>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={statusDist} dataKey="value" nameKey="name"
                    cx="50%" cy="50%" innerRadius={45} outerRadius={70}
                    paddingAngle={2}>
                    {statusDist.map((d) => (
                      <Cell key={d.name} fill={STATUS_COLORS[d.name] || '#9CA3AF'} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => `${v} checks`} />
                  <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Risk Level Donut */}
            <div className="card">
              <h3 className="font-semibold text-gray-800 mb-3 text-sm">Failures by Risk Level</h3>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={riskDist} dataKey="value" nameKey="name"
                    cx="50%" cy="50%" innerRadius={45} outerRadius={70}
                    paddingAngle={2}>
                    {riskDist.map((d) => (
                      <Cell key={d.name} fill={RISK_COLORS[d.name] || '#6B7280'} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => `${v} issues`} />
                  <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Top Failing Categories */}
            <div className="card">
              <h3 className="font-semibold text-gray-800 mb-3 text-sm">Top Failing Categories</h3>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={topFailCats} layout="vertical" margin={{ left: 110, right: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" tick={{ fontSize: 9 }} />
                  <YAxis dataKey="name" type="category" tick={{ fontSize: 9 }} width={110} />
                  <Tooltip />
                  <Bar dataKey="fail" fill="#DC2626" name="Fail" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}

      {/* Top Issues */}
      {kpis.top_issues?.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-800 text-sm">Top Audit Issues</h3>
            <Link to={`/dumps/${dumpId}/audit`}
              className="text-xs text-brand-600 hover:underline flex items-center gap-1">
              View All <ArrowRight size={12} />
            </Link>
          </div>
          <div className="space-y-2">
            {kpis.top_issues.map((issue: any) => (
              <Link key={issue.check_id} to={`/dumps/${dumpId}/audit/${issue.check_id}`}
                className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 hover:bg-red-50 transition-colors">
                <AlertTriangle size={15} className="text-red-500 mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{issue.description}</p>
                  <p className="text-xs text-gray-500">{issue.category} · {issue.finding_count} findings · {INR(issue.amount_at_risk)} at risk</p>
                </div>
                <RiskBadge level={issue.risk_level} />
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Voucher drill-down panel */}
      {drill && (
        <DrillVouchers
          dumpId={dumpId!}
          title={drill.title}
          subtitle={drill.subtitle}
          filters={drill.filters}
          onClose={() => setDrill(null)}
        />
      )}
    </div>
  )
}
