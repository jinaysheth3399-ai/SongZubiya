import { Outlet } from 'react-router-dom'
import { Music2 } from 'lucide-react'

export default function Layout() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-10">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 py-3 flex items-center gap-2">
          <Music2 size={20} className="text-primary" />
          <span className="text-base font-semibold tracking-tight">SongZubiya</span>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 sm:px-6 py-6">
        <Outlet />
      </main>
    </div>
  )
}
