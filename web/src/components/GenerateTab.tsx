import React from 'react'
import GenerateForm from './GenerateForm'
import type { Config, GenerateParams, BatchGenerateParams, Job } from '../types/models'

interface GenerateTabProps {
  config: Config | null
  loading: boolean
  queuePosition: number | null
  currentJob: Job | null
  onGenerate: (params: GenerateParams) => Promise<void>
  onGenerateBatch: (params: BatchGenerateParams) => Promise<void>
  isAdmin: boolean
}

const GenerateTab: React.FC<GenerateTabProps> = ({
  config,
  loading,
  queuePosition,
  onGenerate,
  onGenerateBatch,
  isAdmin,
}) => {
  return (
    <div className="generate-tab">
      {loading && (
        <div className="loading-indicator">
          <div className="spinner"></div>
          <p>
            Generating image...
            {queuePosition !== null && queuePosition > 0 && (
              <span> (Queue position: {queuePosition})</span>
            )}
          </p>
        </div>
      )}

      {!loading && (
        <GenerateForm
          onGenerate={onGenerate}
          onGenerateBatch={onGenerateBatch}
          loading={loading}
          config={config}
          isAdmin={isAdmin}
        />
      )}
    </div>
  )
}

export default GenerateTab
