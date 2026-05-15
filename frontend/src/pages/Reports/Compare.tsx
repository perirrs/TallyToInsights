import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import PageHeader from '../../components/UI/PageHeader'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const INR = (v: number) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(v)

export default function ComparePage() {
  const { companyId } = useParams<{ companyId: string }>()
  const [selected, setSelected] = useState<number[]>([])

  const { data: dumps = [] } = useQuery({
    queryKey: ['dumps', companyId],
    queryFn: () => api.get(`/uploads/${companyId}`).then((r) => r.data.filter((d: any) => d.status === 'processed')),
  })

  const { data: comparison, isLoading } = useQuery({
    queryKey: ['compare', companyId, selected],
    queryFn: () => api.get(`/reports/compare/${companyId}`, { params: { dump_ids: selected } }).then((r) => r.data),
    enabled: selected.length >= 2,
  })

  const toggleDump = (id: number) => {
    setSelected((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id])
  }

  const chartData = comparison?.periods?.map((period: string, i: number) => ({
    period,
    Revenue: comparison.revenue[i],
    Expenses: comparison.expenses[i],
    'Net Profit': comparison.net_profit[i],
  })) || []

  return (
    <div className="p-6">
      <PageHeader title="Period Comparison" subtitle="Compare financial performance across years" />

      <div className="card mb-6">
        <h3 className="font-semibold text-gray-800 mb-3">Select Periods to Compare (min 2)</h3>
        <div className="flex flex-wrap gap-2">
          {dumps.map((d: any) => (
            <button
              key={d.id}
              onClick={() => toggleDump(d.id)}
              className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                selected.includes(d.id)
                  ? 'bg-brand-600 text-white border-brand-600'
                  : 'bg-white text-gray-700 border-gray-300 hover:border-brand-400'
              }`}
            >
              {d.financial_year || d.period_from || `Dump #${d.id}`}
            </button>
          ))}
        </div>
      </div>

      {selected.length < 2 && (
        <div className="text-center py-8 text-gray-400">Select at least 2 periods above to compare.</div>
      )}

      {comparison && (
        <>
          <div className="card mb-6">
            <h3 className="font-semibold text-gray-800 mb-4">Revenue vs Expenses vs Net Profit</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${(v / 100000).toFixed(0)}L`} />
                <Tooltip formatter={(v: number) => `₹${INR(v)}`} />
                <Legend />
                <Bar dataKey="Revenue" fill="#1A56DB" />
                <Bar dataKey="Expenses" fill="#EA580C" />
                <Bar dataKey="Net Profit" fill="#16A34A" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card overflow-x-auto">
            <h3 className="font-semibold text-gray-800 mb-4">Comparative Summary</h3>
            <table className="w-full text-sm">
              <thead><tr className="bg-gray-50 border-b">
                <th className="text-left px-4 py-2">Metric</th>
                {comparison.periods.map((p: string) => (
                  <th key={p} className="text-right px-4 py-2 text-gray-700">{p}</th>
                ))}
              </tr></thead>
              <tbody className="divide-y divide-gray-100">
                {[
                  ['Revenue', comparison.revenue],
                  ['Expenses', comparison.expenses],
                  ['Net Profit', comparison.net_profit],
                  ['Gross Margin %', comparison.gross_margin],
                  ['Total Assets', comparison.total_assets],
                  ['Total Liabilities', comparison.total_liabilities],
                ].map(([label, values]) => (
                  <tr key={label as string}>
                    <td className="px-4 py-2 font-medium text-gray-800">{label as string}</td>
                    {(values as number[]).map((v, i) => (
                      <td key={i} className="px-4 py-2 text-right text-gray-700">
                        {typeof v === 'number' && v > 1000 ? `₹${INR(v)}` : v}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
