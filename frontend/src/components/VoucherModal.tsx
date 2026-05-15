/**
 * VoucherModal — full voucher detail with Dr/Cr lines.
 * Used across every report page when a user clicks on a voucher row.
 */
import { X, ExternalLink, AlertTriangle } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'

const INR = (v: number) =>
  new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(v)

interface VoucherModalProps {
  dumpId: string
  voucherId: number | null
  onClose: () => void
}

export default function VoucherModal({ dumpId, voucherId, onClose }: VoucherModalProps) {
  const { data: v, isLoading } = useQuery({
    queryKey: ['voucher-detail', dumpId, voucherId],
    queryFn: () =>
      api.get(`/reports/${dumpId}/drill/voucher/${voucherId}`).then((r) => r.data),
    enabled: !!voucherId,
  })

  if (!voucherId) return null

  const debitLines = v?.lines?.filter((l: any) => l.is_debit) ?? []
  const creditLines = v?.lines?.filter((l: any) => !l.is_debit) ?? []
  const debitTotal = debitLines.reduce((s: number, l: any) => s + l.amount, 0)
  const creditTotal = creditLines.reduce((s: number, l: any) => s + l.amount, 0)

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b">
          {isLoading ? (
            <div className="h-8 w-48 bg-gray-100 animate-pulse rounded" />
          ) : (
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs bg-blue-100 text-blue-700 px-2.5 py-0.5 rounded-full font-semibold">
                  {v?.voucher_type}
                </span>
                <span className="font-bold text-gray-900 text-base">
                  {v?.voucher_number || '—'}
                </span>
                {v?.is_cancelled && (
                  <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full flex items-center gap-1">
                    <AlertTriangle size={10} /> CANCELLED
                  </span>
                )}
                {v?.is_optional && (
                  <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full">
                    OPTIONAL
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-500 mt-1">
                {v?.date}
                {v?.party_ledger && (
                  <span className="ml-2 font-medium text-gray-700">{v.party_ledger}</span>
                )}
              </p>
            </div>
          )}
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700 transition-colors flex-shrink-0"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 p-5 space-y-5">
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-6 bg-gray-100 animate-pulse rounded" />
              ))}
            </div>
          ) : (
            <>
              {/* Summary row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-gray-50 rounded-xl p-3">
                  <p className="text-xs text-gray-500 mb-0.5">Amount</p>
                  <p className="font-bold text-gray-900 text-lg">₹{INR(v?.amount)}</p>
                </div>
                <div className="bg-gray-50 rounded-xl p-3">
                  <p className="text-xs text-gray-500 mb-0.5">Reference</p>
                  <p className="text-sm font-medium text-gray-700 truncate">{v?.reference || '—'}</p>
                </div>
                <div className="bg-gray-50 rounded-xl p-3">
                  <p className="text-xs text-gray-500 mb-0.5">Posted By</p>
                  <p className="text-sm font-medium text-gray-700">{v?.posted_by || '—'}</p>
                </div>
                <div className="bg-gray-50 rounded-xl p-3">
                  <p className="text-xs text-gray-500 mb-0.5">Altered By</p>
                  <p className="text-sm font-medium text-gray-700">
                    {v?.altered_by || '—'}
                    {v?.altered_date && (
                      <span className="block text-xs text-gray-400">{v.altered_date}</span>
                    )}
                  </p>
                </div>
              </div>

              {/* Narration */}
              {v?.narration && (
                <div className="bg-blue-50 border border-blue-100 rounded-xl p-3 text-sm text-blue-800 italic">
                  "{v.narration}"
                </div>
              )}

              {/* Dr/Cr Lines */}
              {v?.lines?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                    Accounting Entries
                  </h4>
                  <div className="rounded-xl border overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 border-b text-xs">
                          <th className="text-left px-3 py-2 text-gray-600">Ledger</th>
                          <th className="text-right px-3 py-2 text-green-700">Debit (Dr)</th>
                          <th className="text-right px-3 py-2 text-red-700">Credit (Cr)</th>
                          <th className="text-right px-3 py-2 text-gray-500">GST</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50">
                        {v.lines.map((ln: any, i: number) => (
                          <tr key={i} className="hover:bg-gray-50">
                            <td className="px-3 py-2 text-gray-800 max-w-[220px]">
                              {ln.ledger_name}
                            </td>
                            <td className="px-3 py-2 text-right text-green-700 font-medium">
                              {ln.is_debit ? `₹${INR(ln.amount)}` : '—'}
                            </td>
                            <td className="px-3 py-2 text-right text-red-700 font-medium">
                              {!ln.is_debit ? `₹${INR(ln.amount)}` : '—'}
                            </td>
                            <td className="px-3 py-2 text-right text-gray-400 text-xs">
                              {ln.gst_type ? `${ln.gst_type} ${ln.gst_rate}%` : '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr className="border-t bg-gray-50 font-semibold text-xs">
                          <td className="px-3 py-2 text-gray-600">Total</td>
                          <td className="px-3 py-2 text-right text-green-800">₹{INR(debitTotal)}</td>
                          <td className="px-3 py-2 text-right text-red-800">₹{INR(creditTotal)}</td>
                          <td />
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                  {Math.abs(debitTotal - creditTotal) > 0.5 && (
                    <p className="text-xs text-orange-600 mt-1 flex items-center gap-1">
                      <AlertTriangle size={12} />
                      Entry imbalance: Dr {INR(debitTotal)} ≠ Cr {INR(creditTotal)}
                    </p>
                  )}
                </div>
              )}

              {/* GST & supply info */}
              {(v?.gstin || v?.place_of_supply || v?.is_reverse_charge) && (
                <div className="flex flex-wrap gap-4 text-xs text-gray-500 pt-1 border-t">
                  {v.gstin && (
                    <span>
                      GSTIN: <span className="font-mono text-gray-700">{v.gstin}</span>
                    </span>
                  )}
                  {v.place_of_supply && (
                    <span>
                      Place of Supply: <span className="text-gray-700">{v.place_of_supply}</span>
                    </span>
                  )}
                  {v.is_reverse_charge && (
                    <span className="text-orange-600 font-semibold">⚡ Reverse Charge</span>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
