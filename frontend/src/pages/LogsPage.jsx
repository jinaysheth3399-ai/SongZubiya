import { useEffect } from 'react'
import { useAppStore } from '../store/appStore'
import { Card, CardContent } from '../components/ui/Card'

const LEVEL_COLORS = {
  INFO: 'text-blue-700',
  WARNING: 'text-amber-700',
  ERROR: 'text-red-700',
  DEBUG: 'text-zinc-600',
}

export default function LogsPage() {
  const { logs, refreshLogs } = useAppStore()

  useEffect(() => {
    refreshLogs()
    const id = setInterval(refreshLogs, 2000)
    return () => clearInterval(id)
  }, [refreshLogs])

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold tracking-tight">Logs</h1>
      <Card>
        <CardContent className="pt-4">
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-sm">
              <thead className="bg-muted/60 text-left text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 font-medium w-44">Time</th>
                  <th className="px-3 py-2 font-medium w-64">Song</th>
                  <th className="px-3 py-2 font-medium w-20">Level</th>
                  <th className="px-3 py-2 font-medium">Message</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((l) => (
                  <tr key={l.id} className="border-t border-border align-top">
                    <td className="px-3 py-2 text-xs tabular-nums text-muted-foreground">
                      {l.time ? new Date(l.time).toLocaleString() : ''}
                    </td>
                    <td className="px-3 py-2 text-xs text-muted-foreground">{l.song_label || '—'}</td>
                    <td className={`px-3 py-2 text-xs font-medium ${LEVEL_COLORS[l.level] || ''}`}>
                      {l.level}
                    </td>
                    <td className="px-3 py-2 text-xs whitespace-pre-wrap break-words">{l.message}</td>
                  </tr>
                ))}
                {logs.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-3 py-8 text-center text-xs text-muted-foreground">
                      No logs yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
