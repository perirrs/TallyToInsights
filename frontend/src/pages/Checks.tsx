import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import PageHeader from '../components/UI/PageHeader'
import { Plus, Pencil, Trash2, Upload, Search, ChevronLeft, ChevronRight, CheckSquare, Square, Loader } from 'lucide-react'
import clsx from 'clsx'

interface AuditCheck {
  id: number
  desc: string
  category: string
  risk: string
  feasibility: string
  analysis: string
  module?: string
  source?: string
  active?: boolean
}

const RISK_COLORS: Record<string, string> = {
  High: 'bg-red-100 text-red-700',
  Medium: 'bg-yellow-100 text-yellow-700',
  Low: 'bg-green-100 text-green-700',
}

const PAGE_SIZE = 50

export default function ChecksPage() {
  const qc = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [filterRisk, setFilterRisk] = useState('')

  const [showModal, setShowModal] = useState(false)
  const [editingCheck, setEditingCheck] = useState<AuditCheck | null>(null)
  const [form, setForm] = useState({
    desc: '', category: '', risk: 'Medium', feasibility: 'Auto', analysis: '', module: '', source: '',
  })

  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState('')
  const [replaceMode, setReplaceMode] = useState(false)

  // Bulk selection
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [bulkDeleting, setBulkDeleting] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['audit-checks', page, search, filterCategory, filterRisk],
    queryFn: () =>
      api.get('/audit-checks/', {
        params: { page, page_size: PAGE_SIZE, search: search || undefined, category: filterCategory || undefined, risk: filterRisk || undefined },
      }).then((r) => r.data),
    keepPreviousData: true,
  } as any)

  const createMutation = useMutation({
    mutationFn: (d: typeof form) => api.post('/audit-checks/', d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['audit-checks'] }); closeModal() },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, d }: { id: number; d: typeof form }) => api.put(`/audit-checks/${id}`, d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['audit-checks'] }); closeModal() },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/audit-checks/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['audit-checks'] }),
  })

  const items: AuditCheck[] = data?.items || []
  const total: number = data?.total || 0
  const categories: string[] = data?.categories || []
  const totalPages = Math.ceil(total / PAGE_SIZE)

  // Selection helpers
  const pageIds = items.map((c) => c.id)
  const allPageSelected = pageIds.length > 0 && pageIds.every((id) => selected.has(id))
  const somePageSelected = pageIds.some((id) => selected.has(id))

  const toggleSelectAll = () => {
    if (allPageSelected) {
      setSelected((prev) => { const s = new Set(prev); pageIds.forEach((id) => s.delete(id)); return s })
    } else {
      setSelected((prev) => { const s = new Set(prev); pageIds.forEach((id) => s.add(id)); return s })
    }
  }

  const toggleOne = (id: number) => {
    setSelected((prev) => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s })
  }

  const handleBulkDelete = async () => {
    if (selected.size === 0) return
    if (!window.confirm(`Delete ${selected.size} selected check${selected.size !== 1 ? 's' : ''}? This cannot be undone.`)) return
    setBulkDeleting(true)
    try {
      await api.post('/audit-checks/bulk-delete', { ids: Array.from(selected) })
      setSelected(new Set())
      qc.invalidateQueries({ queryKey: ['audit-checks'] })
    } catch (err: any) {
      alert(`Bulk delete failed: ${err?.response?.data?.detail || err.message}`)
    } finally {
      setBulkDeleting(false)
    }
  }

  const openAdd = () => {
    setEditingCheck(null)
    setForm({ desc: '', category: '', risk: 'Medium', feasibility: 'Auto', analysis: '', module: '', source: '' })
    setShowModal(true)
  }

  const openEdit = (check: AuditCheck) => {
    setEditingCheck(check)
    setForm({ desc: check.desc, category: check.category || '', risk: check.risk || 'Medium', feasibility: check.feasibility || 'Auto', analysis: check.analysis || '', module: check.module || '', source: check.source || '' })
    setShowModal(true)
  }

  const closeModal = () => { setShowModal(false); setEditingCheck(null) }

  const handleSubmit = () => {
    if (!form.desc) return
    if (editingCheck) { updateMutation.mutate({ id: editingCheck.id, d: form }) }
    else { createMutation.mutate(form) }
  }

  const handleDelete = (check: AuditCheck) => {
    if (window.confirm(`Delete check #${check.id}: "${check.desc}"?`)) deleteMutation.mutate(check.id)
  }

  const handleExcelUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadMsg('')
    const fd = new FormData()
    fd.append('file', file)
    try {
      const res = await api.post(`/audit-checks/upload-excel?replace=${replaceMode}`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setUploadMsg(res.data.message || 'Imported successfully')
      qc.invalidateQueries({ queryKey: ['audit-checks'] })
    } catch (err: any) {
      setUploadMsg(err?.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  return (
    <div className="p-6">
      <PageHeader
        title="Audit Checks"
        subtitle={`${total.toLocaleString()} checks in the library`}
        actions={
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer select-none">
              <input type="checkbox" checked={replaceMode} onChange={(e) => setReplaceMode(e.target.checked)} className="rounded" />
              Replace all on upload
            </label>
            <input ref={fileInputRef} type="file" accept=".xlsx,.xls" className="hidden" onChange={handleExcelUpload} />
            <button onClick={() => fileInputRef.current?.click()} disabled={uploading} className="btn-secondary flex items-center gap-2 text-sm">
              <Upload size={14} /> {uploading ? 'Uploading...' : 'Upload Excel'}
            </button>
            <button onClick={openAdd} className="btn-primary flex items-center gap-2 text-sm">
              <Plus size={14} /> Add Check
            </button>
          </div>
        }
      />

      {uploadMsg && (
        <div className={clsx('mb-4 px-4 py-2.5 rounded-lg text-sm', uploadMsg.toLowerCase().includes('fail') || uploadMsg.toLowerCase().includes('error') ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-green-50 text-green-700 border border-green-200')}>
          {uploadMsg}
        </div>
      )}

      {/* Filters + bulk action bar */}
      <div className="flex flex-wrap gap-3 mb-4 items-center">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-2.5 text-gray-400" />
          <input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} placeholder="Search checks..." className="pl-8 pr-3 py-2 border rounded-lg text-sm w-64 focus:ring-2 focus:ring-brand-500 focus:outline-none" />
        </div>
        <select value={filterCategory} onChange={(e) => { setFilterCategory(e.target.value); setPage(1) }} className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none">
          <option value="">All Categories</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={filterRisk} onChange={(e) => { setFilterRisk(e.target.value); setPage(1) }} className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none">
          <option value="">All Risk Levels</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
        {(search || filterCategory || filterRisk) && (
          <button onClick={() => { setSearch(''); setFilterCategory(''); setFilterRisk(''); setPage(1) }} className="text-xs text-gray-500 hover:text-gray-700 underline">Clear</button>
        )}
        <span className="text-xs text-gray-500">{total.toLocaleString()} results</span>

        {selected.size > 0 && (
          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs text-gray-600">{selected.size} selected</span>
            <button onClick={() => setSelected(new Set())} className="text-xs text-gray-500 hover:text-gray-700 underline">Deselect all</button>
            <button
              onClick={handleBulkDelete}
              disabled={bulkDeleting}
              className="flex items-center gap-1.5 text-xs font-medium text-red-600 hover:text-red-800 border border-red-200 hover:border-red-400 rounded-lg px-3 py-1.5 transition-colors disabled:opacity-50"
            >
              {bulkDeleting ? <Loader size={11} className="animate-spin" /> : <Trash2 size={11} />}
              Delete {selected.size} selected
            </button>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-50 border-b">
              <th className="px-3 py-2.5 w-8">
                <button onClick={toggleSelectAll} className="text-gray-400 hover:text-gray-700">
                  {allPageSelected
                    ? <CheckSquare size={14} className="text-brand-600" />
                    : somePageSelected
                    ? <CheckSquare size={14} className="text-brand-300" />
                    : <Square size={14} />}
                </button>
              </th>
              <th className="px-4 py-2.5 text-left font-semibold text-gray-600 w-12">#</th>
              <th className="px-4 py-2.5 text-left font-semibold text-gray-600">Description</th>
              <th className="px-4 py-2.5 text-left font-semibold text-gray-600 w-40">Category</th>
              <th className="px-4 py-2.5 text-left font-semibold text-gray-600 w-20">Risk</th>
              <th className="px-4 py-2.5 text-left font-semibold text-gray-600 w-24">Feasibility</th>
              <th className="px-4 py-2.5 text-left font-semibold text-gray-600 w-24">Analysis</th>
              <th className="px-4 py-2.5 text-center font-semibold text-gray-600 w-20">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={8} className="text-center py-10 text-gray-400">Loading checks...</td></tr>
            ) : items.length === 0 ? (
              <tr><td colSpan={8} className="text-center py-10 text-gray-400">No checks found</td></tr>
            ) : items.map((check) => (
              <tr key={check.id} className={clsx('hover:bg-gray-50', selected.has(check.id) && 'bg-brand-50')}>
                <td className="px-3 py-2.5">
                  <button onClick={() => toggleOne(check.id)} className="text-gray-400 hover:text-brand-600">
                    {selected.has(check.id) ? <CheckSquare size={14} className="text-brand-600" /> : <Square size={14} />}
                  </button>
                </td>
                <td className="px-4 py-2.5 text-gray-400 font-mono">{check.id}</td>
                <td className="px-4 py-2.5 text-gray-800 max-w-md"><span className="line-clamp-2">{check.desc}</span></td>
                <td className="px-4 py-2.5 text-gray-500">{check.category}</td>
                <td className="px-4 py-2.5">
                  <span className={clsx('inline-flex px-2 py-0.5 rounded text-xs font-medium', RISK_COLORS[check.risk] || 'bg-gray-100 text-gray-600')}>{check.risk}</span>
                </td>
                <td className="px-4 py-2.5 text-gray-500">{check.feasibility}</td>
                <td className="px-4 py-2.5 text-gray-500">{check.analysis}</td>
                <td className="px-4 py-2.5">
                  <div className="flex items-center justify-center gap-1">
                    <button onClick={() => openEdit(check)} className="p-1.5 rounded-md text-gray-400 hover:text-brand-600 hover:bg-brand-50 transition-colors" title="Edit"><Pencil size={12} /></button>
                    <button onClick={() => handleDelete(check)} className="p-1.5 rounded-md text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors" title="Delete"><Trash2 size={12} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 text-sm text-gray-600">
          <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="btn-secondary text-xs disabled:opacity-40 flex items-center gap-1"><ChevronLeft size={14} /> Prev</button>
          <span>Page {page} of {totalPages} ({total.toLocaleString()} total)</span>
          <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)} className="btn-secondary text-xs disabled:opacity-40 flex items-center gap-1">Next <ChevronRight size={14} /></button>
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={closeModal}>
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-gray-900 mb-5">{editingCheck ? `Edit Check #${editingCheck.id}` : 'Add New Check'}</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description *</label>
                <textarea value={form.desc} onChange={(e) => setForm({ ...form, desc: e.target.value })} rows={3} className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" placeholder="Describe what this check does..." />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  <input value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} list="category-list" className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" placeholder="e.g. Financial Integrity" />
                  <datalist id="category-list">{categories.map((c) => <option key={c} value={c} />)}</datalist>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Risk Level</label>
                  <select value={form.risk} onChange={(e) => setForm({ ...form, risk: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none">
                    <option value="High">High</option>
                    <option value="Medium">Medium</option>
                    <option value="Low">Low</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Feasibility</label>
                  <select value={form.feasibility} onChange={(e) => setForm({ ...form, feasibility: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none">
                    <option value="Auto">Auto</option>
                    <option value="Upload">Upload</option>
                    <option value="Module">Module</option>
                    <option value="Manual">Manual</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Analysis Type</label>
                  <input value={form.analysis} onChange={(e) => setForm({ ...form, analysis: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" placeholder="e.g. Compliance" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Module</label>
                  <input value={form.module} onChange={(e) => setForm({ ...form, module: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" placeholder="e.g. Accounts" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Source</label>
                  <input value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" placeholder="e.g. Day Book" />
                </div>
              </div>
            </div>
            <div className="flex gap-2 mt-6 justify-end">
              <button onClick={closeModal} className="btn-secondary text-sm">Cancel</button>
              <button onClick={handleSubmit} disabled={!form.desc || createMutation.isPending || updateMutation.isPending} className="btn-primary text-sm">
                {createMutation.isPending || updateMutation.isPending ? 'Saving...' : editingCheck ? 'Save Changes' : 'Add Check'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
