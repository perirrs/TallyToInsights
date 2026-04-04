import clsx from 'clsx'

interface KPICardProps {
  title: string
  value: string | number
  subtitle?: string
  icon?: React.ReactNode
  trend?: 'up' | 'down' | 'neutral'
  color?: 'blue' | 'green' | 'red' | 'orange' | 'purple'
  onClick?: () => void
}

const colorMap = {
  blue: 'bg-blue-50 text-blue-700 border-blue-200',
  green: 'bg-green-50 text-green-700 border-green-200',
  red: 'bg-red-50 text-red-700 border-red-200',
  orange: 'bg-orange-50 text-orange-700 border-orange-200',
  purple: 'bg-purple-50 text-purple-700 border-purple-200',
}

export default function KPICard({
  title, value, subtitle, icon, color = 'blue', onClick,
}: KPICardProps) {
  return (
    <div
      className={clsx('rounded-xl border p-5 flex flex-col gap-2', colorMap[color], onClick && 'cursor-pointer hover:brightness-95 transition-all')}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide opacity-70">{title}</p>
        {icon && <div className="opacity-60">{icon}</div>}
      </div>
      <p className="text-2xl font-bold">{value}</p>
      {subtitle && <p className="text-xs opacity-70">{subtitle}</p>}
    </div>
  )
}
