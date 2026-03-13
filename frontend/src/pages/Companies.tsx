import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import PageHeader from '../components/UI/PageHeader'
import { Building2, Plus, Upload, ChevronRight } from 'lucide-react'

interface Company {
  id: number
  name: string
  gstin?: string
  pan?: string
  financial_year_start_month: number
  currency: string
  created_at: string
}

export default function CompaniesPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
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
      setForm({ name: '', gstin: '', pan: '', address: '', financial_year_start_month: 4, currency: 'INR' })
    },
  })

  return (
    <div className="p-6">
      <PageHeader
        title="Companies"
        subtitle="Manage Tally companies and their data dumps"
        actions={
          <button onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-2 text-sm">
            <Plus size={16} /> Add Company
          </button>
        }
      />

      {showForm && (
        <div className="card mb-6">
          <h3 className="font-semibold text-gray-800 mb-4">New Company</h3>
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
              onClick={() => create.mutate(form)}
              disabled={!form.name || create.isPending}
              className="btn-primary text-sm"
            >
              {create.isPending ? 'Creating...' : 'Create Company'}
            </button>
            <button onClick={() => setShowForm(false)} className="btn-secondary text-sm">Cancel</button>
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
            <div key={c.id} className="card hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => navigate(`/companies/${c.id}/uploads`)}>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-brand-50 rounded-lg flex items-center justify-center">
                    <Building2 size={20} className="text-brand-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{c.name}</h3>
                    <p className="text-xs text-gray-500">{c.gstin || 'No GSTIN'}</p>
                  </div>
                </div>
                <ChevronRight size={16} className="text-gray-400 mt-1" />
              </div>
              <div className="mt-4 flex gap-3">
                <button
                  onClick={(e) => { e.stopPropagation(); navigate(`/companies/${c.id}/uploads`) }}
                  className="flex items-center gap-1 text-xs text-brand-600 hover:underline"
                >
                  <Upload size={12} /> Uploads
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
