import { cn } from '../../lib/cn'

export function ProgressBar({ value = 0, className }) {
  const v = Math.max(0, Math.min(100, value))
  return (
    <div className={cn('h-2 w-full overflow-hidden rounded-full bg-muted', className)}>
      <div
        className="h-full bg-emerald-500 transition-all"
        style={{ width: `${v}%` }}
      />
    </div>
  )
}
