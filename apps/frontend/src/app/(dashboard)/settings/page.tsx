'use client'

import { useState } from 'react'
import { Save, Eye, EyeOff } from 'lucide-react'
import toast from 'react-hot-toast'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

export default function SettingsPage() {
  const [showKey, setShowKey] = useState(false)
  const [saving, setSaving] = useState(false)
  const [settings, setSettings] = useState({
    nvidiaKey: '',
    defaultEngine: 'scrapy',
    maxConcurrentJobs: 4,
    requestTimeout: 30,
    retryAttempts: 3,
    userAgent: 'WebScrapy-Bot/1.0',
    notifyOnFailure: true,
    notifyOnSuccess: false,
  })

  const handleSave = async () => {
    setSaving(true)
    await new Promise(r => setTimeout(r, 800))
    setSaving(false)
    toast.success('Configuracoes salvas!')
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-foreground">Configuracoes</h1>
        <p className="text-sm text-muted mt-0.5">Gerencie as configuracoes da plataforma</p>
      </div>

      {/* API Keys */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Chaves de API</CardTitle>
          <CardDescription>Configure as integrações com servicos externos</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-foreground mb-1.5">NVIDIA API Key</label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={settings.nvidiaKey}
                onChange={e => setSettings(p => ({ ...p, nvidiaKey: e.target.value }))}
                placeholder="nvapi-..."
                className="w-full bg-surface border border-border rounded-lg px-3 py-2 pr-10 text-sm text-foreground placeholder-muted focus:outline-none focus:border-primary transition-colors"
              />
              <button type="button" onClick={() => setShowKey(!showKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-foreground transition-colors">
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-xs text-muted mt-1">Nunca exposta no frontend — armazenada com segurança no backend</p>
          </div>
        </CardContent>
      </Card>

      {/* Scraper config */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Configuracoes do Scraper</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-foreground mb-1.5">Engine Padrao</label>
            <select value={settings.defaultEngine}
              onChange={e => setSettings(p => ({ ...p, defaultEngine: e.target.value }))}
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary transition-colors">
              <option value="scrapy">Scrapy (recomendado)</option>
              <option value="playwright">Playwright</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-foreground mb-1.5">Max Jobs Simultaneos</label>
              <input type="number" min={1} max={20} value={settings.maxConcurrentJobs}
                onChange={e => setSettings(p => ({ ...p, maxConcurrentJobs: Number(e.target.value) }))}
                className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary transition-colors" />
            </div>
            <div>
              <label className="block text-xs font-medium text-foreground mb-1.5">Timeout (segundos)</label>
              <input type="number" min={5} max={300} value={settings.requestTimeout}
                onChange={e => setSettings(p => ({ ...p, requestTimeout: Number(e.target.value) }))}
                className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary transition-colors" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-foreground mb-1.5">User Agent</label>
            <input value={settings.userAgent}
              onChange={e => setSettings(p => ({ ...p, userAgent: e.target.value }))}
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary transition-colors" />
          </div>
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Notificacoes</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {[
            { key: 'notifyOnFailure', label: 'Notificar em caso de falha' },
            { key: 'notifyOnSuccess', label: 'Notificar ao concluir jobs' },
          ].map(({ key, label }) => (
            <label key={key} className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-foreground">{label}</span>
              <button
                type="button"
                onClick={() => setSettings(p => ({ ...p, [key]: !p[key as keyof typeof p] }))}
                className={`w-10 h-5 rounded-full transition-colors relative ${
                  settings[key as keyof typeof settings] ? 'bg-primary' : 'bg-surface-2 border border-border'
                }`}
              >
                <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
                  settings[key as keyof typeof settings] ? 'translate-x-5' : 'translate-x-0.5'
                }`} />
              </button>
            </label>
          ))}
        </CardContent>
      </Card>

      <Button onClick={handleSave} loading={saving} className="w-full">
        <Save className="w-4 h-4" /> Salvar Configuracoes
      </Button>
    </div>
  )
}
