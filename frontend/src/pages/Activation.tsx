import { useState, useEffect } from 'react'
import { Shield, Key, Loader, AlertCircle, CheckCircle2, Monitor } from 'lucide-react'

// Auto-format as user types: insert dashes after TALLY and every 5 chars
function formatKeyInput(raw: string): string {
  const clean = raw.toUpperCase().replace(/[^A-Z0-9]/g, '')
  // Expected pattern: TALLY + 20 chars = 25 chars total
  const prefix = clean.slice(0, 5)
  const rest = clean.slice(5, 25)
  const groups = rest.match(/.{1,5}/g) ?? []
  const parts = [prefix, ...groups].filter(Boolean)
  return parts.join('-')
}

export default function ActivationPage() {
  const [rawKey, setRawKey] = useState('')
  const [machineId, setMachineId] = useState('')
  const [version, setVersion] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    window.electron?.getMachineId().then(setMachineId)
    window.electron?.getVersion().then(setVersion)
  }, [])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError('')
    setRawKey(formatKeyInput(e.target.value))
  }

  const handleActivate = async () => {
    const key = rawKey.trim()
    if (!key) return

    setLoading(true)
    setError('')

    try {
      const result = await window.electron?.activate(key)
      if (result?.success) {
        setSuccess(true)
        // App will auto-relaunch — this state is just UX feedback
      } else {
        setError(result?.error ?? 'Invalid product key. Please check and try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleActivate()
  }

  const isKeyComplete = rawKey.replace(/-/g, '').length === 25

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        {/* Logo / brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-600 mb-4">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">TallyInsights</h1>
          <p className="text-slate-400 text-sm mt-1">
            {version ? `v${version} · ` : ''}License Activation
          </p>
        </div>

        {/* Card */}
        <div className="bg-slate-800 rounded-2xl border border-slate-700 p-8 shadow-2xl">
          {success ? (
            <div className="text-center py-4">
              <CheckCircle2 className="w-12 h-12 text-green-400 mx-auto mb-3" />
              <p className="text-white font-semibold text-lg">Activation successful!</p>
              <p className="text-slate-400 text-sm mt-2">Relaunching TallyInsights…</p>
            </div>
          ) : (
            <>
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-white mb-1">Enter your product key</h2>
                <p className="text-slate-400 text-sm">
                  Your key is tied to this machine and validated offline — no internet required.
                </p>
              </div>

              {/* Key input */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  <Key className="inline w-4 h-4 mr-1 mb-0.5" />
                  Product Key
                </label>
                <input
                  type="text"
                  value={rawKey}
                  onChange={handleChange}
                  onKeyDown={handleKeyDown}
                  placeholder="TALLY-XXXXX-XXXXX-XXXXX-XXXXX"
                  maxLength={29} // TALLY-XXXXX-XXXXX-XXXXX-XXXXX = 29 chars
                  spellCheck={false}
                  autoComplete="off"
                  className="w-full px-4 py-3 rounded-lg bg-slate-900 border border-slate-600 text-white
                             placeholder-slate-500 font-mono text-sm tracking-widest
                             focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                             transition-colors"
                />
              </div>

              {/* Error */}
              {error && (
                <div className="flex items-start gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/30 mb-4">
                  <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                  <p className="text-red-300 text-sm">{error}</p>
                </div>
              )}

              {/* Activate button */}
              <button
                onClick={handleActivate}
                disabled={!isKeyComplete || loading}
                className="w-full py-3 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700
                           disabled:text-slate-500 text-white font-semibold transition-colors
                           flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader className="w-4 h-4 animate-spin" />
                    Validating…
                  </>
                ) : (
                  'Activate TallyInsights'
                )}
              </button>

              {/* Machine ID */}
              {machineId && (
                <div className="mt-6 pt-4 border-t border-slate-700">
                  <p className="text-xs text-slate-500 flex items-center gap-1.5">
                    <Monitor className="w-3.5 h-3.5" />
                    Machine ID: <span className="font-mono text-slate-400">{machineId}</span>
                  </p>
                  <p className="text-xs text-slate-600 mt-1">
                    Provide this to support when requesting a new key for a different machine.
                  </p>
                </div>
              )}
            </>
          )}
        </div>

        <p className="text-center text-slate-600 text-xs mt-6">
          © {new Date().getFullYear()} PERI · All rights reserved
        </p>
      </div>
    </div>
  )
}
