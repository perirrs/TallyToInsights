import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import PageHeader from '../components/UI/PageHeader'
import { Plus, User } from 'lucide-react'
import { useAuthStore } from '../store/authStore'

export default function UsersPage() {
  const { isAdmin } = useAuthStore()
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ email: '', name: '', password: '', is_admin: false })

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => api.get('/auth/users').then((r) => r.data).catch(() => []),
    enabled: isAdmin,
  })

  const create = useMutation({
    mutationFn: (data: typeof form) => api.post('/auth/register', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      setShowForm(false)
      setForm({ email: '', name: '', password: '', is_admin: false })
    },
  })

  if (!isAdmin) {
    return (
      <div className="p-6">
        <div className="text-center py-12 text-gray-400">Admin access required.</div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <PageHeader
        title="User Management"
        actions={
          <button onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-2 text-sm">
            <Plus size={16} /> Add User
          </button>
        }
      />

      {showForm && (
        <div className="card mb-6">
          <h3 className="font-semibold mb-4">New User</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" />
            </div>
            <div className="flex items-end pb-2">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.is_admin} onChange={(e) => setForm({ ...form, is_admin: e.target.checked })} />
                Admin
              </label>
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button onClick={() => create.mutate(form)} disabled={create.isPending} className="btn-primary text-sm">
              {create.isPending ? 'Creating...' : 'Create User'}
            </button>
            <button onClick={() => setShowForm(false)} className="btn-secondary text-sm">Cancel</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {users.map((u: any) => (
          <div key={u.id} className="card">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-brand-100 rounded-full flex items-center justify-center">
                <User size={18} className="text-brand-700" />
              </div>
              <div>
                <p className="font-medium text-gray-900">{u.name}</p>
                <p className="text-xs text-gray-500">{u.email}</p>
                {u.is_admin && <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">Admin</span>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
