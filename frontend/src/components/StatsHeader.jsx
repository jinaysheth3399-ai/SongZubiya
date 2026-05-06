import { Card, CardContent } from './ui/Card'
import { ProgressBar } from './ui/ProgressBar'

export function StatsHeader({ status }) {
  if (!status) return null
  const stats = [
    { label: 'Total', value: status.total_songs },
    { label: 'Completed', value: status.completed, tone: 'text-emerald-700' },
    { label: 'Failed', value: status.failed, tone: 'text-red-700' },
    { label: 'Needs Review', value: status.needs_review, tone: 'text-amber-700' },
    { label: 'Pending', value: status.pending, tone: 'text-blue-700' },
  ]
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
      {stats.map((s) => (
        <Card key={s.label}>
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-muted-foreground">{s.label}</div>
            <div className={`mt-1 text-2xl font-semibold ${s.tone || ''}`}>{s.value ?? 0}</div>
          </CardContent>
        </Card>
      ))}
      <Card className="col-span-2 md:col-span-1">
        <CardContent className="pt-4 pb-4">
          <div className="text-xs text-muted-foreground">Progress</div>
          <div className="mt-1 text-2xl font-semibold">{status.progress_pct ?? 0}%</div>
          <ProgressBar value={status.progress_pct ?? 0} className="mt-2" />
        </CardContent>
      </Card>
    </div>
  )
}
