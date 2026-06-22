'use client'

import { useEffect, useState } from 'react'
import { Play, Pause, Trash2, Eye, Filter, RefreshCw, Search } from 'lucide-react'
import toast from 'react-hot-toast'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { scraperApi } from '@/lib/api'

type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'paused'
type JobType = 'instant' | 'scheduled'

interface Job {
  id: string
  name: string
  url: string
  type: JobType
  status: JobStatus
  items: number
  lastRun: string
  nextRun: string | null
  engine: string
}

interface ApiJob {
  id: string
  name: string
  url: string
  status: JobStatus
  job_type: JobType
  items_count?: number | null
  last_run?: string | null
  next_run?: string | null
  updated_at?: string
  created_at?: string
}

const mockJobs: Job[] = [
  { id: '1', name: 'Precos Amazon BR', url: 'amazon.com.br/search', type: 'scheduled', status: 'running', items: 1250, lastRun: '2 min atras', nextRun: 'em 1h', engine: 'scrapy' },
  { id: '2', name: 'Noticias G1 Tech', url: 'g1.globo.com/tecnologia', type: 'scheduled', status: 'completed', items: 87, lastRun: '30 min atras', nextRun: 'amanha 09:00', engine: 'playwright' },
  { id: '3', name: 'Leads LinkedIn SaaS', url: 'linkedin.com/search', type: 'instant', status: 'failed', items: 0, lastRun: '1h atras', nextRun: null, engine: 'playwright' },
  { id: '4', name: 'Vagas Remoteok', url: 'remoteok.com', type: 'scheduled', status: 'pending', items: 0, lastRun: '3h atras', nextRun: 'em 21h', engine: 'scrapy' },
  { id: '5', name: 'Cotacoes Crypto', url: 'coinmarketcap.com', type: 'scheduled', status: 'completed', items: 500, lastRun: '5 min atras', nextRun: 'em 55 min', engine: 'scrapy' },
  { id: '6', name: 'Passagens Latam', url: 'latamairlines.com', type: 'instant', status: 'completed', items: 45, lastRun: '2h atras', nextRun: null, engine: 'playwright' },
  { id: '7', name: 'Imoveis ZapImoveis', url: 'zapimoveis.com.br', type: 'scheduled', status: 'paused', items: 320, lastRun: '1 dia atras', nextRun: 'pausado', engine: 'scrapy' },
]

function StatusBadge({ status }: { status: JobStatus }) {
  const config: Record<JobStatus, { variant: 'success' | 'info' | 'warning' | 'destructive' | 'secondary'; label: string; dot: string }> = {
    completed: { variant: 'success', label: 'Concluido', dot: 'bg-secondary' },
    running: { variant: 'info', label: 'Rodando', dot: 'bg-primary animate-pulse' },
    pending: { variant: 'warning', label: 'Pendente', dot: 'bg-warning' },
    failed: { variant: 'destructive', label: 'Falhou', dot: 'bg-destructive' },
    paused: { variant: 'secondary', label: 'Pausado', dot: 'bg-muted' },
  }
  const c = config[status]
  return (
    <Badge variant={c.variant}>
      <span className={`w-1.5 h-1.5 rounded-full inline-block ${c.dot}`} />
      {c.label}
    </Badge>
  )
}

function formatDate(value?: string | null) {
  if (!value) return '—'
  return new Date(value).toLocaleString('pt-BR')
}

