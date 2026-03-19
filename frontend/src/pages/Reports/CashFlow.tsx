import { useParams, useNavigate } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import PageHeader from '../../components/UI/PageHeader'
import KPICard from '../../components/UI/KPICard'
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const INR = (v: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)

export default function CashFlowPage() {
  const { dumpId } = useParams<{ dumpId: string }>()
  const navigate = useNavigate()
  const { data: cf, isLoading } = useQuery({
    queryKey: ['cashflow', dumpId],
    queryFn: () => api.get(`/reports/${dumpId}/cashflow`).then((r) => r.data),
  })

  if (isLoading) return <div className="p-6 text-gray-500">Loading cash flow...</div>
  if (!cf) return null

  return (
    <div className="p-6">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ChevronLeft size={16} /> Back
      </button>
      <PageHeader title="Cash Flow Report" subtitle="Bank and cash movement analysis" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KPICard title="Opening Balance" value={INR(cf.opening_balance)} color="blue" />
        <KPICard title="Total Inflow" value={INR(cf.total_inflow)} color="green" />
        <KPICard title="Total Outflow" value={INR(cf.total_outflow)} color="red" />
        <KPICard title="Closing Balance" value={INR(cf.closing_balance)} color={cf.closing_balance >= 0 ? 'green' : 'red'} />
      </div>

      <div className="card mb-6">
        <h3 className="font-semibold text-gray-800 mb-4">Monthly Cash Flow</h3>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={cf.monthly_summary || []}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${(v / 100000).toFixed(0)}L`} />
            <Tooltip formatter={(v: number) => INR(v)} />
            <Legend />
            <Bar dataKey="inflow" name="Inflow" fill="#16A34A" />
            <Bar dataKey="outflow" name="Outflow" fill="#DC2626" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h3 className="font-semibold text-gray-800 mb-4">Running Balance</h3>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={cf.daily_items?.slice(-90) || []}>
            <defs>
              <linearGradient id="balGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#1A56DB" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#1A56DB" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 9 }} />
            <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `₹${(v / 100000).toFixed(0)}L`} />
            <Tooltip formatter={(v: number) => INR(v)} />
            <Area type="monotone" dataKey="balance" stroke="#1A56DB" fill="url(#balGrad)" name="Balance" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
