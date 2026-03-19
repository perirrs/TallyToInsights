/**
 * Receivables & Payables — Aging Analysis
 * ─────────────────────────────────────────
 * Drill-down layers:
 *   Aging summary KPIs
 *   → Aging table (filterable by bucket, party, sort)
 *     → Click party row → DrillVouchers (all vouchers for that party)
 *       → VoucherModal (full detail)
 */
import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ChevronLeft, ExternalLink, AlertCircle } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import PageHeader from '../../components/UI/PageHeader'
import KPICard from '../../components/UI/KPICard'
import DrillVouchers, { DrillFilters } from '../../components/DrillVouchers'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'

const INR = (v: number) =>
  new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(v)

function AgingKPIs({ data, type }: { data: any; type: string }) {
  if (!data) return null
  const label = type === 'receivables' ? 'Receivable' : 'Payable'
  const chartData = [
    { name: 'Current',  value: data.buckets?.reduce((s: number, b: any) => s + b.current, 0) ?? 0 },
    { name: '1-30d',    value: data.buckets?.reduce((s: number, b: any) => s + b.days_1_30, 0) ?? 0 },
    { name: '31-60d',   value: data.buckets?.reduce((s: number, b: any) => s + b.days_31_60, 0) ?? 0 },
    { name: '61-90d',   value: data.buckets?.reduce((s: number, b: any) => s + b.days_61_90, 0) ?? 0 },
    { name: '90+d',     value: data.buckets?.reduce((s: number, b: any) => s + b.days_90_plus, 0) ?? 0 },
  ]
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
      <KPICard title={`Total ${label}`} value={`₹${INR(data.total_outstanding)}`} color="blue" />
      <KPICard title="Current" value={`₹${INR(chartData[0].value)}`} color="green" />
      <KPICard title="1-30 Days" value={`₹${INR(chartData[1].value)}`} color="blue" />
      <KPICard title="31-90 Days" value={`₹${INR(chartData[2].value + chartData[3].value)}`} color="orange" />
      <KPICard title="90+ Days (Overdue)" value={`₹${INR(data.overdue_amount)}`} color="red" />
    </div>
  )
}

