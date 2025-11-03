import React from 'react'
import { Loader2 } from 'lucide-react'
import GenerateForm from './GenerateForm'
import { useGeneration } from '../contexts/AppContext'
import { Card, CardContent } from './ui/card'

interface GenerateTabProps {
  isAdmin: boolean
}

const GenerateTab: React.FC<GenerateTabProps> = ({ isAdmin }) => {
  const { config, loading, queuePosition, handleGenerate } = useGeneration()
  return (
    <div className="flex flex-col gap-8">
      {loading && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col items-center justify-center gap-4 py-8" role="status" aria-live="polite" aria-atomic="true">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <p className="text-muted-foreground">
                Generating image...
                {queuePosition !== null && queuePosition > 0 && (
                  <span className="ml-1">(Queue position: {queuePosition})</span>
                )}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {!loading && (
        <GenerateForm
          onGenerate={handleGenerate}
          loading={loading}
          config={config}
          isAdmin={isAdmin}
        />
      )}
    </div>
  )
}

export default GenerateTab
