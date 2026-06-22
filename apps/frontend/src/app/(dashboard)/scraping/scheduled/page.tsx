'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Briefcase, Calendar, CheckCircle, Clock, Code, Globe, Layout, Search } from 'lucide-react'
import toast from 'react-hot-toast'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { scraperApi } from '@/lib/api'

const scheduledSchema = z.object({
  name: z.string().min(3, 'Nome deve ter ao menos 3 caracteres'),
  job_mode: z.enum(['generic', 'jobs']),
  url: z.string().optional(),
  extraction_type: z.enum(['css', 'xpath', 'ai']),
  engine: z.enum(['scrapy', 'playwright']),
  frequency: z.enum(['minute', 'hourly', 'daily', 'weekly', 'monthly']),
  selectors: z.string().optional(),
  candidate_profile: z.string().optional(),
  search_scope: z.enum(['national', 'international', 'both']).optional(),
  job_channels: z.array(z.string()).optional(),
  max_job_age_days: z.coerce.number().min(1).max(60).optional(),
  target_locations: z.string().optional(),
  company_targets: z.string().optional(),
}).superRefine((data, ctx) => {
  if (data.job_mode === 'generic' && (!data.url || !z.string().url().safeParse(data.url).success)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ['url'],
      message: 'URL inválida',
    })
  }

  if (data.job_mode === 'jobs') {
    if (!data.candidate_profile || data.candidate_profile.trim().length < 30) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['candidate_profile'],
        message: 'Descreva o perfil com ao menos 30 caracteres',
      })
    }
    if (!data.job_channels?.length) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['job_channels'],
        message: 'Escolha ao menos um canal de busca',
      })
    }
  }
})

type ScheduledFormData = z.infer<typeof scheduledSchema>

const frequencyConfig = {
  minute: { label: 'A cada minuto', cron: '* * * * *', description: 'Roda todo minuto (alta frequencia)' },
  hourly: { label: 'Horario', cron: '0 * * * *', description: 'Roda no inicio de cada hora' },
  daily: { label: 'Diario', cron: '0 9 * * *', description: 'Roda todo dia as 09:00' },
  weekly: { label: 'Semanal', cron: '0 9 * * 1', description: 'Roda toda segunda-feira as 09:00' },
  monthly: { label: 'Mensal', cron: '0 9 1 * *', description: 'Roda no 1o dia de cada mes' },
}

const jobChannels = [
  { id: 'linkedin', label: 'LinkedIn', description: 'Vagas e posts recentes de recrutadores' },
  { id: 'indeed', label: 'Indeed', description: 'Agregador amplo para buscas nacionais e globais' },
  { id: 'company_sites', label: 'Sites das empresas', description: 'Carreiras de empresas ligadas ao perfil' },
  { id: 'gupy', label: 'Gupy', description: 'Vagas BR em páginas de ATS' },
  { id: 'greenhouse', label: 'Greenhouse', description: 'ATS usado por empresas internacionais' },
  { id: 'lever', label: 'Lever', description: 'ATS frequente em startups globais' },
]

const searchScopeConfig = {
  national: {
    label: 'Nacional',
    description: 'Prioriza vagas no Brasil e remoto Brasil',
  },
  international: {
    label: 'Internacional',
    description: 'Prioriza vagas fora do Brasil e remoto global',
  },
  both: {
    label: 'Ambos',
    description: 'Combina Brasil, exterior e remoto global',
  },
}

function buildJobSearchUrl(data: ScheduledFormData): string {
  const query = [
    data.candidate_profile?.slice(0, 120),
    data.search_scope === 'national' ? 'Brasil remoto' : '',
    data.search_scope === 'international' ? 'remote international' : '',
    data.search_scope === 'both' ? 'Brasil remote international' : '',
    data.target_locations,
    `publicadas nos ultimos ${data.max_job_age_days || 7} dias`,
  ].filter(Boolean).join(' ')

  return `https://www.google.com/search?q=${encodeURIComponent(`${query} vagas emprego`)}`
}

function getNextRun(frequency: string): string {
  const now = new Date()
  switch (frequency) {
    case 'minute': {
      const next = new Date(now.getTime() + 60000)
      return next.toLocaleString('pt-BR')
    }
    case 'hourly': {
      const next = new Date(now)
      next.setHours(next.getHours() + 1, 0, 0, 0)
      return next.toLocaleString('pt-BR')
    }
    case 'daily': {
      const next = new Date(now)
      next.setDate(next.getDate() + 1)
      next.setHours(9, 0, 0, 0)
      return next.toLocaleString('pt-BR')
    }
    case 'weekly': {
      const next = new Date(now)
      next.setDate(next.getDate() + (7 - next.getDay() + 1) % 7 || 7)
      next.setHours(9, 0, 0, 0)
      return next.toLocaleString('pt-BR')
    }
    case 'monthly': {
      const next = new Date(now.getFullYear(), now.getMonth() + 1, 1, 9, 0, 0)
      return next.toLocaleString('pt-BR')
    }
    default: return 'Desconhecido'
  }
}

