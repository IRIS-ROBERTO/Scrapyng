'use client'

import { useState } from 'react'
import { Shield, User, Calendar, Filter } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface AuditEvent {
  id: string
  action: string
  resource: string
  user: string
  ip: string
  status: 'success' | 'failed'
  timestamp: string
}

const mockEvents: AuditEvent[] = [
  { id: '1', action: 'LOGIN', resource: 'auth', user: 'admin@webscrapy.ai', ip: '192.168.1.1', status: 'success', timestamp: '2026-06-22 14:30:00' },
  { id: '2', action: 'CREATE_JOB', resource: 'jobs', user: 'admin@webscrapy.ai', ip: '192.168.1.1', status: 'success', timestamp: '2026-06-22 14:25:00' },
  { id: '3', action: 'EXPORT_DATA', resource: 'results/1', user: 'admin@webscrapy.ai', ip: '192.168.1.1', status: 'success', timestamp: '2026-06-22 13:00:00' },
  { id: '4', action: 'DELETE_JOB', resource: 'jobs/5', user: 'admin@webscrapy.ai', ip: '192.168.1.1', status: 'success', timestamp: '2026-06-22 12:00:00' },
  { id: '5', action: 'LOGIN', resource: 'auth', user: 'unknown@attacker.com', ip: '10.0.0.1', status: 'failed', timestamp: '2026-06-22 11:00:00' },
  { id: '6', action: 'UPDATE_SETTINGS', resource: 'settings', user: 'admin@webscrapy.ai', ip: '192.168.1.1', status: 'success', timestamp: '2026-06-22 10:00:00' },
]

export default function AuditPage() {
  const [events] = useState<AuditEvent[]>(mockEvents)
  const [statusFilter, setStatusFilter] = useState('all')

  const filtered = events.filter(e => statusFilter === 'all' || e.status === statusFilter)

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <Shield className="w-5 h-5 text-primary" />
            Auditoria de Seguranca
          </h1>
          <p className="text-sm text-muted mt-0.5">Registro completo de acoes na plataforma</p>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-foreground">{events.length}</p>
            <p className="text-xs text-muted">Eventos hoje</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-secondary">{events.filter(e => e.status === 'success').length}</p>
            <p className="text-xs text-muted">Bem-sucedidos</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-destructive">{events.filter(e => e.status === 'failed').length}</p>
            <p className="text-xs text-muted">Falhas (possivel ameaca)</p>
          </CardContent>
        </Card>
      </div>

      {/* Filter */}
      <div className="flex gap-3">
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary transition-colors">
          <option value="all">Todos</option>
          <option value="success">Sucesso</option>
          <option value="failed">Falhas</option>
        </select>
      </div>

      {/* Events table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border">
                <tr>
                  <th className="text-left text-xs text-muted font-medium px-4 py-3">Acao</th>
                  <th className="text-left text-xs text-muted font-medium px-4 py-3">Recurso</th>
                  <th className="text-left text-xs text-muted font-medium px-4 py-3">Usuario</th>
                  <th className="text-left text-xs text-muted font-medium px-4 py-3">IP</th>
                  <th className="text-left text-xs text-muted font-medium px-4 py-3">Status</th>
                  <th className="text-right text-xs text-muted font-medium px-4 py-3">Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((event) => (
                  <tr key={event.id} className="border-b border-border last:border-0 hover:bg-surface-2/50 transition-colors">
                    <td className="px-4 py-3">
                      <span className="text-xs font-mono text-primary">{event.action}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-muted font-mono">{event.resource}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <User className="w-3 h-3 text-muted" />
                        <span className="text-xs text-foreground">{event.user}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-mono text-muted">{event.ip}</span>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={event.status === 'success' ? 'success' : 'destructive'}>
                        {event.status === 'success' ? 'OK' : 'Falha'}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-xs text-muted font-mono">{event.timestamp}</span>
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
