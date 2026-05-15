/**
 * Payroll Report
 * ───────────────
 * Drill-down layers:
 *   KPI cards
 *   → Monthly salary trend chart — click month → DrillVouchers (payroll vouchers that month)
 *   → Employee summary table — click employee → DrillVouchers (all salary vouchers)
 *   → Month × Employee grid (salary matrix)
 *     → VoucherModal (full payslip detail)
 */
import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ChevronLeft, ExternalLink, Users, Search } from 'lucide-react'
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

export default function PayrollPage() {
  const { dumpId } = useParams<{ dumpId: string }>()
  const navigate = useNavigate()
  const [drill, setDrill] = useState<{ filters: DrillFilters; title: string } | null>(null)
  const [search, setSearch] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['payroll', dumpId],
    queryFn: () => api.get(`/reports/${dumpId}/payroll`).then((r) => r.data),
  })

  const openDrill = (filters: DrillFilters, title: string) => setDrill({ filters, title })

  const filteredEmployees = useMemo(() => {
    if (!data?.employee_summary) return []
    if (!search) return data.employee_summary
    return data.employee_summary.filter((e: any) =>
      e.employee.toLowerCase().includes(search.toLowerCase())
    )
  }, [data, search])

  if (isLoading) {
    return (
      <div className="p-6 space-y-4 animate-pulse">
        <div className="h-8 bg-gray-100 rounded w-40" />
        <div className="grid grid-cols-3 gap-4">
          {[1,2,3].map(i => <div key={i} className="h-20 bg-gray-100 rounded-xl" />)}
        </div>
        <div className="h-64 bg-gray-100 rounded-xl" />
      </div>
    )
  }
  if (!data) return null

  const avgMonthly = data.total_salary && data.monthly_salary?.length
    ? data.total_salary / data.monthly_salary.length
    : 0

  return (
    <div className="p-6">
      <button onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ChevronLeft size={16} /> Back
      </button>
      <PageHeader title="Payroll Report"
        subtitle="Salary register & employee summary — click any row to drill into salary vouchers" />

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KPICard title="Total Salary Paid" value={`₹${INR(data.total_salary)}`} color="blue" />
        <KPICard title="Employees" value={(data.employee_summary?.length || 0).toLocaleString()} color="green" />
        <KPICard title="Avg Monthly" value={`₹${INR(avgMonthly)}`} color="purple" />
        <KPICard title="Payroll Vouchers" value={(data.total_vouchers || 0).toLocaleString()} color="blue" />
      </div>

      {/* Monthly trend */}
      {data.monthly_salary?.length > 0 && (
        <div className="card mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-800">Monthly Salary Trend</h3>
            <p className="text-xs text-gray-400">Click any bar to drill into that month's payroll vouchers</p>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data.monthly_salary} margin={{ top: 4, right: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${(v / 100000).toFixed(0)}L`} />
              <Tooltip formatter={(v: number) => `₹${INR(v)}`} />
              <Bar dataKey="total" name="Salary" fill="#1A56DB" radius={[3, 3, 0, 0]}
                cursor="pointer"
                onClick={(d: any) => openDrill(
                  { voucher_type: 'Payroll' },
                  `Payroll — ${d.month}`
                )}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Employee summary */}
      {data.employee_summary?.length > 0 && (
        <div className="card p-0 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
            <div className="flex items-center gap-2">
              <Users size={15} className="text-gray-500" />
              <h3 className="font-semibold text-gray-800 text-sm">Employee Salary Summary</h3>
            </div>
            <div className="relative">
              <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Search employee…"
                className="border rounded-lg pl-7 pr-3 py-1.5 text-xs focus:ring-2 focus:ring-brand-500 focus:outline-none w-44" />
            </div>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b text-xs">
                <th className="text-left px-4 py-2.5 text-gray-600">#</th>
                <th className="text-left px-3 py-2.5 text-gray-600">Employee</th>
                <th className="text-right px-3 py-2.5 text-gray-600">Total Paid</th>
                <th className="text-right px-3 py-2.5 text-gray-600">Months</th>
                <th className="text-right px-3 py-2.5 text-gray-600">Avg / Month</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filteredEmployees.length === 0 ? (
                <tr><td colSpan={5} className="text-center py-8 text-gray-400">No employees found</td></tr>
              ) : filteredEmployees.map((e: any, i: number) => (
                <tr key={i} className="hover:bg-blue-50 cursor-pointer group"
                  onClick={() => openDrill(
                    { ledger_name: e.employee, voucher_type: 'Payroll' },
                    `${e.employee} — Salary Vouchers`
                  )}>
                  <td className="px-4 py-2.5 text-gray-400 text-xs">{i + 1}</td>
                  <td className="px-3 py-2.5 font-medium text-gray-800">
                    <span className="flex items-center gap-1">
                      {e.employee}
                      <ExternalLink size={11} className="text-gray-300 group-hover:text-blue-500" />
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-right font-semibold text-gray-900">₹{INR(e.total)}</td>
                  <td className="px-3 py-2.5 text-right text-gray-500">{e.months}</td>
                  <td className="px-3 py-2.5 text-right text-gray-600">
                    ₹{INR(e.total / (e.months || 1))}
                  </td>
                </tr>
              ))}
            </tbody>
            {data.employee_summary?.length > 0 && (
              <tfoot className="border-t bg-gray-50">
                <tr className="text-xs font-bold">
                  <td colSpan={2} className="px-4 py-2 text-gray-700">Total</td>
                  <td className="px-3 py-2 text-right text-gray-900">₹{INR(data.total_salary)}</td>
                  <td colSpan={2} />
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      )}

      {drill && (
        <DrillVouchers
          dumpId={dumpId!}
          title={drill.title}
          subtitle="Click any payroll voucher for full breakdown"
          filters={drill.filters}
          onClose={() => setDrill(null)}
        />
      )}
    </div>
  )
}
