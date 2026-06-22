import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2',
  {
    variants: {
      variant: {
        default:
          'border-transparent bg-primary text-white shadow',
        secondary:
          'border-transparent bg-surface-2 text-foreground',
        destructive:
          'border-transparent bg-destructive/20 text-destructive border-destructive/30',
        outline:
          'border-border text-foreground',
        success:
          'border-transparent bg-success/20 text-success border-success/30',
        warning:
          'border-transparent bg-warning/20 text-warning border-warning/30',
        info:
          'border-transparent bg-primary/20 text-primary border-primary/30',
        accent:
          'border-transparent bg-accent/20 text-accent border-accent/30',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
