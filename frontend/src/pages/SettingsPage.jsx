import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { api } from '../api/client'

export default function SettingsPage() {
  const [authMsg, setAuthMsg] = useState(null)
  const [testMsg, setTestMsg] = useState(null)
  const [busy, setBusy] = useState(false)

  const runAuth = async () => {
    setBusy(true)
    setAuthMsg(null)
    try {
      await api.driveAuth()
      setAuthMsg('Drive auth successful — token.json is ready.')
    } catch (e) {
      setAuthMsg(`Auth failed: ${e.message}`)
    } finally {
      setBusy(false)
    }
  }

  const runTest = async () => {
    setBusy(true)
    setTestMsg(null)
    try {
      const res = await api.driveTest()
      setTestMsg(`Connected as ${res.drive?.user?.emailAddress || 'unknown'}.`)
    } catch (e) {
      setTestMsg(`Test failed: ${e.message}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold tracking-tight">Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle>Google Drive</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            The first auth run opens a browser on the host running the backend.
            After consent, a <code>token.json</code> file is written to the project root.
          </p>
          <div className="flex gap-2">
            <Button onClick={runAuth} disabled={busy}>Run Drive Auth</Button>
            <Button variant="outline" onClick={runTest} disabled={busy}>Test Drive Connection</Button>
          </div>
          {authMsg && <div className="text-xs">{authMsg}</div>}
          {testMsg && <div className="text-xs">{testMsg}</div>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>About</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Use the <strong>Songs</strong> page to start the runner, watch progress, and copy Drive links.
            Songs with confidence 70–84 land on <strong>Manual Review</strong>; below 70 are skipped.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
