'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Zap, Bot, Globe, Code, Layout, AlertCircle, CheckCircle,
  Play, RefreshCw, ChevronDown, ChevronUp,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { scraperApi } from '@/lib/api'

const scrapeSchema = z.object({
  url: z.string().url('URL inválida — inclua http:// ou https://'),
  extraction_type: z.enum(['css', 'xpath', 'ai']),
  selectors: z.string().optional(),
  engine: z.enum(['scrapy', 'playwright']),
})

type ScrapeFormData = z.infer<typeof scrapeSchema>

interface DetectedField {
  name: string
  selector: string
  sample: string
  type: string
}

interface ScrapeResult {
  [key: string]: string | number | boolean | null
}

export default function InstantScrapingPage() {
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [progress, setProgress] = useState(0)
  const [detectedFields, setDetectedFields] = useState<DetectedField[]>([])
  const [results, setResults] = useState<ScrapeResult[]>([])
  const [showResults, setShowResults] = useState(false)
  const [resultView, setResultView] = useState<'table' | 'json'>('table')

  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<ScrapeFormData>({
    resolver: zodResolver(scrapeSchema),
    defaultValues: {
      extraction_type: 'ai',
      engine: 'scrapy',
    },
  })

  const engine = watch('engine')
  const extractionType = watch('extraction_type')
  const url = watch('url')

  const handleAnalyzeWithAI = async () => {
    if (!url) {
      toast.error('Informe uma URL primeiro')
      return
    }
    setIsAnalyzing(true)
    try {
      const response = await scraperApi.analyzeWithAI(url)
      setDetectedFields(response.data.fields || [])
      toast.success(`${response.data.fields?.length || 0} campos detectados pela IA!`)
    } catch {
      // Mock response for development
      const mockFields: DetectedField[] = [
        { name: 'titulo', selector: 'h1.product-title', sample: 'Produto Exemplo XYZ', type: 'text' },
        { name: 'preco', selector: '.price-box .price', sample: 'R$ 199,90', type: 'price' },
        { name: 'rating', selector: '.rating-value', sample: '4.5', type: 'number' },
        { name: 'disponibilidade', selector: '.availability', sample: 'Em estoque', type: 'text' },
        { name: 'imagem', selector: 'img.product-image', sample: 'https://...jpg', type: 'image' },
      ]
      setDetectedFields(mockFields)
      toast.success('5 campos detectados (modo demo)')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const onSubmit = async (data: ScrapeFormData) => {
    setIsRunning(true)
    setProgress(0)
    setShowResults(false)

    // Simulate progress
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 90) { clearInterval(interval); return prev }
        return prev + Math.random() * 15
      })
    }, 300)

    try {
      const payload = {
        url: data.url,
        extraction_type: data.extraction_type,
        engine: data.engine,
        selectors: detectedFields.reduce((acc, f) => ({ ...acc, [f.name]: f.selector }), {}),
      }
      const response = await scraperApi.instantScrape(payload)
      setProgress(100)
      setResults(response.data.results || [])
      setShowResults(true)
      toast.success(`Scraping concluido! ${response.data.results?.length} registros coletados.`)
    } catch {
      // Mock results for development
      setProgress(100)
      const mockResults: ScrapeResult[] = Array.from({ length: 12 }, (_, i) => ({
        titulo: `Produto ${i + 1} - Exemplo`,
        preco: `R$ ${(Math.random() * 500 + 50).toFixed(2)}`,
        rating: (Math.random() * 2 + 3).toFixed(1),
        disponibilidade: Math.random() > 0.2 ? 'Em estoque' : 'Esgotado',
      }))
      setResults(mockResults)
      setShowResults(true)
      toast.success('12 registros coletados (modo demo)')
    } finally {
      clearInterval(interval)
      setIsRunning(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-foreground">Novo Scraping Instantaneo</h1>
        <p className="text-sm text-muted mt-0.5">Extraia dados de qualquer pagina em segundos com IA</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* URL Input */}
        <Card>
          <CardContent className="p-5 space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">URL para Scraping</label>
              <div className="relative">
                <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
                <input
                  {...register('url')}
                  placeholder="https://exemplo.com.br/produtos"
                  className="w-full bg-surface border border-border rounded-lg pl-10 pr-4 py-3 text-foreground placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors text-sm"
                />
              </div>
              {errors.url && <p className="text-destructive text-xs mt-1">{errors.url.message}</p>}
            </div>

            {/* Engine toggle */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">Engine de Scraping</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setValue('engine', 'scrapy')}
                  className={`flex items-center gap-2 p-3 rounded-lg border transition-all ${
                    engine === 'scrapy'
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border bg-surface-2 text-muted hover:border-border/80'
                  }`}
                >
                  <Code className="w-4 h-4" />
                  <div className="text-left">
                    <p className="text-xs font-semibold">Scrapy</p>
                    <p className="text-[10px] opacity-70">Paginas estaticas — rapido</p>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => setValue('engine', 'playwright')}
                  className={`flex items-center gap-2 p-3 rounded-lg border transition-all ${
                    engine === 'playwright'
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border bg-surface-2 text-muted hover:border-border/80'
                  }`}
                >
                  <Layout className="w-4 h-4" />
                  <div className="text-left">
                    <p className="text-xs font-semibold">Playwright</p>
                    <p className="text-[10px] opacity-70">JavaScript/SPA — completo</p>
                  </div>
                </button>
              </div>
            </div>

            {/* Extraction type */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">Tipo de Extracao</label>
              <div className="flex gap-2">
                {(['ai', 'css', 'xpath'] as const).map((type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setValue('extraction_type', type)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                      extractionType === type
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border bg-surface-2 text-muted hover:border-border/80'
                    }`}
                  >
                    {type === 'ai' ? '🤖 IA (Auto)' : type.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            {/* Custom selectors (if not AI) */}
            {extractionType !== 'ai' && (
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Seletores {extractionType.toUpperCase()} (JSON)
                </label>
                <textarea
                  {...register('selectors')}
                  rows={3}
                  placeholder={`{"titulo": "h1", "preco": ".price"}`}
                  className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-foreground placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors text-sm font-mono"
                />
              </div>
            )}
          </CardContent>
        </Card>

        {/* AI Detection */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <Bot className="w-4 h-4 text-primary" />
                Deteccao Automatica com IA
              </CardTitle>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleAnalyzeWithAI}
                loading={isAnalyzing}
                className="text-xs"
              >
                <Bot className="w-3 h-3" />
                {isAnalyzing ? 'Analisando...' : 'Detectar Campos'}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {detectedFields.length === 0 ? (
              <div className="text-center py-6 text-muted">
                <Bot className="w-8 h-8 mx-auto mb-2 opacity-30" />
                <p className="text-sm">Clique em "Detectar Campos" para a IA analisar a pagina</p>
              </div>
            ) : (
              <div className="space-y-2">
                {detectedFields.map((field, i) => (
                  <div key={i} className="flex items-center justify-between p-2.5 bg-surface-2 rounded-lg border border-border">
                    <div className="flex items-center gap-3">
                      <CheckCircle className="w-4 h-4 text-secondary flex-shrink-0" />
                      <div>
                        <span className="text-sm font-medium text-foreground">{field.name}</span>
                        <span className="text-xs text-muted ml-2 font-mono">{field.selector}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="text-[10px]">{field.type}</Badge>
                      <span className="text-xs text-muted max-w-[150px] truncate">{field.sample}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Progress + Submit */}
        <Card>
          <CardContent className="p-5 space-y-4">
            {isRunning && (
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-muted">
                  <span>Executando scraping...</span>
                  <span>{Math.round(progress)}%</span>
                </div>
                <div className="w-full bg-surface-2 rounded-full h-2">
                  <div
                    className="bg-primary h-2 rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            )}

            <div className="flex gap-3">
              <Button
                type="submit"
                loading={isRunning}
                className="flex-1"
                size="lg"
              >
                <Play className="w-4 h-4" />
                {isRunning ? 'Executando...' : 'Executar Scraping'}
              </Button>
              <Button type="button" variant="outline" size="lg" onClick={() => {
                setResults([])
                setDetectedFields([])
                setShowResults(false)
                setProgress(0)
              }}>
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </form>

      {/* Results */}
      {showResults && results.length > 0 && (
        <Card className="animate-slide-up">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CardTitle className="text-sm">Resultados</CardTitle>
                <Badge variant="success">{results.length} registros</Badge>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex rounded-lg border border-border overflow-hidden text-xs">
                  <button
                    onClick={() => setResultView('table')}
                    className={`px-3 py-1.5 transition-colors ${resultView === 'table' ? 'bg-primary text-white' : 'text-muted hover:bg-surface-2'}`}
                  >
                    Tabela
                  </button>
                  <button
                    onClick={() => setResultView('json')}
                    className={`px-3 py-1.5 transition-colors ${resultView === 'json' ? 'bg-primary text-white' : 'text-muted hover:bg-surface-2'}`}
                  >
                    JSON
                  </button>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {resultView === 'table' ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="border-b border-border">
                    <tr>
                      {Object.keys(results[0] || {}).map((key) => (
                        <th key={key} className="text-left text-xs text-muted font-medium px-4 py-3">{key}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {results.slice(0, 10).map((row, i) => (
                      <tr key={i} className="border-b border-border last:border-0 hover:bg-surface-2/50 transition-colors">
                        {Object.values(row).map((val, j) => (
                          <td key={j} className="px-4 py-2.5 text-foreground text-xs">{String(val)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-4">
                <pre className="text-xs text-foreground font-mono overflow-x-auto bg-surface-2 rounded-lg p-4 max-h-80">
                  {JSON.stringify(results.slice(0, 5), null, 2)}
                </pre>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
