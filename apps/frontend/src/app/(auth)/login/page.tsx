'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRouter } from 'next/navigation'
import { Eye, EyeOff, Zap, Bot, Globe } from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'

const loginSchema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(6, 'Senha deve ter no mínimo 6 caracteres'),
})

type LoginFormData = z.infer<typeof loginSchema>

export default function LoginPage() {
  const router = useRouter()
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: LoginFormData) => {
    setIsLoading(true)
    try {
      const response = await api.post('/auth/login', {
        email: data.email,
        password: data.password,
      })
      const { access_token } = response.data
      localStorage.setItem('token', access_token)
      toast.success('Login realizado com sucesso!')
      router.push('/dashboard')
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: unknown } } }
      const detail = err?.response?.data?.detail
      const message = typeof detail === 'string' ? detail : 'Credenciais inválidas'
      toast.error(message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center relative overflow-hidden">
      {/* Animated mesh background */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-primary/10 rounded-full blur-3xl animate-pulse-slow" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-accent/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-secondary/5 rounded-full blur-3xl" />
        {/* Grid pattern */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: 'linear-gradient(#06b6d4 1px, transparent 1px), linear-gradient(90deg, #06b6d4 1px, transparent 1px)',
            backgroundSize: '50px 50px',
          }}
        />
      </div>

      {/* Login Card */}
      <div className="relative z-10 w-full max-w-md px-4">
        <div className="glass rounded-2xl p-8 shadow-2xl animate-slide-up">
          {/* Logo */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 mb-4 glow-cyan">
              <Bot className="w-8 h-8 text-primary" />
            </div>
            <h1 className="text-2xl font-bold gradient-text">WebScrapy AI</h1>
            <p className="text-muted text-sm mt-1">Plataforma Premium de Web Scraping</p>
          </div>

          {/* Feature badges */}
          <div className="flex gap-2 justify-center mb-6">
            <span className="flex items-center gap-1 text-xs bg-primary/10 text-primary px-2 py-1 rounded-full border border-primary/20">
              <Zap className="w-3 h-3" /> NVIDIA AI
            </span>
            <span className="flex items-center gap-1 text-xs bg-secondary/10 text-secondary px-2 py-1 rounded-full border border-secondary/20">
              <Globe className="w-3 h-3" /> Multi-engine
            </span>
          </div>

          <h2 className="text-lg font-semibold text-foreground mb-6">Entrar na plataforma</h2>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Email
              </label>
              <input
                {...register('email')}
                type="email"
                placeholder="seu@email.com"
                className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-foreground placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors"
              />
              {errors.email && (
                <p className="text-destructive text-xs mt-1">{errors.email.message}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Senha
              </label>
              <div className="relative">
                <input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 pr-10 text-foreground placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-foreground transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="text-destructive text-xs mt-1">{errors.password.message}</p>
              )}
            </div>

            {/* Forgot password */}
            <div className="text-right">
              <a href="#" className="text-xs text-primary hover:text-primary/80 transition-colors">
                Esqueci minha senha
              </a>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-primary hover:bg-primary/90 disabled:bg-primary/50 text-white font-semibold py-2.5 rounded-lg transition-all duration-200 flex items-center justify-center gap-2 glow-cyan"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Entrando...
                </>
              ) : (
                'Entrar'
              )}
            </button>
          </form>

          {/* Register link */}
          <p className="text-center text-sm text-muted mt-6">
            Não tem conta?{' '}
            <a href="/register" className="text-primary hover:text-primary/80 transition-colors font-medium">
              Criar conta grátis
            </a>
          </p>

          {/* Demo credentials */}
          <div className="mt-4 p-3 bg-surface rounded-lg border border-border">
            <p className="text-xs text-muted text-center">
              Demo: <span className="text-foreground font-mono">admin@webscrapy.ai</span> / <span className="text-foreground font-mono">admin123</span>
            </p>
          </div>
        </div>

        <p className="text-center text-xs text-muted mt-4">
          WebScrapy AI Platform v0.1.0 — Powered by NVIDIA AI
        </p>
      </div>
    </div>
  )
}
