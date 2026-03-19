import { useParams, useNavigate } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import PageHeader from '../../components/UI/PageHeader'
import KPICard from '../../components/UI/KPICard'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const INR = (v: number) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(v)

export default function GSTPage() {
  const { dumpId } = useParams<{ dumpId: string }>()
  const navigate = useNavigate()
  const { data: gst, isLoading } = useQuery({
    queryKey: ['gst', dumpId],
    queryFn: () => api.get(`/reports/${dumpId}/gst`).then((r) => r.data),
  })

  if (isLoading) return <div className="p-6 text-gray-500">Loading GST report...</div>
  if (!gst) return null

  return (
    <div className="p-6">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ChevronLeft size={16} /> Back
      </button>
      <PageHeader title="GST Report" subtitle="Monthly GST summary with ITC reconciliation" />

      <div className="grid grid-cols-3 gap-4 mb-6">
        <KPICard title="Total Output Tax" value={`₹${INR(gst.total_output_tax)}`} color="orange" />
        <KPICard title="Total ITC" value={`₹${INR(gst.total_itc)}`} color="green" />
        <KPICard title="Net GST Payable" value={`₹${INR(gst.net_payable)}`} color={gst.net_payable > 0 ? 'red' : 'green'} />
      </div>

      <div className="card mb-6">
        <h3 className="font-semibold text-gray-800 mb-4">Monthly GST Overview</h3>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={gst.monthly_summary || []}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v: number) => `₹${INR(v)}`} />
            <Legend />
            <Bar dataKey="total_tax" name="Output GST" fill="#EA580C" />
            <Bar dataKey="total_itc" name="ITC" fill="#16A34A" />
            <Bar dataKey="net_liability" name="Net Liability" fill="#1A56DB" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card overflow-x-auto">
        <h3 className="font-semibold text-gray-800 mb-4">Monthly Breakup</h3>
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-50 border-b">
              {['Month', 'Taxable Sales', 'CGST', 'SGST', 'IGST', 'Output Total', 'Taxable Purch', 'ITC Total', 'Net Liability'].map(h => (
                <th key={h} className="px-3 py-2 text-right first:text-left font-semibold text-gray-600">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {gst.monthly_summary?.map((m: any, i: number) => (
              <tr key={i}>
                <td className="px-3 py-1.5 font-medium">{m.month}</td>
                <td className="px-3 py-1.5 text-right">{INR(m.taxable_sales)}</td>
                <td className="px-3 py-1.5 text-right">{INR(m.cgst_collected)}</td>
                <td className="px-3 py-1.5 text-right">{INR(m.sgst_collected)}</td>
                <td className="px-3 py-1.5 text-right">{INR(m.igst_collected)}</td>
                <td className="px-3 py-1.5 text-right font-medium text-orange-700">{INR(m.total_tax)}</td>
                <td className="px-3 py-1.5 text-right">{INR(m.taxable_purchases)}</td>
                <td className="px-3 py-1.5 text-right font-medium text-green-700">{INR(m.total_itc)}</td>
                <td className={`px-3 py-1.5 text-right font-bold ${m.net_liability > 0 ? 'text-red-700' : 'text-green-700'}`}>
                  {INR(m.net_liability)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
