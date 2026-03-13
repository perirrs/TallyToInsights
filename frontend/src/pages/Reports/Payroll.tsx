import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import PageHeader from '../../components/UI/PageHeader'
import KPICard from '../../components/UI/KPICard'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const INR = (v: number) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(v)

export default function PayrollPage() {
  const { dumpId } = useParams<{ dumpId: string }>()
  const { data, isLoading } = useQuery({
    queryKey: ['payroll', dumpId],
    queryFn: () => api.get(`/reports/${dumpId}/payroll`).then((r) => r.data),
  })

  if (isLoading) return <div className="p-6 text-gray-500">Loading payroll...</div>
  if (!data) return null

  return (
    <div className="p-6">
      <PageHeader title="Payroll Report" subtitle="Salary register and employee summary" />

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <KPICard title="Total Salary Paid" value={`₹${INR(data.total_salary)}`} color="blue" />
        <KPICard title="Total Vouchers" value={data.total_vouchers} color="purple" />
        <KPICard title="Employees" value={data.employee_summary?.length || 0} color="green" />
      </div>

      {data.monthly_salary?.length > 0 && (
        <div className="card mb-6">
          <h3 className="font-semibold text-gray-800 mb-4">Monthly Salary Trend</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data.monthly_salary}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${(v / 100000).toFixed(0)}L`} />
              <Tooltip formatter={(v: number) => `₹${INR(v)}`} />
              <Bar dataKey="total" name="Salary" fill="#1A56DB" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {data.employee_summary?.length > 0 && (
        <div className="card">
          <h3 className="font-semibold text-gray-800 mb-3">Employee Salary Summary</h3>
          <table className="w-full text-xs">
            <thead><tr className="bg-gray-50 border-b">
              <th className="text-left px-3 py-2">Employee</th>
              <th className="text-right px-3 py-2">Total Paid</th>
              <th className="text-right px-3 py-2">Months</th>
              <th className="text-right px-3 py-2">Avg/Month</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-50">
              {data.employee_summary.map((e: any, i: number) => (
                <tr key={i}>
                  <td className="px-3 py-1.5 font-medium text-gray-800">{e.employee}</td>
                  <td className="px-3 py-1.5 text-right">₹{INR(e.total)}</td>
                  <td className="px-3 py-1.5 text-right">{e.months}</td>
                  <td className="px-3 py-1.5 text-right">₹{INR(e.total / (e.months || 1))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
