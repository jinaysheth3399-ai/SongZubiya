import { useEffect, useMemo, useState } from 'react'
import { ExternalLink, Copy, Music2 } from 'lucide-react'
import { Card, CardContent } from '../components/ui/Card'

function SongRow({ song, onCopy }) {
  return (
    <div className="flex items-center gap-3 border-t border-border px-4 py-2.5 hover:bg-muted/40">
      <div className="w-10 shrink-0 text-xs font-mono text-muted-foreground">{song.track_no}</div>
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium">{song.song_name}</div>
        <div className="truncate text-xs text-muted-foreground">{song.artist}</div>
      </div>
      <div className="shrink-0 flex items-center gap-2">
        <a
          href={song.drive_web_link}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 rounded-md border border-border bg-background px-2.5 py-1 text-xs hover:bg-accent"
        >
          <ExternalLink size={12} /> Open
        </a>
        <button
          onClick={() => onCopy(song.drive_web_link)}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
          title="Copy link"
        >
          <Copy size={12} />
        </button>
      </div>
    </div>
  )
}

export default function LibraryPage() {
  const [playlists, setPlaylists] = useState([])
  const [songs, setSongs] = useState([])
  const [toast, setToast] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeRoot, setActiveRoot] = useState(null)

  useEffect(() => {
    fetch('/data.json')
      .then((r) => r.json())
      .then(({ playlists, songs }) => {
        setPlaylists(playlists)
        setSongs(songs)
      })
      .finally(() => setLoading(false))
  }, [])

  const roots = useMemo(() => {
    const seen = new Set()
    for (const p of playlists) seen.add(p.drive_root_name || 'Default')
    return Array.from(seen).sort()
  }, [playlists])

  useEffect(() => {
    if (!activeRoot && roots.length > 0) setActiveRoot(roots[0])
  }, [roots, activeRoot])

  const grouped = useMemo(() => {
    const byPlaylist = new Map()
    for (const p of playlists) {
      const root = p.drive_root_name || 'Default'
      if (activeRoot && root !== activeRoot) continue
      byPlaylist.set(p.id, { playlist: p, songs: [] })
    }
    for (const s of songs) {
      const bucket = byPlaylist.get(s.playlist_id)
      if (bucket) bucket.songs.push(s)
    }
    for (const b of byPlaylist.values()) {
      b.songs.sort((a, b) => (a.track_no || '').localeCompare(b.track_no || ''))
    }
    return Array.from(byPlaylist.values())
      .filter((b) => b.songs.length > 0)
      .sort((a, b) => a.playlist.name.localeCompare(b.playlist.name))
  }, [playlists, songs, activeRoot])

  const totalSongs = useMemo(
    () => grouped.reduce((n, b) => n + b.songs.length, 0),
    [grouped],
  )

  const handleCopy = async (link) => {
    try {
      await navigator.clipboard.writeText(link)
      setToast('Link copied')
    } catch {
      setToast('Copy failed')
    }
    setTimeout(() => setToast(null), 1500)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold tracking-tight">
            <Music2 size={20} /> Music Library
          </h1>
          <p className="text-sm text-muted-foreground">
            {loading ? 'Loading…' : `${totalSongs} songs across ${grouped.length} playlists`}
          </p>
        </div>
        {toast && (
          <div className="rounded-md bg-emerald-50 px-3 py-1.5 text-xs text-emerald-800 border border-emerald-200">
            {toast}
          </div>
        )}
      </div>

      {roots.length > 1 && (
        <div className="flex flex-wrap gap-1 rounded-md border border-border bg-muted/40 p-1 w-fit">
          {roots.map((r) => (
            <button
              key={r}
              onClick={() => setActiveRoot(r)}
              className={
                'rounded-md px-3 py-1.5 text-sm font-medium transition-colors ' +
                (activeRoot === r
                  ? 'bg-background shadow-sm text-foreground'
                  : 'text-muted-foreground hover:text-foreground')
              }
            >
              {r}
            </button>
          ))}
        </div>
      )}

      <div className="space-y-5">
        {grouped.map(({ playlist, songs }) => (
          <Card key={playlist.id}>
            <div className="flex items-baseline justify-between gap-3 border-b border-border px-4 py-3">
              <div>
                <div className="text-sm font-semibold tracking-tight">{playlist.name}</div>
                <div className="text-xs text-muted-foreground">{songs.length} songs</div>
              </div>
              {playlist.drive_folder_id && (
                <a
                  href={`https://drive.google.com/drive/folders/${playlist.drive_folder_id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-blue-700 hover:underline"
                >
                  <ExternalLink size={12} /> Open folder
                </a>
              )}
            </div>
            <CardContent className="p-0">
              {songs.map((s) => (
                <SongRow key={s.id} song={s} onCopy={handleCopy} />
              ))}
            </CardContent>
          </Card>
        ))}
        {!loading && grouped.length === 0 && (
          <Card>
            <CardContent className="py-10 text-center text-sm text-muted-foreground">
              No songs available yet.
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
