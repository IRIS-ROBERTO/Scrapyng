import * as React from 'react'
import { cn } from '@/lib/utils'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, label, error, hint, leftIcon, rightIcon, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-foreground mb-1.5">
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted">
              {leftIcon}
            </div>
          )}
          <input
            type={type}
            className={cn(
              'flex h-9 w-full rounded-lg border border-border bg-surface px-3 py-1 text-sm text-foreground placeholder-muted shadow-sm transition-colors',
              'file:border-0 file:bg-transparent file:text-sm file:font-medium',
              'focus-visible:outline-none focus-visible:border-primary focus-visible:ring-1 focus-visible:ring-primary/30',
              'disabled:cursor-not-allowed disabled:opacity-50',
              error && 'border-destructive focus-visible:border-destructive focus-visible:ring-destructive/30',
              leftIcon && 'pl-9',
              rightIcon && 'pr-9',
              className
            )}
            ref={ref}
            {...props}
          />
          {rightIcon && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-muted">
              {rightIcon}
            </div>
          )}
        </div>
        {error && (
          <p className="text-destructive text-xs mt-1">{error}</p>
        )}
        {hint && !error && (
          <p className="text-muted text-xs mt-1">{hint}</p>
        )}
      </div>
    )
  }
)
Input.displayName = 'Input'

// Textarea variant
export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-foreground mb-1.5">
            {label}
          </label>
        )}
        <textarea
          className={cn(
            'flex min-h-[80px] w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder-muted shadow-sm transition-colors',
            'focus-visible:outline-none focus-visible:border-primary focus-visible:ring-1 focus-visible:ring-primary/30',
            'disabled:cursor-not-allowed disabled:opacity-50',
            error && 'border-destructive',
            className
          )}
          ref={ref}
          {...props}
        />
        {error && (
          <p className="text-destructive text-xs mt-1">{error}</p>
        )}
      </div>
    )
  }
)
Textarea.displayName = 'Textarea'

export { Input, Textarea }