function mapApiJob(job: ApiJob): Job {
  const usePlaywright = false
  return {
    id: job.id,
    name: job.name,
    url: job.url,
    type: job.job_type,
    status: job.status,
    items: job.items_count || 0,
    lastRun: formatDate(job.last_run || job.updated_at || job.created_at),
    nextRun: job.next_run ? formatDate(job.next_run) : null,
    engine: usePlaywright ? 'playwright' : 'scrapy',
  }
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [actionJobId, setActionJobId] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [page, setPage] = useState(1)
  const perPage = 5

  const loadJobs = async () => {
    setLoading(true)
    try {
      const response = await scraperApi.getJobs({ page: 1, page_size: 100 })
      setJobs((response.data.items || []).map(mapApiJob))
    } catch {
      setJobs(mockJobs)
      toast.error('Usando lista demo: API de jobs indisponivel')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadJobs()
  }, [])

  const filtered = jobs.filter((j) => {
    const matchSearch = j.name.toLowerCase().includes(search.toLowerCase()) ||
      j.url.toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'all' || j.status === statusFilter
    const matchType = typeFilter === 'all' || j.type === typeFilter
    return matchSearch && matchStatus && matchType
  })

  const paginated = filtered.slice((page - 1) * perPage, page * perPage)
  const totalPages = Math.ceil(filtered.length / perPage)

  const handlePause = async (id: string) => {
    setActionJobId(id)
    try {
      await scraperApi.pauseJob(id)
      setJobs(prev => prev.map(j => j.id === id ? { ...j, status: 'paused' as JobStatus } : j))
      toast.success('Job pausado')
    } catch {
      toast.error('Nao foi possivel pausar o job')
    } finally {
      setActionJobId(null)
    }
  }

  const handleResume = async (id: string) => {
    setActionJobId(id)
    try {
      await scraperApi.resumeJob(id)
      setJobs(prev => prev.map(j => j.id === id ? { ...j, status: 'running' as JobStatus } : j))
      toast.success('Job retomado')
    } catch {
      toast.error('Nao foi possivel retomar o job')
    } finally {
      setActionJobId(null)
    }
  }

  const handleDelete = async (id: string) => {
    const job = jobs.find(item => item.id === id)
    const confirmed = window.confirm(`Excluir definitivamente o job "${job?.name || id}"?`)
    if (!confirmed) return

    setActionJobId(id)
    try {
      await scraperApi.deleteJob(id)
      setJobs(prev => prev.filter(j => j.id !== id))
      toast.success('Job removido')
    } catch {
      toast.error('Nao foi possivel excluir o job')
    } finally {
      setActionJobId(null)
    }
  }

  const handleRefresh = () => {
    loadJobs()
    toast.success('Lista atualizada')
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">Meus Jobs</h1>
          <p className="text-sm text-muted mt-0.5">{jobs.length} jobs no total</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleRefresh} loading={loading}>
            <RefreshCw className="w-4 h-4" />
          </Button>
          <Button size="sm" asChild>
            <a href="/scraping/instant">+ Novo Job</a>
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-3">
            {/* Search */}
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar por nome ou URL..."
                className="w-full bg-surface border border-border rounded-lg pl-9 pr-4 py-2 text-sm text-foreground placeholder-muted focus:outline-none focus:border-primary transition-colors"
              />
            </div>

            {/* Status filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary transition-colors"
            >
              <option value="all">Todos os status</option>
              <option value="running">Rodando</option>
              <option value="completed">Concluidos</option>
              <option value="pending">Pendentes</option>
              <option value="failed">Falhos</option>
              <option value="paused">Pausados</option>
            </select>

            {/* Type filter */}
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary transition-colors"
            >
              <option value="all">Todos os tipos</option>
              <option value="instant">Instantaneo</option>
              <option value="scheduled">Agendado</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-14 w-full" />
              ))}
            </div>
          ) : paginated.length === 0 ? (
            <div className="text-center py-16 text-muted">
              <Filter className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm font-medium">Nenhum job encontrado</p>
              <p className="text-xs mt-1">Tente ajustar os filtros ou criar um novo job</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-border">
                  <tr>
                    <th className="text-left text-xs text-muted font-medium px-6 py-3">Nome</th>
                    <th className="text-left text-xs text-muted font-medium px-4 py-3">URL</th>
                    <th className="text-left text-xs text-muted font-medium px-4 py-3">Tipo</th>
                    <th className="text-left text-xs text-muted font-medium px-4 py-3">Status</th>
                    <th className="text-left text-xs text-muted font-medium px-4 py-3">Engine</th>
                    <th className="text-right text-xs text-muted font-medium px-4 py-3">Itens</th>
                    <th className="text-left text-xs text-muted font-medium px-4 py-3">Ultima Exec.</th>
                    <th className="text-left text-xs text-muted font-medium px-4 py-3">Proxima Exec.</th>
                    <th className="text-right text-xs text-muted font-medium px-6 py-3">Acoes</th>
                  </tr>
                </thead>
                <tbody>
                  {paginated.map((job) => (
                    <tr key={job.id} className="border-b border-border last:border-0 hover:bg-surface-2/50 transition-colors">
                      <td className="px-6 py-3">
                        <a href={`/results/${job.id}`} className="text-foreground hover:text-primary transition-colors font-medium text-sm">
                          {job.name}
                        </a>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-muted text-xs font-mono truncate max-w-[150px] block">{job.url}</span>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={job.type === 'scheduled' ? 'accent' : 'info'}>
                          {job.type === 'scheduled' ? 'Agendado' : 'Instantaneo'}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={job.status} />
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs text-muted font-mono">{job.engine}</span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-foreground font-mono text-xs">{job.items.toLocaleString('pt-BR')}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-muted text-xs">{job.lastRun}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-muted text-xs">{job.nextRun || '—'}</span>
                      </td>
                      <td className="px-6 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <a
                            href={`/results/${job.id}`}
                            className="p-1.5 rounded-lg hover:bg-surface-2 text-muted hover:text-foreground transition-colors"
                            title="Ver resultados"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </a>
                          {job.status === 'running' || job.status === 'pending' ? (
                            <button
                              onClick={() => handlePause(job.id)}
                              disabled={actionJobId === job.id}
                              className="p-1.5 rounded-lg hover:bg-warning/10 text-muted hover:text-warning transition-colors"
                              title="Pausar"
                            >
                              <Pause className="w-3.5 h-3.5" />
                            </button>
                          ) : job.status === 'paused' ? (
                            <button
                              onClick={() => handleResume(job.id)}
                              disabled={actionJobId === job.id}
                              className="p-1.5 rounded-lg hover:bg-secondary/10 text-muted hover:text-secondary transition-colors"
                              title="Retomar"
                            >
                              <Play className="w-3.5 h-3.5" />
                            </button>
                          ) : null}
                          <button
                            onClick={() => handleDelete(job.id)}
                            disabled={actionJobId === job.id}
                            className="p-1.5 rounded-lg hover:bg-destructive/10 text-muted hover:text-destructive disabled:opacity-40 transition-colors"
                            title="Excluir"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-6 py-4 border-t border-border">
              <span className="text-xs text-muted">
                {filtered.length} resultado(s) — pagina {page} de {totalPages}
              </span>
              <div className="flex gap-1">
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={`w-7 h-7 rounded-lg text-xs font-medium transition-colors ${
                      p === page
                        ? 'bg-primary text-white'
                        : 'text-muted hover:bg-surface-2 hover:text-foreground'
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
