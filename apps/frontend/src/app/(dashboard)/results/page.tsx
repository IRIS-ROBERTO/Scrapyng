'use client'

import { useEffect, useState } from 'react'
import { BarChart3, Eye, FileText, RefreshCw, Search } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { scraperApi } from '@/lib/api'

type ResultStatus = 'pending' | 'running' | 'completed' | 'failed' | 'paused'

interface ResultJob {
  id: string
  name: string
  url: string
  status: ResultStatus
  job_type?: string
  items_count?: number | null
  updated_at?: string
  created_at?: string
}

const demoResults: ResultJob[] = [
  { id: '1', name: 'Precos Amazon BR', url: 'amazon.com.br/search', status: 'completed', job_type: 'scheduled', items_count: 1250, updated_at: '2026-06-22T13:40:00Z' },
  { id: '2', name: 'Noticias G1 Tech', url: 'g1.globo.com/tecnologia', status: 'completed', job_type: 'scheduled', items_count: 87, updated_at: '2026-06-22T13:10:00Z' },
  { id: '4', name: 'Vagas Remoteok', url: 'remoteok.com', status: 'pending', job_type: 'scheduled', items_count: 0, updated_at: '2026-06-22T12:00:00Z' },
  { id: '6', name: 'Passagens Latam', url: 'latamairlines.com', status: 'completed', job_type: 'instant', items_count: 45, updated_at: '2026-06-22T11:30:00Z' },
]

function StatusBadge({ status }: { status: ResultStatus }) {
  const config: Record<ResultStatus, { variant: 'success' | 'info' | 'warning' | 'destructive' | 'secondary'; label: string }> = {
    completed: { variant: 'success', label: 'Com resultados' },
    running: { variant: 'info', label: 'Rodando' },
    pending: { variant: 'warning', label: 'Pendente' },
    failed: { variant: 'destructive', label: 'Falhou' },
    paused: { variant: 'secondary', label: 'Pausado' },
  }
  const item = config[status]
  return <Badge variant={item.variant}>{item.label}</Badge>
}

function formatDate(value?: string) {
  if (!value) return '-'
  return new Date(value).toLocaleString('pt-BR')
}

export default function ResultsIndexPage() {
  const [jobs, setJobs] = useState<ResultJob[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  const loadJobs = async () => {
    setLoading(true)
    try {
      const response = await scraperApi.getJobs({ page: 1 })
      setJobs(response.data.items || [])
    } catch {
      setJobs(demoResults)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadJobs()
  }, [])

  const filtered = jobs.filter((job) =>
    `${job.name} ${job.url}`.toLowerCase().includes(search.toLowerCase())
  )

  const completed = jobs.filter(job => job.status === 'completed').length
  const totalItems = jobs.reduce((sum, job) => sum + (job.items_count || 0), 0)

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">Resultados</h1>
          <p className="text-sm text-muted mt-0.5">Acesse os dados coletados por cada job</p>
        </div>
        <Button variant="outline" size="sm" onClick={loadJobs} loading={loading}>
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg border border-primary/20 bg-primary/10 flex items-center justify-center">
              <FileText className="w-4 h-4 text-primary" />
            </div>
            <div>
              <p className="text-xl font-bold text-foreground">{jobs.length}</p>
              <p className="text-xs text-muted">Jobs monitorados</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg border border-secondary/20 bg-secondary/10 flex items-center justify-center">
              <BarChart3 className="w-4 h-4 text-secondary" />
            </div>
            <div>
              <p className="text-xl font-bold text-foreground">{completed}</p>
              <p className="text-xs text-muted">Com resultados</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg border border-accent/20 bg-accent/10 flex items-center justify-center">
              <FileText className="w-4 h-4 text-accent" />
            </div>
            <div>
              <p className="text-xl font-bold text-foreground">{totalItems.toLocaleString('pt-BR')}</p>
              <p className="text-xs text-muted">Registros coletados</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar resultado por job ou URL..."
              className="w-full bg-surface border border-border rounded-lg pl-9 pr-4 py-2 text-sm text-foreground placeholder-muted focus:outline-none focus:border-primary transition-colors"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <Skeleton key={index} className="h-14 w-full" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-16 text-muted">
              <FileText className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm font-medium">Nenhum resultado encontrado</p>
              <p className="text-xs mt-1">Execute ou agende um job para gerar resultados</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-border">
                  <tr>
                    <th className="text-left text-xs text-muted font-medium px-6 py-3">Job</th>
                    <th className="text-left text-xs text-muted font-medium px-4 py-3">Origem</th>
                    <th className="text-left text-xs text-muted font-medium px-4 py-3">Status</th>
                    <th className="text-right text-xs text-muted font-medium px-4 py-3">Registros</th>
                    <th className="text-left text-xs text-muted font-medium px-4 py-3">Atualizado</th>
                    <th className="text-right text-xs text-muted font-medium px-6 py-3">Acoes</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((job) => (
                    <tr key={job.id} className="border-b border-border last:border-0 hover:bg-surface-2/50 transition-colors">
                      <td className="px-6 py-3">
                        <a href={`/results/${job.id}`} className="text-sm font-medium text-foreground hover:text-primary transition-colors">
                          {job.name}
                        </a>
                        <p className="text-[10px] text-muted mt-0.5">{job.job_type === 'scheduled' ? 'Agendado' : 'Instantaneo'}</p>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs text-muted font-mono truncate max-w-[240px] block">{job.url}</span>
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={job.status} />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-xs text-foreground font-mono">{(job.items_count || 0).toLocaleString('pt-BR')}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs text-muted">{formatDate(job.updated_at || job.created_at)}</span>
                      </td>
                      <td className="px-6 py-3">
                        <div className="flex justify-end">
                          <Button asChild size="sm" variant="outline">
                            <a href={`/results/${job.id}`}>
                              <Eye className="w-3.5 h-3.5" />
                              Abrir
                            </a>
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
