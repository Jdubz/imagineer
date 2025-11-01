import { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface AppShellProps {
  heading: ReactNode
  navigation?: ReactNode
  children: ReactNode
  className?: string
}

export function AppShell({ heading, navigation, children, className }: AppShellProps) {
  return (
    <div className={cn('min-h-screen bg-background text-foreground', className)}>
      <div className="border-b bg-gradient-to-r from-primary via-primary/90 to-secondary text-primary-foreground">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-10 md:flex-row md:items-center md:justify-between md:py-12">
          {heading}
        </div>
      </div>
      <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
        {navigation ? <div className="mb-8">{navigation}</div> : null}
        <div className="space-y-8">{children}</div>
      </div>
    </div>
  )
}

interface AppHeaderProps {
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
  className?: string
}

export function AppHeader({ title, description, actions, className }: AppHeaderProps) {
  return (
    <div className={cn('flex w-full flex-col gap-4 text-left md:flex-row md:items-center md:justify-between', className)}>
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold leading-tight tracking-tight md:text-4xl">{title}</h1>
        {description ? <p className="max-w-xl text-sm text-primary-foreground/90 md:text-base">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </div>
  )
}
