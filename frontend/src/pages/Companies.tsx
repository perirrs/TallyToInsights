import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import PageHeader from '../components/UI/PageHeader'
import { Building2, Plus, Upload, ChevronRight, Trash2, Pencil, Loader } from 'lucide-react'

interface Company {
  id: number
  name: string
  gstin?: string
  pan?: string
  financial_year_start_month: number
  currency: string
  created_at: string
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export default function CompaniesPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editingCompany, setEditingCompany] = useState<Company | null>(null)
  const [form, setForm] = useState({
    name: '', gstin: '', pan: '', address: '',
    financial_year_start_month: 4, currency: 'INR',
  })

  const { data: companies = [], isLoading } = useQuery<Company[]>({
    queryKey: ['companies'],
    queryFn: () => api.get('/companies/').then((r) => r.data),
  })

  const create = useMutation({
    mutationFn: (data: typeof form) => api.post('/companies/', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['companies'] })
      setShowForm(false)
      resetForm()
    },
  })

  const update = useMutation({
    mutationFn: ({ id, data }: { id: number; data: typeof form }) =>
      api.put(`/companies/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['companies'] })
      setShowForm(false)
      setEditingCompany(null)
      resetForm()
    },
  })

  const [deletingId, setDeletingId] = useState<number | null>(null)

  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/companies/${id}`),
    onSuccess: () => {
      setDeletingId(null)
      qc.invalidateQueries({ queryKey: ['companies'] })
    },
    onError: (err: any) => {
      setDeletingId(null)
      alert(`Delete failed: ${err?.response?.data?.detail || err.message || 'Unknown error'}`)
    },
  })

  const resetForm = () => {
    setForm({ name: '', gstin: '', pan: '', address: '', financial_year_start_month: 4, currency: 'INR' })
  }

  const openEdit = (c: Company, e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingCompany(c)
    setForm({
      name: c.name,
      gstin: c.gstin || '',
      pan: c.pan || '',
      address: '',
      financial_year_start_month: c.financial_year_start_month,
      currency: c.currency,
    })
    setShowForm(true)
  }

  const openAdd = () => {
    setEditingCompany(null)
    resetForm()
    setShowForm(true)
  }

  const handleDelete = (c: Company, e: React.MouseEvent) => {
    e.stopPropagation()
    if (window.confirm(`Delete company "${c.name}"? All uploaded data dumps, vouchers and audit results will be permanently removed.`)) {
      setDeletingId(c.id)
      remove.mutate(c.id)
    }
  }

  const handleSubmit = () => {
    if (editingCompany) {
      update.mutate({ id: editingCompany.id, data: form })
    } else {
      create.mutate(form)
    }
  }

  return (
    <div className="p-6">
      <PageHeader
        title="Companies"
        subtitle="Manage Tally companies and their data dumps"
        actions={
          <button onClick={openAdd} className="btn-primary flex items-center gap-2 text-sm">
            <Plus size={16} /> Add Company
          </button>
        }
      />

      {showForm && (
        <div className="card mb-6">
          <h3 className="font-semibold text-gray-800 mb-4">
            {editingCompany ? `Edit: ${editingCompany.name}` : 'New Company'}
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Company Name *</label>
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none"
                placeholder="ABC Enterprises Pvt Ltd"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">GSTIN</label>
              <input
                value={form.gstin}
                onChange={(e) => setForm({ ...form, gstin: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none"
                placeholder="27AAACR5055K1ZL"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">PAN</label>
              <input
                value={form.pan}
                onChange={(e) => setForm({ ...form, pan: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none"
                placeholder="AAACR5055K"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Financial Year Start</label>
              <select
                value={form.financial_year_start_month}
                onChange={(e) => setForm({ ...form, financial_year_start_month: +e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none"
              >
                <option value={4}>April (Indian FY)</option>
                <option value={1}>January (Calendar year)</option>
                <option value={7}>July</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
              <textarea
                value={form.address}
                onChange={(e) => setForm({ ...form, address: e.target.value })}
                rows={2}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none"
              />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button
              onClick={handleSubmit}
              disabled={!form.name || create.isPending || update.isPending}
              className="btn-primary text-sm"
            >
              {create.isPending || update.isPending
                ? (editingCompany ? 'Saving...' : 'Creating...')
                : (editingCompany ? 'Save Changes' : 'Create Company')}
            </button>
            <button
              onClick={() => { setShowForm(false); setEditingCompany(null); resetForm() }}
              className="btn-secondary text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-center text-gray-500 py-12">Loading companies...</div>
      ) : companies.length === 0 ? (
        <div className="text-center py-12">
          <Building2 size={48} className="mx-auto text-gray-300 mb-4" />
          <p className="text-gray-500">No companies yet. Create your first company to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {companies.map((c) => (
            <div
              key={c.id}
              className="card hover:shadow-md transition-shadow cursor-pointer relative"
              onClick={() => navigate(`/companies/${c.id}/uploads`)}
            >
              {/* Action buttons top-right */}
              <div className="absolute top-3 right-3 flex items-center gap-1">
                <button
                  onClick={(e) => openEdit(c, e)}
                  title="Edit company"
                  className="p-1.5 rounded-md text-gray-400 hover:text-brand-600 hover:bg-brand-50 transition-colors"
                >
                  <Pencil size={14} />
                </button>
                <button
                  onClick={(e) => handleDelete(c, e)}
                  disabled={deletingId === c.id}
                  title="Delete company"
                  className="p-1.5 rounded-md text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
                >
                  {deletingId === c.id
                    ? <Loader size={14} className="animate-spin text-red-500" />
                    : <Trash2 size={14} />}
                </button>
              </div>

              <div className="flex items-start gap-3 pr-16">
                <div className="w-11 h-11 bg-brand-50 rounded-xl flex items-center justify-center text-brand-700 font-bold text-lg flex-shrink-0">
                  {c.name.charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0">
                  <h3 className="font-semibold text-gray-900 leading-tight">{c.name}</h3>
                  {c.gstin && <p className="text-xs text-gray-500 mt-0.5">{c.gstin}</p>}
                  {c.pan && <p className="text-xs text-gray-400">{c.pan}</p>}
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between">
                <div className="text-xs text-gray-400">
                  FY starts {MONTHS[(c.financial_year_start_month - 1) % 12]} ·{' '}
                  {c.created_at ? new Date(c.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : ''}
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); navigate(`/companies/${c.id}/uploads`) }}
                  className="flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700 font-medium"
                >
                  <Upload size={11} /> Uploads <ChevronRight size={11} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
