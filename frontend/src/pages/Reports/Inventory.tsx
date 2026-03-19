import { useParams, useNavigate } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import PageHeader from '../../components/UI/PageHeader'
import KPICard from '../../components/UI/KPICard'

const INR = (v: number) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(v)

export default function InventoryPage() {
  const { dumpId } = useParams<{ dumpId: string }>()
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({
    queryKey: ['inventory', dumpId],
    queryFn: () => api.get(`/reports/${dumpId}/inventory`).then((r) => r.data),
  })

  if (isLoading) return <div className="p-6 text-gray-500">Loading inventory...</div>
  if (!data) return null

  return (
    <div className="p-6">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ChevronLeft size={16} /> Back
      </button>
      <PageHeader title="Inventory Report" subtitle="Stock summary, slow-moving & negative stock" />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KPICard title="Total Items" value={data.total_items} color="blue" />
        <KPICard title="Opening Value" value={`₹${INR(data.total_opening_value)}`} color="blue" />
        <KPICard title="Closing Value" value={`₹${INR(data.total_closing_value)}`} color="green" />
        <KPICard title="Negative Stock" value={data.negative_stock_items?.length || 0} color="red" />
      </div>

      {data.negative_stock_items?.length > 0 && (
        <div className="card mb-6 border-red-200 bg-red-50">
          <h3 className="font-semibold text-red-800 mb-3">⚠ Negative Stock Items</h3>
          <table className="w-full text-xs">
            <thead><tr className="border-b">
              <th className="text-left py-1.5 text-red-700">Item</th>
              <th className="text-right py-1.5 text-red-700">Closing Qty</th>
              <th className="text-right py-1.5 text-red-700">Value</th>
            </tr></thead>
            <tbody>
              {data.negative_stock_items.map((i: any, idx: number) => (
                <tr key={idx}><td className="py-1">{i.name}</td><td className="py-1 text-right text-red-800 font-bold">{i.closing_qty}</td><td className="py-1 text-right">{INR(i.closing_value)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="card">
        <h3 className="font-semibold text-gray-800 mb-3">Stock Register (Top 100 by Value)</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead><tr className="bg-gray-50 border-b">
              <th className="text-left px-3 py-2">Item</th>
              <th className="text-left px-3 py-2">Group</th>
              <th className="text-left px-3 py-2">Unit</th>
              <th className="text-right px-3 py-2">Opening Qty</th>
              <th className="text-right px-3 py-2">Opening Val</th>
              <th className="text-right px-3 py-2">Closing Qty</th>
              <th className="text-right px-3 py-2">Closing Val</th>
              <th className="text-right px-3 py-2">Avg Rate</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-50">
              {data.items?.map((i: any, idx: number) => (
                <tr key={idx} className={i.is_negative ? 'bg-red-50' : ''}>
                  <td className="px-3 py-1.5 font-medium text-gray-800">{i.name}</td>
                  <td className="px-3 py-1.5 text-gray-500">{i.group || '—'}</td>
                  <td className="px-3 py-1.5 text-gray-500">{i.unit || '—'}</td>
                  <td className="px-3 py-1.5 text-right">{i.opening_qty}</td>
                  <td className="px-3 py-1.5 text-right">{INR(i.opening_value)}</td>
                  <td className={`px-3 py-1.5 text-right font-medium ${i.is_negative ? 'text-red-700' : ''}`}>{i.closing_qty}</td>
                  <td className="px-3 py-1.5 text-right font-medium">{INR(i.closing_value)}</td>
                  <td className="px-3 py-1.5 text-right text-gray-600">{INR(i.avg_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
