import { useState, useCallback, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import api from '../api/client'
import PageHeader from '../components/UI/PageHeader'
import { Upload, FileText, CheckCircle, XCircle, Loader, BarChart3, RefreshCw, Trash2, ChevronLeft, RotateCcw, ListChecks, X, ChevronDown, ChevronRight as ChevronRightIcon, Square, CheckSquare, MinusSquare } from 'lucide-react'
import clsx from 'clsx'

interface Dump {
  id: number
  filename: string
  file_format: string
  period_from: string | null
  period_to: string | null
  financial_year: string | null
  status: string
  voucher_count: number
  ledger_count: number
  uploaded_at: string
  processed_at: string | null
}

interface AuditCheck {
  id: number
  desc: string
  category: string
  risk: string
}

export default function UploadsPage() {
  const { companyId } = useParams<{ companyId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [periodFrom, setPeriodFrom] = useState('')
  const [periodTo, setPeriodTo] = useState('')
  const [financialYear, setFinancialYear] = useState('')
  const [uploading, setUploading] = useState(false)

  // Checks panel state
  const [showChecksPanel, setShowChecksPanel] = useState(false)
  const [selectedCheckIds, setSelectedCheckIds] = useState<Set<number> | null>(null) // null = all
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())

  const { data: dumps = [], isLoading } = useQuery<Dump[]>({
    queryKey: ['dumps', companyId],
    queryFn: () => api.get(`/uploads/${companyId}`).then((r) => r.data),
    refetchInterval: (query) => {
      const d = query.state.data
      if (d?.some((d) => ['processing', 'uploaded', 'auditing'].includes(d.status))) return 3000
      return false
    },
  })

  // Load all checks for the panel (fetched once when panel opens)
  const { data: allChecksData } = useQuery({
    queryKey: ['all-checks-for-panel'],
    queryFn: () => api.get('/audit-checks/', { params: { page: 1, page_size: 9999 } }).then((r) => r.data),
    enabled: showChecksPanel,
    staleTime: 60_000,
  })
  const allChecks: AuditCheck[] = allChecksData?.items || []

  // Group checks by category
  const checksByCategory = useMemo(() => {
    const map: Record<string, AuditCheck[]> = {}
    for (const c of allChecks) {
      const cat = c.category || 'Uncategorized'
      if (!map[cat]) map[cat] = []
      map[cat].push(c)
    }
    return map
  }, [allChecks])

  const allCheckIds = useMemo(() => allChecks.map((c) => c.id), [allChecks])

  // Effective selection: null means all selected, set means specific ones
  const effectiveSelected = selectedCheckIds ?? new Set(allCheckIds)

  const isAllSelected = selectedCheckIds === null || selectedCheckIds.size === allCheckIds.length
  const selectedCount = selectedCheckIds === null ? allCheckIds.length : selectedCheckIds.size

  const toggleSelectAll = () => {
    if (isAllSelected) {
      setSelectedCheckIds(new Set()) // deselect all
    } else {
      setSelectedCheckIds(null) // select all
    }
  }

  const toggleCategory = (cat: string) => {
    const catIds = (checksByCategory[cat] || []).map((c) => c.id)
    const allCatSelected = catIds.every((id) => effectiveSelected.has(id))
    const next = new Set(effectiveSelected)
    if (allCatSelected) {
      catIds.forEach((id) => next.delete(id))
    } else {
      catIds.forEach((id) => next.add(id))
    }
    setSelectedCheckIds(next.size === allCheckIds.length ? null : next)
  }

  const toggleCheck = (id: number) => {
    const next = new Set(effectiveSelected)
    next.has(id) ? next.delete(id) : next.add(id)
    setSelectedCheckIds(next.size === allCheckIds.length ? null : next)
  }

  const toggleCategoryExpand = (cat: string) => {
    setExpandedCategories((prev) => {
      const s = new Set(prev)
      s.has(cat) ? s.delete(cat) : s.add(cat)
      return s
    })
  }

  const getCategoryState = (cat: string): 'all' | 'some' | 'none' => {
    const catIds = (checksByCategory[cat] || []).map((c) => c.id)
    const selCount = catIds.filter((id) => effectiveSelected.has(id)).length
    if (selCount === 0) return 'none'
    if (selCount === catIds.length) return 'all'
    return 'some'
  }

  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [recheckingAll, setRecheckingAll] = useState(false)

  const deleteDump = useMutation({
    mutationFn: (dumpId: number) => api.delete(`/uploads/${dumpId}`),
    onSuccess: () => { setDeletingId(null); qc.invalidateQueries({ queryKey: ['dumps', companyId] }) },
    onError: (err: any) => { setDeletingId(null); alert(`Delete failed: ${err?.response?.data?.detail || err.message || 'Unknown error'}`) },
  })

  const buildRecheckBody = () =>
    selectedCheckIds === null ? {} : { check_ids: Array.from(selectedCheckIds) }

  const recheckDump = useMutation({
    mutationFn: (dumpId: number) => api.post(`/audit/${dumpId}/rerun`, buildRecheckBody()),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dumps', companyId] }),
    onError: (err: any) => { alert(`Recheck failed: ${err?.response?.data?.detail || err.message || 'Unknown error'}`) },
  })

  const handleRecheckAll = async () => {
    const recheckable = dumps.filter((d) => ['processed', 'failed'].includes(d.status))
    if (recheckable.length === 0) return
    setRecheckingAll(true)
    try {
      await Promise.all(recheckable.map((d) => api.post(`/audit/${d.id}/rerun`, buildRecheckBody())))
      qc.invalidateQueries({ queryKey: ['dumps', companyId] })
    } catch (err: any) {
      alert(`Recheck all failed: ${err?.response?.data?.detail || err.message || 'Unknown error'}`)
    } finally {
      setRecheckingAll(false)
    }
  }

  const onDrop = useCallback(async (files: File[]) => {
    if (!files[0]) return
    setUploading(true)
    const formData = new FormData()
    formData.append('file', files[0])
    if (periodFrom) formData.append('period_from', periodFrom)
    if (periodTo) formData.append('period_to', periodTo)
    if (financialYear) formData.append('financial_year', financialYear)
    try {
      await api.post(`/uploads/${companyId}`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      qc.invalidateQueries({ queryKey: ['dumps', companyId] })
    } finally {
      setUploading(false)
    }
  }, [companyId, periodFrom, periodTo, financialYear])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/xml': ['.xml'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/csv': ['.csv'],
      'application/json': ['.json'],
    },
    multiple: false,
  })

  const StatusIcon = ({ status }: { status: string }) => {
    if (status === 'processed') return <CheckCircle size={16} className="text-green-500" />
    if (status === 'failed') return <XCircle size={16} className="text-red-500" />
    if (status === 'processing') return <Loader size={16} className="text-blue-500 animate-spin" />
    if (status === 'auditing') return <RotateCcw size={16} className="text-purple-500 animate-spin" />
    return <RefreshCw size={16} className="text-gray-400 animate-spin" />
  }

  const handleDeleteDump = (dump: Dump) => {
    if (window.confirm(`Delete "${dump.filename}"? This will remove all vouchers, ledgers and audit results. This cannot be undone.`)) {
      setDeletingId(dump.id)
      deleteDump.mutate(dump.id)
    }
  }

  return (
    <div className="p-6">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ChevronLeft size={16} /> Back to Companies
      </button>

      <PageHeader title="Data Dumps" subtitle={`Tally exports for Company #${companyId}`} />

      {/* Upload Zone */}
      <div className="card mb-6">
        <h3 className="font-semibold text-gray-800 mb-4">Upload Tally Dump</h3>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Period From</label>
            <input type="date" value={periodFrom} onChange={(e) => setPeriodFrom(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Period To</label>
            <input type="date" value={periodTo} onChange={(e) => setPeriodTo(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Financial Year (e.g. 2023-24)</label>
            <input value={financialYear} onChange={(e) => setFinancialYear(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" placeholder="2023-24" />
          </div>
        </div>
        <div {...getRootProps()} className={clsx('border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors', isDragActive ? 'border-brand-500 bg-brand-50' : 'border-gray-300 hover:border-brand-400 hover:bg-gray-50')}>
          <input {...getInputProps()} />
          {uploading ? (
            <div className="flex flex-col items-center gap-2 text-brand-600">
              <Loader size={36} className="animate-spin" />
              <p className="text-sm font-medium">Uploading & processing...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 text-gray-500">
              <Upload size={36} className="text-gray-400" />
              <p className="text-sm font-medium">{isDragActive ? 'Drop file here' : 'Drag & drop or click to upload'}</p>
              <p className="text-xs text-gray-400">Supports XML, XLSX, XLS, CSV, JSON (max 200MB)</p>
            </div>
          )}
        </div>
      </div>

      {/* Dumps List */}
      {isLoading ? (
        <div className="text-center text-gray-500 py-8">Loading...</div>
      ) : dumps.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <FileText size={48} className="mx-auto mb-4 opacity-50" />
          <p>No data dumps yet. Upload your first Tally export above.</p>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-gray-500">{dumps.length} dump{dumps.length !== 1 ? 's' : ''}</p>
            <div className="flex items-center gap-2">
              {/* Checks configuration button */}
              <button
                onClick={() => setShowChecksPanel(true)}
                className={clsx(
                  'flex items-center gap-1.5 text-xs font-medium border rounded-lg px-3 py-1.5 transition-colors',
                  selectedCheckIds !== null
                    ? 'text-orange-600 border-orange-300 bg-orange-50 hover:border-orange-400'
                    : 'text-gray-600 border-gray-200 hover:border-gray-400 hover:text-gray-800'
                )}
              >
                <ListChecks size={12} />
                {selectedCheckIds !== null
                  ? `${selectedCheckIds.size} of ${allCheckIds.length} checks`
                  : `All ${allCheckIds.length || ''} checks`}
              </button>

              {dumps.some((d) => ['processed', 'failed'].includes(d.status)) && (
                <button
                  onClick={handleRecheckAll}
                  disabled={recheckingAll || dumps.some((d) => d.status === 'auditing')}
                  className="flex items-center gap-1.5 text-xs font-medium text-purple-600 hover:text-purple-800 border border-purple-200 hover:border-purple-400 rounded-lg px-3 py-1.5 transition-colors disabled:opacity-50"
                >
                  {recheckingAll || dumps.some((d) => d.status === 'auditing')
                    ? <Loader size={12} className="animate-spin" />
                    : <RotateCcw size={12} />}
                  Recheck All
                </button>
              )}
            </div>
          </div>

          <div className="space-y-3">
            {dumps.map((dump) => (
              <div key={dump.id} className="card">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <StatusIcon status={dump.status} />
                    <div>
                      <p className="font-medium text-gray-900 text-sm">{dump.filename}</p>
                      <p className="text-xs text-gray-500">
                        {dump.financial_year && <span className="mr-2">FY: {dump.financial_year}</span>}
                        {dump.period_from && <span>{dump.period_from} → {dump.period_to}</span>}
                        <span className="ml-2 capitalize bg-gray-100 px-2 py-0.5 rounded text-xs">{dump.file_format}</span>
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right text-xs text-gray-500">
                      <p>{dump.voucher_count.toLocaleString()} vouchers</p>
                      <p>{dump.ledger_count.toLocaleString()} ledgers</p>
                    </div>
                    {dump.status === 'processed' && (
                      <button onClick={() => navigate(`/dumps/${dump.id}/dashboard`)} className="btn-primary text-xs flex items-center gap-1">
                        <BarChart3 size={12} /> View Reports
                      </button>
                    )}
                    {dump.status === 'processing' && <span className="text-xs text-blue-600 font-medium">Processing...</span>}
                    {dump.status === 'auditing' && (
                      <span className="text-xs text-purple-600 font-medium flex items-center gap-1">
                        <Loader size={11} className="animate-spin" /> Rechecking...
                      </span>
                    )}
                    {dump.status === 'failed' && <span className="text-xs text-red-600 font-medium">Failed</span>}
                    {['processed', 'failed'].includes(dump.status) && (
                      <button
                        onClick={() => recheckDump.mutate(dump.id)}
                        disabled={recheckDump.isPending}
                        title={selectedCheckIds !== null ? `Recheck ${selectedCheckIds.size} selected checks` : 'Recheck all checks'}
                        className="p-1.5 rounded-md text-gray-400 hover:text-purple-600 hover:bg-purple-50 transition-colors disabled:opacity-50"
                      >
                        <RotateCcw size={14} />
                      </button>
                    )}
                    <button
                      onClick={() => handleDeleteDump(dump)}
                      disabled={deletingId === dump.id}
                      title="Delete dump"
                      className="p-1.5 rounded-md text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
                    >
                      {deletingId === dump.id ? <Loader size={14} className="animate-spin text-red-500" /> : <Trash2 size={14} />}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Checks slide-over panel */}
      {showChecksPanel && (
        <div className="fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div className="flex-1 bg-black/30" onClick={() => setShowChecksPanel(false)} />

          {/* Panel */}
          <div className="w-96 bg-white shadow-2xl flex flex-col h-full">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
              <div>
                <h3 className="font-semibold text-gray-900 text-sm">Configure Checks</h3>
                <p className="text-xs text-gray-500 mt-0.5">{selectedCount} of {allCheckIds.length} checks selected</p>
              </div>
              <button onClick={() => setShowChecksPanel(false)} className="p-1 rounded hover:bg-gray-200 text-gray-500">
                <X size={16} />
              </button>
            </div>

            {/* Select All / Deselect All */}
            <div className="flex items-center gap-2 px-4 py-2.5 border-b bg-white">
              <button
                onClick={toggleSelectAll}
                className="flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:text-brand-800"
              >
                {isAllSelected ? <CheckSquare size={13} className="text-brand-600" /> : <Square size={13} className="text-gray-400" />}
                {isAllSelected ? 'Deselect All' : 'Select All'}
              </button>
              {selectedCheckIds !== null && selectedCheckIds.size === 0 && (
                <span className="text-xs text-orange-500 ml-auto">No checks selected — recheck will be skipped</span>
              )}
            </div>

            {/* Categories + checks */}
            <div className="flex-1 overflow-y-auto">
              {allChecks.length === 0 ? (
                <div className="flex items-center justify-center h-32 text-gray-400 text-sm">
                  <Loader size={16} className="animate-spin mr-2" /> Loading checks...
                </div>
              ) : (
                Object.entries(checksByCategory).sort(([a], [b]) => a.localeCompare(b)).map(([cat, checks]) => {
                  const state = getCategoryState(cat)
                  const expanded = expandedCategories.has(cat)
                  return (
                    <div key={cat} className="border-b last:border-b-0">
                      {/* Category row */}
                      <div className="flex items-center gap-2 px-4 py-2.5 hover:bg-gray-50 cursor-pointer group">
                        <button
                          onClick={() => toggleCategory(cat)}
                          className="flex-shrink-0 text-gray-400 hover:text-brand-600"
                        >
                          {state === 'all'
                            ? <CheckSquare size={14} className="text-brand-600" />
                            : state === 'some'
                            ? <MinusSquare size={14} className="text-brand-400" />
                            : <Square size={14} />}
                        </button>
                        <button
                          onClick={() => toggleCategoryExpand(cat)}
                          className="flex-1 flex items-center justify-between text-left"
                        >
                          <span className="text-xs font-semibold text-gray-800">{cat}</span>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-400">{checks.filter((c) => effectiveSelected.has(c.id)).length}/{checks.length}</span>
                            {expanded ? <ChevronDown size={12} className="text-gray-400" /> : <ChevronRightIcon size={12} className="text-gray-400" />}
                          </div>
                        </button>
                      </div>

                      {/* Individual checks */}
                      {expanded && (
                        <div className="bg-gray-50 border-t">
                          {checks.map((check) => (
                            <div
                              key={check.id}
                              onClick={() => toggleCheck(check.id)}
                              className="flex items-start gap-2 px-6 py-2 hover:bg-gray-100 cursor-pointer"
                            >
                              <div className="flex-shrink-0 mt-0.5 text-gray-400">
                                {effectiveSelected.has(check.id)
                                  ? <CheckSquare size={12} className="text-brand-600" />
                                  : <Square size={12} />}
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="text-xs text-gray-700 leading-snug line-clamp-2">{check.desc}</p>
                                <span className={clsx(
                                  'inline-block mt-0.5 text-xs px-1.5 rounded',
                                  check.risk === 'High' ? 'bg-red-100 text-red-600' : check.risk === 'Medium' ? 'bg-yellow-100 text-yellow-600' : 'bg-green-100 text-green-600'
                                )}>
                                  {check.risk}
                                </span>
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
            <div className="border-t px-4 py-3 bg-gray-50 flex items-center justify-between">
              <button onClick={() => { setSelectedCheckIds(null); setShowChecksPanel(false) }} className="text-xs text-gray-500 hover:text-gray-700 underline">
                Reset to all
              </button>
              <button onClick={() => setShowChecksPanel(false)} className="btn-primary text-xs">
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
