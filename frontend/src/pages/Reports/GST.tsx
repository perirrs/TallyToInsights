/**
 * GST Report
 * ───────────
 * Drill-down layers:
 *   KPI summary (output tax, ITC, net payable)
 *   → Monthly GSTR summary table — click month → DrillVouchers
 *   → Tax Rate Breakdown (5%/12%/18%/28%) — click slab → DrillVouchers
 *   → Top Parties by sales — click party → DrillVouchers
 *     → VoucherModal (Dr/Cr lines, GSTIN, place of supply)
 */
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ChevronLeft, ExternalLink, Info } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import PageHeader from '../../components/UI/PageHeader'
import KPICard from '../../components/UI/KPICard'
import DrillVouchers, { DrillFilters } from '../../components/DrillVouchers'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'

const INR = (v: number) =>
  new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(v)

const RATE_COLORS: Record<number, string> = {
  0:  'bg-gray-100 text-gray-700',
  5:  'bg-blue-100 text-blue-800',
  12: 'bg-teal-100 text-teal-800',
  18: 'bg-orange-100 text-orange-800',
  28: 'bg-red-100 text-red-800',
}

export default function GSTPage() {
  const { dumpId } = useParams<{ dumpId: string }>()
  const navigate = useNavigate()
  const [drill, setDrill] = useState<{ filters: DrillFilters; title: string } | null>(null)
  const [activeTab, setActiveTab] = useState<'monthly' | 'rates' | 'parties'>('monthly')

  const { data: gst, isLoading: gstLoading } = useQuery({
    queryKey: ['gst', dumpId],
    queryFn: () => api.get(`/reports/${dumpId}/gst`).then((r) => r.data),
  })

  const { data: rates } = useQuery({
    queryKey: ['gst-rates', dumpId],
    queryFn: () => api.get(`/reports/${dumpId}/drill/gst-rates`).then((r) => r.data),
    enabled: !!dumpId,
  })

  const openDrill = (filters: DrillFilters, title: string) => setDrill({ filters, title })

  if (gstLoading) {
    return (
      <div className="p-6 space-y-4 animate-pulse">
        <div className="h-8 bg-gray-100 rounded w-40" />
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => <div key={i} className="h-20 bg-gray-100 rounded-xl" />)}
        </div>
        <div className="h-64 bg-gray-100 rounded-xl" />
      </div>
    )
  }
  if (!gst) return null

  const totalTaxableSales = gst.monthly_summary?.reduce((s: number, m: any) => s + (m.taxable_sales || 0), 0) ?? 0
  const totalTaxablePurch = gst.monthly_summary?.reduce((s: number, m: any) => s + (m.taxable_purchases || 0), 0) ?? 0

  return (
    <div className="p-6">
      <button onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ChevronLeft size={16} /> Back
      </button>
      <PageHeader title="GST Report" subtitle="GSTR summary · rate-wise breakdown · ITC reconciliation" />

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <KPICard title="Output Tax" value={`₹${INR(gst.total_output_tax)}`} color="orange" />
        <KPICard title="Total ITC" value={`₹${INR(gst.total_itc)}`} color="green" />
        <KPICard title="Net GST Payable" value={`₹${INR(gst.net_payable)}`}
          color={gst.net_payable > 0 ? 'red' : 'green'} />
        <KPICard title="Taxable Sales" value={`₹${INR(totalTaxableSales)}`} color="blue" />
        <KPICard title="Taxable Purchases" value={`₹${INR(totalTaxablePurch)}`} color="purple" />
      </div>

      {/* Trend Chart */}
      <div className="card mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-800">Monthly Output Tax vs ITC</h3>
          <p className="text-xs text-gray-400">Click any bar to drill into that month's vouchers</p>
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={gst.monthly_summary || []} margin={{ top: 4, right: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}K`} />
            <Tooltip formatter={(v: number, name: string) => [`₹${INR(v)}`, name]} />
            <Legend />
            <Bar dataKey="total_tax" name="Output GST" fill="#EA580C" radius={[3, 3, 0, 0]}
              cursor="pointer" onClick={(d: any) => openDrill({ voucher_type: 'Sales' }, `Output GST — ${d.month}`)} />
            <Bar dataKey="total_itc" name="ITC" fill="#16A34A" radius={[3, 3, 0, 0]}
              cursor="pointer" onClick={(d: any) => openDrill({ voucher_type: 'Purchase' }, `ITC — ${d.month}`)} />
            <Bar dataKey="net_liability" name="Net Liability" fill="#1A56DB" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b">
        {(['monthly', 'rates', 'parties'] as const).map((t) => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === t
                ? 'border-brand-600 text-brand-700'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}>
            {t === 'monthly' ? 'Monthly Breakup' : t === 'rates' ? 'Tax Rate Analysis' : 'Top Parties'}
          </button>
        ))}
      </div>

      {/* Monthly Breakup */}
      {activeTab === 'monthly' && (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-gray-50 border-b">
                {['Month','Taxable Sales','CGST','SGST','IGST','Output Tax','Taxable Purch','ITC','Net Liability'].map((h) => (
                  <th key={h} className="px-3 py-2.5 text-right first:text-left font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {gst.monthly_summary?.map((m: any, i: number) => (
                <tr key={i} className="hover:bg-blue-50 cursor-pointer group"
                  onClick={() => openDrill({ voucher_type: 'Sales' }, `GST — ${m.month}`)}>
                  <td className="px-3 py-2 font-medium text-gray-800">
                    <span className="flex items-center gap-1">
                      {m.month}
                      <ExternalLink size={10} className="text-gray-300 group-hover:text-blue-500" />
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">{INR(m.taxable_sales)}</td>
                  <td className="px-3 py-2 text-right">{INR(m.cgst_collected)}</td>
                  <td className="px-3 py-2 text-right">{INR(m.sgst_collected)}</td>
                  <td className="px-3 py-2 text-right">{INR(m.igst_collected)}</td>
                  <td className="px-3 py-2 text-right font-semibold text-orange-700">{INR(m.total_tax)}</td>
                  <td className="px-3 py-2 text-right">{INR(m.taxable_purchases)}</td>
                  <td className="px-3 py-2 text-right font-semibold text-green-700">{INR(m.total_itc)}</td>
                  <td className={`px-3 py-2 text-right font-bold ${m.net_liability > 0 ? 'text-red-700' : 'text-green-700'}`}>
                    {INR(m.net_liability)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="border-t bg-gray-50 font-bold text-xs">
              <tr>
                <td className="px-3 py-2 text-gray-700">Total</td>
                {['taxable_sales','cgst_collected','sgst_collected','igst_collected','total_tax','taxable_purchases','total_itc','net_liability'].map((k) => (
                  <td key={k} className="px-3 py-2 text-right text-gray-900">
                    {INR(gst.monthly_summary?.reduce((s: number, m: any) => s + (m[k] || 0), 0) ?? 0)}
                  </td>
                ))}
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      {/* Tax Rate Analysis */}
      {activeTab === 'rates' && (
        <div className="card p-0 overflow-hidden">
          <div className="px-4 py-3 border-b flex items-center gap-2 text-xs text-gray-500 bg-gray-50">
            <Info size={13} /> Based on voucher line-level GST amounts · click any row to see matching vouchers
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b text-xs">
                <th className="text-left px-4 py-2.5 text-gray-600">GST Rate</th>
                <th className="text-right px-3 py-2.5 text-gray-600">Est. Taxable Amt</th>
                <th className="text-right px-3 py-2.5 text-gray-600">CGST</th>
                <th className="text-right px-3 py-2.5 text-gray-600">SGST</th>
                <th className="text-right px-3 py-2.5 text-gray-600">IGST</th>
                <th className="text-right px-3 py-2.5 font-semibold text-orange-700">Total Tax</th>
                <th className="text-right px-3 py-2.5 text-gray-600">Vouchers</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {rates?.rates?.length > 0 ? rates.rates.map((r: any, i: number) => (
                <tr key={i} className="hover:bg-blue-50 cursor-pointer group"
                  onClick={() => openDrill({}, `GST @ ${r.rate}% — Vouchers`)}>
                  <td className="px-4 py-3">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${RATE_COLORS[r.rate] ?? 'bg-gray-100 text-gray-700'}`}>
                      {r.rate}%
                    </span>
                  </td>
                  <td className="px-3 py-3 text-right text-gray-700">₹{INR(r.taxable_amount)}</td>
                  <td className="px-3 py-3 text-right text-gray-600">₹{INR(r.cgst)}</td>
                  <td className="px-3 py-3 text-right text-gray-600">₹{INR(r.sgst)}</td>
                  <td className="px-3 py-3 text-right text-gray-600">₹{INR(r.igst)}</td>
                  <td className="px-3 py-3 text-right font-bold text-orange-700">₹{INR(r.total_tax)}</td>
                  <td className="px-3 py-3 text-right text-gray-500">{r.voucher_count}</td>
                </tr>
              )) : (
                <tr><td colSpan={7} className="text-center py-8 text-gray-400 text-sm">
                  No voucher-line GST data found. This report requires line-level GST amounts from Tally XML.
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Top Parties */}
      {activeTab === 'parties' && (
        <div className="card p-0 overflow-hidden">
          <div className="px-4 py-3 border-b flex items-center gap-2 text-xs text-gray-500 bg-gray-50">
            <Info size={13} /> Top customers by sales value — click to see all their sales vouchers
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b text-xs">
                <th className="text-left px-4 py-2.5 text-gray-600 w-8">#</th>
                <th className="text-left px-3 py-2.5 text-gray-600">Party</th>
                <th className="text-right px-3 py-2.5 text-gray-600">Total Sales Amount</th>
                <th className="text-right px-3 py-2.5 text-gray-600">Vouchers</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {rates?.top_parties?.length > 0 ? rates.top_parties.map((p: any, i: number) => (
                <tr key={i} className="hover:bg-blue-50 cursor-pointer group"
                  onClick={() => openDrill({ ledger_name: p.party, voucher_type: 'Sales' }, `${p.party} — Sales Vouchers`)}>
                  <td className="px-4 py-2.5 text-gray-400 text-xs">{i + 1}</td>
                  <td className="px-3 py-2.5 font-medium text-gray-800">
                    <span className="flex items-center gap-1">
                      {p.party}
                      <ExternalLink size={11} className="text-gray-300 group-hover:text-blue-500" />
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-right font-semibold text-gray-900">₹{INR(p.total_amount)}</td>
                  <td className="px-3 py-2.5 text-right text-gray-500">{p.voucher_count}</td>
                </tr>
              )) : (
                <tr><td colSpan={4} className="text-center py-8 text-gray-400 text-sm">No party data found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {drill && (
        <DrillVouchers
          dumpId={dumpId!}
          title={drill.title}
          subtitle="Click any voucher for Dr/Cr lines and GST details"
          filters={drill.filters}
          onClose={() => setDrill(null)}
        />
      )}
    </div>
  )
}
