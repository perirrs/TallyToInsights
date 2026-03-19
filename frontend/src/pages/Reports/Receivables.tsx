import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import PageHeader from '../../components/UI/PageHeader'

const INR = (v: number) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(v)

function AgingTable({
  dumpId, type, partySearch, agingBucket, sortBy,
}: {
  dumpId: string
  type: 'receivables' | 'payables'
  partySearch: string
  agingBucket: string
  sortBy: string
}) {
  const { data, isLoading } = useQuery({
    queryKey: [type, dumpId],
    queryFn: () => api.get(`/reports/${dumpId}/${type}`).then((r) => r.data),
  })

  const filtered = useMemo(() => {
    if (!data) return []
    let rows = [...(data.buckets || [])]

    if (partySearch) {
      rows = rows.filter((b: any) => b.party.toLowerCase().includes(partySearch.toLowerCase()))
    }

    if (agingBucket === 'current') {
      rows = rows.filter((b: any) => b.current > 0)
    } else if (agingBucket === '30') {
      rows = rows.filter((b: any) => b.days_1_30 > 0)
    } else if (agingBucket === '60') {
      rows = rows.filter((b: any) => b.days_31_60 > 0)
    } else if (agingBucket === '90plus') {
      rows = rows.filter((b: any) => b.days_90_plus > 0)
    }

    if (sortBy === 'amount_desc') {
      rows.sort((a: any, b: any) => b.total - a.total)
    } else if (sortBy === 'amount_asc') {
      rows.sort((a: any, b: any) => a.total - b.total)
    } else if (sortBy === 'overdue_desc') {
      rows.sort((a: any, b: any) => (b.days_90_plus + b.days_61_90) - (a.days_90_plus + a.days_61_90))
    }

    return rows
  }, [data, partySearch, agingBucket, sortBy])

  if (isLoading) return <div className="text-gray-500 p-4">Loading...</div>
  if (!data) return null

  const title = type === 'receivables' ? 'Receivables Aging' : 'Payables Aging'

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-800">{title}</h3>
        <div className="text-right">
          <p className="text-lg font-bold text-gray-900">₹{INR(data.total_outstanding)}</p>
          <p className="text-xs text-red-600">₹{INR(data.overdue_amount)} overdue</p>
        </div>
      </div>
      <p className="text-xs text-gray-500 mb-3">{filtered.length} of {data.buckets?.length || 0} parties shown</p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-50 border-b">
              <th className="text-left px-3 py-2">Party</th>
              <th className="text-right px-3 py-2">Current</th>
              <th className="text-right px-3 py-2">1-30d</th>
              <th className="text-right px-3 py-2">31-60d</th>
              <th className="text-right px-3 py-2">61-90d</th>
              <th className="text-right px-3 py-2 text-red-700">90+d</th>
              <th className="text-right px-3 py-2 font-bold">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {filtered.map((b: any, i: number) => (
              <tr key={i} className={b.days_90_plus > 0 ? 'bg-red-50' : ''}>
                <td className="px-3 py-1.5 font-medium text-gray-800 max-w-[200px] truncate">{b.party}</td>
                <td className="px-3 py-1.5 text-right text-gray-600">{b.current > 0 ? INR(b.current) : '—'}</td>
                <td className="px-3 py-1.5 text-right text-gray-600">{b.days_1_30 > 0 ? INR(b.days_1_30) : '—'}</td>
                <td className="px-3 py-1.5 text-right text-orange-700">{b.days_31_60 > 0 ? INR(b.days_31_60) : '—'}</td>
                <td className="px-3 py-1.5 text-right text-red-700">{b.days_61_90 > 0 ? INR(b.days_61_90) : '—'}</td>
                <td className="px-3 py-1.5 text-right text-red-800 font-semibold">{b.days_90_plus > 0 ? INR(b.days_90_plus) : '—'}</td>
                <td className="px-3 py-1.5 text-right font-bold">{INR(b.total)}</td>
              </tr>
            ))}
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

  return (
    <div className="p-6">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ChevronLeft size={16} /> Back
      </button>
      <PageHeader title="Receivables & Payables" subtitle="Aging analysis and outstanding balances" />

      {/* Drill-down Filters */}
      <div className="card mb-5 py-3">
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Search Party</label>
            <input
              value={partySearch}
              onChange={(e) => setPartySearch(e.target.value)}
              placeholder="Party name..."
              className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none w-48"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Aging Bucket</label>
            <select
              value={agingBucket}
              onChange={(e) => setAgingBucket(e.target.value)}
              className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none"
            >
              <option value="">All buckets</option>
              <option value="current">Current (0 days)</option>
              <option value="30">1-30 days</option>
              <option value="60">31-60 days</option>
              <option value="90plus">90+ days overdue</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Sort By</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none"
            >
              <option value="amount_desc">Highest Amount</option>
              <option value="amount_asc">Lowest Amount</option>
              <option value="overdue_desc">Most Overdue</option>
            </select>
          </div>
          {(partySearch || agingBucket) && (
            <button
              onClick={() => { setPartySearch(''); setAgingBucket('') }}
              className="text-xs text-gray-500 hover:text-gray-700 underline self-end pb-1.5"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      <div className="space-y-6">
        <AgingTable dumpId={dumpId!} type="receivables" partySearch={partySearch} agingBucket={agingBucket} sortBy={sortBy} />
        <AgingTable dumpId={dumpId!} type="payables" partySearch={partySearch} agingBucket={agingBucket} sortBy={sortBy} />
      </div>
    </div>
  )
}
