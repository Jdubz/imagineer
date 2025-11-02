import { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface FormFieldProps {
  label: ReactNode
  htmlFor?: string
  labelSecondary?: ReactNode
  description?: ReactNode
  error?: ReactNode
  children: ReactNode
  className?: string
}

export function FormField({
  label,
  htmlFor,
  labelSecondary,
  description,
  error,
  children,
  className,
}: FormFieldProps) {
  const LabelComponent = htmlFor ? 'label' : 'div'

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <LabelComponent
          {...(htmlFor ? { htmlFor } : {})}
          className="text-sm font-medium leading-none text-foreground"
        >
          {label}
        </LabelComponent>
        {labelSecondary ? (
          <div className="text-sm text-muted-foreground">
            {labelSecondary}
          </div>
        ) : null}
      </div>

      {children}

      {description ? (
        <p className="text-sm text-muted-foreground">
          {description}
        </p>
      ) : null}

      {error ? (
        <p className="text-sm font-medium text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  )
}
