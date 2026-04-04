import { useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import api from '../api/client'
import PageHeader from '../components/UI/PageHeader'
import { Upload, FileText, CheckCircle, XCircle, Loader, BarChart3, RefreshCw, Trash2, ChevronLeft, RotateCcw, AlertCircle } from 'lucide-react'
import clsx from 'clsx'

// All Tally-related and standard file extensions accepted
const ALLOWED_EXTENSIONS = [
  '.1800',  // Tally data files (Manager, TranMgr, VchStatus, etc.)
  '.tsf',   // Tally Synchronization Format (XML-based)
  '.900',   // Older Tally data files
  '.xml',   // Tally XML export
  '.xlsx',  // Excel
  '.xls',   // Excel (legacy)
  '.csv',   // CSV export
  '.json',  // JSON export
]

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
  progress_pct: number
  progress_stage: string | null
}

interface UploadState {
  current: number
  total: number
  currentName: string
  errors: string[]
}

export default function UploadsPage() {
  const { companyId } = useParams<{ companyId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [periodFrom, setPeriodFrom] = useState('')
  const [periodTo, setPeriodTo] = useState('')
  const [financialYear, setFinancialYear] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadState, setUploadState] = useState<UploadState | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [recheckingAll, setRecheckingAll] = useState(false)

  const { data: dumps = [], isLoading } = useQuery<Dump[]>({
    queryKey: ['dumps', companyId],
    queryFn: () => api.get(`/uploads/${companyId}`).then((r) => r.data),
    refetchInterval: (query) => {
      const d = query.state.data
      if (d?.some((d) => ['processing', 'uploaded', 'auditing'].includes(d.status))) return 1500
      return false
    },
  })

  const deleteDump = useMutation({
    mutationFn: (dumpId: number) => api.delete(`/uploads/${dumpId}`),
    onSuccess: () => { setDeletingId(null); qc.invalidateQueries({ queryKey: ['dumps', companyId] }) },
    onError: (err: any) => { setDeletingId(null); alert(`Delete failed: ${err?.response?.data?.detail || err.message || 'Unknown error'}`) },
  })

  const recheckDump = useMutation({
    mutationFn: (dumpId: number) => api.post(`/audit/${dumpId}/rerun`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dumps', companyId] }),
    onError: (err: any) => { alert(`Recheck failed: ${err?.response?.data?.detail || err.message || 'Unknown error'}`) },
  })

  const handleRecheckAll = async () => {
    const recheckable = dumps.filter((d) => ['processed', 'failed'].includes(d.status))
    if (recheckable.length === 0) return
    setRecheckingAll(true)
    try {
      await Promise.all(recheckable.map((d) => api.post(`/audit/${d.id}/rerun`)))
      qc.invalidateQueries({ queryKey: ['dumps', companyId] })
    } catch (err: any) {
      alert(`Recheck all failed: ${err?.response?.data?.detail || err.message || 'Unknown error'}`)
    } finally {
      setRecheckingAll(false)
    }
  }

  const onDrop = useCallback(async (accepted: File[]) => {
    if (!accepted.length) return
    setUploading(true)
    const errors: string[] = []

    for (let i = 0; i < accepted.length; i++) {
      const file = accepted[i]
      setUploadState({ current: i + 1, total: accepted.length, currentName: file.name, errors })

      const formData = new FormData()
      formData.append('file', file)
      if (periodFrom) formData.append('period_from', periodFrom)
      if (periodTo) formData.append('period_to', periodTo)
      if (financialYear) formData.append('financial_year', financialYear)
      try {
        await api.post(`/uploads/${companyId}`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 0, // no timeout for large files
        })
      } catch (err: any) {
        errors.push(`${file.name}: ${err?.response?.data?.detail || err.message || 'Upload failed'}`)
      }
    }

    qc.invalidateQueries({ queryKey: ['dumps', companyId] })
    setUploadState(null)
    setUploading(false)

    if (errors.length) {
      alert(`Upload complete.\n\n${errors.length} file(s) failed:\n${errors.join('\n')}`)
    }
  }, [companyId, periodFrom, periodTo, financialYear])

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    multiple: true,
    // Validate by extension — avoids MIME-type issues with Tally binary files
    validator: (file) => {
      const ext = '.' + (file.name.split('.').pop() || '').toLowerCase()
      if (!ALLOWED_EXTENSIONS.includes(ext)) {
        return { code: 'file-invalid-type', message: `${file.name}: unsupported file type` }
      }
      return null
    },
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
        <h3 className="font-semibold text-gray-800 mb-4">Upload Tally Data</h3>
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

        <div
          {...getRootProps()}
          className={clsx(
            'border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors',
            isDragActive ? 'border-brand-500 bg-brand-50' : 'border-gray-300 hover:border-brand-400 hover:bg-gray-50',
          )}
        >
          <input {...getInputProps()} />

          {uploading && uploadState ? (
            <div className="flex flex-col items-center gap-3">
              <Loader size={36} className="animate-spin text-brand-600" />
              <p className="text-sm font-medium text-brand-600">
                Uploading {uploadState.current} of {uploadState.total}…
              </p>
              <p className="text-xs text-gray-500 max-w-xs truncate">{uploadState.currentName}</p>
              <div className="w-48 h-1.5 bg-brand-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand-500 rounded-full transition-all duration-300"
                  style={{ width: `${(uploadState.current / uploadState.total) * 100}%` }}
                />
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 text-gray-500">
              <Upload size={36} className="text-gray-400" />
              <p className="text-sm font-medium">
                {isDragActive ? 'Drop files here' : 'Drag & drop files or click to select'}
              </p>
              <p className="text-xs text-gray-400">Select multiple files at once — each uploads as a separate entry</p>
            </div>
          )}
        </div>

        {/* Format guidance */}
        <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
          <div className="rounded-lg bg-green-50 border border-green-200 p-3">
            <p className="font-semibold text-green-800 mb-1">✓ Produces full reports</p>
            <p className="text-green-700">
              <strong>.xml</strong> — Tally XML Export (recommended)<br />
              <strong>.xlsx / .xls</strong> — Excel export from Tally<br />
              <strong>.csv / .json</strong> — Tally data exports
            </p>
            <p className="text-green-600 mt-2 text-xs italic">
              In Tally: Gateway → Export → Data → All Vouchers → XML
            </p>
          </div>
          <div className="rounded-lg bg-amber-50 border border-amber-200 p-3">
            <p className="font-semibold text-amber-800 mb-1">⚠ Stored only — no reports</p>
            <p className="text-amber-700">
              <strong>.1800 / .900</strong> — Tally internal binary files<br />
              <strong>.tsf</strong> — Tally sync metadata files
            </p>
            <p className="text-amber-600 mt-2 text-xs italic">
              These are Tally's internal storage files and cannot be parsed for financial data.
            </p>
          </div>
        </div>

        {/* Show rejected files */}
        {fileRejections.length > 0 && !uploading && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center gap-1.5 text-red-700 text-xs font-medium mb-1">
              <AlertCircle size={13} /> {fileRejections.length} file(s) not accepted:
            </div>
            <ul className="text-xs text-red-600 space-y-0.5 list-disc list-inside">
              {fileRejections.slice(0, 5).map(({ file, errors }) => (
                <li key={file.name}>{file.name} — {errors[0]?.message}</li>
              ))}
              {fileRejections.length > 5 && <li>…and {fileRejections.length - 5} more</li>}
            </ul>
          </div>
        )}
      </div>

      {/* Dumps List */}
      {isLoading ? (
        <div className="text-center text-gray-500 py-8">Loading...</div>
      ) : dumps.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <FileText size={48} className="mx-auto mb-4 opacity-50" />
          <p>No data dumps yet. Upload your Tally files above.</p>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-gray-500">{dumps.length} dump{dumps.length !== 1 ? 's' : ''}</p>
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
                    {dump.status === 'processed' && dump.voucher_count > 0 && (
                      <button onClick={() => navigate(`/dumps/${dump.id}/dashboard`)} className="btn-primary text-xs flex items-center gap-1">
                        <BarChart3 size={12} /> View Reports
                      </button>
                    )}
                    {dump.status === 'processed' && dump.voucher_count === 0 && dump.file_format === 'tally_native' && (
                      <span className="text-xs text-amber-600 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded" title="Binary Tally file — export as XML from Tally for reports">
                        No data — binary format
                      </span>
                    )}
                    {dump.status === 'processed' && dump.voucher_count === 0 && dump.file_format === 'xml' && (
                      <span className="text-xs text-gray-500" title="No vouchers found in this file">
                        No financial data in file
                      </span>
                    )}
                    {dump.status === 'processing' && (
                      <div className="text-right min-w-[160px]">
                        <p className="text-xs text-blue-600 font-medium mb-1 flex items-center gap-1 justify-end">
                          <Loader size={11} className="animate-spin" />
                          {dump.progress_pct}% — {dump.progress_stage || 'Processing…'}
                        </p>
                        <div className="h-1.5 bg-blue-100 rounded-full overflow-hidden w-40">
                          <div className="h-full bg-blue-500 rounded-full transition-all duration-700" style={{ width: `${dump.progress_pct || 5}%` }} />
                        </div>
                      </div>
                    )}
                    {dump.status === 'auditing' && (
                      <div className="text-right min-w-[160px]">
                        <p className="text-xs text-purple-600 font-medium mb-1 flex items-center gap-1 justify-end">
                          <Loader size={11} className="animate-spin" />
                          {dump.progress_pct}% — {dump.progress_stage || 'Running audit checks…'}
                        </p>
                        <div className="h-1.5 bg-purple-100 rounded-full overflow-hidden w-40">
                          <div className="h-full bg-purple-500 rounded-full transition-all duration-700" style={{ width: `${dump.progress_pct || 5}%` }} />
                        </div>
                      </div>
                    )}
                    {dump.status === 'failed' && (
                      <span className="text-xs text-red-600 font-medium" title={dump.progress_stage || ''}>Failed</span>
                    )}
                    {['processed', 'failed'].includes(dump.status) && (
                      <button
                        onClick={() => recheckDump.mutate(dump.id)}
                        disabled={recheckDump.isPending}
                        title="Recheck with all audit checks"
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
    </div>
  )
}
