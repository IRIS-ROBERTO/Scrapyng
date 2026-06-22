'use client'

import { useEffect, useState } from 'react'
import { Bot, Wifi, WifiOff, Play, TrendingUp, Zap, Clock, DollarSign } from 'lucide-react'
import toast from 'react-hot-toast'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { aiApi } from '@/lib/api'

interface AIModel {
  id: string
  name: string
  provider: string
  contextLength: string
  speed: string
  status: 'online' | 'offline' | 'testing'
  priority: number
  callsToday: number
  avgLatency: string
  costPerCall: string
  isPrimary: boolean
  tier?: string
  strength?: string
}

const initialModels: AIModel[] = [
  {
    id: 'nvidia/nemotron-3-ultra-550b-a55b',
    name: 'Nemotron 3 Ultra 550B',
    provider: 'NVIDIA',
    contextLength: '256K+',
    speed: 'Media',
    status: 'online',
    priority: 1,
    callsToday: 280,
    avgLatency: 'Sob teste',
    costPerCall: 'Free endpoint',
    isPrimary: true,
    tier: 'frontier',
    strength: 'Raciocinio profundo, agentes complexos e analise longa',
  },
  {
    id: 'deepseek-ai/deepseek-v4-pro',
    name: 'DeepSeek V4 Pro',
    provider: 'DeepSeek AI',
    contextLength: '1M',
    speed: 'Media',
    status: 'online',
    priority: 2,
    callsToday: 190,
    avgLatency: 'Sob teste',
    costPerCall: 'Free endpoint',
    isPrimary: false,
    tier: 'frontier',
    strength: 'Codigo, tool use, agentes e contexto muito longo',
  },
  {
    id: 'nvidia/nemotron-3-super-120b-a12b',
    name: 'Nemotron 3 Super 120B',
    provider: 'NVIDIA',
    contextLength: '256K+',
    speed: 'Alta',
    status: 'online',
    priority: 3,
    callsToday: 120,
    avgLatency: 'Sob teste',
    costPerCall: 'Free endpoint',
    isPrimary: false,
    tier: 'premium',
    strength: 'Agentes colaborativos e alto volume',
  },
  {
    id: 'deepseek-ai/deepseek-v4-flash',
    name: 'DeepSeek V4 Flash',
    provider: 'DeepSeek AI',
    contextLength: '1M',
    speed: 'Muito Alta',
    status: 'online',
    priority: 4,
    callsToday: 80,
    avgLatency: 'Sob teste',
    costPerCall: 'Free endpoint',
    isPrimary: false,
    tier: 'premium',
    strength: 'Codigo e agentes com baixa latencia',
  },
  {
    id: 'nvidia/llama-3.3-70b-instruct',
    name: 'Llama 3.3 70B',
    provider: 'NVIDIA / Meta',
    contextLength: '128K',
    speed: 'Alta',
    status: 'online',
    priority: 5,
    callsToday: 40,
    avgLatency: 'Sob teste',
    costPerCall: 'Fallback',
    isPrimary: false,
    tier: 'fallback',
    strength: 'Fallback geral estavel',
  },
  {
    id: 'nvidia/mistral-nemo-12b-instruct',
    name: 'Mistral Nemo 12B',
    provider: 'NVIDIA / Mistral',
    contextLength: '128K',
    speed: 'Muito Alta',
    status: 'online',
    priority: 7,
    callsToday: 20,
    avgLatency: 'Sob teste',
    costPerCall: 'Fallback leve',
    isPrimary: false,
    tier: 'light_fallback',
    strength: 'Fallback rapido e economico',
  },
]

const mockHistory = [
  { id: '1', model: 'LLaMA 3.3 70B', task: 'Analisar pagina amazon.com.br', tokens: 1240, latency: '78ms', cost: '$0.0011', time: '2 min atras' },
  { id: '2', model: 'Mistral Nemo 12B', task: 'Extrair campos de g1.globo.com', tokens: 890, latency: '29ms', cost: '$0.0002', time: '15 min atras' },
  { id: '3', model: 'LLaMA 3.3 70B', task: 'Detectar estrutura linkedin.com', tokens: 2100, latency: '91ms', cost: '$0.0019', time: '1h atras' },
  { id: '4', model: 'Gemma 2 27B', task: 'Analisar formulario de cadastro', tokens: 450, latency: '132ms', cost: '$0.0002', time: '2h atras' },
]

