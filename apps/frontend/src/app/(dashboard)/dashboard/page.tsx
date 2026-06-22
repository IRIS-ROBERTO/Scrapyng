'use client'

import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Area, AreaChart,
} from 'recharts'
import {
  Database, Zap, CheckCircle, HardDrive, Activity,
  Bot, Server, Clock, AlertCircle, TrendingUp,
} from 'lucide-react'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

// Mock data — replace with real API calls
const mockChartData = [
  { day: 'Seg', jobs: 45, success: 42, failed: 3 },
  { day: 'Ter', jobs: 62, success: 58, failed: 4 },
  { day: 'Qua', jobs: 38, success: 37, failed: 1 },
  { day: 'Qui', jobs: 75, success: 70, failed: 5 },
  { day: 'Sex', jobs: 89, success: 85, failed: 4 },
  { day: 'Sab', jobs: 52, success: 50, failed: 2 },
  { day: 'Dom', jobs: 34, success: 33, failed: 1 },
]

const mockRecentJobs = [
  { id: '1', name: 'Precos E-commerce', url: 'amazon.com.br', status: 'completed', type: 'scheduled', items: 1250, lastRun: '5 min atras' },
  { id: '2', name: 'Noticias Tech', url: 'techcrunch.com', status: 'running', type: 'instant', items: 48, lastRun: 'Agora' },
  { id: '3', name: 'Leads LinkedIn', url: 'linkedin.com', status: 'pending', type: 'scheduled', items: 0, lastRun: '1h atras' },
  { id: '4', name: 'Vagas Remoto', url: 'remoteok.com', status: 'failed', type: 'instant', items: 0, lastRun: '2h atras' },
  { id: '5', name: 'Cotacoes Forex', url: 'xe.com', status: 'completed', type: 'scheduled', items: 320, lastRun: '10 min atras' },
]

const mockServices = [
  { name: 'Scraper Engine', status: 'online', latency: '12ms', icon: Server },
  { name: 'AI NVIDIA', status: 'online', latency: '89ms', icon: Bot },
  { name: 'Scheduler', status: 'online', latency: '5ms', icon: Clock },
  { name: 'Export Engine', status: 'online', latency: '8ms', icon: Database },
]

const mockSparkline = [34, 45, 38, 62, 75, 89, 52]

type JobStatus = 'completed' | 'running' | 'pending' | 'failed'

function StatusBadge({ status }: { status: JobStatus }) {
  const variants: Record<JobStatus, { variant: 'success' | 'info' | 'warning' | 'destructive'; label: string; pulse: boolean }> = {
    completed: { variant: 'success', label: 'Concluido', pulse: false },
    running: { variant: 'info', label: 'Rodando', pulse: true },
    pending: { variant: 'warning', label: 'Pendente', pulse: false },
    failed: { variant: 'destructive', label: 'Falhou', pulse: false },
  }
  const v = variants[status]
  return (
    <Badge variant={v.variant} className={v.pulse ? 'animate-pulse' : ''}>
      <span className={`w-1.5 h-1.5 rounded-full inline-block ${
        status === 'completed' ? 'bg-secondary' :
        status === 'running' ? 'bg-primary' :
        status === 'pending' ? 'bg-warning' : 'bg-destructive'
      }`} />
      {v.label}
    </Badge>
  )
}

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number; name: string }>; label?: string }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-surface-2 border border-border rounded-lg p-3 shadow-xl">
        <p className="text-xs text-muted mb-2">{label}</p>
        {payload.map((p, i) => (
          <p key={i} className="text-xs">
            <span className="text-muted">{p.name}: </span>
            <span className="text-foreground font-semibold">{p.value}</span>
          </p>
        ))}
      </div>
    )
  }
  return null
}

