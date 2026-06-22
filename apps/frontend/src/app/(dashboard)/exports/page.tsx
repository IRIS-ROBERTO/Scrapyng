'use client'

import { Download, FileText, Table, Code, Clock } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import toast from 'react-hot-toast'

interface ExportRecord {
  id: string
  jobName: string
  format: 'csv' | 'excel' | 'json'
  records: number
  size: string
  status: 'ready' | 'processing' | 'expired'
  createdAt: string
}

const mockExports: ExportRecord[] = [
  { id: '1', jobName: 'Precos Amazon BR', format: 'excel', records: 1250, size: '2.4 MB', status: 'ready', createdAt: '22/06/2026 14:30' },
  { id: '2', jobName: 'Noticias G1 Tech', format: 'csv', records: 87, size: '45 KB', status: 'ready', createdAt: '22/06/2026 12:00' },
  { id: '3', jobName: 'Leads SaaS EUA', format: 'json', records: 320, size: '180 KB', status: 'processing', createdAt: '22/06/2026 11:00' },
  { id: '4', jobName: 'Vagas Remoto', format: 'csv', records: 145, size: '78 KB', status: 'expired', createdAt: '21/06/2026 09:00' },
]

const formatIcons = {
  csv: Table,
  excel: FileText,
  json: Code,
}

export default function ExportsPage() {
  const handleDownload = (exp: ExportRecord) => {
    if (exp.status !== 'ready') {
      toast.error('Exportacao nao esta disponivel')
      return
    }
    toast.success(`Baixando ${exp.jobName}.${exp.format}...`)
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-foreground">Exportacoes</h1>
        <p className="text-sm text-muted mt-0.5">Historico de exportacoes geradas</p>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {mockExports.map((exp) => {
          const Icon = formatIcons[exp.format]
          return (
            <Card key={exp.id} className="hover:border-border/80 transition-colors">
              <CardContent className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`w-10 h-10 rounded-lg border flex items-center justify-center ${
                    exp.format === 'excel' ? 'bg-secondary/10 border-secondary/20' :
                    exp.format === 'csv' ? 'bg-primary/10 border-primary/20' :
                    'bg-accent/10 border-accent/20'
                  }`}>
                    <Icon className={`w-5 h-5 ${
                      exp.format === 'excel' ? 'text-secondary' :
                      exp.format === 'csv' ? 'text-primary' : 'text-accent'
                    }`} />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-foreground">{exp.jobName}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs text-muted">{exp.records.toLocaleString()} registros</span>
                      <span className="text-muted">·</span>
                      <span className="text-xs text-muted">{exp.size}</span>
                      <span className="text-muted">·</span>
                      <span className="text-xs font-mono text-muted uppercase">{exp.format}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right hidden sm:block">
                    <div className="flex items-center gap-1 text-xs text-muted">
                      <Clock className="w-3 h-3" /> {exp.createdAt}
                    </div>
                    <Badge
                      variant={exp.status === 'ready' ? 'success' : exp.status === 'processing' ? 'warning' : 'secondary'}
                      className="mt-1 text-[10px]"
                    >
                      {exp.status === 'ready' ? 'Pronto' : exp.status === 'processing' ? 'Processando...' : 'Expirado'}
                    </Badge>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDownload(exp)}
                    disabled={exp.status !== 'ready'}
                  >
                    <Download className="w-3.5 h-3.5" />
                    Baixar
                  </Button>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
