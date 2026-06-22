'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  Zap,
  Calendar,
  Database,
  Globe,
  Bot,
  Download,
  FileText,
  Shield,
  Settings,
  ChevronLeft,
  ChevronRight,
  Search,
  ExternalLink,
  AlertCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface NavItem {
  label: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  badge?: string
  badgeVariant?: 'cyan' | 'emerald' | 'red'
}

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Novo Scraping', href: '/scraping/instant', icon: Zap },
  { label: 'Jobs Agendados', href: '/scraping/scheduled', icon: Calendar },
  { label: 'Meus Jobs', href: '/jobs', icon: Database, badge: '3', badgeVariant: 'cyan' },
  { label: 'Resultados', href: '/results', icon: FileText },
  { label: 'Busca Especializada', href: '/search', icon: Search },
  { label: 'APIs Publicas', href: '/apis', icon: Globe },
  { label: 'IA NVIDIA', href: '/ai', icon: Bot },
  { label: 'Exportacoes', href: '/exports', icon: Download },
  { label: 'Logs', href: '/logs', icon: AlertCircle },
  { label: 'Auditoria', href: '/audit', icon: Shield },
  { label: 'Configuracoes', href: '/settings', icon: Settings },
]

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const pathname = usePathname()

  return (
    <aside
      className={cn(
        'relative flex flex-col h-screen bg-surface border-r border-border transition-all duration-300 ease-in-out',
        collapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Logo */}
      <div className={cn(
        'flex items-center border-b border-border transition-all duration-300',
        collapsed ? 'h-16 px-4 justify-center' : 'h-16 px-5 gap-3'
      )}>
        <div className="flex-shrink-0 w-8 h-8 bg-primary/10 border border-primary/20 rounded-lg flex items-center justify-center glow-cyan">
          <Bot className="w-4 h-4 text-primary" />
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <span className="font-bold text-sm gradient-text whitespace-nowrap">WebScrapy AI</span>
            <p className="text-[10px] text-muted leading-none mt-0.5">Premium Platform</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-0.5">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'group flex items-center rounded-lg transition-all duration-150 relative',
                collapsed ? 'h-10 w-10 mx-auto justify-center' : 'h-9 px-3 gap-3',
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted hover:bg-surface-2 hover:text-foreground'
              )}
              title={collapsed ? item.label : undefined}
            >
              {/* Active indicator */}
              {isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-primary rounded-r-full" />
              )}

              <Icon className={cn(
                'flex-shrink-0 transition-colors',
                collapsed ? 'w-4 h-4' : 'w-4 h-4',
                isActive ? 'text-primary' : 'text-muted group-hover:text-foreground'
              )} />

              {!collapsed && (
                <span className="text-sm font-medium flex-1 truncate">{item.label}</span>
              )}

              {!collapsed && item.badge && (
                <span className={cn(
                  'flex-shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded-full',
                  item.badgeVariant === 'cyan' && 'bg-primary/20 text-primary',
                  item.badgeVariant === 'emerald' && 'bg-secondary/20 text-secondary',
                  item.badgeVariant === 'red' && 'bg-destructive/20 text-destructive',
                )}>
                  {item.badge}
                </span>
              )}

              {/* Tooltip for collapsed state */}
              {collapsed && (
                <span className="absolute left-full ml-2 px-2 py-1 bg-surface-2 border border-border text-foreground text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50">
                  {item.label}
                </span>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      {!collapsed && (
        <div className="p-4 border-t border-border">
          <div className="flex items-center gap-2 text-xs text-muted">
            <span>v0.1.0</span>
            <span>·</span>
            <a
              href="#"
              className="hover:text-primary transition-colors flex items-center gap-1"
            >
              Docs <ExternalLink className="w-2.5 h-2.5" />
            </a>
          </div>
        </div>
      )}

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-20 w-6 h-6 bg-surface border border-border rounded-full flex items-center justify-center text-muted hover:text-foreground hover:border-primary/50 transition-colors z-10"
      >
        {collapsed ? (
          <ChevronRight className="w-3 h-3" />
        ) : (
          <ChevronLeft className="w-3 h-3" />
        )}
      </button>
    </aside>
  )
}
