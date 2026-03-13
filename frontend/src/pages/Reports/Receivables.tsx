import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import PageHeader from '../../components/UI/PageHeader'
import KPICard from '../../components/UI/KPICard'

const INR = (v: number) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(v)

function AgingTable({ dumpId, type }: { dumpId: string; type: 'receivables' | 'payables' }) {
  const { data, isLoading } = useQuery({
    queryKey: [type, dumpId],
    queryFn: () => api.get(`/reports/${dumpId}/${type}`).then((r) => r.data),
  })

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
            {data.buckets.map((b: any, i: number) => (
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
  return (
    <div className="p-6">
      <PageHeader title="Receivables & Payables" subtitle="Aging analysis and outstanding balances" />
      <div className="space-y-6">
        <AgingTable dumpId={dumpId!} type="receivables" />
        <AgingTable dumpId={dumpId!} type="payables" />
      </div>
    </div>
  )
}
