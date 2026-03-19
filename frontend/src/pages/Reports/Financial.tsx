import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import PageHeader from '../../components/UI/PageHeader'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts'
import KPICard from '../../components/UI/KPICard'

const INR = (v: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)
const COLORS = ['#1A56DB', '#16A34A', '#EA580C', '#7C3AED', '#DB2777', '#0891B2', '#854D0E', '#065F46']

export default function FinancialPage() {
  const { dumpId } = useParams<{ dumpId: string }>()
  const navigate = useNavigate()

  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [groupFilter, setGroupFilter] = useState('')
  const [ledgerSearch, setLedgerSearch] = useState('')

  const { data: fs, isLoading } = useQuery({
    queryKey: ['financial', dumpId, dateFrom, dateTo],
    queryFn: () => api.get(`/reports/${dumpId}/financial`, {
      params: {
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      }
    }).then((r) => r.data),
  })

  if (isLoading) return <div className="p-6 text-gray-500">Loading financial summary...</div>
  if (!fs) return null

  const plData = [
    { name: 'Revenue', amount: fs.revenue },
    { name: 'Expenses', amount: fs.expenses },
    { name: 'Gross Profit', amount: fs.gross_profit },
    { name: 'Net Profit', amount: fs.net_profit },
  ]

  const filterLedgers = (ledgers: any[]) => {
    let result = ledgers || []
    if (groupFilter) result = result.filter((l: any) => (l.group || '').toLowerCase().includes(groupFilter.toLowerCase()))
    if (ledgerSearch) result = result.filter((l: any) => l.name.toLowerCase().includes(ledgerSearch.toLowerCase()))
    return result
  }

  const allGroups = [...new Set([
    ...(fs.revenue_ledgers || []),
    ...(fs.expense_ledgers || []),
    ...(fs.asset_ledgers || []),
    ...(fs.liability_ledgers || []),
  ].map((l: any) => l.group).filter(Boolean))] as string[]

  return (
    <div className="p-6">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ChevronLeft size={16} /> Back
      </button>
      <PageHeader
        title="Financial Summary"
        subtitle={`Period: ${fs.period_from || 'N/A'} → ${fs.period_to || 'N/A'}`}
        actions={<a href={`/api/exports/${dumpId}/excel`} className="btn-secondary text-xs">Export Excel</a>}
      />

      {/* Drill-down Filters */}
      <div className="card mb-6 py-3">
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Date From</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Date To</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Ledger Group</label>
            <select
              value={groupFilter}
              onChange={(e) => setGroupFilter(e.target.value)}
              className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none"
            >
              <option value="">All Groups</option>
              {allGroups.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Search Ledger</label>
            <input
              value={ledgerSearch}
              onChange={(e) => setLedgerSearch(e.target.value)}
              placeholder="Ledger name..."
              className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none w-44"
            />
          </div>
          {(dateFrom || dateTo || groupFilter || ledgerSearch) && (
            <button
              onClick={() => { setDateFrom(''); setDateTo(''); setGroupFilter(''); setLedgerSearch('') }}
              className="text-xs text-gray-500 hover:text-gray-700 underline self-end pb-1.5"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

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
              <Pie data={filterLedgers(fs.asset_ledgers).slice(0, 6)} dataKey="amount" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
                {filterLedgers(fs.asset_ledgers).slice(0, 6).map((_: any, i: number) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v: number) => INR(v)} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LedgerTable title="Revenue Ledgers" ledgers={filterLedgers(fs.revenue_ledgers)} />
        <LedgerTable title="Expense Ledgers" ledgers={filterLedgers(fs.expense_ledgers)} />
        <LedgerTable title="Asset Ledgers" ledgers={filterLedgers(fs.asset_ledgers)} />
        <LedgerTable title="Liability Ledgers" ledgers={filterLedgers(fs.liability_ledgers)} />
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
