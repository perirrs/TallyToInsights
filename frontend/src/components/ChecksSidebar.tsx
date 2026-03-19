import { useState, useEffect, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { useChecksStore } from '../store/checksStore'
import clsx from 'clsx'
import {
  CheckSquare, Square, MinusSquare,
  ChevronDown, ChevronRight, RotateCcw, Loader,
  PanelLeftClose, PanelLeftOpen, Shield,
} from 'lucide-react'

interface Props { dumpId: string }

interface CheckResult {
  check_id: number
  description: string
  category: string
  risk_level: string
  status: string
}

export default function ChecksSidebar({ dumpId }: Props) {
  const navigate = useNavigate()
  const location = useLocation()
  const qc = useQueryClient()

  const { getSelection, setSelection, sidebarCollapsed, setSidebarCollapsed } = useChecksStore()
  const storedIds = getSelection(dumpId)

  const [expandedCats, setExpandedCats] = useState<Set<string>>(new Set())
  const [isRechecking, setIsRechecking] = useState(false)

  // ── Data ─────────────────────────────────────────────────────────
  const { data: summary, isLoading } = useQuery({
    queryKey: ['audit-summary', dumpId],
    queryFn: () => api.get(`/audit/${dumpId}/summary`).then((r) => r.data),
    staleTime: 60_000,
  })

  // Poll dump status while rechecking
  const { data: dumpStatus } = useQuery({
    queryKey: ['dump-recheck-status', dumpId],
    queryFn: () => api.get(`/uploads/status/${dumpId}`).then((r) => r.data),
    enabled: isRechecking,
    refetchInterval: isRechecking ? 2000 : false,
  })

  useEffect(() => {
    if (isRechecking && dumpStatus?.status === 'processed') {
      setIsRechecking(false)
      qc.invalidateQueries({ queryKey: ['audit-summary', dumpId] })
    }
  }, [dumpStatus?.status, isRechecking, dumpId, qc])

  const results: CheckResult[] = useMemo(() => summary?.results || [], [summary])
  const allIds = useMemo(() => results.map((r) => r.check_id), [results])

  // Effective selection: null → all selected
  const effectiveSelected = useMemo(
    () => storedIds === null ? new Set(allIds) : new Set(storedIds),
    [storedIds, allIds],
  )

  const isAllSelected = storedIds === null || effectiveSelected.size === allIds.length
  const selectedCount = effectiveSelected.size

  // Category map
  const checksByCategory = useMemo(() => {
    const map: Record<string, CheckResult[]> = {}
    for (const r of results) {
      const cat = r.category || 'Uncategorised'
      if (!map[cat]) map[cat] = []
      map[cat].push(r)
    }
    return map
  }, [results])

  const allCats = useMemo(() => Object.keys(checksByCategory).sort(), [checksByCategory])

  // ── Selection helpers ─────────────────────────────────────────────
  const getCatState = (cat: string): 'all' | 'some' | 'none' => {
    const ids = (checksByCategory[cat] || []).map((c) => c.check_id)
    const n = ids.filter((id) => effectiveSelected.has(id)).length
    if (n === 0) return 'none'
    if (n === ids.length) return 'all'
    return 'some'
  }

  const toggleAll = () => setSelection(dumpId, isAllSelected ? [] : null)

  const toggleCat = (cat: string) => {
    const ids = (checksByCategory[cat] || []).map((c) => c.check_id)
    const allSel = ids.every((id) => effectiveSelected.has(id))
    const next = new Set(effectiveSelected)
    if (allSel) { ids.forEach((id) => next.delete(id)) }
    else { ids.forEach((id) => next.add(id)) }
    setSelection(dumpId, next.size === allIds.length ? null : Array.from(next))
  }

  const toggleCheck = (id: number) => {
    const next = new Set(effectiveSelected)
    next.has(id) ? next.delete(id) : next.add(id)
    setSelection(dumpId, next.size === allIds.length ? null : Array.from(next))
  }

  // ── Navigation ────────────────────────────────────────────────────
  const activeCatFromUrl = new URLSearchParams(location.search).get('cat') || ''
  const isOnAudit = location.pathname.endsWith('/audit')

  const handleCategoryClick = (cat: string) => {
    const target = `/dumps/${dumpId}/audit`
    if (isOnAudit) {
      const p = new URLSearchParams(location.search)
      cat ? p.set('cat', cat) : p.delete('cat')
      navigate({ pathname: target, search: p.toString() }, { replace: true })
    } else {
      navigate(cat ? `${target}?cat=${encodeURIComponent(cat)}` : target)
    }
  }

  const toggleExpand = (cat: string) =>
    setExpandedCats((prev) => { const s = new Set(prev); s.has(cat) ? s.delete(cat) : s.add(cat); return s })

  // ── Re-run ────────────────────────────────────────────────────────
  const handleRerun = async () => {
    const body = storedIds === null ? {} : { check_ids: Array.from(effectiveSelected) }
    setIsRechecking(true)
    try {
      await api.post(`/audit/${dumpId}/rerun`, body)
    } catch (err: any) {
      setIsRechecking(false)
      alert(`Re-run failed: ${err?.response?.data?.detail || err.message}`)
    }
  }

  // ── Collapsed state ───────────────────────────────────────────────
  if (sidebarCollapsed) {
    return (
      <div className="w-10 flex-shrink-0 border-r border-gray-200 bg-gray-50 flex flex-col items-center py-3 gap-3"
        style={{ position: 'sticky', top: 0, height: '100vh' }}>
        <button onClick={() => setSidebarCollapsed(false)} title="Show checks panel"
          className="p-1.5 rounded text-gray-400 hover:text-brand-600 hover:bg-brand-50">
          <PanelLeftOpen size={15} />
        </button>
        <Shield size={14} className="text-gray-300" />
        {selectedCount > 0 && (
          <span className="text-xs font-bold text-brand-600 writing-mode-vertical" style={{ writingMode: 'vertical-rl' }}>
            {selectedCount}
          </span>
        )}
      </div>
    )
  }

  return (
    <aside
      className="w-56 flex-shrink-0 border-r border-gray-200 bg-gray-50 flex flex-col"
      style={{ position: 'sticky', top: 0, height: '100vh', overflowY: 'auto' }}
    >
      {/* Header */}
      <div className="px-3 py-2.5 border-b border-gray-200 bg-white flex-shrink-0">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-800">Checks</span>
          <div className="flex items-center gap-2">
            <button onClick={toggleAll}
              className="text-xs text-brand-600 hover:text-brand-800 font-medium">
              {isAllSelected ? 'Deselect all' : 'Select all'}
            </button>
            <button onClick={() => setSidebarCollapsed(true)} title="Collapse"
              className="text-gray-400 hover:text-gray-600">
              <PanelLeftClose size={13} />
            </button>
          </div>
        </div>
        <p className="text-xs text-gray-400 mt-0.5">
          {isLoading ? 'Loading...' : `${selectedCount} of ${allIds.length} selected`}
        </p>
      </div>

      {/* All Categories */}
      <button
        onClick={() => handleCategoryClick('')}
        className={clsx(
          'flex items-center justify-between w-full text-left px-3 py-2 text-xs font-medium border-b border-gray-100 flex-shrink-0',
          !activeCatFromUrl && isOnAudit
            ? 'bg-brand-50 text-brand-700'
            : 'text-gray-600 hover:bg-gray-100',
        )}
      >
        <span>All Categories</span>
        <span className="text-gray-400">{results.length}</span>
      </button>

      {/* Category list */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-gray-400">
            <Loader size={14} className="animate-spin mr-1.5" /> Loading...
          </div>
        ) : allCats.length === 0 ? (
          <div className="p-4 text-center text-xs text-gray-400">
            <Shield size={24} className="mx-auto mb-2 opacity-30" />
            No audit results yet.<br />Run the audit to see checks.
          </div>
        ) : (
          allCats.map((cat) => {
            const catResults = checksByCategory[cat] || []
            const state = getCatState(cat)
            const expanded = expandedCats.has(cat)
            const failCount = catResults.filter((r) => r.status === 'fail' || r.status === 'warning').length
            const isActive = activeCatFromUrl === cat && isOnAudit

            return (
              <div key={cat} className="border-b border-gray-100 last:border-b-0">
                <div className={clsx(
                  'flex items-center gap-1.5 px-2 py-1.5',
                  isActive ? 'bg-brand-50' : 'hover:bg-gray-100',
                )}>
                  {/* Category checkbox */}
                  <button onClick={() => toggleCat(cat)}
                    className="flex-shrink-0 text-gray-400 hover:text-brand-600">
                    {state === 'all'
                      ? <CheckSquare size={12} className="text-brand-600" />
                      : state === 'some'
                      ? <MinusSquare size={12} className="text-amber-500" />
                      : <Square size={12} />}
                  </button>

                  {/* Category name → navigate/filter */}
                  <button
                    onClick={() => handleCategoryClick(cat)}
                    className="flex-1 flex items-center justify-between text-left min-w-0 gap-1"
                  >
                    <span className={clsx(
                      'text-xs font-medium truncate',
                      isActive ? 'text-brand-700' : 'text-gray-700',
                    )}>{cat}</span>
                    {failCount > 0 && (
                      <span className="text-xs text-red-500 font-semibold flex-shrink-0">{failCount}</span>
                    )}
                  </button>

                  {/* Expand toggle */}
                  <button onClick={() => toggleExpand(cat)}
                    className="flex-shrink-0 text-gray-400 hover:text-gray-600 p-0.5">
                    {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
                  </button>
                </div>

                {/* Individual checks */}
                {expanded && (
                  <div className="bg-white border-t border-gray-50">
                    {catResults.map((r) => (
                      <div
                        key={r.check_id}
                        onClick={() => toggleCheck(r.check_id)}
                        className="flex items-start gap-1.5 px-5 py-1.5 hover:bg-gray-50 cursor-pointer"
                      >
                        <div className="flex-shrink-0 mt-0.5 text-gray-400">
                          {effectiveSelected.has(r.check_id)
                            ? <CheckSquare size={10} className="text-brand-600" />
                            : <Square size={10} />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-gray-600 leading-snug line-clamp-2">{r.description}</p>
                          <span className={clsx(
                            'text-xs px-1 rounded mt-0.5 inline-block',
                            r.status === 'fail' ? 'bg-red-100 text-red-600'
                              : r.status === 'warning' ? 'bg-yellow-100 text-yellow-600'
                              : r.status === 'pass' ? 'bg-green-100 text-green-600'
                              : 'bg-gray-100 text-gray-500',
                          )}>{r.status}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-gray-200 p-2.5 bg-white flex-shrink-0">
        {isRechecking ? (
          <div className="flex items-center justify-center gap-1.5 text-xs text-purple-600 py-1">
            <Loader size={12} className="animate-spin" /> Rechecking...
          </div>
        ) : (
          <button
            onClick={handleRerun}
            disabled={selectedCount === 0}
            className="w-full flex items-center justify-center gap-1.5 text-xs font-medium bg-purple-600 hover:bg-purple-700 disabled:opacity-40 text-white rounded-lg py-2 transition-colors"
          >
            <RotateCcw size={11} />
            {isAllSelected ? 'Re-run all checks' : `Re-run ${selectedCount} checks`}
          </button>
        )}
      </div>
    </aside>
  )
}
