import { cn } from '../../lib/cn'

const STATUS_STYLES = {
  Pending: 'bg-muted text-muted-foreground',
  'Searching YouTube': 'bg-blue-100 text-blue-800',
  'Needs Manual Review': 'bg-amber-100 text-amber-800',
  Approved: 'bg-emerald-100 text-emerald-800',
  'Processing Audio': 'bg-blue-100 text-blue-800',
  'Verifying File': 'bg-blue-100 text-blue-800',
  'Uploading to Drive': 'bg-blue-100 text-blue-800',
  Completed: 'bg-emerald-100 text-emerald-800',
  'Skipped - Low Confidence': 'bg-zinc-100 text-zinc-700',
  'Failed - No Result': 'bg-red-100 text-red-800',
  'Failed - Audio Processing Error': 'bg-red-100 text-red-800',
  'Failed - File Verification Error': 'bg-red-100 text-red-800',
  'Failed - Drive Upload Error': 'bg-red-100 text-red-800',
}

export function StatusBadge({ status, className }) {
  const tone = STATUS_STYLES[status] || 'bg-muted text-muted-foreground'
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium whitespace-nowrap',
        tone,
        className,
      )}
    >
      {status}
    </span>
  )
}

export function ConfidenceBadge({ score }) {
  if (score === null || score === undefined) {
    return <span className="text-xs text-muted-foreground">—</span>
  }
  let tone = 'bg-zinc-100 text-zinc-700'
  if (score >= 85) tone = 'bg-emerald-100 text-emerald-800'
  else if (score >= 70) tone = 'bg-amber-100 text-amber-800'
  else tone = 'bg-red-100 text-red-800'
  return (
    <span className={cn('inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium', tone)}>
      {score}
    </span>
  )
}
