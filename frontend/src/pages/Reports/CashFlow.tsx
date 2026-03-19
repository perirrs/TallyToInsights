/**
 * Cash Flow Report
 * ─────────────────
 * Drill-down layers:
 *   KPIs (opening, inflow, outflow, closing)
 *   → Monthly bar chart — click month → DrillVouchers (bank/cash vouchers for that period)
 *   → Running balance area chart
 *   → Top inflow / outflow parties — click party → DrillVouchers
 *     → VoucherModal (full detail)
 */
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ChevronLeft, TrendingUp, TrendingDown, ExternalLink } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import PageHeader from '../../components/UI/PageHeader'
import KPICard from '../../components/UI/KPICard'
import DrillVouchers, { DrillFilters } from '../../components/DrillVouchers'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts'

const INR = (v: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)

export default function CashFlowPage() {
  const { dumpId } = useParams<{ dumpId: string }>()
  const navigate = useNavigate()
  const [drill, setDrill] = useState<{ filters: DrillFilters; title: string } | null>(null)
  const [view, setView] = useState<'monthly' | 'top-inflow' | 'top-outflow'>('monthly')

  const { data: cf, isLoading } = useQuery({
    queryKey: ['cashflow', dumpId],
    queryFn: () => api.get(`/reports/${dumpId}/cashflow`).then((r) => r.data),
  })

  const openDrill = (filters: DrillFilters, title: string) => setDrill({ filters, title })

  if (isLoading) {
    return (
      <div className="p-6 space-y-4 animate-pulse">
        <div className="h-8 bg-gray-100 rounded w-40" />
        <div className="grid grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <div key={i} className="h-20 bg-gray-100 rounded-xl" />)}
        </div>
        <div className="h-64 bg-gray-100 rounded-xl" />
      </div>
    )
  }
  if (!cf) return null

  const netFlow = (cf.total_inflow || 0) - (cf.total_outflow || 0)

  return (
    <div className="p-6">
      <button onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ChevronLeft size={16} /> Back
      </button>
      <PageHeader title="Cash Flow Report" subtitle="Bank and cash movement — click any bar or party to drill into transactions" />

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <KPICard title="Opening Balance" value={INR(cf.opening_balance)} color="blue" />
        <KPICard title="Total Inflow" value={INR(cf.total_inflow)} color="green" />
        <KPICard title="Total Outflow" value={INR(cf.total_outflow)} color="red" />
        <KPICard title="Net Flow" value={INR(netFlow)} color={netFlow >= 0 ? 'green' : 'red'} />
        <KPICard title="Closing Balance" value={INR(cf.closing_balance)}
          color={cf.closing_balance >= 0 ? 'green' : 'red'} />
      </div>

      {/* Monthly chart */}
      <div className="card mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-800">Monthly Cash Flow</h3>
          <p className="text-xs text-gray-400">Click any bar to drill into that month</p>
        </div>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={cf.monthly_summary || []} margin={{ top: 4, right: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${(v / 100000).toFixed(0)}L`} />
            <Tooltip formatter={(v: number, name: string) => [INR(v), name]} />
            <Legend />
            <Bar dataKey="inflow" name="Inflow" fill="#16A34A" radius={[3, 3, 0, 0]}
              cursor="pointer"
              onClick={(d: any) => openDrill(
                { voucher_type: 'Receipt' },
                `Cash Inflows — ${d.month}`
              )}
            />
            <Bar dataKey="outflow" name="Outflow" fill="#DC2626" radius={[3, 3, 0, 0]}
              cursor="pointer"
              onClick={(d: any) => openDrill(
                { voucher_type: 'Payment' },
                `Cash Outflows — ${d.month}`
              )}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Running balance */}
      {cf.daily_items?.length > 0 && (
        <div className="card mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-800">Running Balance (last 90 days)</h3>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={cf.daily_items?.slice(-90) || []} margin={{ top: 4, right: 8 }}>
              <defs>
                <linearGradient id="balGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1A56DB" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#1A56DB" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 9 }} />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `₹${(v / 100000).toFixed(0)}L`} />
              <Tooltip formatter={(v: number) => INR(v)} />
              <Area type="monotone" dataKey="balance" stroke="#1A56DB" fill="url(#balGrad)" name="Balance" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Top inflows / outflows */}
      {(cf.top_inflows?.length > 0 || cf.top_outflows?.length > 0) && (
        <>
          <div className="flex gap-1 mb-4 border-b">
            {(['top-inflow', 'top-outflow'] as const).map((t) => (
              <button key={t} onClick={() => setView(t)}
                className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                  view === t ? 'border-brand-600 text-brand-700' : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}>
                {t === 'top-inflow' ? (
                  <span className="flex items-center gap-1"><TrendingUp size={13} className="text-green-600" /> Top Inflow Parties</span>
                ) : (
                  <span className="flex items-center gap-1"><TrendingDown size={13} className="text-red-600" /> Top Outflow Parties</span>
                )}
              </button>
            ))}
          </div>

          <div className="card p-0 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b text-xs">
                  <th className="text-left px-4 py-2.5 w-8 text-gray-600">#</th>
                  <th className="text-left px-3 py-2.5 text-gray-600">Party</th>
                  <th className="text-right px-3 py-2.5 text-gray-600">Amount</th>
                  <th className="text-right px-3 py-2.5 text-gray-600">Vouchers</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {(view === 'top-inflow' ? cf.top_inflows : cf.top_outflows)?.map((p: any, i: number) => (
                  <tr key={i} className="hover:bg-blue-50 cursor-pointer group"
                    onClick={() => openDrill(
                      { ledger_name: p.party, voucher_type: view === 'top-inflow' ? 'Receipt' : 'Payment' },
                      `${p.party} — ${view === 'top-inflow' ? 'Receipts' : 'Payments'}`
                    )}>
                    <td className="px-4 py-2.5 text-gray-400 text-xs">{i + 1}</td>
                    <td className="px-3 py-2.5 font-medium text-gray-800">
                      <span className="flex items-center gap-1">
                        {p.party}
                        <ExternalLink size={11} className="text-gray-300 group-hover:text-blue-500" />
                      </span>
                    </td>
                    <td className={`px-3 py-2.5 text-right font-semibold ${
                      view === 'top-inflow' ? 'text-green-700' : 'text-red-700'
                    }`}>
                      ₹{new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(p.amount)}
                    </td>
                    <td className="px-3 py-2.5 text-right text-gray-500">{p.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {drill && (
        <DrillVouchers
          dumpId={dumpId!}
          title={drill.title}
          subtitle="Click any voucher for full detail with Dr/Cr lines"
          filters={drill.filters}
          onClose={() => setDrill(null)}
        />
      )}
    </div>
  )
}
