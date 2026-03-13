import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import PageHeader from '../../components/UI/PageHeader'
import { RiskBadge, StatusBadge } from '../../components/UI/RiskBadge'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import { Shield, AlertTriangle, CheckCircle, Search } from 'lucide-react'

const INR = (v: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)

export default function AuditDashboardPage() {
  const { dumpId } = useParams<{ dumpId: string }>()
  const [search, setSearch] = useState('')
  const [filterRisk, setFilterRisk] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterCat, setFilterCat] = useState('')

  const { data: summary, isLoading } = useQuery({
    queryKey: ['audit-summary', dumpId],
    queryFn: () => api.get(`/audit/${dumpId}/summary`).then((r) => r.data),
  })

  if (isLoading) return <div className="flex items-center justify-center h-full text-gray-500">Running audit analysis...</div>
  if (!summary) return null

  const filtered = (summary.results || []).filter((r: any) => {
    if (filterRisk && r.risk_level !== filterRisk) return false
    if (filterStatus && r.status !== filterStatus) return false
    if (filterCat && r.category !== filterCat) return false
    if (search && !r.description.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const cats = [...new Set((summary.results || []).map((r: any) => r.category))] as string[]

  const catChartData = summary.category_summary?.map((c: any) => ({
    name: c.category.replace(' ', '\n'),
    fail: c.fail || 0,
    pass: c.pass || 0,
  }))

  const healthColor = summary.audit_health_score >= 80 ? 'text-green-600' :
    summary.audit_health_score >= 60 ? 'text-orange-500' : 'text-red-600'

  return (
    <div className="p-6">
      <PageHeader
        title="Audit Report"
        subtitle="300 automated checks across 16 categories"
        actions={
          <a href={`/api/exports/${dumpId}/excel`} className="btn-secondary text-xs">Export Excel</a>
        }
      />

      {/* Scorecard */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <div className="card text-center col-span-2 md:col-span-1">
          <p className={`text-4xl font-bold ${healthColor}`}>{summary.audit_health_score}%</p>
          <p className="text-xs text-gray-500 mt-1">Audit Health Score</p>
        </div>
        <div className="card text-center bg-green-50 border-green-200">
          <p className="text-3xl font-bold text-green-700">{summary.passed}</p>
          <p className="text-xs text-green-600 mt-1">Passed</p>
        </div>
        <div className="card text-center bg-red-50 border-red-200">
          <p className="text-3xl font-bold text-red-700">{summary.failed}</p>
          <p className="text-xs text-red-600 mt-1">Failed</p>
        </div>
        <div className="card text-center bg-yellow-50 border-yellow-200">
          <p className="text-3xl font-bold text-yellow-700">{summary.warnings}</p>
          <p className="text-xs text-yellow-600 mt-1">Warnings</p>
        </div>
        <div className="card text-center bg-red-50 border-red-200">
          <p className="text-2xl font-bold text-red-800">{INR(summary.total_amount_at_risk)}</p>
          <p className="text-xs text-red-600 mt-1">Amount at Risk</p>
        </div>
      </div>

      {/* Category Chart */}
      <div className="card mb-6">
        <h3 className="font-semibold text-gray-800 mb-4">Audit Results by Category</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={catChartData} layout="vertical" margin={{ left: 100 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" tick={{ fontSize: 10 }} />
            <YAxis dataKey="name" type="category" tick={{ fontSize: 10 }} width={100} />
            <Tooltip />
            <Bar dataKey="pass" fill="#16A34A" name="Pass" stackId="a" />
            <Bar dataKey="fail" fill="#DC2626" name="Fail" stackId="a" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-2.5 text-gray-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search checks..."
            className="pl-8 pr-3 py-2 border rounded-lg text-sm w-64 focus:ring-2 focus:ring-brand-500 focus:outline-none"
          />
        </div>
        <select value={filterRisk} onChange={(e) => setFilterRisk(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none">
          <option value="">All Risk Levels</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none">
          <option value="">All Statuses</option>
          <option value="fail">Fail</option>
          <option value="warning">Warning</option>
          <option value="pass">Pass</option>
          <option value="skipped">Skipped</option>
        </select>
        <select value={filterCat} onChange={(e) => setFilterCat(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none">
          <option value="">All Categories</option>
          {cats.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <span className="text-xs text-gray-500 self-center">{filtered.length} checks shown</span>
      </div>

      {/* Results Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-600 w-12">#</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-600">Description</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-600 w-36">Category</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-600 w-20">Risk</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-600 w-24">Status</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-600 w-24">Findings</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-600 w-32">At Risk</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filtered.map((r: any) => (
              <tr
                key={r.check_id}
                className={`hover:bg-gray-50 ${r.status === 'fail' ? 'bg-red-50/30' : r.status === 'warning' ? 'bg-yellow-50/30' : ''}`}
              >
                <td className="px-4 py-2.5 text-gray-400 text-xs">{r.check_id}</td>
                <td className="px-4 py-2.5">
                  <Link
                    to={`/dumps/${dumpId}/audit/${r.check_id}`}
                    className="text-gray-900 hover:text-brand-600 hover:underline font-medium text-xs"
                  >
                    {r.description}
                  </Link>
                </td>
                <td className="px-4 py-2.5 text-xs text-gray-500">{r.category}</td>
                <td className="px-4 py-2.5"><RiskBadge level={r.risk_level} /></td>
                <td className="px-4 py-2.5"><StatusBadge status={r.status} /></td>
                <td className="px-4 py-2.5 text-right text-xs text-gray-600">{r.finding_count}</td>
                <td className="px-4 py-2.5 text-right text-xs font-medium text-red-700">
                  {r.amount_at_risk > 0 ? INR(r.amount_at_risk) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
