import { useEffect, useMemo, useState } from 'react'
import { ExternalLink, Check, X, RotateCw, Forward } from 'lucide-react'
import { useAppStore } from '../store/appStore'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { ConfidenceBadge } from '../components/ui/Badge'
import { api } from '../api/client'

function CandidateRow({ candidate, onApprove, onReject }) {
  return (
    <div className="flex items-start gap-3 rounded-md border border-border p-3">
      {candidate.thumbnail_url && (
        <img
          src={candidate.thumbnail_url}
          alt=""
          className="h-16 w-28 rounded-md object-cover bg-muted shrink-0"
        />
      )}
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <a
            href={candidate.url}
            target="_blank"
            rel="noreferrer"
            className="text-sm font-medium hover:underline line-clamp-2"
          >
            {candidate.title}
          </a>
          <ConfidenceBadge score={candidate.confidence_score} />
        </div>
        <div className="mt-0.5 text-xs text-muted-foreground">
          {candidate.channel} {candidate.duration ? `• ${candidate.duration}` : ''}
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          <Button size="sm" onClick={() => onApprove(candidate)}>
            <Check size={12} className="mr-1" /> Approve
          </Button>
          <Button size="sm" variant="ghost" onClick={() => onReject(candidate)}>
            <X size={12} className="mr-1" /> Reject
          </Button>
          <a
            href={candidate.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs text-blue-700 hover:underline"
          >
            <ExternalLink size={12} /> Open on YouTube
          </a>
        </div>
      </div>
    </div>
  )
}

function ReviewCard({ song, onChange }) {
  const [candidates, setCandidates] = useState(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)

  const load = async () => {
    setLoading(true)
    setErr(null)
    try {
      const c = await api.candidates(song.id)
      setCandidates(c)
    } catch (e) {
      setErr(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [song.id])

  const handleApprove = async (cand) => {
    try {
      await api.approveCandidate(song.id, cand.id, true)
      onChange?.()
    } catch (e) {
      setErr(e.message)
    }
  }

  const handleReject = async (cand) => {
    setCandidates((curr) => curr?.filter((c) => c.id !== cand.id))
  }

  const handleRetry = async () => {
    try {
      await api.retry(song.id)
      onChange?.()
    } catch (e) {
      setErr(e.message)
    }
  }

  const handleSkip = async () => {
    try {
      await api.skip(song.id, 'Skipped from review page')
      onChange?.()
    } catch (e) {
      setErr(e.message)
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>
              {song.track_no} — {song.song_name}
            </CardTitle>
            <div className="mt-0.5 text-xs text-muted-foreground">
              Expected artist: <span className="font-medium">{song.artist}</span> • Playlist: {song.playlist_name}
            </div>
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={handleRetry}>
              <RotateCw size={12} className="mr-1" /> Retry Search
            </Button>
            <Button size="sm" variant="ghost" onClick={handleSkip}>
              <Forward size={12} className="mr-1" /> Mark Skipped
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading && <div className="text-xs text-muted-foreground">Loading candidates…</div>}
        {err && <div className="text-xs text-red-700">{err}</div>}
        {!loading && candidates && candidates.length === 0 && (
          <div className="text-xs text-muted-foreground">No candidates available. Try Retry Search.</div>
        )}
        <div className="space-y-2">
          {candidates?.map((c) => (
            <CandidateRow
              key={c.id}
              candidate={c}
              onApprove={handleApprove}
              onReject={handleReject}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

export default function ManualReviewPage() {
  const { songs, refreshAll, startPolling, stopPolling } = useAppStore()
  useEffect(() => {
    refreshAll()
    startPolling(2000)
    return () => stopPolling()
  }, [refreshAll, startPolling, stopPolling])

  const reviewSongs = useMemo(
    () => songs.filter((s) => s.status === 'Needs Manual Review'),
    [songs],
  )

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold tracking-tight">Manual Review</h1>
      {reviewSongs.length === 0 && (
        <Card>
          <CardContent className="pt-6 text-sm text-muted-foreground">
            Nothing waiting for review. Songs with confidence between 70 and 84 will appear here.
          </CardContent>
        </Card>
      )}
      <div className="space-y-3">
        {reviewSongs.map((s) => (
          <ReviewCard key={s.id} song={s} onChange={refreshAll} />
        ))}
      </div>
    </div>
  )
}