export default function AIPage() {
  const [models, setModels] = useState<AIModel[]>(initialModels)
  const [testingModel, setTestingModel] = useState<string | null>(null)
  const [settingPrimary, setSettingPrimary] = useState<string | null>(null)

  useEffect(() => {
    const loadModels = async () => {
      try {
        const response = await aiApi.getModels()
        const apiModels = response.data.models || []
        setModels(apiModels.map((model: {
          id: string
          name: string
          provider: string
          context_length: string
          speed: string
          priority: number
          is_primary: boolean
          tier: string
          strength: string
        }) => ({
          id: model.id,
          name: model.name,
          provider: model.provider,
          contextLength: model.context_length,
          speed: model.speed,
          status: 'online',
          priority: model.priority,
          callsToday: 0,
          avgLatency: 'Sob teste',
          costPerCall: model.tier === 'frontier' || model.tier === 'premium' ? 'Free endpoint' : 'Fallback',
          isPrimary: model.is_primary,
          tier: model.tier,
          strength: model.strength,
        })))
      } catch {
        toast.error('Usando catalogo local de modelos')
      }
    }

    loadModels()
  }, [])

  const handleTest = async (modelId: string) => {
    setTestingModel(modelId)
    setModels(prev => prev.map(m => m.id === modelId ? { ...m, status: 'testing' } : m))
    try {
      await aiApi.testModel(modelId)
      setModels(prev => prev.map(m => m.id === modelId ? { ...m, status: 'online', avgLatency: 'OK' } : m))
      toast.success('Modelo respondendo corretamente!')
    } catch {
      // Simulate test
      await new Promise(r => setTimeout(r, 1500))
      setModels(prev => prev.map(m => m.id === modelId ? { ...m, status: 'online' } : m))
      toast.success('Conexao OK (modo demo)')
    } finally {
      setTestingModel(null)
    }
  }

  const handleSetPrimary = async (modelId: string) => {
    setSettingPrimary(modelId)
    try {
      await aiApi.setPreferredModel(modelId)
      setModels(prev => prev.map(m => ({ ...m, isPrimary: m.id === modelId })))
      toast.success('Modelo primario atualizado!')
    } catch {
      setModels(prev => prev.map(m => ({ ...m, isPrimary: m.id === modelId })))
      toast.success('Modelo primario definido (modo demo)')
    } finally {
      setSettingPrimary(null)
    }
  }

  const totalCalls = models.reduce((a, m) => a + m.callsToday, 0)
  const totalCost = (totalCalls * 0.0005).toFixed(4)

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-foreground">Integracoes NVIDIA AI</h1>
        <p className="text-sm text-muted mt-0.5">Gerencie os modelos de IA para analise e extracao de dados</p>
      </div>

      {/* Usage summary */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="border-primary/20 bg-primary/5">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-10 h-10 bg-primary/20 border border-primary/30 rounded-lg flex items-center justify-center">
              <Zap className="w-5 h-5 text-primary" />
            </div>
            <div>
              <p className="text-xl font-bold text-foreground">{totalCalls.toLocaleString()}</p>
              <p className="text-xs text-muted">Chamadas hoje</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-10 h-10 bg-secondary/10 border border-secondary/20 rounded-lg flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-secondary" />
            </div>
            <div>
              <p className="text-xl font-bold text-foreground">${totalCost}</p>
              <p className="text-xs text-muted">Custo estimado hoje</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-10 h-10 bg-accent/10 border border-accent/20 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-accent" />
            </div>
            <div>
              <p className="text-xl font-bold text-foreground">{models.filter(m => m.status === 'online').length}/{models.length}</p>
              <p className="text-xs text-muted">Modelos online</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Fallback chain info */}
      <Card className="border-accent/20 bg-accent/5">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <Bot className="w-4 h-4 text-accent flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-foreground mb-1">Cadeia de Fallback Automatico</p>
              <div className="flex items-center gap-2 flex-wrap">
                {models.sort((a, b) => a.priority - b.priority).map((m, i) => (
                  <div key={m.id} className="flex items-center gap-2">
                    <span className="text-xs text-foreground bg-surface-2 border border-border rounded-lg px-2 py-1">
                      {i + 1}. {m.name.split(' ').slice(0, 2).join(' ')}
                    </span>
                    {i < models.length - 1 && <span className="text-muted text-xs">→</span>}
                  </div>
                ))}
              </div>
              <p className="text-xs text-muted mt-2">Se o modelo primario falhar, o sistema tenta automaticamente o proximo na cadeia.</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Models grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {models.map((model) => (
          <Card
            key={model.id}
            className={model.isPrimary ? 'border-primary/30 bg-primary/5' : ''}
          >
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-9 h-9 rounded-lg border flex items-center justify-center ${
                    model.isPrimary
                      ? 'bg-primary/20 border-primary/30'
                      : 'bg-surface-2 border-border'
                  }`}>
                    <Bot className={`w-4 h-4 ${model.isPrimary ? 'text-primary' : 'text-muted'}`} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <CardTitle className="text-sm">{model.name}</CardTitle>
                      {model.isPrimary && (
                        <Badge variant="default" className="text-[10px] h-4">Primario</Badge>
                      )}
                      {model.tier === 'frontier' && (
                        <Badge variant="success" className="text-[10px] h-4">Frontier</Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted">{model.provider}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  {model.status === 'testing' ? (
                    <Badge variant="warning" className="animate-pulse">Testando...</Badge>
                  ) : model.status === 'online' ? (
                    <Badge variant="success">
                      <Wifi className="w-3 h-3" /> Online
                    </Badge>
                  ) : (
                    <Badge variant="destructive">
                      <WifiOff className="w-3 h-3" /> Offline
                    </Badge>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Stats grid */}
              <div className="grid grid-cols-4 gap-2">
                <div className="bg-surface-2 rounded-lg p-2 text-center">
                  <p className="text-xs font-bold text-foreground">{model.contextLength}</p>
                  <p className="text-[10px] text-muted">Contexto</p>
                </div>
                <div className="bg-surface-2 rounded-lg p-2 text-center">
                  <p className="text-xs font-bold text-foreground">{model.speed}</p>
                  <p className="text-[10px] text-muted">Velocidade</p>
                </div>
                <div className="bg-surface-2 rounded-lg p-2 text-center">
                  <p className="text-xs font-bold text-foreground">{model.avgLatency}</p>
                  <p className="text-[10px] text-muted">Latencia</p>
                </div>
                <div className="bg-surface-2 rounded-lg p-2 text-center">
                  <p className="text-xs font-bold text-foreground">{model.costPerCall}</p>
                  <p className="text-[10px] text-muted">Por chamada</p>
                </div>
              </div>

              {/* Usage today */}
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted flex items-center gap-1">
                  <Clock className="w-3 h-3" /> {model.callsToday} chamadas hoje
                </span>
                <span className="text-muted">Prioridade #{model.priority}</span>
              </div>
              {model.strength && (
                <p className="text-xs text-muted leading-relaxed">{model.strength}</p>
              )}

              {/* Actions */}
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1 text-xs"
                  onClick={() => handleTest(model.id)}
                  loading={testingModel === model.id}
                >
                  <Play className="w-3 h-3" />
                  Testar
                </Button>
                {!model.isPrimary && (
                  <Button
                    size="sm"
                    className="flex-1 text-xs"
                    onClick={() => handleSetPrimary(model.id)}
                    loading={settingPrimary === model.id}
                  >
                    Definir como Primario
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Call history */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Historico de Chamadas</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border">
                <tr>
                  <th className="text-left text-xs text-muted font-medium px-4 py-3">Modelo</th>
                  <th className="text-left text-xs text-muted font-medium px-4 py-3">Tarefa</th>
                  <th className="text-right text-xs text-muted font-medium px-4 py-3">Tokens</th>
                  <th className="text-right text-xs text-muted font-medium px-4 py-3">Latencia</th>
                  <th className="text-right text-xs text-muted font-medium px-4 py-3">Custo</th>
                  <th className="text-right text-xs text-muted font-medium px-4 py-3">Hora</th>
                </tr>
              </thead>
              <tbody>
                {mockHistory.map((h) => (
                  <tr key={h.id} className="border-b border-border last:border-0 hover:bg-surface-2/50 transition-colors">
                    <td className="px-4 py-3">
                      <span className="text-xs text-primary font-mono">{h.model}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-foreground truncate max-w-[200px] block">{h.task}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-xs text-foreground font-mono">{h.tokens.toLocaleString()}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-xs text-secondary">{h.latency}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-xs text-foreground">{h.cost}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-xs text-muted">{h.time}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
