/**
 * Financial Report — P&L + Balance Sheet
 * ────────────────────────────────────────
 * Layers of drill-down:
 *   KPI cards
 *   → Monthly trend chart (click bar → month DrillVouchers)
 *   → P&L tree:  Section (Income / Expenses)
 *               → Group (Sales, Direct Expenses…)  [expandable]
 *                 → Ledger row (click → DrillVouchers for that ledger)
 *                   → VoucherModal (full detail)
 *   → Balance Sheet:  Assets / Liabilities  (same pattern)
 */
import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ChevronLeft, ChevronDown, ChevronRight as ChevRight, TrendingUp, TrendingDown, ExternalLink } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import PageHeader from '../../components/UI/PageHeader'
import KPICard from '../../components/UI/KPICard'
import DrillVouchers, { DrillFilters } from '../../components/DrillVouchers'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine, Cell,
} from 'recharts'

const INR = (v: number) =>
  new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(v)
const PCT = (v: number) => (isNaN(v) ? '0' : v.toFixed(1))

const COLORS = ['#1A56DB', '#16A34A', '#EA580C', '#7C3AED', '#DB2777', '#0891B2', '#854D0E', '#065F46']

// ── Expandable P&L group ──────────────────────────────────────────────────────
function PLGroup({
  groupName,
  ledgers,
  total,
  sectionTotal,
  onDrill,
  accent,
}: {
  groupName: string
  ledgers: any[]
  total: number
  sectionTotal: number
  onDrill: (filters: DrillFilters, title: string) => void
  accent: string
}) {
  const [open, setOpen] = useState(false)
  const pct = sectionTotal > 0 ? (total / sectionTotal) * 100 : 0

  return (
    <div className="border-b last:border-0">
      {/* Group header row */}
      <button
        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-gray-50 transition-colors text-left"
        onClick={() => setOpen((o) => !o)}
      >
        <div className="flex items-center gap-2">
          {open ? <ChevronDown size={14} className="text-gray-400" /> : <ChevRight size={14} className="text-gray-400" />}
          <span className="text-sm font-semibold text-gray-700">{groupName}</span>
          <span className="text-xs text-gray-400">({ledgers.length})</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="w-24 bg-gray-100 rounded-full h-1.5 hidden sm:block">
            <div className={`h-full rounded-full ${accent}`} style={{ width: `${Math.min(pct, 100)}%` }} />
          </div>
          <span className="text-xs text-gray-500 w-10 text-right">{PCT(pct)}%</span>
          <span className="text-sm font-bold text-gray-900 w-28 text-right">₹{INR(total)}</span>
        </div>
      </button>

      {/* Ledger rows */}
      {open && (
        <div className="bg-gray-50 border-t">
          {ledgers.map((l: any, i: number) => (
            <button
              key={i}
              className="w-full flex items-center justify-between px-8 py-2 hover:bg-blue-50 transition-colors text-left group"
              onClick={() => onDrill({ ledger_name: l.name }, `${l.name} — Transactions`)}
            >
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-700">{l.name}</span>
                <ExternalLink size={11} className="text-gray-300 group-hover:text-blue-500 transition-colors" />
              </div>
              <div className="flex items-center gap-4">
                <span className="text-xs text-gray-400 w-10 text-right">{l.percentage}%</span>
                <span className="text-xs font-semibold text-gray-800 w-28 text-right">₹{INR(l.amount)}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function FinancialPage() {
  const { dumpId } = useParams<{ dumpId: string }>()
  const navigate = useNavigate()

  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [drill, setDrill] = useState<{ filters: DrillFilters; title: string } | null>(null)
  const [bsSection, setBsSection] = useState<'assets' | 'liabilities'>('assets')

  const { data: fs, isLoading } = useQuery({
    queryKey: ['financial', dumpId, dateFrom, dateTo],
    queryFn: () =>
      api.get(`/reports/${dumpId}/financial`, {
        params: { date_from: dateFrom || undefined, date_to: dateTo || undefined },
      }).then((r) => r.data),
  })

  const { data: monthly = [] } = useQuery({
    queryKey: ['monthly-pl', dumpId],
    queryFn: () => api.get(`/reports/${dumpId}/drill/monthly-pl`).then((r) => r.data),
    enabled: !!dumpId,
  })

  // Group ledgers by group_name
  const group = (ledgers: any[]) => {
    const map: Record<string, { total: number; ledgers: any[] }> = {}
    for (const l of ledgers || []) {
      const g = l.group || 'Other'
      if (!map[g]) map[g] = { total: 0, ledgers: [] }
      map[g].total += Math.abs(l.amount || 0)
      map[g].ledgers.push(l)
    }
    return Object.entries(map).sort((a, b) => b[1].total - a[1].total)
  }

  const revenueGroups = useMemo(() => group(fs?.revenue_ledgers), [fs])
  const expenseGroups = useMemo(() => group(fs?.expense_ledgers), [fs])
  const assetGroups   = useMemo(() => group(fs?.asset_ledgers),   [fs])
  const liabGroups    = useMemo(() => group(fs?.liability_ledgers), [fs])

  const openDrill = (filters: DrillFilters, title: string) =>
    setDrill({ filters, title })

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="space-y-4 animate-pulse">
          <div className="h-8 bg-gray-100 rounded w-48" />
          <div className="grid grid-cols-4 gap-4">
            {[1,2,3,4].map(i => <div key={i} className="h-20 bg-gray-100 rounded-xl" />)}
          </div>
          <div className="h-64 bg-gray-100 rounded-xl" />
        </div>
      </div>
    )
  }
  if (!fs) return null

  return (
    <div className="p-6">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4"
      >
        <ChevronLeft size={16} /> Back
      </button>

      <PageHeader
        title="Financial Summary"
        subtitle={`Period: ${fs.period_from || 'N/A'} → ${fs.period_to || 'N/A'}`}
        actions={
          <a href={`/api/exports/${dumpId}/excel`} className="btn-secondary text-xs">
            Export Excel
          </a>
        }
      />

      {/* Date filters */}
      <div className="card mb-6 py-3">
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">From</label>
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)}
              className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">To</label>
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)}
              className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" />
          </div>
          {(dateFrom || dateTo) && (
            <button onClick={() => { setDateFrom(''); setDateTo('') }}
              className="text-xs text-gray-400 hover:text-gray-600 underline self-end pb-1.5">
              Clear
            </button>
          )}
        </div>
      </div>

      {/* ── KPI Cards ── */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
        <KPICard title="Revenue" value={`₹${INR(fs.revenue)}`} color="blue" />
        <KPICard title="Gross Profit" value={`₹${INR(fs.gross_profit)}`}
          subtitle={`${fs.gross_margin_pct}% margin`} color="green" />
        <KPICard title="Net Profit" value={`₹${INR(fs.net_profit)}`}
          subtitle={`${fs.net_margin_pct}% margin`}
          color={fs.net_profit >= 0 ? 'green' : 'red'} />
        <KPICard title="Total Assets" value={`₹${INR(fs.total_assets)}`} color="blue" />
        <KPICard title="Total Liabilities" value={`₹${INR(fs.total_liabilities)}`} color="orange" />
        <KPICard title="Equity" value={`₹${INR(fs.equity)}`} color="purple" />
      </div>

      {/* ── Monthly P&L Trend ── */}
      {monthly.length > 0 && (
        <div className="card mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-800">Monthly Revenue vs Expenses</h3>
            <p className="text-xs text-gray-400">Click a month to drill into its vouchers</p>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={monthly} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${(v / 100000).toFixed(0)}L`} />
              <Tooltip
                formatter={(v: number, name: string) => [`₹${INR(v)}`, name]}
                labelStyle={{ fontWeight: 600 }}
              />
              <Legend />
              <ReferenceLine y={0} stroke="#666" />
              <Bar dataKey="revenue" name="Revenue" fill="#1A56DB" radius={[3,3,0,0]}
                cursor="pointer"
                onClick={(d: any) => openDrill(
                  { date_from: `${d.month}-01`, date_to: `${d.month}-31`, voucher_type: 'Sales' },
                  `Revenue — ${d.label}`
                )}
              />
              <Bar dataKey="expenses" name="Expenses" fill="#EA580C" radius={[3,3,0,0]}
                cursor="pointer"
                onClick={(d: any) => openDrill(
                  { date_from: `${d.month}-01`, date_to: `${d.month}-31`, voucher_type: 'Purchase' },
                  `Expenses — ${d.label}`
                )}
              />
              <Bar dataKey="profit" name="Net Profit" fill="#16A34A" radius={[3,3,0,0]}
                cursor="pointer"
                onClick={(d: any) => openDrill(
                  { date_from: `${d.month}-01`, date_to: `${d.month}-31` },
                  `All Vouchers — ${d.label}`
                )}
              >
                {monthly.map((m: any, i: number) => (
                  <Cell key={i} fill={m.profit >= 0 ? '#16A34A' : '#DC2626'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── P&L Statement ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Income */}
        <div className="card overflow-hidden p-0">
          <div className="flex items-center justify-between px-4 py-3 border-b bg-green-50">
            <h3 className="font-bold text-green-800 flex items-center gap-2">
              <TrendingUp size={16} /> Income
            </h3>
            <span className="font-bold text-green-900 text-base">₹{INR(fs.revenue)}</span>
          </div>
          {revenueGroups.map(([g, { total, ledgers }]) => (
            <PLGroup key={g} groupName={g} ledgers={ledgers} total={total}
              sectionTotal={fs.revenue} onDrill={openDrill} accent="bg-green-500" />
          ))}
          {revenueGroups.length === 0 && (
            <p className="text-xs text-gray-400 p-4">No income ledgers found</p>
          )}
        </div>

        {/* Expenses */}
        <div className="card overflow-hidden p-0">
          <div className="flex items-center justify-between px-4 py-3 border-b bg-orange-50">
            <h3 className="font-bold text-orange-800 flex items-center gap-2">
              <TrendingDown size={16} /> Expenses
            </h3>
            <span className="font-bold text-orange-900 text-base">₹{INR(fs.expenses)}</span>
          </div>
          {expenseGroups.map(([g, { total, ledgers }]) => (
            <PLGroup key={g} groupName={g} ledgers={ledgers} total={total}
              sectionTotal={fs.expenses} onDrill={openDrill} accent="bg-orange-500" />
          ))}
          {expenseGroups.length === 0 && (
            <p className="text-xs text-gray-400 p-4">No expense ledgers found</p>
          )}
        </div>
      </div>

      {/* ── P&L Summary ── */}
      <div className="card mb-6 bg-gradient-to-r from-gray-50 to-white">
        <h3 className="font-bold text-gray-800 mb-3">Profit & Loss Summary</h3>
        <div className="divide-y text-sm">
          {[
            { label: 'Total Revenue', value: fs.revenue, bold: false, color: 'text-gray-900' },
            { label: 'Cost of Goods Sold', value: -(fs.revenue - fs.gross_profit), bold: false, color: 'text-red-700' },
            { label: 'Gross Profit', value: fs.gross_profit, bold: true, color: fs.gross_profit >= 0 ? 'text-green-700' : 'text-red-700' },
            { label: `Operating Expenses`, value: -(fs.expenses - (fs.revenue - fs.gross_profit)), bold: false, color: 'text-red-700' },
            { label: 'Net Profit / (Loss)', value: fs.net_profit, bold: true, color: fs.net_profit >= 0 ? 'text-green-700' : 'text-red-700' },
          ].map((row, i) => (
            <div key={i} className={`flex items-center justify-between py-2 ${row.bold ? 'bg-gray-50 rounded px-2 font-bold' : 'px-2'}`}>
              <span className={row.bold ? 'text-gray-800' : 'text-gray-600'}>{row.label}</span>
              <span className={`font-medium tabular-nums ${row.color}`}>₹{INR(Math.abs(row.value))}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Balance Sheet ── */}
      <div className="card overflow-hidden p-0">
        <div className="flex items-center justify-between px-4 py-3 border-b bg-blue-50">
          <h3 className="font-bold text-blue-900">Balance Sheet</h3>
          <div className="flex gap-1">
            {(['assets', 'liabilities'] as const).map((s) => (
              <button key={s} onClick={() => setBsSection(s)}
                className={`text-xs px-3 py-1 rounded-full font-medium transition-colors ${
                  bsSection === s ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'
                }`}>
                {s === 'assets' ? `Assets ₹${INR(fs.total_assets)}` : `Liabilities ₹${INR(fs.total_liabilities)}`}
              </button>
            ))}
          </div>
        </div>
        {(bsSection === 'assets' ? assetGroups : liabGroups).map(([g, { total, ledgers }]) => (
          <PLGroup key={g} groupName={g} ledgers={ledgers} total={total}
            sectionTotal={bsSection === 'assets' ? fs.total_assets : fs.total_liabilities}
            onDrill={openDrill}
            accent={bsSection === 'assets' ? 'bg-blue-500' : 'bg-purple-500'}
          />
        ))}
      </div>

      {/* Drill-down panel */}
      {drill && (
        <DrillVouchers
          dumpId={dumpId!}
          title={drill.title}
          subtitle="Click any row for full voucher detail (Dr/Cr lines)"
          filters={drill.filters}
          onClose={() => setDrill(null)}
        />
      )}
    </div>
  )
}
