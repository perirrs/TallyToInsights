import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import PageHeader from '../../components/UI/PageHeader'
import { RiskBadge, StatusBadge } from '../../components/UI/RiskBadge'
import DrillVouchers, { DrillFilters } from '../../components/DrillVouchers'
import { ChevronLeft, ExternalLink } from 'lucide-react'

const INR = (v: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)

interface Drill { title: string; subtitle?: string; filters: DrillFilters }

export default function CheckDetailPage() {
  const { dumpId, checkId } = useParams<{ dumpId: string; checkId: string }>()
  const navigate = useNavigate()
  const [drill, setDrill] = useState<Drill | null>(null)

  const { data: check, isLoading } = useQuery({
    queryKey: ['audit-check', dumpId, checkId],
    queryFn: () => api.get(`/audit/${dumpId}/checks/${checkId}`).then((r) => r.data),
  })

  function openFinding(f: any) {
    const filters: DrillFilters = {}
    if (f.voucher_no) filters.voucher_number = f.voucher_no
    else if (f.party) filters.ledger_name = f.party
    else if (f.ledger) filters.ledger_name = f.ledger
    if (f.date) { filters.date_from = f.date; filters.date_to = f.date }
    setDrill({
      title: f.voucher_no ? `Voucher ${f.voucher_no}` : (f.party || f.ledger || 'Voucher Detail'),
      subtitle: f.detail,
      filters,
    })
  }

  if (isLoading) return <div className="p-6 text-gray-500">Loading...</div>
  if (!check) return null

  return (
    <div className="p-6">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ChevronLeft size={16} /> Back
      </button>

      <div className="card mb-6">
        <div className="flex items-start gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm text-gray-400">Check #{check.check_id}</span>
              <RiskBadge level={check.risk_level} />
              <StatusBadge status={check.status} />
            </div>
            <h1 className="text-xl font-bold text-gray-900">{check.description}</h1>
            <p className="text-sm text-gray-500 mt-1">Category: {check.category}</p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold text-red-700">{check.finding_count}</p>
            <p className="text-xs text-gray-500">Findings</p>
            {check.amount_at_risk > 0 && (
              <>
                <p className="text-lg font-bold text-red-700 mt-1">{INR(check.amount_at_risk)}</p>
                <p className="text-xs text-gray-500">Amount at Risk</p>
              </>
            )}
          </div>
        </div>
      </div>

      {check.findings?.length > 0 ? (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-800">
              Findings ({check.findings.length}{check.finding_count > check.findings.length ? ` of ${check.finding_count}` : ''})
            </h3>
            <p className="text-xs text-gray-400 flex items-center gap-1">
              <ExternalLink size={11} /> Click any row to view voucher detail
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b">
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-600">Detail</th>
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-600 w-28">Voucher No</th>
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-600 w-24">Date</th>
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-600 w-40">Party</th>
                  <th className="text-right px-4 py-2.5 text-xs font-semibold text-gray-600 w-28">Amount</th>
                  <th className="w-6" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {check.findings.map((f: any, i: number) => (
                  <tr
                    key={i}
                    className="hover:bg-blue-50 cursor-pointer transition-colors"
                    onClick={() => openFinding(f)}
                    title="Click to view voucher detail"
                  >
                    <td className="px-4 py-2.5 text-xs text-gray-800">{f.detail}</td>
                    <td className="px-4 py-2.5 text-xs font-mono text-blue-600 underline decoration-dotted">
                      {f.voucher_no || '—'}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-gray-500">{f.date || '—'}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-700 truncate max-w-[160px]">{f.party || f.ledger || '—'}</td>
                    <td className="px-4 py-2.5 text-xs text-right font-medium text-gray-800">
                      {f.amount ? INR(f.amount) : '—'}
                    </td>
                    <td className="pr-3 text-gray-300">
                      <ExternalLink size={12} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="card text-center py-8 text-gray-400">
          {check.status === 'pass' ? 'All clear — no issues found for this check.' :
           check.status === 'skipped' ? 'This check was skipped (insufficient data or external dependency required).' :
           'No detailed findings available.'}
        </div>
      )}

      {/* Voucher drill-down panel */}
      {drill && (
        <DrillVouchers
          dumpId={dumpId!}
          title={drill.title}
          subtitle={drill.subtitle}
          filters={drill.filters}
          onClose={() => setDrill(null)}
        />
      )}
    </div>
  )
}
