import { cn } from '../../lib/cn'

export function Card({ className, children }) {
  return (
    <div className={cn('rounded-lg border border-border bg-background shadow-sm', className)}>
      {children}
    </div>
  )
}

export function CardHeader({ className, children }) {
  return <div className={cn('px-5 pt-4 pb-2', className)}>{children}</div>
}

export function CardContent({ className, children }) {
  return <div className={cn('px-5 pb-5', className)}>{children}</div>
}

export function CardTitle({ className, children }) {
  return <h3 className={cn('text-sm font-semibold tracking-tight', className)}>{children}</h3>
}
