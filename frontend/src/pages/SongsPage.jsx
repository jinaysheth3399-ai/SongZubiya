import { useEffect, useMemo, useState } from 'react'
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { Copy, ExternalLink, RotateCw, Forward } from 'lucide-react'
import { useAppStore } from '../store/appStore'
import { StatsHeader } from '../components/StatsHeader'
import { RunnerControls } from '../components/RunnerControls'
import { StatusBadge, ConfidenceBadge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card, CardContent } from '../components/ui/Card'
import { api } from '../api/client'

export default function SongsPage() {
  const { status, songs, refreshAll, startPolling, stopPolling, error } = useAppStore()
  const [filter, setFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [actionMsg, setActionMsg] = useState(null)

  useEffect(() => {
    refreshAll()
    startPolling(2000)
    return () => stopPolling()
  }, [refreshAll, startPolling, stopPolling])

  const filteredSongs = useMemo(() => {
    return songs.filter((s) => {
      if (statusFilter !== 'all' && s.status !== statusFilter) return false
      if (!filter) return true
      const f = filter.toLowerCase()
      return (
        s.song_name?.toLowerCase().includes(f) ||
        s.artist?.toLowerCase().includes(f) ||
        s.playlist_name?.toLowerCase().includes(f)
      )
    })
  }, [songs, filter, statusFilter])

  const handleCopy = async (link) => {
    try {
      await navigator.clipboard.writeText(link)
      setActionMsg('Link copied')
      setTimeout(() => setActionMsg(null), 1500)
    } catch {
      setActionMsg('Copy failed')
    }
  }

  const handleRetry = async (id) => {
    try {
      await api.retry(id)
      refreshAll()
    } catch (e) {
      setActionMsg(e.message)
    }
  }

  const handleSkip = async (id) => {
    try {
      await api.skip(id, 'Skipped via dashboard')
      refreshAll()
    } catch (e) {
      setActionMsg(e.message)
    }
  }

  const columns = useMemo(
    () => [
      { accessorKey: 'track_no', header: 'Track' },
      { accessorKey: 'song_name', header: 'Song' },
      { accessorKey: 'artist', header: 'Artist' },
      { accessorKey: 'playlist_name', header: 'Playlist' },
      {
        accessorKey: 'status',
        header: 'Status',
        cell: ({ getValue }) => <StatusBadge status={getValue()} />,
      },
      {
        accessorKey: 'confidence_score',
        header: 'Confidence',
        cell: ({ getValue }) => <ConfidenceBadge score={getValue()} />,
      },
      {
        accessorKey: 'selected_youtube_title',
        header: 'YouTube Match',
        cell: ({ row, getValue }) => {
          const title = getValue()
          const url = row.original.selected_youtube_url
          if (!title) return <span className="text-xs text-muted-foreground">—</span>
          return (
            <a
              href={url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-xs text-blue-700 hover:underline"
              title={title}
            >
              <span className="line-clamp-1 max-w-[260px]">{title}</span>
              <ExternalLink size={12} />
            </a>
          )
        },
      },
      {
        id: 'drive',
        header: 'Drive Link',
        cell: ({ row }) => {
          const link = row.original.drive_web_link
          if (!link) return <span className="text-xs text-muted-foreground">Not uploaded yet</span>
          return (
            <div className="flex items-center gap-2">
              <a
                href={link}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-xs text-blue-700 hover:underline"
              >
                <ExternalLink size={12} /> Open Drive File
              </a>
              <button
                onClick={() => handleCopy(link)}
                className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              >
                <Copy size={12} /> Copy Link
              </button>
            </div>
          )
        },
      },
      {
        id: 'actions',
        header: 'Actions',
        cell: ({ row }) => (
          <div className="flex items-center gap-1">
            <Button size="sm" variant="outline" onClick={() => handleRetry(row.original.id)}>
              <RotateCw size={12} className="mr-1" /> Retry
            </Button>
            <Button size="sm" variant="ghost" onClick={() => handleSkip(row.original.id)}>
              <Forward size={12} className="mr-1" /> Skip
            </Button>
          </div>
        ),
      },
    ],
    [],
  )

  const table = useReactTable({
    data: filteredSongs,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  const allStatuses = useMemo(() => {
    const set = new Set(songs.map((s) => s.status).filter(Boolean))
    return Array.from(set).sort()
  }, [songs])

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <h1 className="text-xl font-semibold tracking-tight">Songs</h1>
        <RunnerControls runner={status?.runner} onChange={refreshAll} />
      </div>

      <StatsHeader status={status} />

      {(error || actionMsg) && (
        <div className="text-xs text-amber-800 bg-amber-50 border border-amber-200 px-3 py-2 rounded-md">
          {error || actionMsg}
        </div>
      )}

      <Card>
        <CardContent className="pt-4">
          <div className="mb-3 flex flex-wrap gap-2">
            <input
              type="text"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter by song, artist, playlist…"
              className="h-9 flex-1 min-w-[240px] rounded-md border border-border px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-9 rounded-md border border-border px-2 text-sm"
            >
              <option value="all">All statuses</option>
              {allStatuses.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-sm">
              <thead className="bg-muted/60 text-left text-xs uppercase text-muted-foreground">
                {table.getHeaderGroups().map((hg) => (
                  <tr key={hg.id}>
                    {hg.headers.map((h) => (
                      <th key={h.id} className="px-3 py-2 font-medium">
                        {flexRender(h.column.columnDef.header, h.getContext())}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map((row) => (
                  <tr key={row.id} className="border-t border-border hover:bg-muted/40">
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-3 py-2 align-middle">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
                {table.getRowModel().rows.length === 0 && (
                  <tr>
                    <td colSpan={columns.length} className="px-3 py-8 text-center text-xs text-muted-foreground">
                      No songs match the current filter.
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