function AgingTable({
  dumpId, type, partySearch, agingBucket, sortBy, onDrillParty,
}: {
  dumpId: string
  type: 'receivables' | 'payables'
  partySearch: string
  agingBucket: string
  sortBy: string
  onDrillParty: (party: string) => void
}) {
  const { data, isLoading } = useQuery({
    queryKey: [type, dumpId],
    queryFn: () => api.get(`/reports/${dumpId}/${type}`).then((r) => r.data),
  })

  const filtered = useMemo(() => {
    if (!data) return []
    let rows = [...(data.buckets || [])]
    if (partySearch) rows = rows.filter((b: any) => b.party.toLowerCase().includes(partySearch.toLowerCase()))
    if (agingBucket === 'current')  rows = rows.filter((b: any) => b.current > 0)
    if (agingBucket === '30')       rows = rows.filter((b: any) => b.days_1_30 > 0)
    if (agingBucket === '60')       rows = rows.filter((b: any) => b.days_31_60 > 0)
    if (agingBucket === '90plus')   rows = rows.filter((b: any) => b.days_90_plus > 0)
    if (sortBy === 'amount_desc')   rows.sort((a: any, b: any) => b.total - a.total)
    if (sortBy === 'amount_asc')    rows.sort((a: any, b: any) => a.total - b.total)
    if (sortBy === 'overdue_desc')  rows.sort((a: any, b: any) => (b.days_90_plus + b.days_61_90) - (a.days_90_plus + a.days_61_90))
    return rows
  }, [data, partySearch, agingBucket, sortBy])

  const title = type === 'receivables' ? 'Receivables Aging' : 'Payables Aging'

  if (isLoading) {
    return (
      <div className="card">
        <h3 className="font-semibold text-gray-800 mb-4">{title}</h3>
        <div className="space-y-2">
          {[1,2,3,4].map(i => <div key={i} className="h-8 bg-gray-100 animate-pulse rounded" />)}
        </div>
      </div>
    )
  }
  if (!data) return null

  // Aggregate bar chart for aging buckets
  const agingChart = [
    { name: 'Current', value: filtered.reduce((s: number, b: any) => s + b.current, 0) },
    { name: '1-30d',   value: filtered.reduce((s: number, b: any) => s + b.days_1_30, 0) },
    { name: '31-60d',  value: filtered.reduce((s: number, b: any) => s + b.days_31_60, 0) },
    { name: '61-90d',  value: filtered.reduce((s: number, b: any) => s + b.days_61_90, 0) },
    { name: '90+d',    value: filtered.reduce((s: number, b: any) => s + b.days_90_plus, 0) },
  ]
  const agingColors = ['#16A34A', '#1A56DB', '#EA580C', '#DC2626', '#7F1D1D']

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-800">{title}</h3>
        <div className="text-right">
          <p className="text-lg font-bold text-gray-900">₹{INR(data.total_outstanding)}</p>
          {data.overdue_amount > 0 && (
            <p className="text-xs text-red-600 flex items-center gap-1 justify-end">
              <AlertCircle size={11} /> ₹{INR(data.overdue_amount)} overdue
            </p>
          )}
        </div>
      </div>

      {/* Aging distribution chart */}
      <div className="mb-4">
        <ResponsiveContainer width="100%" height={120}>
          <BarChart data={agingChart} layout="vertical" margin={{ left: 20 }}>
            <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v) => `₹${(v/100000).toFixed(0)}L`} />
            <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={45} />
            <Tooltip formatter={(v: number) => `₹${INR(v)}`} />
            <Bar dataKey="value" radius={[0,3,3,0]}>
              {agingChart.map((_, i) => (
                <Bar key={i} dataKey="value" fill={agingColors[i]} />
              ))}
              {agingChart.map((_, i) => (
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                <rect key={`cell-${i}`} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <p className="text-xs text-gray-400 mb-2">
        {filtered.length} of {data.buckets?.length || 0} parties shown ·{' '}
        <span className="text-blue-500">Click any party to see their transactions</span>
      </p>

      <div className="overflow-x-auto rounded-xl border">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-50 border-b">
              <th className="text-left px-3 py-2.5 text-gray-600">Party</th>
              <th className="text-right px-3 py-2.5 text-gray-600">Current</th>
              <th className="text-right px-3 py-2.5 text-gray-600">1-30d</th>
              <th className="text-right px-3 py-2.5 text-orange-600">31-60d</th>
              <th className="text-right px-3 py-2.5 text-red-600">61-90d</th>
              <th className="text-right px-3 py-2.5 text-red-800 font-bold">90+d</th>
              <th className="text-right px-3 py-2.5 font-bold text-gray-700">Total</th>
              <th className="w-6" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {filtered.map((b: any, i: number) => {
              const isOverdue = b.days_90_plus > 0
              const isWarning = b.days_61_90 > 0
              return (
                <tr
                  key={i}
                  className={`cursor-pointer transition-colors group ${
                    isOverdue ? 'bg-red-50 hover:bg-red-100' :
                    isWarning ? 'bg-orange-50 hover:bg-orange-100' :
                    'hover:bg-blue-50'
                  }`}
                  onClick={() => onDrillParty(b.party)}
                >
                  <td className="px-3 py-2 font-medium text-gray-800 max-w-[180px]">
                    <div className="flex items-center gap-1 truncate">
                      {b.party}
                      <ExternalLink size={11} className="text-gray-300 group-hover:text-blue-500 flex-shrink-0" />
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right text-gray-600">{b.current > 0 ? `₹${INR(b.current)}` : '—'}</td>
                  <td className="px-3 py-2 text-right text-gray-600">{b.days_1_30 > 0 ? `₹${INR(b.days_1_30)}` : '—'}</td>
                  <td className="px-3 py-2 text-right text-orange-700">{b.days_31_60 > 0 ? `₹${INR(b.days_31_60)}` : '—'}</td>
                  <td className="px-3 py-2 text-right text-red-700">{b.days_61_90 > 0 ? `₹${INR(b.days_61_90)}` : '—'}</td>
                  <td className="px-3 py-2 text-right text-red-800 font-bold">{b.days_90_plus > 0 ? `₹${INR(b.days_90_plus)}` : '—'}</td>
                  <td className="px-3 py-2 text-right font-bold text-gray-900">₹{INR(b.total)}</td>
                  <td className="pr-2 text-gray-300 group-hover:text-blue-400">›</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function ReceivablesPage() {
  const { dumpId } = useParams<{ dumpId: string }>()
  const navigate = useNavigate()

  const [partySearch, setPartySearch] = useState('')
  const [agingBucket, setAgingBucket] = useState('')
  const [sortBy, setSortBy] = useState('amount_desc')
  const [drill, setDrill] = useState<{ filters: DrillFilters; title: string } | null>(null)

  return (
    <div className="p-6">
      <button onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ChevronLeft size={16} /> Back
      </button>
      <PageHeader title="Receivables & Payables" subtitle="Aging analysis — click any party to drill into their transactions" />

      {/* Filters */}
      <div className="card mb-5 py-3">
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Search Party</label>
            <input value={partySearch} onChange={(e) => setPartySearch(e.target.value)}
              placeholder="Party name…"
              className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none w-48" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Aging Bucket</label>
            <select value={agingBucket} onChange={(e) => setAgingBucket(e.target.value)}
              className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none">
              <option value="">All buckets</option>
              <option value="current">Current (0 days)</option>
              <option value="30">1-30 days</option>
              <option value="60">31-60 days</option>
              <option value="90plus">90+ days (overdue)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Sort By</label>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}
              className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none">
              <option value="amount_desc">Highest Amount</option>
              <option value="amount_asc">Lowest Amount</option>
              <option value="overdue_desc">Most Overdue First</option>
            </select>
          </div>
          {(partySearch || agingBucket) && (
            <button onClick={() => { setPartySearch(''); setAgingBucket('') }}
              className="text-xs text-gray-400 hover:text-gray-600 underline self-end pb-1.5">
              Clear filters
            </button>
          )}
        </div>
      </div>

      <div className="space-y-6">
        <AgingTable dumpId={dumpId!} type="receivables" partySearch={partySearch}
          agingBucket={agingBucket} sortBy={sortBy}
          onDrillParty={(party) => setDrill({
            filters: { ledger_name: party },
            title: `${party} — Receivable Transactions`,
          })} />
        <AgingTable dumpId={dumpId!} type="payables" partySearch={partySearch}
          agingBucket={agingBucket} sortBy={sortBy}
          onDrillParty={(party) => setDrill({
            filters: { ledger_name: party },
            title: `${party} — Payable Transactions`,
          })} />
      </div>

      {drill && (
        <DrillVouchers
          dumpId={dumpId!}
          title={drill.title}
          subtitle="All transactions for this party — click for full voucher detail"
          filters={drill.filters}
          onClose={() => setDrill(null)}
        />
      )}
    </div>
  )
}
