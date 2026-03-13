import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import PageHeader from '../../components/UI/PageHeader'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend } from 'recharts'
import KPICard from '../../components/UI/KPICard'

const INR = (v: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)
const COLORS = ['#1A56DB', '#16A34A', '#EA580C', '#7C3AED', '#DB2777', '#0891B2', '#854D0E', '#065F46']

export default function FinancialPage() {
  const { dumpId } = useParams<{ dumpId: string }>()
  const { data: fs, isLoading } = useQuery({
    queryKey: ['financial', dumpId],
    queryFn: () => api.get(`/reports/${dumpId}/financial`).then((r) => r.data),
  })

  if (isLoading) return <div className="p-6 text-gray-500">Loading financial summary...</div>
  if (!fs) return null

  const plData = [
    { name: 'Revenue', amount: fs.revenue },
    { name: 'Expenses', amount: fs.expenses },
    { name: 'Gross Profit', amount: fs.gross_profit },
    { name: 'Net Profit', amount: fs.net_profit },
  ]

  return (
    <div className="p-6">
      <PageHeader
        title="Financial Summary"
        subtitle={`Period: ${fs.period_from || 'N/A'} → ${fs.period_to || 'N/A'}`}
        actions={<a href={`/api/exports/${dumpId}/excel`} className="btn-secondary text-xs">Export Excel</a>}
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KPICard title="Revenue" value={INR(fs.revenue)} color="blue" />
        <KPICard title="Gross Profit" value={INR(fs.gross_profit)} subtitle={`${fs.gross_margin_pct}% margin`} color="green" />
        <KPICard title="Net Profit" value={INR(fs.net_profit)} subtitle={`${fs.net_margin_pct}% margin`} color={fs.net_profit >= 0 ? 'green' : 'red'} />
        <KPICard title="Equity" value={INR(fs.equity)} color="purple" />
        <KPICard title="Total Assets" value={INR(fs.total_assets)} color="blue" />
        <KPICard title="Total Liabilities" value={INR(fs.total_liabilities)} color="orange" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="card">
          <h3 className="font-semibold text-gray-800 mb-4">P&L Overview</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={plData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${(v / 100000).toFixed(0)}L`} />
              <Tooltip formatter={(v: number) => INR(v)} />
              <Bar dataKey="amount" fill="#1A56DB" radius={[4, 4, 0, 0]}>
                {plData.map((entry, i) => (
                  <Cell key={i} fill={entry.amount < 0 ? '#DC2626' : COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h3 className="font-semibold text-gray-800 mb-4">Asset Distribution</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={fs.asset_ledgers.slice(0, 6)} dataKey="amount" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
                {fs.asset_ledgers.slice(0, 6).map((_: any, i: number) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v: number) => INR(v)} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LedgerTable title="Revenue Ledgers" ledgers={fs.revenue_ledgers} />
        <LedgerTable title="Expense Ledgers" ledgers={fs.expense_ledgers} />
        <LedgerTable title="Asset Ledgers" ledgers={fs.asset_ledgers} />
        <LedgerTable title="Liability Ledgers" ledgers={fs.liability_ledgers} />
      </div>
    </div>
  )
}

function LedgerTable({ title, ledgers }: { title: string; ledgers: any[] }) {
  return (
    <div className="card">
      <h3 className="font-semibold text-gray-800 mb-3">{title}</h3>
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b">
            <th className="text-left pb-2 text-gray-600">Ledger</th>
            <th className="text-right pb-2 text-gray-600">Amount</th>
            <th className="text-right pb-2 text-gray-600">%</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {ledgers.map((l: any, i: number) => (
            <tr key={i}>
              <td className="py-1.5 text-gray-800">{l.name}</td>
              <td className="py-1.5 text-right font-medium">{new Intl.NumberFormat('en-IN').format(l.amount)}</td>
              <td className="py-1.5 text-right text-gray-500">{l.percentage}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
