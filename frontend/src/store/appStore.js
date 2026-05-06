import { create } from 'zustand'
import { api } from '../api/client'

export const useAppStore = create((set, get) => ({
  status: null,
  songs: [],
  playlists: [],
  logs: [],
  isPolling: false,
  error: null,

  setError: (error) => set({ error }),

  refreshAll: async () => {
    try {
      const [status, songs, playlists] = await Promise.all([
        api.status(),
        api.songs(),
        api.playlists(),
      ])
      set({ status, songs, playlists, error: null })
    } catch (e) {
      set({ error: e.message })
    }
  },

  refreshLogs: async () => {
    try {
      const logs = await api.logs(500)
      set({ logs, error: null })
    } catch (e) {
      set({ error: e.message })
    }
  },

  startPolling: (intervalMs = 2000) => {
    if (get().isPolling) return
    set({ isPolling: true })
    const tick = async () => {
      if (!get().isPolling) return
      await get().refreshAll()
      setTimeout(tick, intervalMs)
    }
    tick()
  },

  stopPolling: () => set({ isPolling: false }),
}))
