/**
 * DrillVouchers — slide-over panel that shows vouchers matching any drill-down filter.
 * Used across ALL report pages to provide "n-layer" drill-down:
 *   Report summary  →  DrillVouchers (list)  →  VoucherModal (full detail)
 */
import { useState } from 'react'
import { X, ChevronRight, Search, RotateCcw } from 'lucide-react'
import { useQuery, keepPreviousData } from '@tanstack/react-query'
import api from '../api/client'
import VoucherModal from './VoucherModal'

interface DrillPage {
  items: any[]
  total: number
}

const INR = (v: number) =>
  new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(v)

export interface DrillFilters {
  ledger_name?: string
  voucher_type?: string
  date_from?: string
  date_to?: string
  min_amount?: number
  narration?: string
}

interface DrillVouchersProps {
  dumpId: string
  title: string
  subtitle?: string
  filters: DrillFilters
  onClose: () => void
}

const PAGE_SIZE = 30

export default function DrillVouchers({
  dumpId,
  title,
  subtitle,
  filters,
  onClose,
}: DrillVouchersProps) {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [selectedVoucherId, setSelectedVoucherId] = useState<number | null>(null)

  const activeFilters: DrillFilters = {
    ...filters,
    ...(search ? { ledger_name: search } : {}),
  }

  const { data, isLoading } = useQuery<DrillPage>({
    queryKey: ['drill-vouchers', dumpId, activeFilters, page],
    queryFn: () =>
      api
        .get(`/reports/${dumpId}/drill/vouchers`, {
          params: {
            page,
            page_size: PAGE_SIZE,
            ...activeFilters,
          },
        })
        .then((r) => r.data),
    placeholderData: keepPreviousData,
  })

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Slide-over panel */}
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-2xl flex flex-col bg-white shadow-2xl border-l">
        {/* Header */}
        <div className="flex items-start justify-between px-5 py-4 border-b bg-gray-50">
          <div>
            <h2 className="font-bold text-gray-900 text-base">{title}</h2>
            {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
            {data && (
              <p className="text-xs text-blue-600 mt-1 font-medium">
                {data.total.toLocaleString()} voucher{data.total !== 1 ? 's' : ''} found
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-200 text-gray-400 hover:text-gray-700 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Active filter chips */}
        <div className="px-5 py-2 border-b flex flex-wrap gap-1.5 bg-white">
          {Object.entries(filters).map(([k, v]) =>
            v ? (
              <span
                key={k}
                className="text-xs bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full"
              >
                {k.replace(/_/g, ' ')}: {String(v)}
              </span>
            ) : null
          )}
          {/* In-panel search */}
          <div className="ml-auto relative">
            <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
              placeholder="Refine by ledger…"
              className="border rounded-full pl-6 pr-3 py-0.5 text-xs focus:ring-2 focus:ring-brand-500 focus:outline-none w-40"
            />
          </div>
        </div>

        {/* Voucher list */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="space-y-2 p-5">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="h-12 bg-gray-100 animate-pulse rounded-lg" />
              ))}
            </div>
          ) : data?.items?.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-gray-400">
              <RotateCcw size={32} className="mb-2 opacity-40" />
              <p className="text-sm">No vouchers match these filters</p>
            </div>
          ) : (
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-gray-50 border-b z-10">
                <tr>
                  <th className="text-left px-4 py-2.5 text-gray-600">Date</th>
                  <th className="text-left px-3 py-2.5 text-gray-600">Type</th>
                  <th className="text-left px-3 py-2.5 text-gray-600">Voucher No</th>
                  <th className="text-left px-3 py-2.5 text-gray-600 max-w-[140px]">Party</th>
                  <th className="text-right px-4 py-2.5 text-gray-600">Amount</th>
                  <th className="w-6" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {data?.items?.map((v: any) => (
                  <tr
                    key={v.id}
                    className="hover:bg-blue-50 cursor-pointer transition-colors"
                    onClick={() => setSelectedVoucherId(v.id)}
                  >
                    <td className="px-4 py-2.5 text-gray-600 whitespace-nowrap">{v.date}</td>
                    <td className="px-3 py-2.5">
                      <span className="bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded text-xs">
                        {v.voucher_type}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 font-mono text-gray-500">
                      {v.voucher_number || '—'}
                    </td>
                    <td className="px-3 py-2.5 text-gray-800 max-w-[140px] truncate">
                      {v.party_ledger || <span className="text-gray-400">—</span>}
                    </td>
                    <td className="px-4 py-2.5 text-right font-semibold text-gray-900">
                      {v.is_cancelled ? (
                        <span className="line-through text-gray-400">₹{INR(v.amount)}</span>
                      ) : (
                        `₹${INR(v.amount)}`
                      )}
                    </td>
                    <td className="pr-3">
                      <ChevronRight size={14} className="text-gray-300" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {data && totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-3 border-t bg-gray-50 text-xs text-gray-600">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="px-3 py-1.5 border rounded-lg disabled:opacity-40 hover:bg-white transition-colors"
            >
              ← Prev
            </button>
            <span>
              Page {page} of {totalPages} &nbsp;·&nbsp; {data.total.toLocaleString()} total
            </span>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1.5 border rounded-lg disabled:opacity-40 hover:bg-white transition-colors"
            >
              Next →
            </button>
          </div>
        )}
      </div>

      {/* Voucher detail modal (layer 2) */}
      {selectedVoucherId && (
        <VoucherModal
          dumpId={dumpId}
          voucherId={selectedVoucherId}
          onClose={() => setSelectedVoucherId(null)}
        />
      )}
    </>
  )
}
