import { useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import api from '../api/client'
import PageHeader from '../components/UI/PageHeader'
import { Upload, FileText, CheckCircle, XCircle, Loader, BarChart3, RefreshCw, Trash2, ChevronLeft } from 'lucide-react'
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

export default function UploadsPage() {
  const { companyId } = useParams<{ companyId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [periodFrom, setPeriodFrom] = useState('')
  const [periodTo, setPeriodTo] = useState('')
  const [financialYear, setFinancialYear] = useState('')
  const [uploading, setUploading] = useState(false)

  const { data: dumps = [], isLoading } = useQuery<Dump[]>({
    queryKey: ['dumps', companyId],
    queryFn: () => api.get(`/uploads/${companyId}`).then((r) => r.data),
    refetchInterval: (query) => {
      const d = query.state.data
      if (d?.some((d) => d.status === 'processing' || d.status === 'uploaded')) return 3000
      return false
    },
  })

  const [deletingId, setDeletingId] = useState<number | null>(null)

  const deleteDump = useMutation({
    mutationFn: (dumpId: number) => api.delete(`/uploads/${dumpId}`),
    onSuccess: () => {
      setDeletingId(null)
      qc.invalidateQueries({ queryKey: ['dumps', companyId] })
    },
    onError: (err: any) => {
      setDeletingId(null)
      alert(`Delete failed: ${err?.response?.data?.detail || err.message || 'Unknown error'}`)
    },
  })

  const onDrop = useCallback(async (files: File[]) => {
    if (!files[0]) return
    setUploading(true)
    const formData = new FormData()
    formData.append('file', files[0])
    if (periodFrom) formData.append('period_from', periodFrom)
    if (periodTo) formData.append('period_to', periodTo)
    if (financialYear) formData.append('financial_year', financialYear)
    try {
      await api.post(`/uploads/${companyId}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
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
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4"
      >
        <ChevronLeft size={16} /> Back to Companies
      </button>

      <PageHeader
        title="Data Dumps"
        subtitle={`Tally exports for Company #${companyId}`}
      />

      {/* Upload Zone */}
      <div className="card mb-6">
        <h3 className="font-semibold text-gray-800 mb-4">Upload Tally Dump</h3>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Period From</label>
            <input type="date" value={periodFrom} onChange={(e) => setPeriodFrom(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Period To</label>
            <input type="date" value={periodTo} onChange={(e) => setPeriodTo(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Financial Year (e.g. 2023-24)</label>
            <input value={financialYear} onChange={(e) => setFinancialYear(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none"
              placeholder="2023-24" />
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
          {uploading ? (
            <div className="flex flex-col items-center gap-2 text-brand-600">
              <Loader size={36} className="animate-spin" />
              <p className="text-sm font-medium">Uploading & processing...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 text-gray-500">
              <Upload size={36} className="text-gray-400" />
              <p className="text-sm font-medium">
                {isDragActive ? 'Drop file here' : 'Drag & drop or click to upload'}
              </p>
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
                    <button
                      onClick={() => navigate(`/dumps/${dump.id}/dashboard`)}
                      className="btn-primary text-xs flex items-center gap-1"
                    >
                      <BarChart3 size={12} /> View Reports
                    </button>
                  )}
                  {dump.status === 'processing' && (
                    <span className="text-xs text-blue-600 font-medium">Processing...</span>
                  )}
                  {dump.status === 'failed' && (
                    <span className="text-xs text-red-600 font-medium">Failed</span>
                  )}
                  <button
                    onClick={() => handleDeleteDump(dump)}
                    disabled={deletingId === dump.id}
                    title="Delete dump"
                    className="p-1.5 rounded-md text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
                  >
                    {deletingId === dump.id
                      ? <Loader size={14} className="animate-spin text-red-500" />
                      : <Trash2 size={14} />}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
