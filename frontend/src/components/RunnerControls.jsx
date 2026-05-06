import { useState } from 'react'
import { Play, Pause, RotateCw, KeyRound, CheckCircle2 } from 'lucide-react'
import { Button } from './ui/Button'
import { api } from '../api/client'

export function RunnerControls({ runner, onChange }) {
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)

  const wrap = async (fn) => {
    setBusy(true)
    setMsg(null)
    try {
      await fn()
      onChange?.()
    } catch (e) {
      setMsg(e.message)
    } finally {
      setBusy(false)
    }
  }

  const isRunning = runner?.is_running
  const isPaused = runner?.is_paused

  return (
    <div className="flex flex-wrap items-center gap-2">
      {!isRunning && (
        <Button onClick={() => wrap(api.start)} disabled={busy}>
          <Play size={14} className="mr-1" /> Start
        </Button>
      )}
      {isRunning && !isPaused && (
        <Button variant="secondary" onClick={() => wrap(api.pause)} disabled={busy}>
          <Pause size={14} className="mr-1" /> Pause
        </Button>
      )}
      {isRunning && isPaused && (
        <Button onClick={() => wrap(api.resume)} disabled={busy}>
          <Play size={14} className="mr-1" /> Resume
        </Button>
      )}
      <Button variant="outline" onClick={() => wrap(api.driveAuth)} disabled={busy}>
        <KeyRound size={14} className="mr-1" /> Drive Auth
      </Button>
      <Button variant="outline" onClick={() => wrap(api.driveTest)} disabled={busy}>
        <CheckCircle2 size={14} className="mr-1" /> Test Drive
      </Button>
      {busy && (
        <span className="text-xs text-muted-foreground inline-flex items-center">
          <RotateCw size={12} className="mr-1 animate-spin" /> working…
        </span>
      )}
      {msg && <span className="text-xs text-red-700">{msg}</span>}
    </div>
  )
}
