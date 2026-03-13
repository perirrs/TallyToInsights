import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import PageHeader from '../../components/UI/PageHeader'
import { Search } from 'lucide-react'

const INR = (v: number) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(v)

export default function VouchersPage() {
  const { dumpId } = useParams<{ dumpId: string }>()
  const [page, setPage] = useState(1)
  const [vtype, setVtype] = useState('')
  const [party, setParty] = useState('')
  const [minAmt, setMinAmt] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['vouchers', dumpId, page, vtype, party, minAmt],
    queryFn: () => api.get(`/reports/${dumpId}/vouchers`, {
      params: { page, voucher_type: vtype || undefined, party: party || undefined, min_amount: minAmt || undefined }
    }).then((r) => r.data),
  })

  return (
    <div className="p-6">
      <PageHeader title="Vouchers" subtitle="Transaction drill-down with filters" />

      <div className="flex flex-wrap gap-3 mb-4">
        <input value={vtype} onChange={(e) => { setVtype(e.target.value); setPage(1) }}
          placeholder="Voucher Type" className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none w-36" />
        <input value={party} onChange={(e) => { setParty(e.target.value); setPage(1) }}
          placeholder="Party name..." className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none w-48" />
        <input value={minAmt} onChange={(e) => { setMinAmt(e.target.value); setPage(1) }}
          placeholder="Min amount" type="number" className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none w-36" />
        {data && <span className="text-xs text-gray-500 self-center">{data.total?.toLocaleString()} vouchers</span>}
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
