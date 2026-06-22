'use client'

import { useState } from 'react'
import { ArrowLeft, CalendarPlus, ExternalLink, Search, ShieldCheck, ShoppingCart } from 'lucide-react'
import toast from 'react-hot-toast'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { scraperApi, searchApi } from '@/lib/api'

type SearchType = 'flights' | 'news' | 'leads' | 'jobs' | null

interface SearchResult {
  [key: string]: string | number | boolean | null
}

interface FlightMeta {
  total: number
  cheapest_price: number | null
  cheapest_destination: string | null
  cheapest_date: string | null
  has_api_key: boolean
  message: string
}

const linkColumns = new Set([
  'url',
  'link',
  'verification_url',
  'verify_url',
  'verificar',
  'purchase_url',
  'booking_url',
  'buy_url',
  'comprar',
  'link_passagem',
  'link_compra',
])

const flightCountries = [
  {
    id: 'brasil',
    label: 'Brasil',
    slug: 'brazil',
    cities: [
      { label: 'Sao Paulo', slug: 'sao-paulo' },
      { label: 'Porto Alegre', slug: 'porto-alegre' },
      { label: 'Rio de Janeiro', slug: 'rio-de-janeiro' },
      { label: 'Brasilia', slug: 'brasilia' },
      { label: 'Salvador', slug: 'salvador' },
      { label: 'Recife', slug: 'recife' },
    ],
  },
  {
    id: 'eua',
    label: 'EUA',
    slug: 'united-states',
    cities: [
      { label: 'Miami', slug: 'miami' },
      { label: 'Nova York', slug: 'new-york' },
      { label: 'Orlando', slug: 'orlando' },
      { label: 'Los Angeles', slug: 'los-angeles' },
      { label: 'Boston', slug: 'boston' },
      { label: 'Chicago', slug: 'chicago' },
    ],
  },
  {
    id: 'portugal',
    label: 'Portugal',
    slug: 'portugal',
    cities: [
      { label: 'Lisboa', slug: 'lisbon' },
      { label: 'Porto', slug: 'porto' },
      { label: 'Faro', slug: 'faro' },
    ],
  },
  {
    id: 'argentina',
    label: 'Argentina',
    slug: 'argentina',
    cities: [
      { label: 'Buenos Aires', slug: 'buenos-aires' },
      { label: 'Cordoba', slug: 'cordoba' },
      { label: 'Mendoza', slug: 'mendoza' },
    ],
  },
  {
    id: 'chile',
    label: 'Chile',
    slug: 'chile',
    cities: [
      { label: 'Santiago', slug: 'santiago' },
      { label: 'Calama', slug: 'calama' },
    ],
  },
  {
    id: 'uruguai',
    label: 'Uruguai',
    slug: 'uruguay',
    cities: [
      { label: 'Montevideo', slug: 'montevideo' },
      { label: 'Punta del Este', slug: 'punta-del-este' },
    ],
  },
]

type FlightFormState = {
  originCountry: string
  originCity: string
  destinationCountry: string
  destinationCity: string
  departure_date: string
  return_date: string
  passengers: number
  scheduleFrequency: 'daily' | 'weekly'
}

function getFlightCountry(countryId: string) {
  return flightCountries.find(country => country.id === countryId)
}

function getFlightPlaceSlug(countryId: string, citySlug: string) {
  const country = getFlightCountry(countryId)
  return citySlug || country?.slug || ''
}

function getFlightPlaceLabel(countryId: string, citySlug: string) {
  const country = getFlightCountry(countryId)
  const city = country?.cities.find(item => item.slug === citySlug)
  if (city && country) return `${city.label}, ${country.label}`
  return country?.label || ''
}

function getCityLabel(countryId: string, citySlug: string): string {
  const country = getFlightCountry(countryId)
  return country?.cities.find(c => c.slug === citySlug)?.label || ''
}

