'use client'

import { Globe, Zap, Star, ExternalLink, Search } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useState } from 'react'

interface PublicAPI {
  id: string
  name: string
  description: string
  category: string
  auth: 'none' | 'api_key' | 'oauth'
  https: boolean
  cors: boolean
  url: string
  docsUrl: string
}

const mockApis: PublicAPI[] = [
  { id: '1', name: 'NewsAPI', description: 'Noticias de mais de 80.000 fontes em tempo real', category: 'News', auth: 'api_key', https: true, cors: false, url: 'https://newsapi.org', docsUrl: 'https://newsapi.org/docs' },
  { id: '2', name: 'AviationStack', description: 'Dados de voos, aeroportos e companhias aereas', category: 'Transportation', auth: 'api_key', https: true, cors: false, url: 'https://aviationstack.com', docsUrl: 'https://aviationstack.com/documentation' },
  { id: '3', name: 'Hunter.io', description: 'Encontre emails corporativos de qualquer dominio', category: 'Business', auth: 'api_key', https: true, cors: true, url: 'https://hunter.io', docsUrl: 'https://hunter.io/api-documentation' },
  { id: '4', name: 'Open Exchange Rates', description: 'Taxas de cambio em tempo real para 170+ moedas', category: 'Finance', auth: 'api_key', https: true, cors: true, url: 'https://openexchangerates.org', docsUrl: 'https://docs.openexchangerates.org' },
  { id: '5', name: 'IBGE API', description: 'Dados geograficos e demograficos do Brasil', category: 'Government', auth: 'none', https: true, cors: true, url: 'https://servicodados.ibge.gov.br', docsUrl: 'https://servicodados.ibge.gov.br/api/docs' },
  { id: '6', name: 'Adzuna Jobs', description: 'Busca de vagas de emprego em todo o mundo', category: 'Jobs', auth: 'api_key', https: true, cors: false, url: 'https://adzuna.com', docsUrl: 'https://developer.adzuna.com/docs' },
]

export default function APIsPage() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('all')

  const categories = ['all', ...Array.from(new Set(mockApis.map(a => a.category)))]
  const filtered = mockApis.filter(api => {
    const matchSearch = api.name.toLowerCase().includes(search.toLowerCase()) ||
      api.description.toLowerCase().includes(search.toLowerCase())
    const matchCategory = category === 'all' || api.category === category
    return matchSearch && matchCategory
  })

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-foreground">APIs Publicas</h1>
        <p className="text-sm text-muted mt-0.5">Catalogo de APIs integradas para busca especializada</p>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Buscar APIs..."
            className="w-full bg-surface border border-border rounded-lg pl-9 pr-4 py-2 text-sm text-foreground placeholder-muted focus:outline-none focus:border-primary transition-colors" />
        </div>
        <select value={category} onChange={e => setCategory(e.target.value)}
          className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary transition-colors">
          {categories.map(c => <option key={c} value={c}>{c === 'all' ? 'Todas as categorias' : c}</option>)}
        </select>
      </div>

      {/* APIs grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((api) => (
          <Card key={api.id} className="hover:border-border/80 transition-all duration-200 group">
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-primary/10 border border-primary/20 rounded-lg flex items-center justify-center">
                    <Globe className="w-4 h-4 text-primary" />
                  </div>
                  <CardTitle className="text-sm">{api.name}</CardTitle>
                </div>
                <Badge variant={api.auth === 'none' ? 'success' : 'warning'}>
                  {api.auth === 'none' ? 'Free' : 'API Key'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <CardDescription className="text-xs leading-relaxed">{api.description}</CardDescription>
              <div className="flex flex-wrap gap-1.5">
                <Badge variant="secondary" className="text-[10px]">{api.category}</Badge>
                {api.https && <Badge variant="success" className="text-[10px]">HTTPS</Badge>}
                {api.cors && <Badge variant="info" className="text-[10px]">CORS</Badge>}
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" className="flex-1 text-xs" asChild>
                  <a href={api.docsUrl} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="w-3 h-3" /> Docs
                  </a>
                </Button>
                <Button size="sm" className="flex-1 text-xs">
                  <Zap className="w-3 h-3" /> Usar
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12 text-muted">
          <Globe className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">Nenhuma API encontrada para essa busca</p>
        </div>
      )}
    </div>
  )
}
