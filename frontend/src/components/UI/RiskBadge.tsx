import clsx from 'clsx'

type Risk = 'High' | 'Medium' | 'Low'
type Status = 'pass' | 'fail' | 'warning' | 'skipped' | 'error'

export function RiskBadge({ level }: { level: Risk }) {
  return (
    <span className={clsx(
      'inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold',
      level === 'High' && 'bg-red-100 text-red-800',
      level === 'Medium' && 'bg-orange-100 text-orange-800',
      level === 'Low' && 'bg-green-100 text-green-800',
    )}>
      {level}
    </span>
  )
}

export function StatusBadge({ status }: { status: Status | string }) {
  return (
    <span className={clsx(
      'inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold uppercase',
      status === 'pass' && 'bg-green-100 text-green-800',
      status === 'fail' && 'bg-red-100 text-red-800',
      status === 'warning' && 'bg-yellow-100 text-yellow-800',
      status === 'skipped' && 'bg-gray-100 text-gray-600',
      status === 'error' && 'bg-purple-100 text-purple-800',
    )}>
      {status}
    </span>
  )
}
