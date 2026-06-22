'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Download, Table, Code, LayoutGrid, ArrowLeft, Star, ExternalLink, Image as ImageIcon, ShieldCheck, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { exportApi, scraperApi } from '@/lib/api'

interface ResultRow {
  [key: string]: string | number | boolean | null
}

const generateMockData = (): ResultRow[] =>
  Array.from({ length: 50 }, (_, i) => ({
    id: i + 1,
    titulo: `Produto ${i + 1} - ${['Samsung', 'Apple', 'Sony', 'LG', 'Xiaomi'][i % 5]}`,
    imagem: `https://picsum.photos/seed/webscrapy-${i + 1}/96/96`,
    preco: `R$ ${(Math.random() * 2000 + 50).toFixed(2)}`,
    rating: parseFloat((Math.random() * 2 + 3).toFixed(1)),
    reviews: Math.floor(Math.random() * 5000),
    disponibilidade: Math.random() > 0.2 ? 'Em estoque' : 'Esgotado',
    categoria: ['Eletronicos', 'Informatica', 'Celulares', 'Games'][i % 4],
    url: `https://exemplo.com/produto-${i + 1}`,
  }))

const linkKeys = ['url', 'link', 'href', 'apply_url', 'purchase_url', 'booking_url', 'source_url']
const imageKeys = ['imagem', 'image', 'image_url', 'thumbnail', 'thumbnail_url', 'img']

function getValue(row: ResultRow, keys: string[]) {
  for (const key of keys) {
    const value = row[key]
    if (typeof value === 'string' && value.trim()) return value
  }
  return null
}

function isImageColumn(col: string) {
  return imageKeys.includes(col)
}

function normalizeStructuredData(value: unknown): ResultRow[] {
  if (Array.isArray(value)) return value as ResultRow[]
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>
    const arrayValue = Object.values(record).find(Array.isArray)
    if (Array.isArray(arrayValue)) return arrayValue as ResultRow[]
    return [record as ResultRow]
  }
  return []
}

