import React from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'

interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  change?: number
  icon: React.ComponentType<{ className?: string }>
  iconColor?: 'cyan' | 'emerald' | 'accent' | 'warning' | 'destructive'
  sparkline?: number[]
  loading?: boolean
}

const colorMap = {
  cyan: {
    bg: 'bg-primary/10',
    border: 'border-primary/20',
    icon: 'text-primary',
    glow: 'glow-cyan',
  },
  emerald: {
    bg: 'bg-secondary/10',
    border: 'border-secondary/20',
    icon: 'text-secondary',
    glow: 'glow-emerald',
  },
  accent: {
    bg: 'bg-accent/10',
    border: 'border-accent/20',
    icon: 'text-accent',
    glow: '',
  },
  warning: {
    bg: 'bg-warning/10',
    border: 'border-warning/20',
    icon: 'text-warning',
    glow: '',
  },
  destructive: {
    bg: 'bg-destructive/10',
    border: 'border-destructive/20',
    icon: 'text-destructive',
    glow: '',
  },
}

function MiniSparkline({ data }: { data: number[] }) {
  if (!data || data.length === 0) return null

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const width = 80
  const height = 24
  const step = width / (data.length - 1)

  const points = data.map((val, idx) => {
    const x = idx * step
    const y = height - ((val - min) / range) * height
    return `${x},${y}`
  }).join(' ')

  return (
    <svg width={width} height={height} className="opacity-60">
      <polyline
        points={points}
        fill="none"
        stroke="#06b6d4"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function MetricCard({
  title,
  value,
  subtitle,
  change,
  icon: Icon,
  iconColor = 'cyan',
  sparkline,
  loading = false,
}: MetricCardProps) {
  const colors = colorMap[iconColor]

  if (loading) {
    return (
      <div className="bg-surface border border-border rounded-xl p-5 animate-pulse">
        <div className="flex items-start justify-between mb-4">
          <div className="w-10 h-10 bg-surface-2 rounded-lg" />
          <div className="w-16 h-5 bg-surface-2 rounded" />
        </div>
        <div className="w-24 h-8 bg-surface-2 rounded mb-2" />
        <div className="w-32 h-4 bg-surface-2 rounded" />
      </div>
    )
  }

  return (
    <div className={cn(
      'relative bg-surface border border-border rounded-xl p-5 overflow-hidden',
      'hover:border-border/80 transition-all duration-200 group',
      'hover:shadow-lg hover:shadow-black/20'
    )}>
      {/* Subtle gradient overlay */}
      <div className={cn(
        'absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300',
        'bg-gradient-to-br from-primary/3 to-transparent'
      )} />

      <div className="relative">
        <div className="flex items-start justify-between mb-4">
          {/* Icon */}
          <div className={cn(
            'w-10 h-10 rounded-lg border flex items-center justify-center',
            colors.bg,
            colors.border,
            colors.glow
          )}>
            <Icon className={cn('w-5 h-5', colors.icon)} />
          </div>

          {/* Sparkline */}
          {sparkline && sparkline.length > 0 && (
            <div className="flex items-end">
              <MiniSparkline data={sparkline} />
            </div>
          )}
        </div>

        {/* Value */}
        <div className="mb-1">
          <span className="text-2xl font-bold text-foreground tabular-nums">
            {typeof value === 'number' ? value.toLocaleString('pt-BR') : value}
          </span>
        </div>

        {/* Title */}
        <p className="text-sm text-muted font-medium">{title}</p>

        {/* Subtitle and change */}
        <div className="flex items-center justify-between mt-2">
          {subtitle && (
            <span className="text-xs text-muted">{subtitle}</span>
          )}
          {change !== undefined && (
            <div className={cn(
              'flex items-center gap-1 text-xs font-medium',
              change > 0 ? 'text-secondary' : change < 0 ? 'text-destructive' : 'text-muted'
            )}>
              {change > 0 ? (
                <TrendingUp className="w-3 h-3" />
              ) : change < 0 ? (
                <TrendingDown className="w-3 h-3" />
              ) : (
                <Minus className="w-3 h-3" />
              )}
              <span>{Math.abs(change)}%</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