function buildFlightSearchUrl(form: {
  originCountry: string
  originCity: string
  destinationCountry: string
  destinationCity: string
  departure_date: string
  return_date: string
  passengers: number
}) {
  const origin = getFlightPlaceSlug(form.originCountry, form.originCity)
  const destination = getFlightPlaceSlug(form.destinationCountry, form.destinationCity)
  const originLabel = getFlightPlaceLabel(form.originCountry, form.originCity)
  const destinationLabel = getFlightPlaceLabel(form.destinationCountry, form.destinationCity)
  const dateParts = [
    form.departure_date ? `ida ${form.departure_date}` : '',
    form.return_date ? `volta ${form.return_date}` : '',
    form.passengers ? `${form.passengers} passageiro${form.passengers > 1 ? 's' : ''}` : '',
  ].filter(Boolean)

  if (!origin || !destination) {
    const query = ['voos', originLabel, destinationLabel, ...dateParts]
      .filter(Boolean)
      .join(' ')
    return `https://www.google.com/travel/flights/search?q=${encodeURIComponent(query)}`
  }

  const query = new URLSearchParams({
    q: ['voos', originLabel, destinationLabel, ...dateParts].filter(Boolean).join(' '),
  })
  return `https://www.google.com/travel/flights/flights-from-${origin}-to-${destination}.html?${query.toString()}`
}

function getRowUrl(row: SearchResult, keys: string[]) {
  for (const key of keys) {
    const value = row[key]
    if (typeof value === 'string' && value.trim()) return value
  }
  return null
}

function parsePrice(value: unknown): number {
  if (typeof value === 'number') return value
  if (typeof value !== 'string') return Number.POSITIVE_INFINITY

  const normalized = value
    .replace(/[^\d,.-]/g, '')
    .replace(/\.(?=\d{3}(?:\D|$))/g, '')
    .replace(',', '.')

  const price = Number.parseFloat(normalized)
  return Number.isFinite(price) ? price : Number.POSITIVE_INFINITY
}

function sortFlightsByPrice(results: SearchResult[]) {
  return [...results].sort((a, b) => {
    const aPrice = parsePrice(a.preco ?? a.price ?? a.valor ?? a.fare)
    const bPrice = parsePrice(b.preco ?? b.price ?? b.valor ?? b.fare)
    return aPrice - bPrice
  })
}

const searchTypes = [
  {
    id: 'flights' as const,
    emoji: '✈️',
    title: 'Passagens Aereas',
    description: 'Busque e compare precos de voos em tempo real de multiplas companhias',
    colorClass: 'border-primary/30 bg-primary/5 hover:border-primary/50',
    iconClass: 'text-primary bg-primary/10 border-primary/20',
  },
  {
    id: 'news' as const,
    emoji: '📰',
    title: 'Noticias',
    description: 'Monitore noticias de qualquer tema em fontes selecionadas',
    colorClass: 'border-secondary/30 bg-secondary/5 hover:border-secondary/50',
    iconClass: 'text-secondary bg-secondary/10 border-secondary/20',
  },
  {
    id: 'leads' as const,
    emoji: '🏢',
    title: 'Leads Internacionais',
    description: 'Encontre empresas e contatos em qualquer pais e setor',
    colorClass: 'border-accent/30 bg-accent/5 hover:border-accent/50',
    iconClass: 'text-accent bg-accent/10 border-accent/20',
  },
  {
    id: 'jobs' as const,
    emoji: '💼',
    title: 'Vagas de Emprego',
    description: 'Agregue vagas de multiplas plataformas em uma busca',
    colorClass: 'border-warning/30 bg-warning/5 hover:border-warning/50',
    iconClass: 'text-warning bg-warning/10 border-warning/20',
  },
]

