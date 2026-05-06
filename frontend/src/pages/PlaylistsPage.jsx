import { useEffect } from 'react'
import { useAppStore } from '../store/appStore'
import { Card, CardContent } from '../components/ui/Card'
import { ProgressBar } from '../components/ui/ProgressBar'

export default function PlaylistsPage() {
  const { playlists, refreshAll, startPolling, stopPolling } = useAppStore()
  useEffect(() => {
    refreshAll()
    startPolling(2000)
    return () => stopPolling()
  }, [refreshAll, startPolling, stopPolling])

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold tracking-tight">Playlists</h1>
      <Card>
        <CardContent className="pt-4">
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-sm">
              <thead className="bg-muted/60 text-left text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 font-medium">Playlist</th>
                  <th className="px-3 py-2 font-medium text-right">Total</th>
                  <th className="px-3 py-2 font-medium text-right">Completed</th>
                  <th className="px-3 py-2 font-medium text-right">Failed</th>
                  <th className="px-3 py-2 font-medium text-right">Needs Review</th>
                  <th className="px-3 py-2 font-medium">Progress</th>
                </tr>
              </thead>
              <tbody>
                {playlists.map((p) => (
                  <tr key={p.id} className="border-t border-border">
                    <td className="px-3 py-2 font-medium">{p.name}</td>
                    <td className="px-3 py-2 text-right">{p.total}</td>
                    <td className="px-3 py-2 text-right text-emerald-700">{p.completed}</td>
                    <td className="px-3 py-2 text-right text-red-700">{p.failed}</td>
                    <td className="px-3 py-2 text-right text-amber-700">{p.needs_review}</td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <ProgressBar value={p.progress_pct} className="w-32" />
                        <span className="text-xs tabular-nums">{p.progress_pct}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
                {playlists.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-3 py-8 text-center text-xs text-muted-foreground">
                      No playlists yet. Run <code>python -m backend.seed_data</code> to seed.
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