export default function DashboardPage() {
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Simulate API load
    const t = setTimeout(() => setLoading(false), 800)
    return () => clearTimeout(t)
  }, [])

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">Dashboard</h1>
          <p className="text-sm text-muted mt-0.5">Visao geral da plataforma</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted bg-surface border border-border rounded-lg px-3 py-1.5">
          <Activity className="w-3 h-3 text-secondary" />
          <span>Todos os sistemas operacionais</span>
        </div>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard
          title="Total de Jobs"
          value={loading ? '...' : 247}
          subtitle="Ultimos 30 dias"
          change={12}
          icon={Database}
          iconColor="cyan"
          sparkline={mockSparkline}
          loading={loading}
        />
        <MetricCard
          title="Jobs Ativos"
          value={loading ? '...' : 8}
          subtitle="Rodando agora"
          change={3}
          icon={Zap}
          iconColor="emerald"
          loading={loading}
        />
        <MetricCard
          title="Taxa de Sucesso"
          value={loading ? '...' : '94.2%'}
          subtitle="Media semanal"
          change={2}
          icon={CheckCircle}
          iconColor="accent"
          sparkline={[88, 91, 89, 93, 94, 92, 94]}
          loading={loading}
        />
        <MetricCard
          title="Dados Coletados"
          value={loading ? '...' : '2.4M'}
          subtitle="Registros totais"
          change={18}
          icon={HardDrive}
          iconColor="warning"
          loading={loading}
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Volume chart */}
        <Card className="xl:col-span-2">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Volume de Scraping — Ultimos 7 dias</CardTitle>
              <div className="flex items-center gap-3 text-xs text-muted">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-primary inline-block" />
                  Jobs
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-secondary inline-block" />
                  Sucesso
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-destructive inline-block" />
                  Falhas
                </span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-48 w-full" />
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={mockChartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorJobs" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorSuccess" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
                  <XAxis dataKey="day" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="jobs" name="Jobs" stroke="#06b6d4" strokeWidth={2} fill="url(#colorJobs)" />
                  <Area type="monotone" dataKey="success" name="Sucesso" stroke="#10b981" strokeWidth={2} fill="url(#colorSuccess)" />
                  <Bar dataKey="failed" name="Falhas" fill="#ef444430" radius={[2, 2, 0, 0]} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Services health */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Health dos Servicos</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))
            ) : (
              mockServices.map((svc) => {
                const Icon = svc.icon
                return (
                  <div key={svc.name} className="flex items-center justify-between p-3 bg-surface-2 rounded-lg border border-border">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-secondary/10 border border-secondary/20 rounded-lg flex items-center justify-center">
                        <Icon className="w-4 h-4 text-secondary" />
                      </div>
                      <div>
                        <p className="text-xs font-medium text-foreground">{svc.name}</p>
                        <p className="text-[10px] text-muted">{svc.latency}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-secondary status-pulse" />
                      <span className="text-xs text-secondary font-medium">Online</span>
                    </div>
                  </div>
                )
              })
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent jobs table */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Jobs Recentes</CardTitle>
            <a href="/jobs" className="text-xs text-primary hover:text-primary/80 transition-colors flex items-center gap-1">
              Ver todos <TrendingUp className="w-3 h-3" />
            </a>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left text-xs text-muted font-medium px-6 py-3">Nome</th>
                    <th className="text-left text-xs text-muted font-medium px-4 py-3">URL</th>
                    <th className="text-left text-xs text-muted font-medium px-4 py-3">Status</th>
                    <th className="text-left text-xs text-muted font-medium px-4 py-3">Tipo</th>
                    <th className="text-right text-xs text-muted font-medium px-6 py-3">Itens</th>
                    <th className="text-right text-xs text-muted font-medium px-6 py-3">Ultima Execucao</th>
                  </tr>
                </thead>
                <tbody>
                  {mockRecentJobs.map((job) => (
                    <tr key={job.id} className="border-b border-border last:border-0 hover:bg-surface-2/50 transition-colors">
                      <td className="px-6 py-3">
                        <a href={`/jobs/${job.id}`} className="text-foreground hover:text-primary transition-colors font-medium">
                          {job.name}
                        </a>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-muted text-xs font-mono">{job.url}</span>
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={job.status as JobStatus} />
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={job.type === 'scheduled' ? 'accent' : 'secondary'}>
                          {job.type === 'scheduled' ? 'Agendado' : 'Instantaneo'}
                        </Badge>
                      </td>
                      <td className="px-6 py-3 text-right">
                        <span className="text-foreground font-mono text-xs">
                          {job.items.toLocaleString('pt-BR')}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-right">
                        <span className="text-muted text-xs">{job.lastRun}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* AI Usage card */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <Bot className="w-4 h-4 text-primary" />
              <CardTitle className="text-sm">NVIDIA AI — Uso do Mes</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-20 w-full" />
            ) : (
              <div className="space-y-3">
                <div className="flex justify-between items-end">
                  <div>
                    <p className="text-2xl font-bold text-foreground">1,247</p>
                    <p className="text-xs text-muted">chamadas de API</p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-primary">$2.47</p>
                    <p className="text-xs text-muted">custo estimado</p>
                  </div>
                </div>
                <div className="w-full bg-surface-2 rounded-full h-1.5">
                  <div className="bg-primary h-1.5 rounded-full" style={{ width: '42%' }} />
                </div>
                <p className="text-xs text-muted">42% da cota mensal utilizada</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-warning" />
              <CardTitle className="text-sm">Alertas do Sistema</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-20 w-full" />
            ) : (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs p-2 bg-warning/10 border border-warning/20 rounded-lg">
                  <AlertCircle className="w-3 h-3 text-warning flex-shrink-0" />
                  <span className="text-foreground">4 jobs falharam nas ultimas 24h</span>
                </div>
                <div className="flex items-center gap-2 text-xs p-2 bg-surface-2 border border-border rounded-lg">
                  <CheckCircle className="w-3 h-3 text-secondary flex-shrink-0" />
                  <span className="text-muted">Sistema funcionando normalmente</span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Atividade Rapida</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {loading ? (
              <Skeleton className="h-20 w-full" />
            ) : (
              <>
                <a href="/scraping/instant"
                  className="flex items-center gap-3 p-2.5 bg-primary/10 border border-primary/20 rounded-lg hover:bg-primary/15 transition-colors group">
                  <Zap className="w-4 h-4 text-primary" />
                  <span className="text-sm text-foreground group-hover:text-primary transition-colors">Novo Scraping Rapido</span>
                </a>
                <a href="/scraping/scheduled"
                  className="flex items-center gap-3 p-2.5 bg-surface-2 border border-border rounded-lg hover:bg-surface-2/80 transition-colors group">
                  <ActivityIcon className="w-4 h-4 text-muted group-hover:text-foreground" />
                  <span className="text-sm text-muted group-hover:text-foreground transition-colors">Agendar Job</span>
                </a>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function ActivityIcon({ className }: { className?: string }) {
  return <Activity className={className} />
}
