'use client'

import { Bell, ChevronRight, LogOut, Settings, User } from 'lucide-react'
import { usePathname, useRouter } from 'next/navigation'
import { useState } from 'react'
import toast from 'react-hot-toast'

const breadcrumbMap: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/scraping/instant': 'Novo Scraping',
  '/scraping/scheduled': 'Scraping Agendado',
  '/jobs': 'Meus Jobs',
  '/results': 'Resultados',
  '/search': 'Busca Especializada',
  '/apis': 'APIs Publicas',
  '/ai': 'IA NVIDIA',
  '/exports': 'Exportacoes',
  '/logs': 'Logs',
  '/audit': 'Auditoria',
  '/settings': 'Configuracoes',
}

export function Header() {
  const pathname = usePathname()
  const router = useRouter()
  const [showUserMenu, setShowUserMenu] = useState(false)

  const currentPage = breadcrumbMap[pathname] || 'WebScrapy AI'

  const handleLogout = () => {
    localStorage.removeItem('token')
    toast.success('Sessao encerrada')
    router.push('/login')
  }

  return (
    <header className="h-14 border-b border-border bg-surface flex items-center justify-between px-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <span className="text-muted">WebScrapy AI</span>
        <ChevronRight className="w-3 h-3 text-muted" />
        <span className="text-foreground font-medium">{currentPage}</span>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3">
        {/* Notifications */}
        <button className="relative w-8 h-8 rounded-lg hover:bg-surface-2 flex items-center justify-center text-muted hover:text-foreground transition-colors">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-primary rounded-full" />
        </button>

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 h-8 px-2 rounded-lg hover:bg-surface-2 transition-colors"
          >
            <div className="w-6 h-6 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center">
              <User className="w-3 h-3 text-primary" />
            </div>
            <div className="text-left hidden sm:block">
              <p className="text-xs font-medium text-foreground leading-none">Admin</p>
              <p className="text-[10px] text-muted leading-none mt-0.5">admin@webscrapy.ai</p>
            </div>
          </button>

          {showUserMenu && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowUserMenu(false)}
              />
              <div className="absolute right-0 top-10 z-20 w-48 bg-surface border border-border rounded-xl shadow-xl overflow-hidden">
                <div className="p-3 border-b border-border">
                  <p className="text-sm font-medium text-foreground">Admin User</p>
                  <p className="text-xs text-muted">admin@webscrapy.ai</p>
                </div>
                <div className="p-1">
                  <button
                    onClick={() => { router.push('/settings'); setShowUserMenu(false) }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-foreground hover:bg-surface-2 rounded-lg transition-colors"
                  >
                    <Settings className="w-4 h-4 text-muted" />
                    Configuracoes
                  </button>
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-destructive hover:bg-destructive/10 rounded-lg transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                    Sair
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