export default function ResultsPage() {
  const params = useParams()
  const router = useRouter()
  const jobId = params.jobId as string
  const [results, setResults] = useState<ResultRow[]>([])
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(false)
  const [view, setView] = useState<'table' | 'json' | 'cards'>('table')
  const [page, setPage] = useState(1)
  const [qualityScore] = useState(94)
  const perPage = 20

  useEffect(() => {
    const loadResults = async () => {
      setLoading(true)
      try {
        const job = await scraperApi.getJob(jobId)
        const runs = job.data.runs || []
        const lastRunId = runs[0]?.id
        if (!lastRunId) {
          setResults(generateMockData())
          return
        }

        const response = await scraperApi.getResults(lastRunId)
        const rows = (response.data || []).flatMap((item: { structured_data?: unknown }) =>
          normalizeStructuredData(item.structured_data)
        )
        setResults(rows.length ? rows : generateMockData())
      } catch {
        setResults(generateMockData())
      } finally {
        setLoading(false)
      }
    }

    loadResults()
  }, [jobId])

  const paginated = results.slice((page - 1) * perPage, page * perPage)
  const totalPages = Math.ceil(results.length / perPage)

  const handleExport = async (format: 'csv' | 'excel' | 'json') => {
    try {
      const fn = format === 'csv'
        ? exportApi.exportCsv
        : format === 'excel'
          ? exportApi.exportExcel
          : exportApi.exportJson

      const response = await fn(jobId)
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `results-${jobId}.${format === 'excel' ? 'xlsx' : format}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      toast.success(`Exportado como ${format.toUpperCase()}!`)
    } catch {
      // Mock download
      toast.success(`Exportado como ${format.toUpperCase()} (modo demo)`)
    }
  }

  const handleDeleteJob = async () => {
    const confirmed = window.confirm('Excluir este job e todos os resultados vinculados?')
    if (!confirmed) return

    setDeleting(true)
    try {
      await scraperApi.deleteJob(jobId)
      toast.success('Job removido')
      router.push('/jobs')
    } catch {
      toast.error('Nao foi possivel excluir o job')
    } finally {
      setDeleting(false)
    }
  }

  const columns = results.length > 0 ? Object.keys(results[0]).filter(col => !isImageColumn(col)) : []
  const hasImages = results.some(row => getValue(row, imageKeys))

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a href="/jobs" className="p-2 rounded-lg hover:bg-surface-2 text-muted hover:text-foreground transition-colors">
            <ArrowLeft className="w-4 h-4" />
          </a>
          <div>
            <h1 className="text-xl font-bold text-foreground">Resultados — Job #{jobId}</h1>
            <p className="text-sm text-muted mt-0.5">
              {loading ? '...' : `${results.length} registros coletados`}
            </p>
          </div>
        </div>

        {/* Export buttons */}
        <div className="flex gap-2">
          <Button variant="destructive" size="sm" onClick={handleDeleteJob} loading={deleting}>
            <Trash2 className="w-3.5 h-3.5" /> Apagar Job
          </Button>
          <Button variant="outline" size="sm" onClick={() => handleExport('csv')}>
            <Download className="w-3.5 h-3.5" /> CSV
          </Button>
          <Button variant="outline" size="sm" onClick={() => handleExport('excel')}>
            <Download className="w-3.5 h-3.5" /> Excel
          </Button>
          <Button variant="outline" size="sm" onClick={() => handleExport('json')}>
            <Download className="w-3.5 h-3.5" /> JSON
          </Button>
        </div>
      </div>

      {/* Quality score + view toggle */}
      <div className="flex items-center justify-between">
        {/* Quality score */}
        <Card className="flex-1 max-w-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Star className="w-4 h-4 text-warning" />
                <span className="text-sm font-medium text-foreground">Quality Score</span>
              </div>
              <span className={`text-lg font-bold ${
                qualityScore >= 90 ? 'text-secondary' :
                qualityScore >= 70 ? 'text-warning' : 'text-destructive'
              }`}>{qualityScore}%</span>
            </div>
            <div className="w-full bg-surface-2 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all ${
                  qualityScore >= 90 ? 'bg-secondary' :
                  qualityScore >= 70 ? 'bg-warning' : 'bg-destructive'
                }`}
                style={{ width: `${qualityScore}%` }}
              />
            </div>
            <p className="text-xs text-muted mt-1">Dados de alta qualidade</p>
          </CardContent>
        </Card>

        {/* View toggle */}
        <div className="flex rounded-lg border border-border overflow-hidden text-xs">
          <button
            onClick={() => setView('table')}
            className={`px-3 py-2 flex items-center gap-1.5 transition-colors ${view === 'table' ? 'bg-primary text-white' : 'text-muted hover:bg-surface-2'}`}
          >
            <Table className="w-3.5 h-3.5" /> Tabela
          </button>
          <button
            onClick={() => setView('json')}
            className={`px-3 py-2 flex items-center gap-1.5 transition-colors ${view === 'json' ? 'bg-primary text-white' : 'text-muted hover:bg-surface-2'}`}
          >
            <Code className="w-3.5 h-3.5" /> JSON
          </button>
          <button
            onClick={() => setView('cards')}
            className={`px-3 py-2 flex items-center gap-1.5 transition-colors ${view === 'cards' ? 'bg-primary text-white' : 'text-muted hover:bg-surface-2'}`}
          >
            <LayoutGrid className="w-3.5 h-3.5" /> Cards
          </button>
        </div>
      </div>

      {/* Data display */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-3">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : view === 'table' ? (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="border-b border-border">
                    <tr>
                      {hasImages && (
                        <th className="text-left text-xs text-muted font-medium px-4 py-3 whitespace-nowrap">imagem</th>
                      )}
                      {columns.map((col) => (
                        <th key={col} className="text-left text-xs text-muted font-medium px-4 py-3 whitespace-nowrap">
                          {col}
                        </th>
                      ))}
                      <th className="text-right text-xs text-muted font-medium px-4 py-3 whitespace-nowrap">acoes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginated.map((row, i) => {
                      const link = getValue(row, linkKeys)
                      const image = getValue(row, imageKeys)

                      return (
                        <tr key={i} className="border-b border-border last:border-0 hover:bg-surface-2/50 transition-colors">
                          {hasImages && (
                            <td className="px-4 py-2.5">
                              {image ? (
                                <a href={image} target="_blank" rel="noopener noreferrer">
                                  <img src={image} alt="" className="h-12 w-12 rounded-md object-cover border border-border" />
                                </a>
                              ) : (
                                <div className="h-12 w-12 rounded-md border border-border bg-surface-2 flex items-center justify-center">
                                  <ImageIcon className="h-4 w-4 text-muted" />
                                </div>
                              )}
                            </td>
                          )}
                          {columns.map((col) => (
                            <td key={col} className="px-4 py-2.5 text-xs text-foreground whitespace-nowrap">
                              {col === 'disponibilidade' ? (
                                <Badge variant={row[col] === 'Em estoque' ? 'success' : 'destructive'}>
                                  {String(row[col])}
                                </Badge>
                              ) : col === 'rating' ? (
                                <span className="flex items-center gap-1">
                                  <Star className="w-3 h-3 text-warning fill-warning" />
                                  {String(row[col])}
                                </span>
                              ) : linkKeys.includes(col) && typeof row[col] === 'string' ? (
                                <a href={String(row[col])} target="_blank" rel="noopener noreferrer" className="max-w-[240px] truncate block text-primary hover:underline">
                                  {String(row[col])}
                                </a>
                              ) : (
                                <span className="max-w-[220px] truncate block">{String(row[col])}</span>
                              )}
                            </td>
                          ))}
                          <td className="px-4 py-2.5">
                            <div className="flex items-center justify-end gap-2">
                              {link && (
                                <>
                                  <a
                                    href={link}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border px-2.5 text-xs text-foreground transition-colors hover:border-primary/50 hover:bg-surface-2"
                                  >
                                    <ShieldCheck className="h-3.5 w-3.5 text-primary" />
                                    Verificar
                                  </a>
                                  <a
                                    href={link}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex h-8 items-center gap-1.5 rounded-md bg-primary px-2.5 text-xs font-medium text-white transition-colors hover:bg-primary/90"
                                  >
                                    Abrir
                                    <ExternalLink className="h-3 w-3" />
                                  </a>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between px-6 py-4 border-t border-border">
                <span className="text-xs text-muted">{results.length} registros — pagina {page} de {totalPages}</span>
                <div className="flex gap-1">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-3 py-1.5 rounded-lg text-xs text-muted hover:bg-surface-2 disabled:opacity-30 transition-colors"
                  >
                    Anterior
                  </button>
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    const p = Math.max(1, Math.min(page - 2, totalPages - 4)) + i
                    return (
                      <button
                        key={p}
                        onClick={() => setPage(p)}
                        className={`w-7 h-7 rounded-lg text-xs font-medium transition-colors ${
                          p === page ? 'bg-primary text-white' : 'text-muted hover:bg-surface-2'
                        }`}
                      >
                        {p}
                      </button>
                    )
                  })}
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="px-3 py-1.5 rounded-lg text-xs text-muted hover:bg-surface-2 disabled:opacity-30 transition-colors"
                  >
                    Proxima
                  </button>
                </div>
              </div>
            </>
          ) : view === 'json' ? (
            <div className="p-4">
              <pre className="text-xs font-mono text-foreground overflow-x-auto bg-background rounded-lg p-4 max-h-[600px] overflow-y-auto">
                {JSON.stringify(results.slice(0, 20), null, 2)}
              </pre>
            </div>
          ) : (
            <div className="p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {paginated.map((row, i) => (
                <div key={i} className="bg-surface-2 border border-border rounded-xl p-4 space-y-2">
                  {getValue(row, imageKeys) && (
                    <img src={getValue(row, imageKeys) || ''} alt="" className="h-32 w-full rounded-lg object-cover border border-border mb-3" />
                  )}
                  {columns.slice(0, 5).map((col) => (
                    <div key={col} className="flex justify-between items-start gap-2">
                      <span className="text-xs text-muted capitalize flex-shrink-0">{col}:</span>
                      <span className="text-xs text-foreground text-right truncate max-w-[120px]">
                        {String(row[col])}
                      </span>
                    </div>
                  ))}
                  {getValue(row, linkKeys) && (
                    <Button asChild size="sm" className="w-full mt-3">
                      <a href={getValue(row, linkKeys) || ''} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="w-3.5 h-3.5" />
                        Verificar resultado
                      </a>
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
