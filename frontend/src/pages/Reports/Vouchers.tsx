import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import PageHeader from '../../components/UI/PageHeader'

const INR = (v: number) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(v)

export default function VouchersPage() {
  const { dumpId } = useParams<{ dumpId: string }>()
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [vtype, setVtype] = useState('')
  const [party, setParty] = useState('')
  const [minAmt, setMinAmt] = useState('')
  const [maxAmt, setMaxAmt] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['vouchers', dumpId, page, vtype, party, minAmt, maxAmt, dateFrom, dateTo],
    queryFn: () => api.get(`/reports/${dumpId}/vouchers`, {
      params: {
        page,
        voucher_type: vtype || undefined,
        party: party || undefined,
        min_amount: minAmt || undefined,
        max_amount: maxAmt || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      }
    }).then((r) => r.data),
  })

  const resetFilters = () => {
    setVtype(''); setParty(''); setMinAmt(''); setMaxAmt(''); setDateFrom(''); setDateTo(''); setPage(1)
  }

  const hasFilters = vtype || party || minAmt || maxAmt || dateFrom || dateTo

  return (
    <div className="p-6">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ChevronLeft size={16} /> Back
      </button>
      <PageHeader title="Vouchers" subtitle="Transaction drill-down with filters" />

      <div className="card mb-4 py-3">
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Voucher Type</label>
            <input value={vtype} onChange={(e) => { setVtype(e.target.value); setPage(1) }}
              placeholder="e.g. Sales" className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none w-36" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Party / Ledger</label>
            <input value={party} onChange={(e) => { setParty(e.target.value); setPage(1) }}
              placeholder="Party name..." className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none w-44" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Date From</label>
            <input type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1) }}
              className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Date To</label>
            <input type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1) }}
              className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Min Amount</label>
            <input value={minAmt} onChange={(e) => { setMinAmt(e.target.value); setPage(1) }}
              placeholder="0" type="number" className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none w-28" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Max Amount</label>
            <input value={maxAmt} onChange={(e) => { setMaxAmt(e.target.value); setPage(1) }}
              placeholder="Any" type="number" className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none w-28" />
          </div>
          {hasFilters && (
            <button onClick={resetFilters} className="text-xs text-gray-500 hover:text-gray-700 underline self-end pb-1.5">
              Clear filters
            </button>
          )}
          {data && <span className="text-xs text-gray-500 self-end pb-1.5">{data.total?.toLocaleString()} vouchers</span>}
        </div>
      </div>

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-50 border-b">
              {['Voucher No', 'Type', 'Date', 'Party', 'Narration', 'Amount', 'Posted By'].map(h => (
                <th key={h} className="px-3 py-2.5 text-left font-semibold text-gray-600">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={7} className="text-center py-8 text-gray-400">Loading...</td></tr>
            ) : (
              data?.items?.map((v: any) => (
                <tr key={v.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-mono text-gray-600">{v.voucher_number || '—'}</td>
                  <td className="px-3 py-2 text-gray-700">{v.voucher_type}</td>
                  <td className="px-3 py-2 text-gray-600">{v.date}</td>
                  <td className="px-3 py-2 max-w-[150px] truncate text-gray-800">{v.party_ledger || '—'}</td>
                  <td className="px-3 py-2 max-w-[200px] truncate text-gray-500">{v.narration || '—'}</td>
                  <td className="px-3 py-2 text-right font-medium text-gray-900">₹{INR(v.amount)}</td>
                  <td className="px-3 py-2 text-gray-500">{v.posted_by || '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {data && (
        <div className="flex items-center justify-between mt-4 text-sm text-gray-600">
          <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="btn-secondary text-xs disabled:opacity-40">← Prev</button>
          <span>Page {page} of {Math.ceil(data.total / data.page_size)}</span>
          <button disabled={page >= Math.ceil(data.total / data.page_size)} onClick={() => setPage(p => p + 1)} className="btn-secondary text-xs disabled:opacity-40">Next →</button>
        </div>
      )}
    </div>
  )
}
