import { useState, useEffect, useMemo } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../../api/client'
import { RiskBadge, StatusBadge } from '../../components/UI/RiskBadge'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import {
  Shield, AlertTriangle, CheckCircle2, Search, ChevronLeft,
  ChevronDown, ChevronRight, Square, CheckSquare, MinusSquare,
  RotateCcw, Loader,
} from 'lucide-react'
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
  const qc = useQueryClient()

  // Main filters (view)
  const [search, setSearch] = useState('')
  const [filterRisk, setFilterRisk] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [activeCat, setActiveCat] = useState('') // selected category in sidebar

  // Sidebar state
  const [expandedCats, setExpandedCats] = useState<Set<string>>(new Set())
  const [selectedCheckIds, setSelectedCheckIds] = useState<Set<number> | null>(null) // null = all
  const [isRechecking, setIsRechecking] = useState(false)

  // Audit summary
  const { data: summary, isLoading, refetch: refetchSummary } = useQuery({
    queryKey: ['audit-summary', dumpId],
    queryFn: () => api.get(`/audit/${dumpId}/summary`).then((r) => r.data),
  })

  // Poll dump status while rechecking
  const { data: dumpStatus } = useQuery({
    queryKey: ['dump-recheck-status', dumpId],
    queryFn: () => api.get(`/uploads/status/${dumpId}`).then((r) => r.data),
    enabled: isRechecking,
    refetchInterval: isRechecking ? 2000 : false,
  })

  useEffect(() => {
    if (isRechecking && dumpStatus?.status === 'processed') {
      setIsRechecking(false)
      refetchSummary()
    }
  }, [dumpStatus?.status, isRechecking, refetchSummary])

  const results: CheckResult[] = summary?.results || []

  // Build category map from results
  const checksByCategory = useMemo(() => {
    const map: Record<string, CheckResult[]> = {}
    for (const r of results) {
      const cat = r.category || 'Uncategorised'
      if (!map[cat]) map[cat] = []
      map[cat].push(r)
    }
    return map
  }, [results])

  const allCats = useMemo(() => Object.keys(checksByCategory).sort(), [checksByCategory])
  const allIds = useMemo(() => results.map((r) => r.check_id), [results])
  const effectiveSelected = selectedCheckIds ?? new Set(allIds)
  const isAllSelected = selectedCheckIds === null || selectedCheckIds.size === allIds.length
  const selectedCount = effectiveSelected.size

  // Sidebar helpers
  const getCatState = (cat: string): 'all' | 'some' | 'none' => {
    const ids = (checksByCategory[cat] || []).map((c) => c.check_id)
    const n = ids.filter((id) => effectiveSelected.has(id)).length
    if (n === 0) return 'none'
    if (n === ids.length) return 'all'
    return 'some'
  }

  const toggleAll = () => {
    setSelectedCheckIds(isAllSelected ? new Set() : null)
  }

  const toggleCat = (cat: string) => {
    const ids = (checksByCategory[cat] || []).map((c) => c.check_id)
    const allSel = ids.every((id) => effectiveSelected.has(id))
    const next = new Set(effectiveSelected)
    if (allSel) { ids.forEach((id) => next.delete(id)) }
    else { ids.forEach((id) => next.add(id)) }
    setSelectedCheckIds(next.size === allIds.length ? null : next)
  }

  const toggleCheck = (id: number) => {
    const next = new Set(effectiveSelected)
    next.has(id) ? next.delete(id) : next.add(id)
    setSelectedCheckIds(next.size === allIds.length ? null : next)
  }

  const toggleExpand = (cat: string) => {
    setExpandedCats((prev) => { const s = new Set(prev); s.has(cat) ? s.delete(cat) : s.add(cat); return s })
  }

  const handleRerun = async () => {
    const body = selectedCheckIds === null ? {} : { check_ids: Array.from(effectiveSelected) }
    setIsRechecking(true)
    try {
      await api.post(`/audit/${dumpId}/rerun`, body)
    } catch (err: any) {
      setIsRechecking(false)
      alert(`Re-run failed: ${err?.response?.data?.detail || err.message}`)
    }
  }

  // Filtered results for main table
  const filtered = results.filter((r) => {
    if (filterRisk && r.risk_level !== filterRisk) return false
    if (filterStatus && r.status !== filterStatus) return false
    if (activeCat && r.category !== activeCat) return false
    if (search && !r.description.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const catChartData = summary?.category_summary?.map((c: any) => ({
    name: c.category,
    fail: c.fail || 0,
    pass: c.pass || 0,
  }))

  const healthColor = summary?.audit_health_score >= 80 ? 'text-green-600'
    : summary?.audit_health_score >= 60 ? 'text-orange-500' : 'text-red-600'

  if (isLoading) return (
    <div className="flex items-center justify-center h-full text-gray-500 p-12">
      <Loader size={20} className="animate-spin mr-2" /> Loading audit report...
    </div>
  )
  if (!summary) return null

  return (
    <div className="flex" style={{ minHeight: '100vh' }}>

      {/* ── Left Checks Sidebar ──────────────────────────────────────── */}
      <aside
        className="w-56 flex-shrink-0 border-r border-gray-200 bg-gray-50 flex flex-col"
        style={{ position: 'sticky', top: 0, height: '100vh', overflowY: 'auto' }}
      >
        {/* Header */}
        <div className="px-3 py-3 border-b border-gray-200 bg-white">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-800">Checks</span>
            <button
              onClick={toggleAll}
              className="text-xs text-brand-600 hover:text-brand-800 font-medium"
            >
              {isAllSelected ? 'Deselect all' : 'Select all'}
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">{selectedCount} of {allIds.length} selected</p>
        </div>

        {/* All categories entry */}
        <button
          onClick={() => setActiveCat('')}
          className={clsx(
            'flex items-center justify-between w-full text-left px-3 py-2 text-xs font-medium border-b border-gray-100',
            activeCat === '' ? 'bg-brand-50 text-brand-700' : 'text-gray-600 hover:bg-gray-100'
          )}
        >
          <span>All Categories</span>
          <span className="text-gray-400">{results.length}</span>
        </button>

        {/* Category list */}
        <div className="flex-1 overflow-y-auto">
          {allCats.map((cat) => {
            const catResults = checksByCategory[cat] || []
            const state = getCatState(cat)
            const expanded = expandedCats.has(cat)
            const failCount = catResults.filter((r) => r.status === 'fail' || r.status === 'warning').length
            return (
              <div key={cat} className="border-b border-gray-100 last:border-b-0">
                {/* Category row */}
                <div className={clsx(
                  'flex items-center gap-1.5 px-2 py-2',
                  activeCat === cat ? 'bg-brand-50' : 'hover:bg-gray-100'
                )}>
                  {/* Select checkbox */}
                  <button onClick={() => toggleCat(cat)} className="flex-shrink-0 text-gray-400 hover:text-brand-600">
                    {state === 'all'
                      ? <CheckSquare size={13} className="text-brand-600" />
                      : state === 'some'
                      ? <MinusSquare size={13} className="text-brand-400" />
                      : <Square size={13} />}
                  </button>

                  {/* Category name (click = filter) */}
                  <button
                    onClick={() => setActiveCat(activeCat === cat ? '' : cat)}
                    className="flex-1 flex items-center justify-between text-left min-w-0"
                  >
                    <span className={clsx(
                      'text-xs font-medium truncate',
                      activeCat === cat ? 'text-brand-700' : 'text-gray-700'
                    )}>{cat}</span>
                    <div className="flex items-center gap-1 flex-shrink-0 ml-1">
                      {failCount > 0 && (
                        <span className="text-xs text-red-500 font-semibold">{failCount}</span>
                      )}
                    </div>
                  </button>

                  {/* Expand toggle */}
                  <button onClick={() => toggleExpand(cat)} className="flex-shrink-0 text-gray-400 hover:text-gray-600">
                    {expanded ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
                  </button>
                </div>

                {/* Individual checks */}
                {expanded && (
                  <div className="bg-white border-t border-gray-100">
                    {catResults.map((r) => (
                      <div
                        key={r.check_id}
                        onClick={() => toggleCheck(r.check_id)}
                        className="flex items-start gap-1.5 px-5 py-1.5 hover:bg-gray-50 cursor-pointer"
                      >
                        <div className="flex-shrink-0 mt-0.5 text-gray-400">
                          {effectiveSelected.has(r.check_id)
                            ? <CheckSquare size={11} className="text-brand-600" />
                            : <Square size={11} />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-gray-600 leading-snug line-clamp-2">{r.description}</p>
                          <div className="flex items-center gap-1 mt-0.5">
                            <span className={clsx(
                              'text-xs px-1 rounded',
                              r.status === 'fail' ? 'bg-red-100 text-red-600'
                                : r.status === 'warning' ? 'bg-yellow-100 text-yellow-600'
                                : r.status === 'pass' ? 'bg-green-100 text-green-600'
                                : 'bg-gray-100 text-gray-500'
                            )}>{r.status}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Footer — Re-run button */}
        <div className="border-t border-gray-200 p-3 bg-white">
          {isRechecking ? (
            <div className="flex items-center justify-center gap-2 text-xs text-purple-600 py-1">
              <Loader size={13} className="animate-spin" /> Rechecking...
            </div>
          ) : (
            <button
              onClick={handleRerun}
              disabled={selectedCount === 0}
              className="w-full flex items-center justify-center gap-1.5 text-xs font-medium bg-purple-600 hover:bg-purple-700 text-white rounded-lg py-2 transition-colors disabled:opacity-40"
            >
              <RotateCcw size={12} />
              {isAllSelected ? 'Re-run all checks' : `Re-run ${selectedCount} checks`}
            </button>
          )}
          {selectedCount === 0 && (
            <p className="text-xs text-center text-orange-500 mt-1.5">No checks selected</p>
          )}
        </div>
      </aside>

      {/* ── Main Content ────────────────────────────────────────────── */}
      <div className="flex-1 min-w-0 p-6 overflow-y-auto">

        {/* Back + header */}
        <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
          <ChevronLeft size={16} /> Back
        </button>

        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Audit Report</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {activeCat ? activeCat : `${results.length} checks across ${allCats.length} categories`}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {isRechecking && (
              <span className="text-xs text-purple-600 flex items-center gap-1">
                <Loader size={12} className="animate-spin" /> Rechecking...
              </span>
            )}
            <a href={`/api/exports/${dumpId}/excel`} className="btn-secondary text-xs">Export Excel</a>
          </div>
        </div>

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

        {/* Category Chart (hidden when filtering a specific category) */}
        {!activeCat && catChartData?.length > 0 && (
          <div className="card mb-6">
            <h3 className="font-semibold text-gray-800 mb-4 text-sm">Results by Category</h3>
            <ResponsiveContainer width="100%" height={Math.max(180, allCats.length * 22)}>
              <BarChart data={catChartData} layout="vertical" margin={{ left: 140, right: 20, top: 0, bottom: 0 }}>
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
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search checks..."
              className="pl-8 pr-3 py-2 border rounded-lg text-sm w-56 focus:ring-2 focus:ring-brand-500 focus:outline-none"
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
                <tr><td colSpan={7} className="text-center py-10 text-gray-400 text-sm">No checks match the current filters</td></tr>
              ) : filtered.map((r: any) => (
                <tr
                  key={r.check_id}
                  className={clsx(
                    'hover:bg-gray-50',
                    r.status === 'fail' && 'bg-red-50/30',
                    r.status === 'warning' && 'bg-yellow-50/30',
                  )}
                >
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
    </div>
  )
}