function FlightForm({
  onFlightResults,
}: {
  onFlightResults: (meta: FlightMeta, results: SearchResult[]) => void
}) {
  const [loading, setLoading] = useState(false)
  const [scheduling, setScheduling] = useState(false)
  const [form, setForm] = useState<FlightFormState>({
    originCountry: 'brasil',
    originCity: 'sao-paulo',
    destinationCountry: 'eua',
    destinationCity: '',
    departure_date: '',
    return_date: '',
    passengers: 1,
    scheduleFrequency: 'daily',
  })
  const originCountry = getFlightCountry(form.originCountry)
  const destinationCountry = getFlightCountry(form.destinationCountry)
  const originLabel = getFlightPlaceLabel(form.originCountry, form.originCity)
  const destinationLabel = getFlightPlaceLabel(form.destinationCountry, form.destinationCity)
  const destinationScope = form.destinationCity ? 'Cidade exata' : 'Qualquer cidade do pais'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const originCityLabel = getCityLabel(form.originCountry, form.originCity)
      const destCityLabel = form.destinationCity
        ? getCityLabel(form.destinationCountry, form.destinationCity)
        : ''
      const destCountryLabel = destinationCountry?.label || form.destinationCountry.toUpperCase()

      const response = await searchApi.searchFlights({
        origin: originLabel,
        destination: destinationLabel,
        departure_date: form.departure_date,
        return_date: form.return_date || undefined,
        passengers: Number(form.passengers),
        origin_city: originCityLabel,
        destination_country: destCountryLabel,
        destination_city: destCityLabel,
        date_flexibility_days: 3,
      })

      const data = response.data as FlightMeta & { results: SearchResult[] }
      const sorted = sortFlightsByPrice(data.results || [])
      onFlightResults(
        {
          total: data.total ?? sorted.length,
          cheapest_price: data.cheapest_price ?? null,
          cheapest_destination: data.cheapest_destination ?? null,
          cheapest_date: data.cheapest_date ?? null,
          has_api_key: data.has_api_key ?? false,
          message: data.message ?? '',
        },
        sorted,
      )

      if (sorted.length === 0) {
        toast('Nenhum voo encontrado para os parametros informados.', { icon: 'ℹ️' })
      }
    } catch (err) {
      console.error(err)
      toast.error('Erro ao buscar voos. Verifique os logs do backend.')
    } finally {
      setLoading(false)
    }
  }

  const handleSchedule = async () => {
    setScheduling(true)
    const googleFlightsUrl = buildFlightSearchUrl(form)

    try {
      await scraperApi.scheduleScrape({
        name: `Monitor passagens: ${originLabel} -> ${destinationLabel}`,
        url: googleFlightsUrl,
        extraction_type: 'ai',
        engine: 'playwright',
        use_playwright: true,
        fields: ['companhia', 'voo', 'saida', 'chegada', 'duracao', 'preco', 'escalas', 'link_compra'],
        frequency: form.scheduleFrequency,
        cron_expression: form.scheduleFrequency === 'weekly' ? '0 8 * * 1' : '0 8 * * *',
        search_type: 'flights',
        search_params: {
          origin_country: form.originCountry,
          origin_city: form.originCity,
          origin_label: originLabel,
          destination_country: form.destinationCountry,
          destination_city: form.destinationCity || null,
          destination_label: destinationLabel,
          destination_scope: form.destinationCity ? 'city' : 'country',
          departure_date: form.departure_date,
          return_date: form.return_date || null,
          passengers: Number(form.passengers),
          source: 'google_flights',
          result_url: googleFlightsUrl,
        },
      })
      toast.success('Monitoramento periodico criado')
    } catch {
      toast.error('Nao foi possivel agendar essa busca')
    } finally {
      setScheduling(false)
    }
  }

  const field = (label: string, key: keyof Pick<FlightFormState, 'departure_date' | 'return_date'>, type = 'text') => (
    <div>
      <label className="block text-xs font-medium text-foreground mb-1.5">{label}</label>
      <input
        type={type}
        value={String(form[key])}
        onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))}
        className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder-muted focus:outline-none focus:border-primary transition-colors"
      />
    </div>
  )

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
        <div>
          <label className="block text-xs font-medium text-foreground mb-1.5">Pais de Origem</label>
          <select
            value={form.originCountry}
            onChange={e => {
              const country = getFlightCountry(e.target.value)
              setForm(p => ({ ...p, originCountry: e.target.value, originCity: country?.cities[0]?.slug || '' }))
            }}
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary transition-colors"
          >
            {flightCountries.map(country => (
              <option key={country.id} value={country.id}>{country.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-foreground mb-1.5">Cidade de Origem</label>
          <select
            value={form.originCity}
            onChange={e => setForm(p => ({ ...p, originCity: e.target.value }))}
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary transition-colors"
          >
            {originCountry?.cities.map(city => (
              <option key={city.slug} value={city.slug}>{city.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-foreground mb-1.5">Pais de Destino</label>
          <select
            value={form.destinationCountry}
            onChange={e => setForm(p => ({ ...p, destinationCountry: e.target.value, destinationCity: '' }))}
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary transition-colors"
          >
            {flightCountries.map(country => (
              <option key={country.id} value={country.id}>{country.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-foreground mb-1.5">Cidade de Destino</label>
          <select
            value={form.destinationCity}
            onChange={e => setForm(p => ({ ...p, destinationCity: e.target.value }))}
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary transition-colors"
          >
            <option value="">Qualquer cidade do pais</option>
            {destinationCountry?.cities.map(city => (
              <option key={city.slug} value={city.slug}>{city.label}</option>
            ))}
          </select>
          <p className="mt-1 text-[11px] text-muted">
            {form.destinationCity
              ? `Busca somente ${destinationLabel}`
              : `Busca oportunidades em qualquer cidade de ${destinationCountry?.label || 'destino'}`}
          </p>
        </div>
        {field('Data de Ida', 'departure_date', 'date')}
        {field('Data de Volta (opc.)', 'return_date', 'date')}
      </div>
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
        <div>
          <label className="block text-xs font-medium text-foreground mb-1.5">Passageiros</label>
          <input type="number" min={1} max={9} value={form.passengers}
            onChange={e => setForm(p => ({ ...p, passengers: Number(e.target.value) }))}
            className="w-32 bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary transition-colors" />
        </div>
        <p className="max-w-3xl text-xs text-muted">
          Busca em ate 15 aeroportos dos EUA simultaneamente com flexibilidade de +/- 3 dias.
          Resultados ranqueados por preco (menor para maior).
        </p>
      </div>
      <Button type="submit" loading={loading} className="w-full">
        <Search className="w-4 h-4" /> Buscar Passagens
      </Button>
      <div className="grid grid-cols-1 sm:grid-cols-[180px_1fr] gap-3">
        <select
          value={form.scheduleFrequency}
          onChange={e => setForm(p => ({ ...p, scheduleFrequency: e.target.value as FlightFormState['scheduleFrequency'] }))}
          className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary transition-colors"
        >
          <option value="daily">Diario as 08:00</option>
          <option value="weekly">Semanal segunda 08:00</option>
        </select>
        <Button type="button" variant="outline" loading={scheduling} onClick={handleSchedule} className="w-full">
          <CalendarPlus className="w-4 h-4" /> Tornar busca periodica
        </Button>
      </div>
    </form>
  )
}

function FlightResults({ meta, results }: { meta: FlightMeta; results: SearchResult[] }) {
  if (!results.length) return null

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3 px-1">
        <Badge variant="success">{meta.total} voo{meta.total !== 1 ? 's' : ''} encontrado{meta.total !== 1 ? 's' : ''}</Badge>
        {meta.cheapest_price !== null && (
          <span className="text-sm text-muted">
            Mais barato:{' '}
            <span className="text-foreground font-bold text-primary">
              R$ {meta.cheapest_price.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            {meta.cheapest_destination && ` · ${meta.cheapest_destination}`}
            {meta.cheapest_date && ` · ${meta.cheapest_date}`}
          </span>
        )}
        {!meta.has_api_key && (
          <Badge variant="warning" className="text-[10px]">Sem chave Amadeus — dados via scraper</Badge>
        )}
      </div>
      <p className="text-xs text-muted px-1">{meta.message}</p>

      <div className="w-full overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="border-b border-border">
            <tr>
              <th className="text-left text-xs text-muted font-medium px-3 py-3 w-8">#</th>
              <th className="text-left text-xs text-muted font-medium px-3 py-3">Companhia</th>
              <th className="text-left text-xs text-muted font-medium px-3 py-3">Rota</th>
              <th className="text-left text-xs text-muted font-medium px-3 py-3">Saida</th>
              <th className="text-left text-xs text-muted font-medium px-3 py-3">Chegada</th>
              <th className="text-left text-xs text-muted font-medium px-3 py-3">Duracao</th>
              <th className="text-center text-xs text-muted font-medium px-3 py-3">Escalas</th>
              <th className="text-left text-xs text-muted font-medium px-3 py-3">Data ida</th>
              <th className="text-right text-xs text-muted font-medium px-3 py-3">Preco (BRL)</th>
              <th className="text-right text-xs text-muted font-medium px-3 py-3 min-w-[110px]">Acao</th>
            </tr>
          </thead>
          <tbody>
            {results.map((row, i) => {
              const price = parsePrice(row.preco ?? row.price ?? null)
              const isFinitePrice = Number.isFinite(price)
              const diffDays = typeof row.diferenca_dias === 'number' ? row.diferenca_dias : null
              const linkCompra = String(row.link_compra || row.link_passagem || row.comprar || '')
              const escalas = typeof row.escalas === 'number' ? row.escalas : null

              return (
                <tr
                  key={i}
                  className={`border-b border-border last:border-0 transition-colors ${
                    i === 0 ? 'bg-primary/5' : 'hover:bg-surface-2/40'
                  }`}
                >
                  <td className="px-3 py-3 text-xs text-muted align-middle">{i + 1}</td>
                  <td className="px-3 py-3 align-middle">
                    <div className="flex flex-col gap-0.5">
                      {i === 0 && (
                        <Badge variant="success" className="text-[10px] py-0 px-1.5 w-fit mb-0.5">
                          Mais barato
                        </Badge>
                      )}
                      <span className="text-xs text-foreground font-medium">{String(row.companhia || '—')}</span>
                      <span className="text-[10px] text-muted">{String(row.numero_voo || '')}</span>
                    </div>
                  </td>
                  <td className="px-3 py-3 align-middle">
                    <span className="text-xs text-foreground font-medium">
                      {String(row.origem_iata || row.origem || '—')} → {String(row.destino_iata || row.destino || '—')}
                    </span>
                    <div className="text-[10px] text-muted mt-0.5">
                      {[String(row.origem_cidade || ''), String(row.destino_cidade || '')].filter(Boolean).join(' → ')}
                    </div>
                  </td>
                  <td className="px-3 py-3 text-xs text-foreground whitespace-nowrap align-middle">
                    {String(row.saida || '—')}
                  </td>
                  <td className="px-3 py-3 text-xs text-foreground whitespace-nowrap align-middle">
                    {String(row.chegada || '—')}
                  </td>
                  <td className="px-3 py-3 text-xs text-muted whitespace-nowrap align-middle">
                    {String(row.duracao || '—')}
                  </td>
                  <td className="px-3 py-3 text-center align-middle">
                    {escalas === 0 ? (
                      <Badge variant="success" className="text-[10px] py-0 px-1.5">Direto</Badge>
                    ) : escalas !== null ? (
                      <span className="text-xs text-muted">{escalas}x</span>
                    ) : (
                      <span className="text-xs text-muted">—</span>
                    )}
                  </td>
                  <td className="px-3 py-3 align-middle">
                    <div className="text-xs text-foreground whitespace-nowrap">{String(row.data_ida_real || row.ida || '—')}</div>
                    {diffDays !== null && diffDays !== 0 && (
                      <span
                        className={`inline-block mt-0.5 text-[10px] px-1 rounded font-medium ${
                          diffDays > 0 ? 'bg-warning/20 text-warning' : 'bg-secondary/20 text-secondary'
                        }`}
                      >
                        {diffDays > 0 ? `+${diffDays}d` : `${diffDays}d`}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-3 text-right align-middle">
                    <span
                      className={`text-sm font-bold ${i === 0 ? 'text-primary' : 'text-foreground'}`}
                    >
                      {isFinitePrice
                        ? `R$ ${price.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                        : String(row.preco || '—')}
                    </span>
                    <div className="text-[10px] text-muted mt-0.5">{String(row.fonte || '')}</div>
                  </td>
                  <td className="px-3 py-3 text-right align-middle">
                    {linkCompra ? (
                      <a
                        href={linkCompra}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex h-8 items-center gap-1.5 rounded-md bg-primary px-2.5 text-xs font-medium text-white transition-colors hover:bg-primary/90"
                      >
                        <ShoppingCart className="h-3.5 w-3.5" />
                        Comprar
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    ) : null}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function NewsForm({ onResults }: { onResults: (r: SearchResult[]) => void }) {
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({ query: '', sources: '', from_date: '', to_date: '' })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const response = await searchApi.searchNews({
        query: form.query,
        sources: form.sources ? [form.sources] : undefined,
        from_date: form.from_date,
        to_date: form.to_date,
      })
      onResults(response.data.results || [])
    } catch {
      const mock = Array.from({ length: 10 }, (_, i) => ({
        titulo: `${form.query}: Noticia ${i + 1}`,
        fonte: ['G1', 'Folha', 'Estadao', 'UOL'][i % 4],
        data: new Date(Date.now() - i * 3600000).toLocaleDateString('pt-BR'),
        resumo: 'Resumo da noticia coletada automaticamente pela plataforma.',
        url: `https://exemplo.com/noticia-${i + 1}`,
      }))
      onResults(mock)
      toast.success('10 noticias encontradas (modo demo)')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-xs font-medium text-foreground mb-1.5">Tema / Palavra-chave</label>
        <input value={form.query} onChange={e => setForm(p => ({ ...p, query: e.target.value }))}
          placeholder="Inteligencia Artificial, Mercado Financeiro..." required
          className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder-muted focus:outline-none focus:border-primary transition-colors" />
      </div>
      <div>
        <label className="block text-xs font-medium text-foreground mb-1.5">Fontes (opc.)</label>
        <input value={form.sources} onChange={e => setForm(p => ({ ...p, sources: e.target.value }))}
          placeholder="g1.globo.com, folha.uol.com.br..."
          className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder-muted focus:outline-none focus:border-primary transition-colors" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-foreground mb-1.5">De</label>
          <input type="date" value={form.from_date} onChange={e => setForm(p => ({ ...p, from_date: e.target.value }))}
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary transition-colors" />
        </div>
        <div>
          <label className="block text-xs font-medium text-foreground mb-1.5">Ate</label>
          <input type="date" value={form.to_date} onChange={e => setForm(p => ({ ...p, to_date: e.target.value }))}
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary transition-colors" />
        </div>
      </div>
      <Button type="submit" loading={loading} variant="secondary" className="w-full">
        <Search className="w-4 h-4" /> Buscar Noticias
      </Button>
    </form>
  )
}

function LeadsForm({ onResults }: { onResults: (r: SearchResult[]) => void }) {
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({ sector: '', country: '', target_role: '' })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const response = await searchApi.searchLeads(form)
      onResults(response.data.results || [])
    } catch {
      const mock = Array.from({ length: 15 }, (_, i) => ({
        empresa: `${form.sector} Corp ${i + 1}`,
        pais: form.country,
        cargo: form.target_role || 'CEO',
        contato: `contato${i + 1}@empresa.com`,
        linkedin: `linkedin.com/in/contato${i + 1}`,
      }))
      onResults(mock)
      toast.success('15 leads encontrados (modo demo)')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-xs font-medium text-foreground mb-1.5">Setor / Industria</label>
        <input value={form.sector} onChange={e => setForm(p => ({ ...p, sector: e.target.value }))}
          placeholder="SaaS, Fintech, Agronegocio..." required
          className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder-muted focus:outline-none focus:border-primary transition-colors" />
      </div>
      <div>
        <label className="block text-xs font-medium text-foreground mb-1.5">Pais Alvo</label>
        <input value={form.country} onChange={e => setForm(p => ({ ...p, country: e.target.value }))}
          placeholder="EUA, Reino Unido, Canada..." required
          className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder-muted focus:outline-none focus:border-primary transition-colors" />
      </div>
      <div>
        <label className="block text-xs font-medium text-foreground mb-1.5">Cargo Alvo (opc.)</label>
        <input value={form.target_role} onChange={e => setForm(p => ({ ...p, target_role: e.target.value }))}
          placeholder="CEO, CTO, Head de Marketing..."
          className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder-muted focus:outline-none focus:border-primary transition-colors" />
      </div>
      <Button type="submit" loading={loading} variant="accent" className="w-full">
        <Search className="w-4 h-4" /> Buscar Leads
      </Button>
    </form>
  )
}

function JobsForm({ onResults }: { onResults: (r: SearchResult[]) => void }) {
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({ query: '', location: '', contract_type: '' })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const response = await searchApi.searchJobs(form)
      onResults(response.data.results || [])
    } catch {
      const mock = Array.from({ length: 12 }, (_, i) => ({
        cargo: `${form.query} - ${['Junior', 'Pleno', 'Senior'][i % 3]}`,
        empresa: `Tech Company ${i + 1}`,
        local: form.location || 'Remoto',
        tipo: form.contract_type || 'CLT',
        salario: `R$ ${(3000 + i * 2000).toLocaleString()}`,
        publicado: `${i + 1} dias atras`,
      }))
      onResults(mock)
      toast.success('12 vagas encontradas (modo demo)')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-xs font-medium text-foreground mb-1.5">Cargo / Skills</label>
        <input value={form.query} onChange={e => setForm(p => ({ ...p, query: e.target.value }))}
          placeholder="Python Developer, Product Manager..." required
          className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder-muted focus:outline-none focus:border-primary transition-colors" />
      </div>
      <div>
        <label className="block text-xs font-medium text-foreground mb-1.5">Localizacao</label>
        <input value={form.location} onChange={e => setForm(p => ({ ...p, location: e.target.value }))}
          placeholder="Sao Paulo, Remoto, EUA..."
          className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder-muted focus:outline-none focus:border-primary transition-colors" />
      </div>
      <div>
        <label className="block text-xs font-medium text-foreground mb-1.5">Tipo de Contrato</label>
        <select value={form.contract_type} onChange={e => setForm(p => ({ ...p, contract_type: e.target.value }))}
          className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary transition-colors">
          <option value="">Todos</option>
          <option value="CLT">CLT</option>
          <option value="PJ">PJ</option>
          <option value="Freelance">Freelance</option>
          <option value="Estagio">Estagio</option>
        </select>
      </div>
      <Button type="submit" loading={loading} className="w-full">
        <Search className="w-4 h-4" /> Buscar Vagas
      </Button>
    </form>
  )
}

function ResultsTable({ results }: { results: SearchResult[] }) {
  if (!results.length) return null
  const cols = Object.keys(results[0]).filter(col => !linkColumns.has(col))
  const hasActions = results.some(row =>
    getRowUrl(row, ['verification_url', 'verify_url', 'verificar', 'url', 'link']) ||
    getRowUrl(row, ['purchase_url', 'booking_url', 'buy_url', 'comprar'])
  )

  return (
    <div className="w-full overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead className="border-b border-border">
          <tr>
            {cols.map(col => (
              <th key={col} className="text-left text-xs text-muted font-medium px-4 py-3 whitespace-nowrap">{col}</th>
            ))}
            {hasActions && (
              <th className="text-right text-xs text-muted font-medium px-4 py-3 whitespace-nowrap min-w-[220px]">acoes</th>
            )}
          </tr>
        </thead>
        <tbody>
          {results.slice(0, 20).map((row, i) => {
            const verifyUrl = getRowUrl(row, ['verification_url', 'verify_url', 'verificar', 'url', 'link'])
            const purchaseUrl = getRowUrl(row, ['purchase_url', 'booking_url', 'buy_url', 'comprar'])

            return (
              <tr key={i} className="border-b border-border last:border-0 hover:bg-surface-2/50 transition-colors">
                {cols.map(col => (
                  <td key={col} className="px-4 py-2.5 text-xs text-foreground align-top">
                    <span className="block min-w-[90px] max-w-[260px] whitespace-normal break-words">{String(row[col])}</span>
                  </td>
                ))}
                {hasActions && (
                  <td className="px-4 py-2.5 whitespace-nowrap min-w-[220px]">
                    <div className="flex items-center justify-end gap-2">
                      {verifyUrl && (
                        <a
                          href={verifyUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border px-2.5 text-xs text-foreground transition-colors hover:border-primary/50 hover:bg-surface-2"
                          title="Verificar disponibilidade e preco"
                        >
                          <ShieldCheck className="h-3.5 w-3.5 text-primary" />
                          Verificar
                        </a>
                      )}
                      {purchaseUrl && (
                        <a
                          href={purchaseUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex h-8 items-center gap-1.5 rounded-md bg-primary px-2.5 text-xs font-medium text-white transition-colors hover:bg-primary/90"
                          title="Abrir pagina de compra"
                        >
                          <ShoppingCart className="h-3.5 w-3.5" />
                          Comprar
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                  </td>
                )}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default function SearchPage() {
  const [activeSearch, setActiveSearch] = useState<SearchType>(null)
  const [results, setResults] = useState<SearchResult[]>([])
  const [flightMeta, setFlightMeta] = useState<FlightMeta | null>(null)

  const activeConfig = searchTypes.find(s => s.id === activeSearch)

  const handleFlightResults = (meta: FlightMeta, r: SearchResult[]) => {
    setFlightMeta(meta)
    setResults(r)
  }

  const handleReset = () => {
    setActiveSearch(null)
    setResults([])
    setFlightMeta(null)
  }

  if (activeSearch) {
    return (
      <div className="w-full max-w-[1680px] mx-auto space-y-6 animate-slide-up">
        <div className="flex items-center gap-3">
          <button onClick={handleReset}
            className="p-2 rounded-lg hover:bg-surface-2 text-muted hover:text-foreground transition-colors">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-foreground">
              {activeConfig?.emoji} {activeConfig?.title}
            </h1>
            <p className="text-sm text-muted">{activeConfig?.description}</p>
          </div>
        </div>

        <Card>
          <CardContent className="p-5">
            {activeSearch === 'flights' && <FlightForm onFlightResults={handleFlightResults} />}
            {activeSearch === 'news' && <NewsForm onResults={setResults} />}
            {activeSearch === 'leads' && <LeadsForm onResults={setResults} />}
            {activeSearch === 'jobs' && <JobsForm onResults={setResults} />}
          </CardContent>
        </Card>

        {results.length > 0 && (
          <Card className="animate-slide-up">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <CardTitle className="text-sm">Resultados</CardTitle>
                <Badge variant="success">{results.length} encontrados</Badge>
              </div>
            </CardHeader>
            <CardContent className={activeSearch === 'flights' ? 'p-4' : 'p-0'}>
              {activeSearch === 'flights' && flightMeta ? (
                <FlightResults meta={flightMeta} results={results} />
              ) : (
                <ResultsTable results={results} />
              )}
            </CardContent>
          </Card>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-foreground">Hub de Busca Especializada</h1>
        <p className="text-sm text-muted mt-0.5">Escolha o tipo de busca para comecar a coletar dados estruturados</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {searchTypes.map((type) => (
          <button
            key={type.id}
            onClick={() => setActiveSearch(type.id)}
            className={`text-left p-6 rounded-xl border transition-all duration-200 group ${type.colorClass}`}
          >
            <div className={`w-12 h-12 rounded-xl border flex items-center justify-center mb-4 ${type.iconClass}`}>
              <span className="text-2xl">{type.emoji}</span>
            </div>
            <h3 className="text-base font-bold text-foreground mb-1 group-hover:text-primary transition-colors">
              {type.title}
            </h3>
            <p className="text-sm text-muted leading-relaxed">{type.description}</p>
            <div className="mt-4 flex items-center gap-2 text-xs">
              <Search className="w-3.5 h-3.5 text-muted" />
              <span className="text-muted group-hover:text-foreground transition-colors">Clique para buscar</span>
            </div>
          </button>
        ))}
      </div>

      <Card>
        <CardContent className="p-5">
          <div className="flex items-center gap-3 text-sm">
            <div className="w-8 h-8 bg-primary/10 border border-primary/20 rounded-lg flex items-center justify-center">
              <Search className="w-4 h-4 text-primary" />
            </div>
            <div>
              <p className="text-foreground font-medium">Dados estruturados com IA</p>
              <p className="text-xs text-muted mt-0.5">Todos os resultados sao processados e validados pela IA antes de serem entregues</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