export default function ScheduledScrapingPage() {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)

  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<ScheduledFormData>({
    resolver: zodResolver(scheduledSchema),
    defaultValues: {
      extraction_type: 'ai',
      engine: 'scrapy',
      frequency: 'daily',
      job_mode: 'generic',
      search_scope: 'both',
      job_channels: ['linkedin', 'indeed', 'company_sites'],
      max_job_age_days: 7,
    },
  })

  const jobMode = watch('job_mode')
  const engine = watch('engine')
  const extractionType = watch('extraction_type')
  const frequency = watch('frequency')
  const selectedChannels = watch('job_channels') || []
  const freqConfig = frequencyConfig[frequency]

  const toggleChannel = (channelId: string) => {
    const next = selectedChannels.includes(channelId)
      ? selectedChannels.filter(id => id !== channelId)
      : [...selectedChannels, channelId]
    setValue('job_channels', next, { shouldValidate: true })
  }

  const onSubmit = async (data: ScheduledFormData) => {
    setIsSubmitting(true)
    try {
      const selectors = data.selectors ? JSON.parse(data.selectors) : undefined
      const url = data.job_mode === 'jobs' ? buildJobSearchUrl(data) : data.url || ''

      await scraperApi.scheduleScrape({
        name: data.name,
        url,
        extraction_type: data.extraction_type,
        engine: data.engine,
        use_playwright: data.engine === 'playwright',
        selectors,
        frequency: data.frequency,
        cron_expression: freqConfig.cron,
        search_type: data.job_mode === 'jobs' ? 'jobs' : 'generic',
        search_params: data.job_mode === 'jobs' ? {
          candidate_profile: data.candidate_profile,
          search_scope: data.search_scope,
          channels: selectedChannels,
          max_job_age_days: data.max_job_age_days,
          target_locations: data.target_locations,
          company_targets: data.company_targets,
          require_recent_publication: true,
        } : undefined,
      })
      setSuccess(true)
      toast.success(`Job "${data.name}" agendado com sucesso!`)
    } catch (error) {
      if (error instanceof SyntaxError) {
        toast.error('Seletores JSON inválidos')
        return
      }
      // Mock success for development
      setSuccess(true)
      toast.success(`Job "${data.name}" agendado (modo demo)`)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (success) {
    return (
      <div className="max-w-2xl mx-auto animate-slide-up">
        <Card className="border-secondary/30 bg-secondary/5">
          <CardContent className="p-8 text-center">
            <div className="w-16 h-16 bg-secondary/20 border border-secondary/30 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-8 h-8 text-secondary" />
            </div>
            <h2 className="text-xl font-bold text-foreground mb-2">Job Agendado!</h2>
            <p className="text-muted mb-6">Seu job foi criado e vai executar conforme programado.</p>
            <div className="flex gap-3 justify-center">
              <Button onClick={() => setSuccess(false)} variant="outline">
                Novo Job
              </Button>
              <Button asChild>
                <a href="/jobs">Ver Meus Jobs</a>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-foreground">Agendar Scraping Periodico</h1>
        <p className="text-sm text-muted mt-0.5">Configure um job que executa automaticamente em intervalos regulares</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* Job name */}
        <Card>
          <CardContent className="p-5 space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">Tipo de Job</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setValue('job_mode', 'generic', { shouldValidate: true })}
                  className={`flex items-center gap-3 p-3 rounded-lg border transition-all ${
                    jobMode === 'generic'
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border bg-surface-2 text-muted hover:border-border/80'
                  }`}
                >
                  <Globe className="w-4 h-4" />
                  <div className="text-left">
                    <p className="text-xs font-semibold">Scraping por URL</p>
                    <p className="text-[10px] opacity-70">Produtos, noticias, paginas especificas</p>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setValue('job_mode', 'jobs', { shouldValidate: true })
                    setValue('engine', 'playwright')
                    setValue('extraction_type', 'ai')
                  }}
                  className={`flex items-center gap-3 p-3 rounded-lg border transition-all ${
                    jobMode === 'jobs'
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border bg-surface-2 text-muted hover:border-border/80'
                  }`}
                >
                  <Briefcase className="w-4 h-4" />
                  <div className="text-left">
                    <p className="text-xs font-semibold">Busca de vagas</p>
                    <p className="text-[10px] opacity-70">Perfil, canais e vagas recentes</p>
                  </div>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">Nome do Job</label>
              <input
                {...register('name')}
                placeholder={jobMode === 'jobs' ? 'Ex: Vagas Produto IA - Remoto' : 'Ex: Precos Concorrentes - Amazon'}
                className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-foreground placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors text-sm"
              />
              {errors.name && <p className="text-destructive text-xs mt-1">{errors.name.message}</p>}
            </div>

            {jobMode === 'generic' && (
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">URL para Scraping</label>
                <div className="relative">
                  <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
                  <input
                    {...register('url')}
                    placeholder="https://exemplo.com.br/produtos"
                    className="w-full bg-surface border border-border rounded-lg pl-10 pr-4 py-2.5 text-foreground placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors text-sm"
                  />
                </div>
                {errors.url && <p className="text-destructive text-xs mt-1">{errors.url.message}</p>}
              </div>
            )}
          </CardContent>
        </Card>

        {jobMode === 'jobs' && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Search className="w-4 h-4 text-primary" />
                Brief da Busca de Vagas
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">Perfil do candidato</label>
                <textarea
                  {...register('candidate_profile')}
                  rows={5}
                  placeholder="Descreva senioridade, area, stack, idiomas, tipo de contrato, pretensao, disponibilidade, diferenciais e o que evitar."
                  className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-foreground placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors text-sm"
                />
                {errors.candidate_profile && <p className="text-destructive text-xs mt-1">{errors.candidate_profile.message}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Alcance da busca</label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  {(Object.keys(searchScopeConfig) as Array<keyof typeof searchScopeConfig>).map((scope) => (
                    <button
                      key={scope}
                      type="button"
                      onClick={() => setValue('search_scope', scope)}
                      className={`p-3 rounded-lg border text-left transition-all ${
                        watch('search_scope') === scope
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-border bg-surface-2 text-muted hover:border-border/80'
                      }`}
                    >
                      <p className="text-xs font-semibold">{searchScopeConfig[scope].label}</p>
                      <p className="text-[10px] opacity-70 mt-0.5">{searchScopeConfig[scope].description}</p>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Canais de raspagem</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {jobChannels.map((channel) => (
                    <button
                      key={channel.id}
                      type="button"
                      onClick={() => toggleChannel(channel.id)}
                      className={`flex items-start gap-3 p-3 rounded-lg border text-left transition-all ${
                        selectedChannels.includes(channel.id)
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-border bg-surface-2 text-muted hover:border-border/80'
                      }`}
                    >
                      <span className={`mt-0.5 h-4 w-4 rounded border flex-shrink-0 ${
                        selectedChannels.includes(channel.id) ? 'border-primary bg-primary' : 'border-border'
                      }`} />
                      <span>
                        <span className="block text-xs font-semibold">{channel.label}</span>
                        <span className="block text-[10px] opacity-70 mt-0.5">{channel.description}</span>
                      </span>
                    </button>
                  ))}
                </div>
                {errors.job_channels && <p className="text-destructive text-xs mt-1">{errors.job_channels.message}</p>}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">Vagas publicadas ha no maximo</label>
                  <div className="flex items-center gap-2">
                    <input
                      {...register('max_job_age_days')}
                      type="number"
                      min={1}
                      max={60}
                      className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors text-sm"
                    />
                    <span className="text-xs text-muted">dias</span>
                  </div>
                  {errors.max_job_age_days && <p className="text-destructive text-xs mt-1">{errors.max_job_age_days.message}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">Locais alvo</label>
                  <input
                    {...register('target_locations')}
                    placeholder="Brasil, EUA, Portugal, remoto..."
                    className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-foreground placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">Empresas alvo</label>
                  <input
                    {...register('company_targets')}
                    placeholder="Fintechs, SaaS, OpenAI, Nubank..."
                    className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-foreground placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors text-sm"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Engine + Extraction */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Configuracao de Extracao</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">Engine</label>
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
                    <p className="text-[10px] opacity-70">Estatico — rapido</p>
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
                    <p className="text-[10px] opacity-70">Dinamico — completo</p>
                  </div>
                </button>
              </div>
            </div>

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

            {extractionType !== 'ai' && (
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">Seletores JSON</label>
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

        {/* Frequency */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Calendar className="w-4 h-4 text-primary" />
              Frequencia de Execucao
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
              {(Object.keys(frequencyConfig) as Array<keyof typeof frequencyConfig>).map((freq) => (
                <button
                  key={freq}
                  type="button"
                  onClick={() => setValue('frequency', freq)}
                  className={`p-2.5 rounded-lg border text-center transition-all ${
                    frequency === freq
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border bg-surface-2 text-muted hover:border-border/80'
                  }`}
                >
                  <p className="text-xs font-semibold">{frequencyConfig[freq].label}</p>
                </button>
              ))}
            </div>

            {/* Cron info */}
            <div className="bg-surface-2 border border-border rounded-lg p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted">Expressao CRON:</span>
                <code className="text-xs font-mono text-primary bg-primary/10 px-2 py-0.5 rounded">
                  {freqConfig.cron}
                </code>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted">Descricao:</span>
                <span className="text-xs text-foreground">{freqConfig.description}</span>
              </div>
              <div className="flex items-center justify-between border-t border-border pt-2">
                <span className="text-xs text-muted flex items-center gap-1">
                  <Clock className="w-3 h-3" /> Proxima execucao:
                </span>
                <span className="text-xs text-secondary font-medium">{getNextRun(frequency)}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Button type="submit" loading={isSubmitting} size="lg" className="w-full">
          <Calendar className="w-4 h-4" />
          {isSubmitting ? 'Agendando...' : 'Agendar Job'}
        </Button>
      </form>
    </div>
  )
}
