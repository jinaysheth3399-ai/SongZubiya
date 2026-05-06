// Centralized fetch wrapper. The Vite dev server proxies /api -> uvicorn.
const BASE = ''

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let detail
    try {
      detail = (await res.json()).detail
    } catch {
      detail = res.statusText
    }
    throw new Error(detail || `Request failed: ${res.status}`)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  status: () => request('/api/status'),
  songs: () => request('/api/songs'),
  playlists: () => request('/api/playlists'),
  logs: (limit = 500) => request(`/api/logs?limit=${limit}`),
  candidates: (songId) => request(`/api/songs/${songId}/candidates`),

  start: () => request('/api/start', { method: 'POST' }),
  pause: () => request('/api/pause', { method: 'POST' }),
  resume: () => request('/api/resume', { method: 'POST' }),

  retry: (songId) => request(`/api/retry/${songId}`, { method: 'POST' }),
  approveCandidate: (songId, candidateId, autoProcess = true) =>
    request('/api/approve-candidate', {
      method: 'POST',
      body: JSON.stringify({
        song_id: songId,
        candidate_id: candidateId,
        auto_process: autoProcess,
      }),
    }),
  skip: (songId, reason) =>
    request(`/api/skip/${songId}`, {
      method: 'POST',
      body: JSON.stringify({ reason: reason || null }),
    }),

  driveAuth: () => request('/api/drive/auth', { method: 'POST' }),
  driveTest: () => request('/api/drive/test', { method: 'POST' }),
}
