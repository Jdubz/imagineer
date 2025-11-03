import React, { useState, useEffect, useCallback } from 'react'
import { Loader2, RotateCw, Palette, CheckCircle2, Info } from 'lucide-react'
import { logger } from '../lib/logger'
import { api } from '../lib/api'
import { formatErrorMessage, isAuthError } from '../lib/errorUtils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface LoraModel {
  folder: string
  filename: string
  format?: string
  default_weight?: number
  has_preview?: boolean
  organized_at?: string
}

const LorasTab: React.FC = () => {
  const [loras, setLoras] = useState<LoraModel[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedLora, setSelectedLora] = useState<LoraModel | null>(null)

  const fetchLoras = useCallback(async (): Promise<void> => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.loras.getAll()
      setLoras(data || [])
    } catch (err) {
      if (isAuthError(err)) {
        logger.warn('LoRA catalogue requires admin authentication')
        setError('Admin authentication required to view available LoRAs.')
        return
      }
      logger.error('Failed to fetch LoRAs:', err)
      const errorMessage = formatErrorMessage(err, 'Failed to fetch LoRAs')
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchLoras()
  }, [fetchLoras])

  const handleLoraClick = (lora: LoraModel): void => {
    setSelectedLora(selectedLora?.folder === lora.folder ? null : lora)
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center justify-center gap-4 py-12">
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
            <p className="text-muted-foreground">Loading LoRAs...</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center justify-center gap-4 py-12">
            <p className="text-destructive flex items-center gap-2">
              <Info className="h-5 w-5" />
              {error}
            </p>
            <Button onClick={fetchLoras} variant="outline">
              <RotateCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Palette className="h-5 w-5" />
            LoRA Models
          </CardTitle>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{loras.length} models</span>
            <Button onClick={fetchLoras} variant="ghost" size="icon" title="Refresh">
              <RotateCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loras.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            <p>No LoRAs found. Add .safetensors files to the LoRA directory.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {loras.map((lora) => (
              <div
                key={lora.folder}
                className={`rounded-lg border-2 transition-all cursor-pointer overflow-hidden ${
                  selectedLora?.folder === lora.folder
                    ? 'border-primary shadow-lg'
                    : 'border-transparent bg-card hover:border-primary/50 hover:shadow-md'
                }`}
                onClick={() => handleLoraClick(lora)}
              >
                <div className="p-5 flex items-start gap-4">
                  {lora.has_preview ? (
                    <div className="w-20 h-20 rounded-md overflow-hidden flex-shrink-0 bg-muted">
                      <img
                        src={`/api/loras/${lora.folder}/preview`}
                        alt={lora.filename}
                        loading="lazy"
                        className="w-full h-full object-cover"
                      />
                    </div>
                  ) : (
                    <div className="w-20 h-20 rounded-md bg-muted flex items-center justify-center flex-shrink-0">
                      <Palette className="h-8 w-8 text-muted-foreground" />
                    </div>
                  )}

                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-lg mb-1 truncate" title={lora.filename}>
                      {lora.folder.replace(/_/g, ' ')}
                    </h3>
                    <div className="mb-2">
                      <code className="text-xs bg-muted px-2 py-1 rounded font-mono break-all">
                        {lora.filename}
                      </code>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="secondary">{lora.format || 'SD1.5'}</Badge>
                      {lora.default_weight && (
                        <Badge variant="outline">Weight: {lora.default_weight}</Badge>
                      )}
                      {lora.has_preview && (
                        <Badge variant="default" className="gap-1">
                          <CheckCircle2 className="h-3 w-3" />
                          Preview
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>

                {selectedLora?.folder === lora.folder && (
                  <div className="px-5 pb-5 pt-2 border-t bg-muted/50">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="text-muted-foreground">Filename:</span>
                        <span className="ml-2 font-medium">{lora.filename}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Folder:</span>
                        <span className="ml-2 font-medium">{lora.folder}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Format:</span>
                        <span className="ml-2 font-medium">{lora.format || 'SD1.5'}</span>
                      </div>
                      {lora.default_weight && (
                        <div>
                          <span className="text-muted-foreground">Default Weight:</span>
                          <span className="ml-2 font-medium">{lora.default_weight}</span>
                        </div>
                      )}
                      {lora.organized_at && (
                        <div className="md:col-span-2">
                          <span className="text-muted-foreground">Organized:</span>
                          <span className="ml-2 font-medium">
                            {new Date(lora.organized_at).toLocaleString()}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default LorasTab
