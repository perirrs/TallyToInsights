import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import PageHeader from '../components/UI/PageHeader'
import KPICard from '../components/UI/KPICard'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import {
  TrendingUp, TrendingDown, DollarSign, Shield, AlertTriangle,
  FileText, BarChart3, Download, ArrowRight,
} from 'lucide-react'
import { RiskBadge } from '../components/UI/RiskBadge'

const INR = (v: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)

const COLORS = ['#1A56DB', '#16A34A', '#EA580C', '#7C3AED', '#DB2777', '#0891B2']

export default function DashboardPage() {
  const { dumpId } = useParams<{ dumpId: string }>()
  const navigate = useNavigate()

  const { data: kpis, isLoading } = useQuery({
    queryKey: ['dashboard', dumpId],
    queryFn: () => api.get(`/reports/${dumpId}/dashboard`).then((r) => r.data),
  })

  if (isLoading) {
    return <div className="flex items-center justify-center h-full text-gray-500">Loading dashboard...</div>
  }
  if (!kpis) return null

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

  return (
    <div className="p-6">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">
            {kpis.financial_year && `FY ${kpis.financial_year} · `}
            {kpis.period_from && `${kpis.period_from} → ${kpis.period_to}`}
          </p>
        </div>
        <div className="flex gap-2">
          <a
            href={`/api/exports/${dumpId}/excel`}
            className="btn-secondary text-xs flex items-center gap-1"
          >
            <Download size={12} /> Excel
          </a>
          <a
            href={`/api/exports/${dumpId}/pdf`}
            className="btn-secondary text-xs flex items-center gap-1"
          >
            <Download size={12} /> PDF
          </a>
        </div>
      </div>

      {/* Quick Nav */}
      <div className="flex flex-wrap gap-2 mb-6">
        {navLinks.map((l) => (
          <Link
            key={l.path}
            to={`/dumps/${dumpId}/${l.path}`}
            className="flex items-center gap-1 text-xs bg-white border border-gray-200 px-3 py-1.5 rounded-lg hover:bg-brand-50 hover:border-brand-300 transition-colors text-gray-600"
          >
            {l.icon} {l.label}
          </Link>
        ))}
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4 mb-6">
        <KPICard title="Revenue" value={INR(kpis.revenue)} color="blue" icon={<TrendingUp size={18} />} />
        <KPICard title="Expenses" value={INR(kpis.expenses)} color="orange" icon={<TrendingDown size={18} />} />
        <KPICard
          title="Net Profit"
          value={INR(kpis.net_profit)}
          subtitle={`${kpis.net_margin_pct?.toFixed(1)}% margin`}
          color={kpis.net_profit >= 0 ? 'green' : 'red'}
        />
        <KPICard title="Cash Position" value={INR(kpis.cash_position)} color="green" icon={<DollarSign size={18} />} />
        <KPICard
          title="Audit Health"
          value={`${kpis.audit_health_score}%`}
          subtitle={`${kpis.audit_failures} failures`}
          color={kpis.audit_health_score >= 80 ? 'green' : kpis.audit_health_score >= 60 ? 'orange' : 'red'}
          icon={<Shield size={18} />}
        />
        <KPICard title="Receivables" value={INR(kpis.receivables)} color="purple" />
        <KPICard title="Payables" value={INR(kpis.payables)} color="orange" />
        <KPICard title="Amount at Risk" value={INR(kpis.amount_at_risk)} color="red" icon={<AlertTriangle size={18} />} />
        <KPICard title="Total Vouchers" value={kpis.total_vouchers?.toLocaleString()} color="blue" />
        <KPICard title="High Risk Issues" value={kpis.audit_high_risk} color="red" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Monthly Revenue Chart */}
        <div className="card">
          <h3 className="font-semibold text-gray-800 mb-4">Monthly Revenue</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={kpis.monthly_revenue || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}K`} />
              <Tooltip formatter={(v: number) => INR(v)} />
              <Bar dataKey="revenue" fill="#1A56DB" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Voucher Type Breakdown */}
        <div className="card">
          <h3 className="font-semibold text-gray-800 mb-4">Voucher Type Distribution</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={kpis.voucher_breakdown || []}
                dataKey="count"
                nameKey="type"
                cx="50%"
                cy="50%"
                outerRadius={80}
                label={({ type, count }) => `${type}: ${count}`}
                labelLine={false}
              >
                {(kpis.voucher_breakdown || []).map((_: any, i: number) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top Issues */}
      {kpis.top_issues?.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-800">Top Audit Issues</h3>
            <Link
              to={`/dumps/${dumpId}/audit`}
              className="text-xs text-brand-600 hover:underline flex items-center gap-1"
            >
              View All <ArrowRight size={12} />
            </Link>
          </div>
          <div className="space-y-3">
            {kpis.top_issues.map((issue: any) => (
              <Link
                key={issue.check_id}
                to={`/dumps/${dumpId}/audit/${issue.check_id}`}
                className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 hover:bg-red-50 transition-colors"
              >
                <AlertTriangle size={16} className="text-red-500 mt-0.5 flex-shrink-0" />
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
    </div>
  )
}
