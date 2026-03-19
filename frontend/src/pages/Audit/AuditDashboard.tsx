import { useMemo, useState } from 'react'
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import { RiskBadge, StatusBadge } from '../../components/UI/RiskBadge'
import { useChecksStore } from '../../store/checksStore'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { Search, ChevronLeft, Loader } from 'lucide-react'
import clsx from 'clsx'

const INR = (v: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)

interface CheckResult {
  check_id: number
  description: string
  category: string
  risk_level: string
  status: string
  finding_count: number
  amount_at_risk: number
}

export default function AuditDashboardPage() {
  const { dumpId } = useParams<{ dumpId: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // Active category comes from URL so it's shareable and survives navigation
  const activeCat = searchParams.get('cat') || ''

  // Table filters (local — intentionally transient)
  const [search, setSearch] = useState('')
  const [filterRisk, setFilterRisk] = useState('')
  const [filterStatus, setFilterStatus] = useState('')

  // Check selection from persisted store
  const storedIds = useChecksStore((s) => s.getSelection(dumpId!))

  const { data: summary, isLoading } = useQuery({
    queryKey: ['audit-summary', dumpId],
    queryFn: () => api.get(`/audit/${dumpId}/summary`).then((r) => r.data),
    staleTime: 60_000,
  })

  const results: CheckResult[] = useMemo(() => summary?.results || [], [summary])
  const allIds = useMemo(() => results.map((r) => r.check_id), [results])
  const effectiveIds = useMemo(
    () => storedIds === null ? null : new Set(storedIds),
    [storedIds],
  )

  // Results visible per the sidebar selection (used for scorecards)
  const selectedResults = useMemo(
    () => effectiveIds === null ? results : results.filter((r) => effectiveIds.has(r.check_id)),
    [results, effectiveIds],
  )

  // Table rows — apply all filters on top of selection
  const filtered = useMemo(
    () => selectedResults.filter((r) => {
      if (activeCat && r.category !== activeCat) return false
      if (filterRisk && r.risk_level !== filterRisk) return false
      if (filterStatus && r.status !== filterStatus) return false
      if (search && !r.description.toLowerCase().includes(search.toLowerCase())) return false
      return true
    }),
    [selectedResults, activeCat, filterRisk, filterStatus, search],
  )

  // Stats derived from selection (not affected by search/risk/status filters)
  const stats = useMemo(() => {
    const passed = selectedResults.filter((r) => r.status === 'pass').length
    const failed = selectedResults.filter((r) => r.status === 'fail').length
    const warnings = selectedResults.filter((r) => r.status === 'warning').length
    const amountAtRisk = selectedResults.reduce((s, r) => s + (r.amount_at_risk || 0), 0)
    const total = passed + failed + warnings
    const healthScore = total > 0 ? Math.round((passed / total) * 100) : 100
    return { passed, failed, warnings, amountAtRisk, healthScore }
  }, [selectedResults])

  const allCats = useMemo(
    () => [...new Set(selectedResults.map((r) => r.category))].sort(),
    [selectedResults],
  )

  const catChartData = useMemo(
    () => summary?.category_summary
      ?.filter((c: any) => !activeCat || c.category === activeCat)
      .map((c: any) => ({ name: c.category, fail: c.fail || 0, pass: c.pass || 0 })),
    [summary, activeCat],
  )

  const healthColor = stats.healthScore >= 80 ? 'text-green-600'
    : stats.healthScore >= 60 ? 'text-orange-500' : 'text-red-600'

  if (isLoading) return (
    <div className="flex items-center justify-center h-full text-gray-500 p-12">
      <Loader size={20} className="animate-spin mr-2" /> Loading audit report...
    </div>
  )
  if (!summary) return null

  return (
    <div className="p-6">
      {/* Header */}
      <button onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ChevronLeft size={16} /> Back
      </button>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Audit Report</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {activeCat
              ? <span className="text-brand-600 font-medium">{activeCat}</span>
              : `${selectedResults.length} checks across ${allCats.length} categories`}
          </p>
        </div>
        <a href={`/api/exports/${dumpId}/excel`} className="btn-secondary text-xs">Export Excel</a>
      </div>

      {/* Scorecard — reflects sidebar selection */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <div className="card text-center col-span-2 md:col-span-1">
          <p className={`text-4xl font-bold ${healthColor}`}>{stats.healthScore}%</p>
          <p className="text-xs text-gray-500 mt-1">Audit Health Score</p>
        </div>
        <div className="card text-center bg-green-50 border-green-200">
          <p className="text-3xl font-bold text-green-700">{stats.passed}</p>
          <p className="text-xs text-green-600 mt-1">Passed</p>
        </div>
        <div className="card text-center bg-red-50 border-red-200">
          <p className="text-3xl font-bold text-red-700">{stats.failed}</p>
          <p className="text-xs text-red-600 mt-1">Failed</p>
        </div>
        <div className="card text-center bg-yellow-50 border-yellow-200">
          <p className="text-3xl font-bold text-yellow-700">{stats.warnings}</p>
          <p className="text-xs text-yellow-600 mt-1">Warnings</p>
        </div>
        <div className="card text-center bg-red-50 border-red-200">
          <p className="text-2xl font-bold text-red-800">{INR(stats.amountAtRisk)}</p>
          <p className="text-xs text-red-600 mt-1">Amount at Risk</p>
        </div>
      </div>

      {/* Category Chart */}
      {!activeCat && catChartData?.length > 0 && (
        <div className="card mb-6">
          <h3 className="font-semibold text-gray-800 mb-4 text-sm">Results by Category</h3>
          <ResponsiveContainer width="100%" height={Math.max(180, allCats.length * 22)}>
            <BarChart data={catChartData} layout="vertical" margin={{ left: 140, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tick={{ fontSize: 10 }} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 9 }} width={140} />
              <Tooltip />
              <Bar dataKey="pass" fill="#16A34A" name="Pass" stackId="a" />
              <Bar dataKey="fail" fill="#DC2626" name="Fail" stackId="a" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-2.5 text-gray-400" />
          <input
            value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search checks..."
            className="pl-8 pr-3 py-2 border rounded-lg text-sm w-52 focus:ring-2 focus:ring-brand-500 focus:outline-none"
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
        {(search || filterRisk || filterStatus) && (
          <button onClick={() => { setSearch(''); setFilterRisk(''); setFilterStatus('') }}
            className="text-xs text-gray-500 hover:text-gray-700 underline self-center">Clear</button>
        )}
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
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-10 text-gray-400 text-sm">
                  No checks match the current filters
                </td>
              </tr>
            ) : filtered.map((r) => (
              <tr key={r.check_id}
                className={clsx(
                  'hover:bg-gray-50',
                  r.status === 'fail' && 'bg-red-50/30',
                  r.status === 'warning' && 'bg-yellow-50/30',
                )}>
                <td className="px-4 py-2.5 text-gray-400 text-xs">{r.check_id}</td>
                <td className="px-4 py-2.5">
                  <Link to={`/dumps/${dumpId}/audit/${r.check_id}`}
                    className="text-gray-900 hover:text-brand-600 hover:underline font-medium text-xs">
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
