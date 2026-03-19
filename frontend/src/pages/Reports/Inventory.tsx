/**
 * Inventory Report
 * ─────────────────
 * Drill-down layers:
 *   KPI cards (total items, values, negative stock count)
 *   → Negative stock alert table — click item → DrillVouchers
 *   → Stock register with group filter + search — click item → DrillVouchers
 *     → VoucherModal (stock movement vouchers for that item)
 */
import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ChevronLeft, AlertTriangle, ExternalLink, Package, Search } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import PageHeader from '../../components/UI/PageHeader'
import KPICard from '../../components/UI/KPICard'
import DrillVouchers, { DrillFilters } from '../../components/DrillVouchers'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts'

const INR = (v: number) =>
  new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(v)

export default function InventoryPage() {
  const { dumpId } = useParams<{ dumpId: string }>()
  const navigate = useNavigate()
  const [drill, setDrill] = useState<{ filters: DrillFilters; title: string } | null>(null)
  const [search, setSearch] = useState('')
  const [groupFilter, setGroupFilter] = useState('')
  const [sortBy, setSortBy] = useState<'value' | 'qty'>('value')

  const { data, isLoading } = useQuery({
    queryKey: ['inventory', dumpId],
    queryFn: () => api.get(`/reports/${dumpId}/inventory`).then((r) => r.data),
  })

  const allGroups: string[] = useMemo(
    () => [...new Set((data?.items || []).map((i: any) => i.group).filter(Boolean))],
    [data]
  )

  const filtered = useMemo(() => {
    let items = data?.items || []
    if (search) items = items.filter((i: any) => i.name.toLowerCase().includes(search.toLowerCase()))
    if (groupFilter) items = items.filter((i: any) => i.group === groupFilter)
    if (sortBy === 'value') items = [...items].sort((a: any, b: any) => b.closing_value - a.closing_value)
    if (sortBy === 'qty')   items = [...items].sort((a: any, b: any) => b.closing_qty - a.closing_qty)
    return items
  }, [data, search, groupFilter, sortBy])

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
  if (!data) return null

  // Group-wise value chart (top 10)
  const groupChart = Object.entries(
    filtered.reduce((acc: Record<string, number>, i: any) => {
      const g = i.group || 'Ungrouped'
      acc[g] = (acc[g] || 0) + (i.closing_value || 0)
      return acc
    }, {})
  )
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([name, value]) => ({ name, value }))

  return (
    <div className="p-6">
      <button onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ChevronLeft size={16} /> Back
      </button>
      <PageHeader title="Inventory Report"
        subtitle="Stock summary, negative stock alerts, group analysis — click any item to see its vouchers" />

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KPICard title="Total Items" value={(data.total_items || 0).toLocaleString()} color="blue" />
        <KPICard title="Opening Value" value={`₹${INR(data.total_opening_value)}`} color="blue" />
        <KPICard title="Closing Value" value={`₹${INR(data.total_closing_value)}`} color="green" />
        <KPICard title="Negative Stock Items" value={(data.negative_stock_items?.length || 0).toLocaleString()} color="red" />
      </div>

      {/* Negative stock alert */}
      {data.negative_stock_items?.length > 0 && (
        <div className="card mb-6 border-red-200 bg-red-50 p-0 overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-red-200 bg-red-100">
            <AlertTriangle size={16} className="text-red-700" />
            <h3 className="font-semibold text-red-800">Negative Stock Items ({data.negative_stock_items.length})</h3>
          </div>
          <table className="w-full text-xs">
            <thead><tr className="border-b border-red-200">
              <th className="text-left px-4 py-2 text-red-700">Item</th>
              <th className="text-right px-3 py-2 text-red-700">Closing Qty</th>
              <th className="text-right px-3 py-2 text-red-700">Closing Value</th>
            </tr></thead>
            <tbody className="divide-y divide-red-100">
              {data.negative_stock_items.map((item: any, i: number) => (
                <tr key={i} className="cursor-pointer hover:bg-red-100 group"
                  onClick={() => openDrill({ ledger_name: item.name }, `${item.name} — Stock Vouchers`)}>
                  <td className="px-4 py-2 font-medium text-red-900 flex items-center gap-1">
                    {item.name}
                    <ExternalLink size={10} className="text-red-400 group-hover:text-red-700" />
                  </td>
                  <td className="px-3 py-2 text-right font-bold text-red-800">{item.closing_qty}</td>
                  <td className="px-3 py-2 text-right">₹{INR(item.closing_value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Group value chart */}
      {groupChart.length > 0 && (
        <div className="card mb-6">
          <h3 className="font-semibold text-gray-800 mb-4">Closing Value by Group (Top 10)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={groupChart} layout="vertical" margin={{ left: 10, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10 }}
                tickFormatter={(v) => `₹${(v / 100000).toFixed(0)}L`} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={120} />
              <Tooltip formatter={(v: number) => `₹${INR(v)}`} />
              <Bar dataKey="value" fill="#1A56DB" radius={[0, 3, 3, 0]}
                cursor="pointer"
                onClick={(d: any) => openDrill({ ledger_name: d.name }, `${d.name} — Inventory Vouchers`)} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Filters */}
      <div className="card mb-4 py-3">
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Search Item</label>
            <div className="relative">
              <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Item name…"
                className="border rounded-lg pl-7 pr-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none w-48" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Group</label>
            <select value={groupFilter} onChange={(e) => setGroupFilter(e.target.value)}
              className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none">
              <option value="">All Groups</option>
              {allGroups.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Sort By</label>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value as 'value' | 'qty')}
              className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none">
              <option value="value">Highest Value</option>
              <option value="qty">Highest Qty</option>
            </select>
          </div>
          {(search || groupFilter) && (
            <button onClick={() => { setSearch(''); setGroupFilter('') }}
              className="text-xs text-gray-400 hover:text-gray-600 underline self-end pb-1.5">
              Clear
            </button>
          )}
          <span className="text-xs text-gray-400 self-end pb-1.5">
            {filtered.length} items
          </span>
        </div>
      </div>

      {/* Stock Register */}
      <div className="card p-0 overflow-hidden">
        <div className="px-4 py-2.5 border-b bg-gray-50 flex items-center gap-2">
          <Package size={14} className="text-gray-500" />
          <h3 className="font-semibold text-gray-800 text-sm">Stock Register</h3>
          <span className="text-xs text-blue-500 ml-auto">Click any item to see movement vouchers</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-gray-50 border-b">
                <th className="text-left px-3 py-2.5 text-gray-600">Item</th>
                <th className="text-left px-3 py-2.5 text-gray-600">Group</th>
                <th className="text-left px-3 py-2.5 text-gray-600">Unit</th>
                <th className="text-right px-3 py-2.5 text-gray-600">Open Qty</th>
                <th className="text-right px-3 py-2.5 text-gray-600">Open Value</th>
                <th className="text-right px-3 py-2.5 text-gray-600">Close Qty</th>
                <th className="text-right px-3 py-2.5 text-gray-600">Close Value</th>
                <th className="text-right px-3 py-2.5 text-gray-600">Avg Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.length === 0 ? (
                <tr><td colSpan={8} className="text-center py-10 text-gray-400">No items match</td></tr>
              ) : filtered.map((item: any, i: number) => (
                <tr key={i}
                  className={`cursor-pointer transition-colors group ${
                    item.is_negative ? 'bg-red-50 hover:bg-red-100' : 'hover:bg-blue-50'
                  }`}
                  onClick={() => openDrill({ ledger_name: item.name }, `${item.name} — Stock Vouchers`)}>
                  <td className="px-3 py-2 font-medium text-gray-800 max-w-[180px]">
                    <span className="flex items-center gap-1 truncate">
                      {item.name}
                      <ExternalLink size={10} className="text-gray-300 group-hover:text-blue-500 flex-shrink-0" />
                    </span>
                  </td>
                  <td className="px-3 py-2 text-gray-500">{item.group || '—'}</td>
                  <td className="px-3 py-2 text-gray-500">{item.unit || '—'}</td>
                  <td className="px-3 py-2 text-right text-gray-600">{item.opening_qty}</td>
                  <td className="px-3 py-2 text-right text-gray-600">₹{INR(item.opening_value)}</td>
                  <td className={`px-3 py-2 text-right font-semibold ${item.is_negative ? 'text-red-700' : 'text-gray-800'}`}>
                    {item.closing_qty}
                  </td>
                  <td className="px-3 py-2 text-right font-semibold text-gray-800">₹{INR(item.closing_value)}</td>
                  <td className="px-3 py-2 text-right text-gray-500">₹{INR(item.avg_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {drill && (
        <DrillVouchers
          dumpId={dumpId!}
          title={drill.title}
          subtitle="Stock movement vouchers — click any row for full detail"
          filters={drill.filters}
          onClose={() => setDrill(null)}
        />
      )}
    </div>
  )
}
